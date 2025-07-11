import asyncio
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

from .exchanges.base import BaseExchange, Order, OrderSide, OrderType, OrderStatus
from .database import Database, TradeRecord, OrderRecord, BalanceRecord
from .strategy import ArbitrageSignal
from .config import Config

logger = logging.getLogger(__name__)


class TradeStatus(Enum):
    PENDING = "pending"
    PARTIALLY_FILLED = "partially_filled"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ActiveTrade:
    id: int
    signal: ArbitrageSignal
    buy_order: Optional[Order] = None
    sell_order: Optional[Order] = None
    status: TradeStatus = TradeStatus.PENDING
    start_time: float = 0.0
    end_time: Optional[float] = None
    actual_profit: float = 0.0
    error_message: Optional[str] = None


class LiveTrader:
    def __init__(self, config: Config, database: Database):
        self.config = config
        self.database = database
        self.exchanges: Dict[str, BaseExchange] = {}
        self.active_trades: Dict[int, ActiveTrade] = {}
        self.trade_counter = 0
        self.is_running = False
        self.balances: Dict[str, Dict[str, float]] = {}
        self.max_concurrent_trades = config.risk_management.max_concurrent_trades
        
        # Performance tracking
        self.total_trades = 0
        self.successful_trades = 0
        self.failed_trades = 0
        self.total_profit = 0.0
        self.total_volume = 0.0
        
        # Risk management
        self.initial_balances: Dict[str, Dict[str, float]] = {}
        self.max_drawdown = 0.0
        self.current_drawdown = 0.0
        
        # Trade monitoring
        self._monitor_task: Optional[asyncio.Task] = None
        self._balance_task: Optional[asyncio.Task] = None
    
    async def initialize(self, exchanges: Dict[str, BaseExchange]) -> None:
        """Initialize trader with exchanges"""
        self.exchanges = exchanges
        
        # Get initial balances
        await self._update_balances()
        self.initial_balances = self.balances.copy()
        
        # Set up order update callbacks
        for exchange in exchanges.values():
            exchange.on_order_update(self._on_order_update)
        
        logger.info("Live trader initialized")
    
    async def start(self) -> None:
        """Start the live trader"""
        self.is_running = True
        
        # Start monitoring tasks
        self._monitor_task = asyncio.create_task(self._monitor_trades())
        self._balance_task = asyncio.create_task(self._balance_monitor())
        
        logger.info("Live trader started")
    
    async def stop(self) -> None:
        """Stop the live trader"""
        self.is_running = False
        
        # Cancel monitoring tasks
        if self._monitor_task:
            self._monitor_task.cancel()
        if self._balance_task:
            self._balance_task.cancel()
        
        # Cancel all active trades
        for trade in self.active_trades.values():
            await self._cancel_trade(trade)
        
        logger.info("Live trader stopped")
    
    async def execute_arbitrage(self, signal: ArbitrageSignal) -> bool:
        """Execute an arbitrage trade"""
        if not self.is_running:
            return False
        
        # Check if we can execute more trades
        if len(self.active_trades) >= self.max_concurrent_trades:
            logger.warning("Max concurrent trades reached, skipping trade")
            return False
        
        # Risk management checks
        if not await self._risk_checks(signal):
            return False
        
        # Create trade record
        self.trade_counter += 1
        trade_id = self.trade_counter
        
        trade = ActiveTrade(
            id=trade_id,
            signal=signal,
            status=TradeStatus.PENDING,
            start_time=time.time()
        )
        
        self.active_trades[trade_id] = trade
        
        logger.info(f"Executing arbitrage trade {trade_id}: {signal.symbol} "
                   f"Buy {signal.buy_exchange} @ {signal.buy_price:.6f} "
                   f"Sell {signal.sell_exchange} @ {signal.sell_price:.6f}")
        
        # Execute trade
        success = await self._execute_trade(trade)
        
        if success:
            self.total_trades += 1
            logger.info(f"Trade {trade_id} initiated successfully")
        else:
            # Remove failed trade
            del self.active_trades[trade_id]
            logger.error(f"Trade {trade_id} failed to initiate")
        
        return success
    
    async def _execute_trade(self, trade: ActiveTrade) -> bool:
        """Execute the actual trade orders"""
        try:
            signal = trade.signal
            
            # Calculate trade size
            trade_size = self._calculate_trade_size(signal)
            if trade_size <= 0:
                trade.error_message = "Invalid trade size"
                return False
            
            # Get exchanges
            buy_exchange = self.exchanges.get(signal.buy_exchange)
            sell_exchange = self.exchanges.get(signal.sell_exchange)
            
            if not buy_exchange or not sell_exchange:
                trade.error_message = "Exchange not available"
                return False
            
            # Place buy order
            try:
                trade.buy_order = await buy_exchange.place_order(
                    symbol=signal.symbol,
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity=trade_size
                )
                
                # Store order in database
                await self._store_order(trade.buy_order, signal.buy_exchange)
                
            except Exception as e:
                trade.error_message = f"Failed to place buy order: {e}"
                logger.error(f"Failed to place buy order for trade {trade.id}: {e}")
                return False
            
            # Place sell order
            try:
                trade.sell_order = await sell_exchange.place_order(
                    symbol=signal.symbol,
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=trade_size
                )
                
                # Store order in database
                await self._store_order(trade.sell_order, signal.sell_exchange)
                
            except Exception as e:
                trade.error_message = f"Failed to place sell order: {e}"
                logger.error(f"Failed to place sell order for trade {trade.id}: {e}")
                
                # Try to cancel buy order if sell order fails
                if trade.buy_order:
                    try:
                        await buy_exchange.cancel_order(trade.buy_order.order_id, signal.symbol)
                    except Exception as cancel_e:
                        logger.error(f"Failed to cancel buy order: {cancel_e}")
                
                return False
            
            # Store trade in database
            await self._store_trade(trade)
            
            return True
            
        except Exception as e:
            trade.error_message = f"Trade execution error: {e}"
            logger.error(f"Trade execution error for trade {trade.id}: {e}")
            return False
    
    async def _store_order(self, order: Order, exchange: str) -> None:
        """Store order in database"""
        order_record = OrderRecord(
            exchange=exchange,
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side.value,
            order_type=order.type.value,
            quantity=order.quantity,
            price=order.price,
            status=order.status.value,
            filled_quantity=order.filled_quantity,
            average_price=order.average_price,
            timestamp=order.timestamp or time.time()
        )
        
        await self.database.insert_order(order_record)
    
    async def _store_trade(self, trade: ActiveTrade) -> None:
        """Store trade in database"""
        trade_record = TradeRecord(
            symbol=trade.signal.symbol,
            buy_exchange=trade.signal.buy_exchange,
            sell_exchange=trade.signal.sell_exchange,
            buy_price=trade.signal.buy_price,
            sell_price=trade.signal.sell_price,
            quantity=trade.buy_order.quantity if trade.buy_order else 0,
            profit=trade.signal.profit,
            profit_percent=trade.signal.profit_percent,
            buy_order_id=trade.buy_order.order_id if trade.buy_order else None,
            sell_order_id=trade.sell_order.order_id if trade.sell_order else None,
            status=trade.status.value,
            timestamp=trade.start_time
        )
        
        trade.id = await self.database.insert_trade(trade_record)
    
    def _calculate_trade_size(self, signal: ArbitrageSignal) -> float:
        """Calculate appropriate trade size"""
        # Get available balance
        base_asset = signal.symbol.replace('USDT', '').replace('USDC', '')
        quote_asset = 'USDT' if 'USDT' in signal.symbol else 'USDC'
        
        # Check balances on both exchanges
        buy_balance = self.balances.get(signal.buy_exchange, {}).get(quote_asset, 0)
        sell_balance = self.balances.get(signal.sell_exchange, {}).get(base_asset, 0)
        
        # Calculate max trade size based on balances
        max_buy_size = buy_balance / signal.buy_price
        max_sell_size = sell_balance
        
        # Use configured trade amount
        desired_size = self.config.arbitrage.trade_amount_usd / signal.buy_price
        
        # Consider available sizes from ticker
        max_size = min(max_buy_size, max_sell_size, signal.buy_size, signal.sell_size, desired_size)
        
        # Apply position size limits
        if max_size * signal.buy_price > self.config.arbitrage.max_position_size:
            max_size = self.config.arbitrage.max_position_size / signal.buy_price
        
        return max(0, max_size)
    
    async def _risk_checks(self, signal: ArbitrageSignal) -> bool:
        """Perform risk management checks"""
        
        # Check minimum profit threshold
        if signal.profit_percent < self.config.arbitrage.min_profit_threshold:
            logger.warning(f"Signal profit {signal.profit_percent:.4f}% below threshold")
            return False
        
        # Check balance thresholds
        required_balance = self.config.arbitrage.trade_amount_usd
        
        # Check buy exchange balance
        quote_asset = 'USDT' if 'USDT' in signal.symbol else 'USDC'
        buy_balance = self.balances.get(signal.buy_exchange, {}).get(quote_asset, 0)
        
        if buy_balance < required_balance:
            logger.warning(f"Insufficient balance on {signal.buy_exchange}: {buy_balance}")
            return False
        
        # Check sell exchange balance
        base_asset = signal.symbol.replace('USDT', '').replace('USDC', '')
        sell_balance = self.balances.get(signal.sell_exchange, {}).get(base_asset, 0)
        required_base = required_balance / signal.sell_price
        
        if sell_balance < required_base:
            logger.warning(f"Insufficient {base_asset} balance on {signal.sell_exchange}: {sell_balance}")
            return False
        
        # Check drawdown limits
        if self.current_drawdown > self.config.risk_management.max_drawdown_percent:
            logger.warning(f"Max drawdown exceeded: {self.current_drawdown:.2f}%")
            return False
        
        # Check signal age
        if time.time() - signal.timestamp > self.config.arbitrage.max_spread_age_seconds:
            logger.warning("Signal too old")
            return False
        
        return True
    
    async def _monitor_trades(self) -> None:
        """Monitor active trades"""
        while self.is_running:
            try:
                await asyncio.sleep(1)  # Check every second
                
                completed_trades = []
                
                for trade_id, trade in self.active_trades.items():
                    await self._update_trade_status(trade)
                    
                    # Check for timeout
                    if time.time() - trade.start_time > 300:  # 5 minutes timeout
                        logger.warning(f"Trade {trade_id} timed out")
                        await self._cancel_trade(trade)
                        completed_trades.append(trade_id)
                    
                    # Check if trade is completed
                    elif trade.status in [TradeStatus.COMPLETED, TradeStatus.FAILED, TradeStatus.CANCELLED]:
                        completed_trades.append(trade_id)
                        await self._finalize_trade(trade)
                
                # Remove completed trades
                for trade_id in completed_trades:
                    del self.active_trades[trade_id]
                
            except Exception as e:
                logger.error(f"Error in trade monitor: {e}")
    
    async def _update_trade_status(self, trade: ActiveTrade) -> None:
        """Update trade status based on order statuses"""
        try:
            # Update buy order status
            if trade.buy_order:
                buy_exchange = self.exchanges[trade.signal.buy_exchange]
                updated_buy_order = await buy_exchange.get_order_status(
                    trade.buy_order.order_id, trade.signal.symbol
                )
                trade.buy_order = updated_buy_order
            
            # Update sell order status
            if trade.sell_order:
                sell_exchange = self.exchanges[trade.signal.sell_exchange]
                updated_sell_order = await sell_exchange.get_order_status(
                    trade.sell_order.order_id, trade.signal.symbol
                )
                trade.sell_order = updated_sell_order
            
            # Determine overall trade status
            if trade.buy_order and trade.sell_order:
                buy_filled = trade.buy_order.status == OrderStatus.FILLED
                sell_filled = trade.sell_order.status == OrderStatus.FILLED
                
                if buy_filled and sell_filled:
                    trade.status = TradeStatus.COMPLETED
                    trade.end_time = time.time()
                    
                    # Calculate actual profit
                    actual_buy_price = trade.buy_order.average_price or trade.buy_order.price
                    actual_sell_price = trade.sell_order.average_price or trade.sell_order.price
                    
                    if actual_buy_price and actual_sell_price:
                        trade.actual_profit = (actual_sell_price - actual_buy_price) * trade.buy_order.filled_quantity
                
                elif (trade.buy_order.status == OrderStatus.REJECTED or 
                      trade.sell_order.status == OrderStatus.REJECTED):
                    trade.status = TradeStatus.FAILED
                    trade.end_time = time.time()
        
        except Exception as e:
            logger.error(f"Error updating trade status: {e}")
    
    async def _cancel_trade(self, trade: ActiveTrade) -> None:
        """Cancel an active trade"""
        try:
            # Cancel buy order
            if trade.buy_order and trade.buy_order.status == OrderStatus.NEW:
                buy_exchange = self.exchanges[trade.signal.buy_exchange]
                await buy_exchange.cancel_order(trade.buy_order.order_id, trade.signal.symbol)
            
            # Cancel sell order
            if trade.sell_order and trade.sell_order.status == OrderStatus.NEW:
                sell_exchange = self.exchanges[trade.signal.sell_exchange]
                await sell_exchange.cancel_order(trade.sell_order.order_id, trade.signal.symbol)
            
            trade.status = TradeStatus.CANCELLED
            trade.end_time = time.time()
            
        except Exception as e:
            logger.error(f"Error cancelling trade: {e}")
    
    async def _finalize_trade(self, trade: ActiveTrade) -> None:
        """Finalize completed trade"""
        try:
            # Update trade status in database
            await self.database.update_trade_status(
                trade.id, 
                trade.status.value,
                trade.buy_order.order_id if trade.buy_order else None,
                trade.sell_order.order_id if trade.sell_order else None
            )
            
            # Update statistics
            if trade.status == TradeStatus.COMPLETED:
                self.successful_trades += 1
                self.total_profit += trade.actual_profit
                self.total_volume += trade.buy_order.filled_quantity * trade.buy_order.average_price
            else:
                self.failed_trades += 1
            
            logger.info(f"Trade {trade.id} finalized: {trade.status.value}")
            
        except Exception as e:
            logger.error(f"Error finalizing trade: {e}")
    
    async def _update_balances(self) -> None:
        """Update balances from all exchanges"""
        try:
            for exchange_name, exchange in self.exchanges.items():
                balances = await exchange.get_balance()
                
                # Store balances
                self.balances[exchange_name] = {}
                for asset, balance in balances.items():
                    self.balances[exchange_name][asset] = balance.free
                    
                    # Store in database
                    balance_record = BalanceRecord(
                        exchange=exchange_name,
                        asset=asset,
                        free=balance.free,
                        locked=balance.locked,
                        total=balance.total,
                        timestamp=time.time()
                    )
                    await self.database.insert_balance(balance_record)
                
        except Exception as e:
            logger.error(f"Error updating balances: {e}")
    
    async def _balance_monitor(self) -> None:
        """Monitor balances and calculate drawdown"""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Update every minute
                await self._update_balances()
                
                # Calculate current portfolio value
                current_value = self._calculate_portfolio_value()
                initial_value = self._calculate_initial_portfolio_value()
                
                if initial_value > 0:
                    self.current_drawdown = max(0, (initial_value - current_value) / initial_value * 100)
                    self.max_drawdown = max(self.max_drawdown, self.current_drawdown)
                
                # Check balance thresholds
                if current_value < initial_value * (1 - self.config.risk_management.balance_threshold_percent / 100):
                    logger.warning(f"Balance below threshold: {current_value:.2f} < {initial_value * (1 - self.config.risk_management.balance_threshold_percent / 100):.2f}")
                    
            except Exception as e:
                logger.error(f"Error in balance monitor: {e}")
    
    def _calculate_portfolio_value(self) -> float:
        """Calculate current portfolio value in USD"""
        total_value = 0
        for exchange_name, exchange_balances in self.balances.items():
            for asset, balance in exchange_balances.items():
                if asset in ['USDT', 'USDC', 'USD']:
                    total_value += balance
                # For other assets, we'd need price data to convert to USD
                # This is simplified for now
        return total_value
    
    def _calculate_initial_portfolio_value(self) -> float:
        """Calculate initial portfolio value in USD"""
        total_value = 0
        for exchange_name, exchange_balances in self.initial_balances.items():
            for asset, balance in exchange_balances.items():
                if asset in ['USDT', 'USDC', 'USD']:
                    total_value += balance
        return total_value
    
    async def _on_order_update(self, order: Order) -> None:
        """Handle order updates from exchanges"""
        try:
            # Find the trade this order belongs to
            for trade in self.active_trades.values():
                if ((trade.buy_order and trade.buy_order.order_id == order.order_id) or
                    (trade.sell_order and trade.sell_order.order_id == order.order_id)):
                    
                    # Update order status in database
                    exchange = trade.signal.buy_exchange if (trade.buy_order and trade.buy_order.order_id == order.order_id) else trade.signal.sell_exchange
                    await self.database.update_order_status(
                        order.order_id, exchange, order.status.value, 
                        order.filled_quantity, order.average_price
                    )
                    break
                    
        except Exception as e:
            logger.error(f"Error handling order update: {e}")
    
    def get_stats(self) -> Dict[str, any]:
        """Get trader statistics"""
        return {
            'total_trades': self.total_trades,
            'successful_trades': self.successful_trades,
            'failed_trades': self.failed_trades,
            'success_rate': (self.successful_trades / self.total_trades * 100) if self.total_trades > 0 else 0,
            'total_profit': self.total_profit,
            'total_volume': self.total_volume,
            'active_trades': len(self.active_trades),
            'max_drawdown': self.max_drawdown,
            'current_drawdown': self.current_drawdown,
            'portfolio_value': self._calculate_portfolio_value()
        }
    
    def get_active_trades(self) -> List[ActiveTrade]:
        """Get list of active trades"""
        return list(self.active_trades.values())