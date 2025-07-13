import asyncio
import time
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from collections import defaultdict, deque

from .exchanges.base import BaseExchange, Ticker, OrderSide
from .database import Database, ArbitrageOpportunity, TickerRecord
from .config import Config

logger = logging.getLogger(__name__)


@dataclass
class ArbitrageSignal:
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    profit: float
    profit_percent: float
    buy_size: float
    sell_size: float
    timestamp: float
    confidence: float = 1.0


@dataclass
class ExchangeData:
    exchange_name: str
    ticker: Ticker
    last_updated: float
    fees: Dict[str, float] = None


class ArbitrageStrategy:
    def __init__(self, config: Config, database: Database):
        self.config = config
        self.database = database
        self.exchange_data: Dict[str, Dict[str, ExchangeData]] = defaultdict(dict)
        self.recent_signals: deque = deque(maxlen=100)
        self.signal_callbacks: List[callable] = []
        self.is_running = False
        self.trade_cooldown: Dict[str, float] = {}
        self.exchange_fees: Dict[str, Dict[str, float]] = {}
        self._last_cleanup = time.time()
        
        # Performance tracking
        self.signals_generated = 0
        self.signals_executed = 0
        self.total_profit = 0.0
        
        # Symbol management
        self.active_symbols = self.config.arbitrage.symbols  # Default to config symbols
    
    def add_signal_callback(self, callback: callable) -> None:
        """Add callback for arbitrage signals"""
        self.signal_callbacks.append(callback)
    
    def set_active_symbols(self, symbols: List[str]) -> None:
        """Set the list of symbols to monitor for arbitrage opportunities"""
        self.active_symbols = symbols
        logger.info(f"Strategy updated to monitor {len(symbols)} symbols")
    
    async def initialize(self, exchanges: Dict[str, BaseExchange]) -> None:
        """Initialize strategy with exchanges"""
        logger.info("Initializing arbitrage strategy")
        
        # Store exchanges reference
        self.exchanges = exchanges
        
        logger.info("Trading fees will be loaded from config")
        
        # Set up ticker callbacks with exchange name closure
        for exchange_name, exchange in exchanges.items():
            # Create a closure to capture exchange name
            def create_ticker_callback(exchange_name):
                async def callback(ticker):
                    await self._on_ticker_update(ticker, exchange_name)
                return callback
            
            exchange.on_ticker(create_ticker_callback(exchange_name))
        
        logger.info("Arbitrage strategy initialized")
    
    async def get_trading_fees(self, exchange_name: str, symbol: str) -> Dict[str, float]:
        """Get trading fees from config for exchange and symbol"""
        # Get fees from exchange config
        exchange_config = self.config.exchanges.get(exchange_name)
        if exchange_config:
            fees = {
                'maker': exchange_config.maker_fee,
                'taker': exchange_config.taker_fee
            }
            logger.debug(f"Using config fees for {exchange_name}: {fees}")
            return fees
        else:
            # Fallback to default fees
            logger.warning(f"Exchange {exchange_name} not found in config, using default fees")
            fees = {'maker': 0.001, 'taker': 0.001}
            return fees
    
    async def _on_ticker_update(self, ticker: Ticker, exchange_name: str) -> None:
        """Handle ticker updates from exchanges"""
        if ticker.symbol not in self.active_symbols:
            return
        
        # Get fees from config
        exchange_config = self.config.exchanges.get(exchange_name)
        fees = {
            'maker': exchange_config.maker_fee if exchange_config else 0.001,
            'taker': exchange_config.taker_fee if exchange_config else 0.001
        }
        
        # Update exchange data
        self.exchange_data[exchange_name][ticker.symbol] = ExchangeData(
            exchange_name=exchange_name,
            ticker=ticker,
            last_updated=ticker.timestamp,
            fees=fees
        )
        
        # Store ticker in database
        ticker_record = TickerRecord(
            exchange=exchange_name,
            symbol=ticker.symbol,
            bid=ticker.bid,
            ask=ticker.ask,
            bid_size=ticker.bid_size,
            ask_size=ticker.ask_size,
            timestamp=ticker.timestamp
        )
        
        try:
            await self.database.insert_ticker(ticker_record)
        except Exception as e:
            logger.error(f"Failed to store ticker: {e}")
        
        # Check for arbitrage opportunities
        await self._check_arbitrage_opportunities(ticker.symbol)
    
    async def _check_arbitrage_opportunities(self, symbol: str) -> None:
        """Check for arbitrage opportunities for a given symbol"""
        if not self.is_running:
            return
        
        # Get all exchanges with data for this symbol
        exchanges_with_data = []
        current_time = time.time()
        
        for exchange_name, exchange_data in self.exchange_data.items():
            if symbol in exchange_data:
                data = exchange_data[symbol]
                # Check if data is fresh (within max_spread_age_seconds)
                if current_time - data.last_updated <= self.config.arbitrage.max_spread_age_seconds:
                    exchanges_with_data.append(data)
        
        if len(exchanges_with_data) < 2:
            # Debug log to see what data we have
            if len(exchanges_with_data) == 1:
                logger.debug(f"Only 1 exchange data for {symbol}: {exchanges_with_data[0].exchange_name}")
            return
        
        # Find arbitrage opportunities
        opportunities = []
        
        for i in range(len(exchanges_with_data)):
            for j in range(i + 1, len(exchanges_with_data)):
                exchange1 = exchanges_with_data[i]
                exchange2 = exchanges_with_data[j]
                
                # Check both directions
                opp1 = await self._calculate_arbitrage(exchange1, exchange2, symbol)
                opp2 = await self._calculate_arbitrage(exchange2, exchange1, symbol)
                
                if opp1:
                    opportunities.append(opp1)
                if opp2:
                    opportunities.append(opp2)
        
        # Process opportunities
        if opportunities:
            logger.debug(f"Found {len(opportunities)} arbitrage opportunities for {symbol}")
            
        for opportunity in opportunities:
            # Check if opportunity meets minimum profit threshold and doesn't exceed max spread threshold (abnormal filter)
            if (opportunity.profit_percent >= self.config.arbitrage.min_profit_threshold and 
                opportunity.profit_percent <= self.config.arbitrage.max_spread_threshold):
                await self._handle_arbitrage_opportunity(opportunity)
            elif opportunity.profit_percent > self.config.arbitrage.max_spread_threshold:
                logger.warning(f"Abnormal spread detected for {opportunity.symbol}: {opportunity.profit_percent*100:.2f}% > {self.config.arbitrage.max_spread_threshold*100:.1f}% - filtering out")
    
    async def _calculate_arbitrage(self, buy_exchange: ExchangeData, sell_exchange: ExchangeData, 
                           symbol: str) -> Optional[ArbitrageSignal]:
        """Calculate arbitrage opportunity between two exchanges"""
        
        # Get prices
        buy_price = buy_exchange.ticker.ask  # We buy at ask price
        sell_price = sell_exchange.ticker.bid  # We sell at bid price
        
        # Get available sizes
        buy_size = buy_exchange.ticker.ask_size
        sell_size = sell_exchange.ticker.bid_size
        
        # Get trading fees dynamically (with caching)
        try:
            buy_fees = await self.get_trading_fees(buy_exchange.exchange_name, symbol)
            sell_fees = await self.get_trading_fees(sell_exchange.exchange_name, symbol)
            buy_fee = buy_fees.get('taker', 0.001)  # Assume taker fee for market orders
            sell_fee = sell_fees.get('taker', 0.001)
        except Exception as e:
            logger.warning(f"Error getting fees for arbitrage calculation: {e}, using defaults")
            buy_fee = 0.001
            sell_fee = 0.001
        
        # Calculate profit accounting for fees
        gross_profit = sell_price - buy_price
        fee_cost = (buy_price * buy_fee) + (sell_price * sell_fee)
        net_profit = gross_profit - fee_cost
        
        # Calculate profit percentage
        profit_percent = (net_profit / buy_price) if buy_price > 0 else 0
        
        # Account for slippage
        slippage_cost = buy_price * self.config.arbitrage.slippage_tolerance
        adjusted_profit = net_profit - slippage_cost
        adjusted_profit_percent = (adjusted_profit / buy_price) if buy_price > 0 else 0
        
        # Check if profitable
        if adjusted_profit_percent <= 0:
            return None
        
        # Calculate confidence based on size and age
        size_confidence = min(min(buy_size, sell_size) / 1000, 1.0)  # Normalize to 1000 units
        age_confidence = max(0, 1 - (time.time() - max(buy_exchange.last_updated, sell_exchange.last_updated)) / 
                           self.config.arbitrage.max_spread_age_seconds)
        confidence = (size_confidence + age_confidence) / 2
        
        return ArbitrageSignal(
            symbol=symbol,
            buy_exchange=buy_exchange.exchange_name,
            sell_exchange=sell_exchange.exchange_name,
            buy_price=buy_price,
            sell_price=sell_price,
            profit=adjusted_profit,
            profit_percent=adjusted_profit_percent,
            buy_size=buy_size,
            sell_size=sell_size,
            timestamp=time.time(),
            confidence=confidence
        )
    
    async def _handle_arbitrage_opportunity(self, signal: ArbitrageSignal) -> None:
        """Handle detected arbitrage opportunity"""
        
        # Check cooldown
        cooldown_key = f"{signal.symbol}_{signal.buy_exchange}_{signal.sell_exchange}"
        if cooldown_key in self.trade_cooldown:
            if time.time() - self.trade_cooldown[cooldown_key] < 60:  # 1 minute cooldown
                return
        
        # Check if we've exceeded max trades per hour
        recent_trades = [s for s in self.recent_signals if time.time() - s.timestamp < 3600]
        if len(recent_trades) >= self.config.arbitrage.max_trades_per_hour:
            logger.warning("Max trades per hour reached, skipping opportunity")
            return
        
        # Store opportunity in database
        opportunity = ArbitrageOpportunity(
            symbol=signal.symbol,
            buy_exchange=signal.buy_exchange,
            sell_exchange=signal.sell_exchange,
            buy_price=signal.buy_price,
            sell_price=signal.sell_price,
            profit=signal.profit,
            profit_percent=signal.profit_percent,
            timestamp=signal.timestamp
        )
        
        try:
            await self.database.insert_arbitrage_opportunity(opportunity)
        except Exception as e:
            logger.error(f"Failed to store arbitrage opportunity: {e}")
        
        # Add to recent signals
        self.recent_signals.append(signal)
        self.signals_generated += 1
        
        # Set cooldown
        self.trade_cooldown[cooldown_key] = time.time()
        
        # Emit signal to callbacks
        for callback in self.signal_callbacks:
            try:
                await callback(signal)
            except Exception as e:
                logger.error(f"Error in signal callback: {e}")
        
        logger.info(f"Arbitrage opportunity detected: {signal.symbol} "
                   f"Buy {signal.buy_exchange} @ {signal.buy_price:.6f} "
                   f"Sell {signal.sell_exchange} @ {signal.sell_price:.6f} "
                   f"Profit: {signal.profit_percent:.4f}%")
    
    async def start(self) -> None:
        """Start the arbitrage strategy"""
        self.is_running = True
        logger.info("Arbitrage strategy started")
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_task())
    
    async def stop(self) -> None:
        """Stop the arbitrage strategy"""
        self.is_running = False
        logger.info("Arbitrage strategy stopped")
    
    async def _cleanup_task(self) -> None:
        """Periodic cleanup task"""
        while self.is_running:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                current_time = time.time()
                
                # Clean up old exchange data
                for exchange_name in list(self.exchange_data.keys()):
                    for symbol in list(self.exchange_data[exchange_name].keys()):
                        data = self.exchange_data[exchange_name][symbol]
                        if current_time - data.last_updated > 300:  # 5 minutes
                            del self.exchange_data[exchange_name][symbol]
                
                # Clean up old cooldowns
                expired_cooldowns = [key for key, timestamp in self.trade_cooldown.items() 
                                   if current_time - timestamp > 3600]  # 1 hour
                for key in expired_cooldowns:
                    del self.trade_cooldown[key]
                
                # Database cleanup (once per hour)
                if current_time - self._last_cleanup > 3600:
                    await self.database.cleanup_old_data(self.config.database.max_history_days)
                    self._last_cleanup = current_time
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
    
    def get_stats(self) -> Dict[str, any]:
        """Get strategy statistics"""
        recent_signals = [s for s in self.recent_signals if time.time() - s.timestamp < 3600]
        
        return {
            'signals_generated': self.signals_generated,
            'signals_executed': self.signals_executed,
            'total_profit': self.total_profit,
            'recent_signals_1h': len(recent_signals),
            'avg_profit_percent': sum(s.profit_percent for s in recent_signals) / len(recent_signals) if recent_signals else 0,
            'execution_rate': (self.signals_executed / self.signals_generated * 100) if self.signals_generated > 0 else 0,
            'active_exchanges': len(self.exchange_data),
            'tracked_symbols': len(set(symbol for exchange_data in self.exchange_data.values() for symbol in exchange_data.keys()))
        }
    
    def get_recent_signals(self, limit: int = 10) -> List[ArbitrageSignal]:
        """Get recent arbitrage signals"""
        return list(self.recent_signals)[-limit:]
    
    def mark_signal_executed(self, profit: float) -> None:
        """Mark a signal as executed"""
        self.signals_executed += 1
        self.total_profit += profit