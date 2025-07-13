import asyncio
import time
import uuid
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

from .exchanges.base import Order, OrderSide, OrderType, OrderStatus
from .database import Database, TradeRecord, OrderRecord
from .strategy import ArbitrageSignal
from .config import Config

logger = logging.getLogger(__name__)


@dataclass
class SimulatedOrder:
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.NEW
    filled_quantity: float = 0.0
    average_price: Optional[float] = None
    timestamp: float = field(default_factory=time.time)
    fill_time: Optional[float] = None
    exchange: str = ""


@dataclass
class SimulatedBalance:
    asset: str
    free: float
    locked: float
    
    @property
    def total(self) -> float:
        return self.free + self.locked


@dataclass
class SimulatedTrade:
    id: int
    signal: ArbitrageSignal
    buy_order: Optional[SimulatedOrder] = None
    sell_order: Optional[SimulatedOrder] = None
    status: str = "pending"
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    actual_profit: float = 0.0
    fees_paid: float = 0.0


class TradingSimulator:
    def __init__(self, config: Config, database: Database):
        self.config = config
        self.database = database
        self.balances: Dict[str, Dict[str, SimulatedBalance]] = {}
        self.orders: Dict[str, SimulatedOrder] = {}
        self.active_trades: Dict[int, SimulatedTrade] = {}
        self.completed_trades: List[SimulatedTrade] = []
        self.trade_counter = 0
        self.is_running = False
        
        # Exchange fees (simulated)
        self.exchange_fees = {
            'binance': {'maker': 0.001, 'taker': 0.001},
            'bybit': {'maker': 0.001, 'taker': 0.001},
            'okx': {'maker': 0.0008, 'taker': 0.001},
            'bitget': {'maker': 0.001, 'taker': 0.001}
        }
        
        # Performance tracking
        self.total_trades = 0
        self.successful_trades = 0
        self.failed_trades = 0
        self.total_profit = 0.0
        self.total_fees = 0.0
        self.total_volume = 0.0
        self.max_drawdown = 0.0
        self.current_drawdown = 0.0
        self.initial_portfolio_value = 0.0
        
        # Simulation parameters
        self.slippage_percent = config.arbitrage.slippage_tolerance
        self.fill_delay_seconds = 2.0  # Simulated order fill delay
        self.partial_fill_probability = 0.1  # 10% chance of partial fill
        self.order_reject_probability = 0.05  # 5% chance of order rejection
        
        # Initialize balances
        self._initialize_balances()
    
    def _initialize_balances(self) -> None:
        """Initialize simulated balances for all exchanges"""
        initial_balance_usd = 10000.0  # $10,000 per exchange
        
        for exchange_name in self.config.get_enabled_exchanges():
            self.balances[exchange_name] = {}
            
            # Add USDT balance
            self.balances[exchange_name]['USDT'] = SimulatedBalance(
                asset='USDT',
                free=initial_balance_usd,
                locked=0.0
            )
            
            # Add some crypto balances
            crypto_assets = ['BTC', 'ETH', 'BNB', 'ADA', 'DOT']
            for asset in crypto_assets:
                # Simulate having some crypto (worth about $1000 each)
                if asset == 'BTC':
                    amount = 1000.0 / 50000.0  # Assume BTC = $50,000
                elif asset == 'ETH':
                    amount = 1000.0 / 3000.0   # Assume ETH = $3,000
                else:
                    amount = 1000.0 / 1.0      # Assume other coins = $1
                
                self.balances[exchange_name][asset] = SimulatedBalance(
                    asset=asset,
                    free=amount,
                    locked=0.0
                )
        
        self.initial_portfolio_value = self._calculate_portfolio_value()
        logger.info(f"Initialized simulator with ${self.initial_portfolio_value:,.2f} portfolio value")
    
    async def start(self) -> None:
        """Start the trading simulator"""
        self.is_running = True
        
        # Start order processing task
        asyncio.create_task(self._process_orders())
        
        logger.info("Trading simulator started")
    
    async def stop(self) -> None:
        """Stop the trading simulator"""
        self.is_running = False
        logger.info("Trading simulator stopped")
    
    async def execute_arbitrage(self, signal: ArbitrageSignal) -> bool:
        """Execute simulated arbitrage trade"""
        if not self.is_running:
            return False
        
        # Risk checks
        if not self._can_execute_trade(signal):
            return False
        
        # Create trade
        self.trade_counter += 1
        trade = SimulatedTrade(
            id=self.trade_counter,
            signal=signal
        )
        
        # Calculate trade size
        trade_size = self._calculate_trade_size(signal)
        if trade_size <= 0:
            logger.warning(f"Cannot execute trade: insufficient size {trade_size}")
            return False
        
        # Place buy order
        trade.buy_order = self._place_simulated_order(
            exchange=signal.buy_exchange,
            symbol=signal.symbol,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=trade_size,
            price=signal.buy_price
        )
        
        # Place sell order
        trade.sell_order = self._place_simulated_order(
            exchange=signal.sell_exchange,
            symbol=signal.symbol,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=trade_size,
            price=signal.sell_price
        )
        
        # Check if both orders were placed successfully
        if not trade.buy_order or not trade.sell_order:
            logger.error("Failed to place orders")
            return False
        
        # Reserve balances
        if not self._reserve_balances(trade):
            logger.error("Failed to reserve balances")
            return False
        
        # Add to active trades
        self.active_trades[trade.id] = trade
        self.total_trades += 1
        
        # Store trade in database
        await self._store_trade(trade)
        
        logger.info(f"Simulated trade {trade.id} initiated: {signal.symbol} "
                   f"Buy {signal.buy_exchange} @ {signal.buy_price:.6f} "
                   f"Sell {signal.sell_exchange} @ {signal.sell_price:.6f} "
                   f"Size: {trade_size:.6f}")
        
        return True
    
    def _place_simulated_order(self, exchange: str, symbol: str, side: OrderSide, 
                             order_type: OrderType, quantity: float, price: float) -> Optional[SimulatedOrder]:
        """Place a simulated order"""
        
        # Check for order rejection
        if self._should_reject_order():
            logger.warning(f"Order rejected: {exchange} {symbol} {side.value} {quantity}")
            return None
        
        # Create order
        order = SimulatedOrder(
            order_id=str(uuid.uuid4()),
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            exchange=exchange,
            status=OrderStatus.NEW
        )
        
        # Add to orders
        self.orders[order.order_id] = order
        
        return order
    
    def _reserve_balances(self, trade: SimulatedTrade) -> bool:
        """Reserve balances for trade execution"""
        try:
            # Reserve for buy order
            if trade.buy_order:
                quote_asset = 'USDT' if 'USDT' in trade.signal.symbol else 'USDC'
                required_amount = trade.buy_order.quantity * trade.buy_order.price
                
                exchange_balance = self.balances[trade.signal.buy_exchange][quote_asset]
                if exchange_balance.free < required_amount:
                    return False
                
                exchange_balance.free -= required_amount
                exchange_balance.locked += required_amount
            
            # Reserve for sell order
            if trade.sell_order:
                base_asset = trade.signal.symbol.replace('USDT', '').replace('USDC', '')
                required_amount = trade.sell_order.quantity
                
                exchange_balance = self.balances[trade.signal.sell_exchange][base_asset]
                if exchange_balance.free < required_amount:
                    return False
                
                exchange_balance.free -= required_amount
                exchange_balance.locked += required_amount
            
            return True
            
        except Exception as e:
            logger.error(f"Error reserving balances: {e}")
            return False
    
    async def _process_orders(self) -> None:
        """Process simulated orders"""
        while self.is_running:
            try:
                await asyncio.sleep(0.1)  # Check every 100ms
                
                # Process pending orders
                for order in list(self.orders.values()):
                    if order.status == OrderStatus.NEW:
                        await self._process_order(order)
                
                # Check completed trades
                completed_trade_ids = []
                for trade_id, trade in self.active_trades.items():
                    if self._is_trade_completed(trade):
                        await self._complete_trade(trade)
                        completed_trade_ids.append(trade_id)
                
                # Remove completed trades
                for trade_id in completed_trade_ids:
                    self.completed_trades.append(self.active_trades[trade_id])
                    del self.active_trades[trade_id]
                
            except Exception as e:
                logger.error(f"Error processing orders: {e}")
    
    async def _process_order(self, order: SimulatedOrder) -> None:
        """Process a single simulated order"""
        try:
            # Check if order should be filled
            if time.time() - order.timestamp < self.fill_delay_seconds:
                return
            
            # Simulate order filling
            if self._should_fill_order(order):
                await self._fill_order(order)
            
        except Exception as e:
            logger.error(f"Error processing order {order.order_id}: {e}")
    
    def _should_fill_order(self, order: SimulatedOrder) -> bool:
        """Determine if order should be filled"""
        # For market orders, always fill after delay
        if order.order_type == OrderType.MARKET:
            return True
        
        # For limit orders, check if price would be hit
        # This is simplified - in reality, we'd need market data
        return True
    
    async def _fill_order(self, order: SimulatedOrder) -> None:
        """Fill a simulated order"""
        try:
            # Apply slippage
            if order.side == OrderSide.BUY:
                fill_price = order.price * (1 + self.slippage_percent)
            else:
                fill_price = order.price * (1 - self.slippage_percent)
            
            # Determine fill quantity
            if self._should_partial_fill():
                fill_quantity = order.quantity * 0.7  # 70% fill
                order.status = OrderStatus.PARTIALLY_FILLED
            else:
                fill_quantity = order.quantity
                order.status = OrderStatus.FILLED
            
            order.filled_quantity = fill_quantity
            order.average_price = fill_price
            order.fill_time = time.time()
            
            # Update balances
            self._update_balances_after_fill(order)
            
            # Store order in database
            await self._store_order(order)
            
            logger.debug(f"Order filled: {order.order_id} {order.symbol} "
                        f"{order.side.value} {fill_quantity:.6f} @ {fill_price:.6f}")
            
        except Exception as e:
            logger.error(f"Error filling order {order.order_id}: {e}")
    
    def _update_balances_after_fill(self, order: SimulatedOrder) -> None:
        """Update balances after order fill"""
        try:
            exchange_balances = self.balances[order.exchange]
            
            if order.side == OrderSide.BUY:
                # Buying crypto with USDT
                quote_asset = 'USDT' if 'USDT' in order.symbol else 'USDC'
                base_asset = order.symbol.replace('USDT', '').replace('USDC', '')
                
                cost = order.filled_quantity * order.average_price
                fee = cost * self.exchange_fees[order.exchange]['taker']
                
                # Reduce quote balance
                exchange_balances[quote_asset].locked -= cost
                
                # Add base balance
                if base_asset not in exchange_balances:
                    exchange_balances[base_asset] = SimulatedBalance(base_asset, 0.0, 0.0)
                
                exchange_balances[base_asset].free += order.filled_quantity
                
                # Deduct fee
                exchange_balances[quote_asset].free -= fee
                self.total_fees += fee
                
            else:
                # Selling crypto for USDT
                base_asset = order.symbol.replace('USDT', '').replace('USDC', '')
                quote_asset = 'USDT' if 'USDT' in order.symbol else 'USDC'
                
                proceeds = order.filled_quantity * order.average_price
                fee = proceeds * self.exchange_fees[order.exchange]['taker']
                
                # Reduce base balance
                exchange_balances[base_asset].locked -= order.filled_quantity
                
                # Add quote balance
                if quote_asset not in exchange_balances:
                    exchange_balances[quote_asset] = SimulatedBalance(quote_asset, 0.0, 0.0)
                
                exchange_balances[quote_asset].free += proceeds - fee
                self.total_fees += fee
            
        except Exception as e:
            logger.error(f"Error updating balances for order {order.order_id}: {e}")
    
    def _is_trade_completed(self, trade: SimulatedTrade) -> bool:
        """Check if trade is completed"""
        buy_completed = (trade.buy_order and 
                        trade.buy_order.status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED])
        sell_completed = (trade.sell_order and 
                         trade.sell_order.status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED])
        
        return buy_completed and sell_completed
    
    async def _complete_trade(self, trade: SimulatedTrade) -> None:
        """Complete a simulated trade"""
        try:
            trade.status = "completed"
            trade.end_time = time.time()
            
            # Calculate actual profit
            if trade.buy_order and trade.sell_order:
                buy_cost = trade.buy_order.filled_quantity * trade.buy_order.average_price
                sell_proceeds = trade.sell_order.filled_quantity * trade.sell_order.average_price
                
                # Calculate fees
                buy_fee = buy_cost * self.exchange_fees[trade.signal.buy_exchange]['taker']
                sell_fee = sell_proceeds * self.exchange_fees[trade.signal.sell_exchange]['taker']
                trade.fees_paid = buy_fee + sell_fee
                
                # Net profit
                trade.actual_profit = sell_proceeds - buy_cost - trade.fees_paid
                
                self.total_profit += trade.actual_profit
                self.total_volume += buy_cost
                
                if trade.actual_profit > 0:
                    self.successful_trades += 1
                else:
                    self.failed_trades += 1
            
            # Update trade in database
            await self.database.update_trade_status(
                trade.id,
                trade.status,
                trade.buy_order.order_id if trade.buy_order else None,
                trade.sell_order.order_id if trade.sell_order else None
            )
            
            # Update drawdown
            self._update_drawdown()
            
            logger.info(f"Trade {trade.id} completed: Profit ${trade.actual_profit:.2f}")
            
        except Exception as e:
            logger.error(f"Error completing trade {trade.id}: {e}")
    
    def _update_drawdown(self) -> None:
        """Update drawdown calculations"""
        current_value = self._calculate_portfolio_value()
        drawdown = max(0, (self.initial_portfolio_value - current_value) / self.initial_portfolio_value * 100)
        
        self.current_drawdown = drawdown
        self.max_drawdown = max(self.max_drawdown, drawdown)
    
    def _calculate_portfolio_value(self) -> float:
        """Calculate current portfolio value"""
        total_value = 0.0
        
        for exchange_name, exchange_balances in self.balances.items():
            for asset, balance in exchange_balances.items():
                if asset in ['USDT', 'USDC']:
                    total_value += balance.total
                else:
                    # For crypto assets, estimate value
                    # This is simplified - in reality, we'd need current prices
                    if asset == 'BTC':
                        total_value += balance.total * 50000  # Assume BTC = $50,000
                    elif asset == 'ETH':
                        total_value += balance.total * 3000   # Assume ETH = $3,000
                    else:
                        total_value += balance.total * 1.0    # Assume other coins = $1
        
        return total_value
    
    def _calculate_trade_size(self, signal: ArbitrageSignal) -> float:
        """Calculate trade size for simulation"""
        # Use configured trade amount
        trade_amount_usd = self.config.arbitrage.trade_amount_usd
        
        # Convert to base asset quantity
        trade_size = trade_amount_usd / signal.buy_price
        
        # Check available balances
        quote_asset = 'USDT' if 'USDT' in signal.symbol else 'USDC'
        base_asset = signal.symbol.replace('USDT', '').replace('USDC', '')
        
        # Check buy exchange balance
        buy_balance = self.balances[signal.buy_exchange][quote_asset].free
        max_buy_size = buy_balance / signal.buy_price
        
        # Check sell exchange balance
        sell_balance = self.balances[signal.sell_exchange][base_asset].free
        
        # Use minimum of all constraints
        return min(trade_size, max_buy_size, sell_balance, signal.buy_size, signal.sell_size)
    
    def _can_execute_trade(self, signal: ArbitrageSignal) -> bool:
        """Check if trade can be executed"""
        # Check profit threshold
        if signal.profit_percent < self.config.arbitrage.min_profit_threshold:
            return False
        
        # Check if we have required balances
        trade_size = self._calculate_trade_size(signal)
        return trade_size > 0
    
    def _should_reject_order(self) -> bool:
        """Randomly reject orders based on probability"""
        import random
        return random.random() < self.order_reject_probability
    
    def _should_partial_fill(self) -> bool:
        """Randomly partial fill orders based on probability"""
        import random
        return random.random() < self.partial_fill_probability
    
    async def _store_trade(self, trade: SimulatedTrade) -> None:
        """Store simulated trade in database"""
        try:
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
                status=trade.status,
                timestamp=trade.start_time
            )
            
            trade.id = await self.database.insert_trade(trade_record)
            
        except Exception as e:
            logger.error(f"Error storing trade: {e}")
    
    async def _store_order(self, order: SimulatedOrder) -> None:
        """Store simulated order in database"""
        try:
            order_record = OrderRecord(
                exchange=order.exchange,
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side.value,
                order_type=order.order_type.value,
                quantity=order.quantity,
                price=order.price,
                status=order.status.value,
                filled_quantity=order.filled_quantity,
                average_price=order.average_price,
                timestamp=order.timestamp
            )
            
            await self.database.insert_order(order_record)
            
        except Exception as e:
            logger.error(f"Error storing order: {e}")
    
    def get_stats(self) -> Dict[str, any]:
        """Get simulator statistics"""
        return {
            'total_trades': self.total_trades,
            'successful_trades': self.successful_trades,
            'failed_trades': self.failed_trades,
            'success_rate': (self.successful_trades / self.total_trades * 100) if self.total_trades > 0 else 0,
            'total_profit': self.total_profit,
            'total_fees': self.total_fees,
            'net_profit': self.total_profit - self.total_fees,
            'total_volume': self.total_volume,
            'active_trades': len(self.active_trades),
            'max_drawdown': self.max_drawdown,
            'current_drawdown': self.current_drawdown,
            'portfolio_value': self._calculate_portfolio_value(),
            'profit_percent': ((self._calculate_portfolio_value() - self.initial_portfolio_value) / self.initial_portfolio_value * 100) if self.initial_portfolio_value > 0 else 0
        }
    
    def get_balances(self) -> Dict[str, Dict[str, SimulatedBalance]]:
        """Get current balances"""
        return self.balances
    
    def get_active_trades(self) -> List[SimulatedTrade]:
        """Get active trades"""
        return list(self.active_trades.values())
    
    def get_completed_trades(self) -> List[SimulatedTrade]:
        """Get completed trades"""
        return self.completed_trades
    
    def reset_portfolio(self) -> None:
        """Reset the simulator portfolio to initial state"""
        try:
            # Clear all active and completed trades
            self.active_trades.clear()
            self.completed_trades.clear()
            self.orders.clear()
            
            # Reset counters and statistics
            self.trade_counter = 0
            self.total_trades = 0
            self.successful_trades = 0
            self.failed_trades = 0
            self.total_profit = 0.0
            self.total_fees = 0.0
            self.total_volume = 0.0
            self.max_drawdown = 0.0
            self.current_drawdown = 0.0
            
            # Reinitialize balances to starting values
            self._initialize_balances()
            
            logger.info("Portfolio reset to initial state")
            
        except Exception as e:
            logger.error(f"Error resetting portfolio: {e}")
            raise