import sqlite3
import asyncio
import aiosqlite
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class TickerRecord:
    id: Optional[int] = None
    exchange: str = ""
    symbol: str = ""
    bid: float = 0.0
    ask: float = 0.0
    bid_size: float = 0.0
    ask_size: float = 0.0
    timestamp: float = 0.0
    created_at: Optional[datetime] = None


@dataclass
class OrderRecord:
    id: Optional[int] = None
    exchange: str = ""
    order_id: str = ""
    symbol: str = ""
    side: str = ""
    order_type: str = ""
    quantity: float = 0.0
    price: Optional[float] = None
    status: str = ""
    filled_quantity: float = 0.0
    average_price: Optional[float] = None
    timestamp: float = 0.0
    created_at: Optional[datetime] = None


@dataclass
class TradeRecord:
    id: Optional[int] = None
    symbol: str = ""
    buy_exchange: str = ""
    sell_exchange: str = ""
    buy_price: float = 0.0
    sell_price: float = 0.0
    quantity: float = 0.0
    profit: float = 0.0
    profit_percent: float = 0.0
    buy_order_id: Optional[str] = None
    sell_order_id: Optional[str] = None
    status: str = "pending"  # pending, completed, failed
    timestamp: float = 0.0
    created_at: Optional[datetime] = None


@dataclass
class ArbitrageOpportunity:
    id: Optional[int] = None
    symbol: str = ""
    buy_exchange: str = ""
    sell_exchange: str = ""
    buy_price: float = 0.0
    sell_price: float = 0.0
    profit: float = 0.0
    profit_percent: float = 0.0
    executed: bool = False
    timestamp: float = 0.0
    created_at: Optional[datetime] = None


@dataclass
class BalanceRecord:
    id: Optional[int] = None
    exchange: str = ""
    asset: str = ""
    free: float = 0.0
    locked: float = 0.0
    total: float = 0.0
    usd_value: Optional[float] = None
    timestamp: float = 0.0
    created_at: Optional[datetime] = None


@dataclass
class TradingFeeRecord:
    id: Optional[int] = None
    exchange: str = ""
    symbol: str = ""
    maker_fee: float = 0.001
    taker_fee: float = 0.001
    timestamp: float = 0.0
    created_at: Optional[datetime] = None


class Database:
    def __init__(self, config = None):
        if config and hasattr(config, 'database'):
            self.db_path = config.database.db_path
        else:
            self.db_path = "arbot.db"
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize database and create tables"""
        if self._initialized:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            await self._create_tables(db)
            await db.commit()
        
        self._initialized = True
        logger.info(f"Database initialized at {self.db_path}")
    
    async def _create_tables(self, db: aiosqlite.Connection) -> None:
        """Create all database tables"""
        
        # Tickers table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS tickers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exchange TEXT NOT NULL,
                symbol TEXT NOT NULL,
                bid REAL NOT NULL,
                ask REAL NOT NULL,
                bid_size REAL NOT NULL,
                ask_size REAL NOT NULL,
                timestamp REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Orders table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exchange TEXT NOT NULL,
                order_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                order_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL,
                status TEXT NOT NULL,
                filled_quantity REAL DEFAULT 0,
                average_price REAL,
                timestamp REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Trades table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                buy_exchange TEXT NOT NULL,
                sell_exchange TEXT NOT NULL,
                buy_price REAL NOT NULL,
                sell_price REAL NOT NULL,
                quantity REAL NOT NULL,
                profit REAL NOT NULL,
                profit_percent REAL NOT NULL,
                buy_order_id TEXT,
                sell_order_id TEXT,
                status TEXT DEFAULT 'pending',
                timestamp REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Arbitrage opportunities table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                buy_exchange TEXT NOT NULL,
                sell_exchange TEXT NOT NULL,
                buy_price REAL NOT NULL,
                sell_price REAL NOT NULL,
                profit REAL NOT NULL,
                profit_percent REAL NOT NULL,
                executed BOOLEAN DEFAULT FALSE,
                timestamp REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Balances table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS balances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exchange TEXT NOT NULL,
                asset TEXT NOT NULL,
                free REAL NOT NULL,
                locked REAL NOT NULL,
                total REAL NOT NULL,
                usd_value REAL,
                timestamp REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Trading fees table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS trading_fees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exchange TEXT NOT NULL,
                symbol TEXT NOT NULL,
                maker_fee REAL NOT NULL,
                taker_fee REAL NOT NULL,
                timestamp REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(exchange, symbol)
            )
        ''')
        
        # Create indexes for better performance
        await db.execute('CREATE INDEX IF NOT EXISTS idx_tickers_exchange_symbol ON tickers(exchange, symbol)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_tickers_timestamp ON tickers(timestamp)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_orders_exchange_order_id ON orders(exchange, order_id)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_arbitrage_symbol ON arbitrage_opportunities(symbol)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_balances_exchange_asset ON balances(exchange, asset)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_trading_fees_exchange_symbol ON trading_fees(exchange, symbol)')
    
    async def insert_ticker(self, ticker: TickerRecord) -> int:
        """Insert ticker data"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                INSERT INTO tickers (exchange, symbol, bid, ask, bid_size, ask_size, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (ticker.exchange, ticker.symbol, ticker.bid, ticker.ask, 
                  ticker.bid_size, ticker.ask_size, ticker.timestamp))
            await db.commit()
            return cursor.lastrowid
    
    async def insert_tickers_batch(self, tickers: List[TickerRecord]) -> int:
        """Insert multiple ticker records in a single transaction"""
        if not tickers:
            return 0
        
        async with aiosqlite.connect(self.db_path) as db:
            data = [(ticker.exchange, ticker.symbol, ticker.bid, ticker.ask, 
                    ticker.bid_size, ticker.ask_size, ticker.timestamp) for ticker in tickers]
            
            await db.executemany('''
                INSERT INTO tickers (exchange, symbol, bid, ask, bid_size, ask_size, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', data)
            await db.commit()
            return len(tickers)
    
    async def insert_order(self, order: OrderRecord) -> int:
        """Insert order data"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                INSERT INTO orders (exchange, order_id, symbol, side, order_type, quantity, 
                                  price, status, filled_quantity, average_price, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (order.exchange, order.order_id, order.symbol, order.side, order.order_type,
                  order.quantity, order.price, order.status, order.filled_quantity,
                  order.average_price, order.timestamp))
            await db.commit()
            return cursor.lastrowid
    
    async def insert_trade(self, trade: TradeRecord) -> int:
        """Insert trade data"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                INSERT INTO trades (symbol, buy_exchange, sell_exchange, buy_price, sell_price,
                                  quantity, profit, profit_percent, buy_order_id, sell_order_id,
                                  status, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (trade.symbol, trade.buy_exchange, trade.sell_exchange, trade.buy_price,
                  trade.sell_price, trade.quantity, trade.profit, trade.profit_percent,
                  trade.buy_order_id, trade.sell_order_id, trade.status, trade.timestamp))
            await db.commit()
            return cursor.lastrowid
    
    async def insert_arbitrage_opportunity(self, opportunity: ArbitrageOpportunity) -> int:
        """Insert arbitrage opportunity data"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                INSERT INTO arbitrage_opportunities (symbol, buy_exchange, sell_exchange, 
                                                   buy_price, sell_price, profit, profit_percent,
                                                   executed, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (opportunity.symbol, opportunity.buy_exchange, opportunity.sell_exchange,
                  opportunity.buy_price, opportunity.sell_price, opportunity.profit,
                  opportunity.profit_percent, opportunity.executed, opportunity.timestamp))
            await db.commit()
            return cursor.lastrowid
    
    async def insert_balance(self, balance: BalanceRecord) -> int:
        """Insert balance data"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                INSERT INTO balances (exchange, asset, free, locked, total, usd_value, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (balance.exchange, balance.asset, balance.free, balance.locked,
                  balance.total, balance.usd_value, balance.timestamp))
            await db.commit()
            return cursor.lastrowid
    
    async def get_latest_ticker(self, exchange: str, symbol: str) -> Optional[TickerRecord]:
        """Get latest ticker for exchange and symbol"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM tickers 
                WHERE exchange = ? AND symbol = ?
                ORDER BY timestamp DESC
                LIMIT 1
            ''', (exchange, symbol))
            row = await cursor.fetchone()
            
            if row:
                return TickerRecord(**dict(row))
            return None
    
    async def get_trades(self, symbol: Optional[str] = None, limit: int = 100) -> List[TradeRecord]:
        """Get trade history"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            if symbol:
                cursor = await db.execute('''
                    SELECT * FROM trades 
                    WHERE symbol = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (symbol, limit))
            else:
                cursor = await db.execute('''
                    SELECT * FROM trades 
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))
            
            rows = await cursor.fetchall()
            return [TradeRecord(**dict(row)) for row in rows]
    
    async def get_arbitrage_opportunities(self, symbol: Optional[str] = None, 
                                        limit: int = 100) -> List[ArbitrageOpportunity]:
        """Get arbitrage opportunities"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            if symbol:
                cursor = await db.execute('''
                    SELECT * FROM arbitrage_opportunities 
                    WHERE symbol = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (symbol, limit))
            else:
                cursor = await db.execute('''
                    SELECT * FROM arbitrage_opportunities 
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))
            
            rows = await cursor.fetchall()
            return [ArbitrageOpportunity(**dict(row)) for row in rows]
    
    async def get_balances(self, exchange: Optional[str] = None) -> List[BalanceRecord]:
        """Get latest balances"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            if exchange:
                cursor = await db.execute('''
                    SELECT * FROM balances 
                    WHERE exchange = ?
                    ORDER BY timestamp DESC
                ''', (exchange,))
            else:
                cursor = await db.execute('''
                    SELECT * FROM balances 
                    ORDER BY timestamp DESC
                ''')
            
            rows = await cursor.fetchall()
            return [BalanceRecord(**dict(row)) for row in rows]
    
    async def update_trade_status(self, trade_id: int, status: str, 
                                buy_order_id: Optional[str] = None,
                                sell_order_id: Optional[str] = None) -> None:
        """Update trade status"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE trades 
                SET status = ?, buy_order_id = ?, sell_order_id = ?
                WHERE id = ?
            ''', (status, buy_order_id, sell_order_id, trade_id))
            await db.commit()
    
    async def update_order_status(self, order_id: str, exchange: str, status: str,
                                filled_quantity: float, average_price: Optional[float] = None) -> None:
        """Update order status"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE orders 
                SET status = ?, filled_quantity = ?, average_price = ?
                WHERE order_id = ? AND exchange = ?
            ''', (status, filled_quantity, average_price, order_id, exchange))
            await db.commit()
    
    async def insert_or_update_trading_fee(self, fee: TradingFeeRecord) -> None:
        """Insert or update trading fee data"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO trading_fees (exchange, symbol, maker_fee, taker_fee, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (fee.exchange, fee.symbol, fee.maker_fee, fee.taker_fee, fee.timestamp))
            await db.commit()
    
    async def get_trading_fee(self, exchange: str, symbol: str) -> Optional[TradingFeeRecord]:
        """Get trading fee for exchange and symbol"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM trading_fees 
                WHERE exchange = ? AND symbol = ?
                ORDER BY timestamp DESC
                LIMIT 1
            ''', (exchange, symbol))
            row = await cursor.fetchone()
            
            if row:
                return TradingFeeRecord(**dict(row))
            return None
    
    async def get_cached_trading_fees(self, exchange: str, max_age_hours: int = 24) -> Dict[str, Dict[str, float]]:
        """Get all cached trading fees for an exchange within max age"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT symbol, maker_fee, taker_fee FROM trading_fees 
                WHERE exchange = ? AND timestamp > ?
            ''', (exchange, cutoff_time))
            rows = await cursor.fetchall()
            
            fees = {}
            for row in rows:
                fees[row['symbol']] = {
                    'maker': row['maker_fee'],
                    'taker': row['taker_fee']
                }
            return fees
    
    async def cleanup_old_data(self, days: int = 30) -> None:
        """Remove old data beyond specified days"""
        cutoff_time = datetime.now() - timedelta(days=days)
        cutoff_timestamp = cutoff_time.timestamp()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Clean up old ticker data
            await db.execute('DELETE FROM tickers WHERE timestamp < ?', (cutoff_timestamp,))
            
            # Clean up old balance data (keep only latest per exchange/asset)
            await db.execute('''
                DELETE FROM balances 
                WHERE id NOT IN (
                    SELECT MAX(id) 
                    FROM balances 
                    GROUP BY exchange, asset
                ) AND timestamp < ?
            ''', (cutoff_timestamp,))
            
            await db.commit()
            logger.info(f"Cleaned up data older than {days} days")
    
    async def get_performance_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get performance statistics"""
        start_time = datetime.now() - timedelta(days=days)
        start_timestamp = start_time.timestamp()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Total trades
            cursor = await db.execute('''
                SELECT COUNT(*) as total_trades,
                       SUM(profit) as total_profit,
                       AVG(profit_percent) as avg_profit_percent,
                       COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_trades
                FROM trades
                WHERE timestamp >= ?
            ''', (start_timestamp,))
            trade_stats = await cursor.fetchone()
            
            # Arbitrage opportunities
            cursor = await db.execute('''
                SELECT COUNT(*) as total_opportunities,
                       COUNT(CASE WHEN executed = 1 THEN 1 END) as executed_opportunities,
                       AVG(profit_percent) as avg_opportunity_percent
                FROM arbitrage_opportunities
                WHERE timestamp >= ?
            ''', (start_timestamp,))
            arb_stats = await cursor.fetchone()
            
            return {
                'total_trades': trade_stats['total_trades'],
                'completed_trades': trade_stats['completed_trades'],
                'total_profit': trade_stats['total_profit'] or 0,
                'avg_profit_percent': trade_stats['avg_profit_percent'] or 0,
                'total_opportunities': arb_stats['total_opportunities'],
                'executed_opportunities': arb_stats['executed_opportunities'],
                'avg_opportunity_percent': arb_stats['avg_opportunity_percent'] or 0,
                'execution_rate': (arb_stats['executed_opportunities'] / arb_stats['total_opportunities'] * 100) if arb_stats['total_opportunities'] > 0 else 0
            }
    
    async def backup_database(self, backup_path: str) -> None:
        """Create database backup"""
        async with aiosqlite.connect(self.db_path) as source:
            async with aiosqlite.connect(backup_path) as backup:
                await source.backup(backup)
        logger.info(f"Database backed up to {backup_path}")
    
    async def close(self) -> None:
        """Close database connection"""
        # Connection is closed automatically with context manager
        pass