# Database Architecture

ArBot uses SQLite as its primary database solution, providing a lightweight, embedded database that requires no separate server setup while offering excellent performance for arbitrage trading applications. This document covers the complete database architecture, schema design, and optimization strategies.

## Database Overview

### SQLite Benefits for ArBot

**Embedded Database Advantages:**
- Zero configuration required
- No separate database server
- Single file storage
- ACID compliance
- Cross-platform compatibility
- High performance for read-heavy workloads

**Perfect for Arbitrage Trading:**
- Fast price data ingestion
- Efficient historical analysis
- Real-time query performance
- Minimal maintenance overhead
- Backup simplicity

### Database Files Structure

```
arbot/
├── data/
│   ├── arbot.db              # Main trading database
│   ├── historical.db         # Historical price data
│   ├── backtest.db          # Backtesting results
│   └── config.db            # Configuration storage
└── backups/
    ├── arbot_YYYYMMDD.db    # Daily backups
    └── weekly/              # Weekly backup archives
```

## Core Schema Design

### Price Data Tables

**Tickers Table (Real-time Price Data):**
```sql
CREATE TABLE tickers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    bid REAL NOT NULL,
    ask REAL NOT NULL,
    bid_size REAL,
    ask_size REAL,
    timestamp REAL NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, exchange, timestamp)
);

-- Optimized indexes for fast lookups
CREATE INDEX idx_tickers_symbol_exchange ON tickers(symbol, exchange);
CREATE INDEX idx_tickers_timestamp ON tickers(timestamp);
CREATE INDEX idx_tickers_symbol_timestamp ON tickers(symbol, timestamp);
```

**OHLCV Data (Candlestick Data):**
```sql
CREATE TABLE ohlcv (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    open_time INTEGER NOT NULL,
    close_time INTEGER NOT NULL,
    open_price REAL NOT NULL,
    high_price REAL NOT NULL,
    low_price REAL NOT NULL,
    close_price REAL NOT NULL,
    volume REAL NOT NULL,
    quote_volume REAL,
    trades_count INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, exchange, timeframe, open_time)
);

CREATE INDEX idx_ohlcv_symbol_timeframe ON ohlcv(symbol, timeframe);
CREATE INDEX idx_ohlcv_open_time ON ohlcv(open_time);
```

### Trading Tables

**Arbitrage Signals:**
```sql
CREATE TABLE arbitrage_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    buy_exchange TEXT NOT NULL,
    sell_exchange TEXT NOT NULL,
    buy_price REAL NOT NULL,
    sell_price REAL NOT NULL,
    profit REAL NOT NULL,
    profit_percent REAL NOT NULL,
    buy_size REAL NOT NULL,
    sell_size REAL NOT NULL,
    confidence REAL NOT NULL,
    trend_direction TEXT,
    executed BOOLEAN DEFAULT FALSE,
    timestamp REAL NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_signals_symbol ON arbitrage_signals(symbol);
CREATE INDEX idx_signals_timestamp ON arbitrage_signals(timestamp);
CREATE INDEX idx_signals_profit ON arbitrage_signals(profit_percent);
```

**Trades Table:**
```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id INTEGER,
    symbol TEXT NOT NULL,
    buy_exchange TEXT NOT NULL,
    sell_exchange TEXT NOT NULL,
    buy_order_id TEXT,
    sell_order_id TEXT,
    planned_buy_price REAL NOT NULL,
    planned_sell_price REAL NOT NULL,
    actual_buy_price REAL,
    actual_sell_price REAL,
    quantity REAL NOT NULL,
    planned_profit REAL NOT NULL,
    actual_profit REAL,
    fees_paid REAL DEFAULT 0,
    slippage REAL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    error_message TEXT,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    FOREIGN KEY (signal_id) REFERENCES arbitrage_signals(id)
);

CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_started_at ON trades(started_at);
```

**Balances Table:**
```sql
CREATE TABLE balances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange TEXT NOT NULL,
    asset TEXT NOT NULL,
    free_balance REAL NOT NULL DEFAULT 0,
    locked_balance REAL NOT NULL DEFAULT 0,
    total_balance REAL GENERATED ALWAYS AS (free_balance + locked_balance),
    timestamp REAL NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(exchange, asset, timestamp)
);

CREATE INDEX idx_balances_exchange_asset ON balances(exchange, asset);
CREATE INDEX idx_balances_timestamp ON balances(timestamp);
```

### Configuration Tables

**Settings Table:**
```sql
CREATE TABLE settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    data_type TEXT NOT NULL DEFAULT 'string',
    description TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category, key)
);

CREATE INDEX idx_settings_category ON settings(category);
```

**Exchange Configuration:**
```sql
CREATE TABLE exchange_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange TEXT NOT NULL UNIQUE,
    enabled BOOLEAN DEFAULT TRUE,
    arbitrage_enabled BOOLEAN DEFAULT TRUE,
    region TEXT,
    premium_baseline REAL DEFAULT 0,
    maker_fee REAL DEFAULT 0.001,
    taker_fee REAL DEFAULT 0.001,
    min_trade_amount REAL DEFAULT 10,
    max_trade_amount REAL DEFAULT 10000,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Analytics Tables

**Performance Metrics:**
```sql
CREATE TABLE performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    total_trades INTEGER DEFAULT 0,
    successful_trades INTEGER DEFAULT 0,
    total_profit REAL DEFAULT 0,
    total_fees REAL DEFAULT 0,
    avg_profit_percent REAL DEFAULT 0,
    max_drawdown REAL DEFAULT 0,
    sharpe_ratio REAL,
    win_rate REAL DEFAULT 0,
    avg_trade_duration REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date)
);

CREATE INDEX idx_metrics_date ON performance_metrics(date);
```

**Symbol Statistics:**
```sql
CREATE TABLE symbol_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    signals_generated INTEGER DEFAULT 0,
    signals_executed INTEGER DEFAULT 0,
    avg_spread REAL DEFAULT 0,
    max_spread REAL DEFAULT 0,
    total_volume REAL DEFAULT 0,
    profitability_score REAL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date)
);

CREATE INDEX idx_symbol_stats_symbol ON symbol_stats(symbol);
CREATE INDEX idx_symbol_stats_date ON symbol_stats(date);
```

## Database Operations

### Price Data Management

**Real-time Data Insertion:**
```python
class PriceDataManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.connection_pool = self._create_connection_pool()
    
    async def insert_ticker(self, ticker_data):
        query = """
        INSERT OR REPLACE INTO tickers 
        (symbol, exchange, bid, ask, bid_size, ask_size, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        async with self.connection_pool.acquire() as conn:
            await conn.execute(query, (
                ticker_data.symbol,
                ticker_data.exchange,
                ticker_data.bid,
                ticker_data.ask,
                ticker_data.bid_size,
                ticker_data.ask_size,
                ticker_data.timestamp
            ))
            await conn.commit()
    
    async def bulk_insert_tickers(self, ticker_list):
        query = """
        INSERT OR REPLACE INTO tickers 
        (symbol, exchange, bid, ask, bid_size, ask_size, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        data = [
            (t.symbol, t.exchange, t.bid, t.ask, t.bid_size, t.ask_size, t.timestamp)
            for t in ticker_list
        ]
        
        async with self.connection_pool.acquire() as conn:
            await conn.executemany(query, data)
            await conn.commit()
```

**Historical Data Queries:**
```python
class HistoricalDataQuery:
    def __init__(self, db_manager):
        self.db = db_manager
    
    async def get_price_history(self, symbol, exchange, start_time, end_time):
        query = """
        SELECT timestamp, bid, ask, bid_size, ask_size
        FROM tickers
        WHERE symbol = ? AND exchange = ?
        AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp ASC
        """
        
        async with self.db.connection_pool.acquire() as conn:
            cursor = await conn.execute(query, (symbol, exchange, start_time, end_time))
            rows = await cursor.fetchall()
            
            return [
                {
                    'timestamp': row[0],
                    'bid': row[1],
                    'ask': row[2],
                    'bid_size': row[3],
                    'ask_size': row[4]
                }
                for row in rows
            ]
    
    async def get_spread_analysis(self, symbol, timeframe='1h', limit=100):
        query = """
        WITH spread_data AS (
            SELECT 
                symbol,
                timestamp,
                ask - bid as spread,
                (ask - bid) / ((ask + bid) / 2) * 100 as spread_percent
            FROM tickers
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT ?
        )
        SELECT 
            AVG(spread) as avg_spread,
            MIN(spread) as min_spread,
            MAX(spread) as max_spread,
            AVG(spread_percent) as avg_spread_percent,
            STDEV(spread_percent) as spread_volatility
        FROM spread_data
        """
        
        async with self.db.connection_pool.acquire() as conn:
            cursor = await conn.execute(query, (symbol, limit))
            result = await cursor.fetchone()
            
            return {
                'avg_spread': result[0],
                'min_spread': result[1],
                'max_spread': result[2],
                'avg_spread_percent': result[3],
                'spread_volatility': result[4]
            }
```

### Trading Data Management

**Signal Tracking:**
```python
class SignalManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    async def save_signal(self, signal):
        query = """
        INSERT INTO arbitrage_signals
        (symbol, buy_exchange, sell_exchange, buy_price, sell_price,
         profit, profit_percent, buy_size, sell_size, confidence,
         trend_direction, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        async with self.db.connection_pool.acquire() as conn:
            cursor = await conn.execute(query, (
                signal.symbol, signal.buy_exchange, signal.sell_exchange,
                signal.buy_price, signal.sell_price, signal.profit,
                signal.profit_percent, signal.buy_size, signal.sell_size,
                signal.confidence, signal.trend_direction, signal.timestamp
            ))
            await conn.commit()
            return cursor.lastrowid
    
    async def mark_signal_executed(self, signal_id):
        query = "UPDATE arbitrage_signals SET executed = TRUE WHERE id = ?"
        
        async with self.db.connection_pool.acquire() as conn:
            await conn.execute(query, (signal_id,))
            await conn.commit()
    
    async def get_signal_statistics(self, period_hours=24):
        cutoff_time = time.time() - (period_hours * 3600)
        
        query = """
        SELECT 
            COUNT(*) as total_signals,
            COUNT(CASE WHEN executed = TRUE THEN 1 END) as executed_signals,
            AVG(profit_percent) as avg_profit_percent,
            MAX(profit_percent) as max_profit_percent,
            AVG(confidence) as avg_confidence
        FROM arbitrage_signals
        WHERE timestamp > ?
        """
        
        async with self.db.connection_pool.acquire() as conn:
            cursor = await conn.execute(query, (cutoff_time,))
            result = await cursor.fetchone()
            
            return {
                'total_signals': result[0],
                'executed_signals': result[1],
                'execution_rate': result[1] / result[0] if result[0] > 0 else 0,
                'avg_profit_percent': result[2],
                'max_profit_percent': result[3],
                'avg_confidence': result[4]
            }
```

**Trade Execution Tracking:**
```python
class TradeManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    async def create_trade(self, trade_params):
        query = """
        INSERT INTO trades
        (signal_id, symbol, buy_exchange, sell_exchange,
         planned_buy_price, planned_sell_price, quantity, planned_profit, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """
        
        async with self.db.connection_pool.acquire() as conn:
            cursor = await conn.execute(query, (
                trade_params.signal_id, trade_params.symbol,
                trade_params.buy_exchange, trade_params.sell_exchange,
                trade_params.planned_buy_price, trade_params.planned_sell_price,
                trade_params.quantity, trade_params.planned_profit
            ))
            await conn.commit()
            return cursor.lastrowid
    
    async def update_trade_execution(self, trade_id, execution_data):
        query = """
        UPDATE trades SET
            buy_order_id = ?, sell_order_id = ?,
            actual_buy_price = ?, actual_sell_price = ?,
            actual_profit = ?, fees_paid = ?, slippage = ?,
            status = ?, completed_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """
        
        async with self.db.connection_pool.acquire() as conn:
            await conn.execute(query, (
                execution_data.buy_order_id, execution_data.sell_order_id,
                execution_data.actual_buy_price, execution_data.actual_sell_price,
                execution_data.actual_profit, execution_data.fees_paid,
                execution_data.slippage, execution_data.status, trade_id
            ))
            await conn.commit()
```

## Performance Optimization

### Indexing Strategy

**Composite Indexes for Common Queries:**
```sql
-- Fast symbol + exchange + time range queries
CREATE INDEX idx_tickers_composite ON tickers(symbol, exchange, timestamp);

-- Arbitrage signal analysis
CREATE INDEX idx_signals_composite ON arbitrage_signals(symbol, profit_percent, timestamp);

-- Trade performance analysis
CREATE INDEX idx_trades_composite ON trades(symbol, status, started_at);

-- Balance queries
CREATE INDEX idx_balances_composite ON balances(exchange, asset, timestamp);
```

**Partial Indexes for Filtered Queries:**
```sql
-- Only index successful trades
CREATE INDEX idx_trades_successful ON trades(symbol, actual_profit, completed_at)
WHERE status = 'completed' AND actual_profit > 0;

-- Only index executed signals
CREATE INDEX idx_signals_executed ON arbitrage_signals(symbol, profit_percent, timestamp)
WHERE executed = TRUE;
```

### Query Optimization

**Efficient Aggregation Queries:**
```sql
-- Daily performance summary with window functions
WITH daily_trades AS (
    SELECT 
        DATE(started_at) as trade_date,
        COUNT(*) as trade_count,
        SUM(actual_profit) as daily_profit,
        AVG(actual_profit) as avg_profit,
        SUM(fees_paid) as total_fees
    FROM trades
    WHERE status = 'completed'
    AND started_at >= date('now', '-30 days')
    GROUP BY DATE(started_at)
)
SELECT 
    trade_date,
    trade_count,
    daily_profit,
    avg_profit,
    total_fees,
    SUM(daily_profit) OVER (ORDER BY trade_date) as cumulative_profit
FROM daily_trades
ORDER BY trade_date;
```

**Optimized Spread Analysis:**
```sql
-- Recent spread statistics with subquery optimization
SELECT 
    symbol,
    exchange,
    AVG(spread) as avg_spread,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY spread) as median_spread,
    STDEV(spread) as spread_volatility
FROM (
    SELECT 
        symbol,
        exchange,
        ask - bid as spread
    FROM tickers
    WHERE timestamp > ? -- Last 24 hours
    AND bid > 0 AND ask > bid -- Valid prices only
) spread_data
GROUP BY symbol, exchange
HAVING COUNT(*) >= 100 -- Minimum data points
ORDER BY avg_spread DESC;
```

### Connection Management

**Connection Pooling:**
```python
import aiosqlite
import asyncio
from contextlib import asynccontextmanager

class DatabasePool:
    def __init__(self, db_path, max_connections=10):
        self.db_path = db_path
        self.max_connections = max_connections
        self.pool = asyncio.Queue(maxsize=max_connections)
        self.created_connections = 0
    
    async def initialize(self):
        # Pre-create connections
        for _ in range(min(5, self.max_connections)):
            conn = await aiosqlite.connect(self.db_path)
            await conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
            await conn.execute("PRAGMA synchronous=NORMAL")
            await conn.execute("PRAGMA cache_size=10000")
            await conn.execute("PRAGMA temp_store=memory")
            await self.pool.put(conn)
            self.created_connections += 1
    
    @asynccontextmanager
    async def acquire(self):
        try:
            # Try to get existing connection
            conn = await asyncio.wait_for(self.pool.get(), timeout=1.0)
        except asyncio.TimeoutError:
            # Create new connection if under limit
            if self.created_connections < self.max_connections:
                conn = await aiosqlite.connect(self.db_path)
                await conn.execute("PRAGMA journal_mode=WAL")
                await conn.execute("PRAGMA synchronous=NORMAL")
                self.created_connections += 1
            else:
                # Wait for available connection
                conn = await self.pool.get()
        
        try:
            yield conn
        finally:
            await self.pool.put(conn)
    
    async def close_all(self):
        while not self.pool.empty():
            conn = await self.pool.get()
            await conn.close()
```

## Data Management

### Data Retention Policies

**Automated Cleanup:**
```python
class DataRetentionManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    async def cleanup_old_data(self):
        retention_policies = {
            'tickers': 7,  # Keep 7 days of raw ticker data
            'arbitrage_signals': 30,  # Keep 30 days of signals
            'trades': 365,  # Keep 1 year of trade history
            'performance_metrics': 1095  # Keep 3 years of metrics
        }
        
        for table, days in retention_policies.items():
            cutoff_date = datetime.now() - timedelta(days=days)
            
            if table == 'tickers':
                await self._cleanup_tickers(cutoff_date)
            elif table == 'arbitrage_signals':
                await self._cleanup_signals(cutoff_date)
            # Add other cleanup methods...
    
    async def _cleanup_tickers(self, cutoff_date):
        cutoff_timestamp = cutoff_date.timestamp()
        
        # Archive to historical database before deletion
        await self._archive_ticker_data(cutoff_timestamp)
        
        # Delete old data
        query = "DELETE FROM tickers WHERE timestamp < ?"
        async with self.db.connection_pool.acquire() as conn:
            await conn.execute(query, (cutoff_timestamp,))
            await conn.commit()
    
    async def _archive_ticker_data(self, cutoff_timestamp):
        # Create OHLCV aggregates before deletion
        query = """
        INSERT OR REPLACE INTO ohlcv
        (symbol, exchange, timeframe, open_time, close_time, 
         open_price, high_price, low_price, close_price, volume)
        SELECT 
            symbol,
            exchange,
            '1h' as timeframe,
            CAST(timestamp / 3600) * 3600 as open_time,
            CAST(timestamp / 3600) * 3600 + 3599 as close_time,
            FIRST_VALUE(bid) OVER (PARTITION BY symbol, exchange, CAST(timestamp / 3600) 
                                   ORDER BY timestamp) as open_price,
            MAX((bid + ask) / 2) as high_price,
            MIN((bid + ask) / 2) as low_price,
            LAST_VALUE(ask) OVER (PARTITION BY symbol, exchange, CAST(timestamp / 3600) 
                                  ORDER BY timestamp ROWS BETWEEN UNBOUNDED PRECEDING 
                                  AND UNBOUNDED FOLLOWING) as close_price,
            COUNT(*) as volume
        FROM tickers
        WHERE timestamp < ?
        GROUP BY symbol, exchange, CAST(timestamp / 3600)
        """
        
        async with self.db.connection_pool.acquire() as conn:
            await conn.execute(query, (cutoff_timestamp,))
            await conn.commit()
```

### Backup and Recovery

**Automated Backup System:**
```python
import shutil
import gzip
from pathlib import Path

class BackupManager:
    def __init__(self, db_path, backup_dir):
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
    
    async def create_backup(self, compress=True):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"arbot_{timestamp}.db"
        backup_path = self.backup_dir / backup_name
        
        # Use SQLite backup API for consistent backup
        async with aiosqlite.connect(self.db_path) as source:
            async with aiosqlite.connect(backup_path) as backup:
                await source.backup(backup)
        
        if compress:
            compressed_path = backup_path.with_suffix('.db.gz')
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            backup_path.unlink()  # Remove uncompressed file
            return compressed_path
        
        return backup_path
    
    async def restore_backup(self, backup_path):
        backup_path = Path(backup_path)
        
        if backup_path.suffix == '.gz':
            # Decompress first
            temp_path = backup_path.with_suffix('')
            with gzip.open(backup_path, 'rb') as f_in:
                with open(temp_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            backup_path = temp_path
        
        # Backup current database
        current_backup = await self.create_backup()
        
        try:
            # Replace current database
            shutil.copy2(backup_path, self.db_path)
            print(f"Database restored from {backup_path}")
            print(f"Previous database backed up to {current_backup}")
        except Exception as e:
            print(f"Restore failed: {e}")
            # Restore could fail, current_backup still exists
        finally:
            if backup_path.suffix == '':
                backup_path.unlink()  # Clean up temp file
```

## Monitoring and Maintenance

### Database Health Monitoring

**Performance Metrics:**
```python
class DatabaseMonitor:
    def __init__(self, db_manager):
        self.db = db_manager
    
    async def get_database_stats(self):
        stats = {}
        
        async with self.db.connection_pool.acquire() as conn:
            # Database file size
            cursor = await conn.execute("PRAGMA page_count")
            page_count = (await cursor.fetchone())[0]
            
            cursor = await conn.execute("PRAGMA page_size")
            page_size = (await cursor.fetchone())[0]
            
            stats['file_size_mb'] = (page_count * page_size) / (1024 * 1024)
            
            # Table statistics
            tables = ['tickers', 'arbitrage_signals', 'trades', 'balances']
            for table in tables:
                cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")
                stats[f'{table}_count'] = (await cursor.fetchone())[0]
            
            # Index usage
            cursor = await conn.execute("""
                SELECT name, sql FROM sqlite_master 
                WHERE type = 'index' AND sql IS NOT NULL
            """)
            stats['indexes'] = await cursor.fetchall()
            
            # Cache hit ratio
            cursor = await conn.execute("PRAGMA cache_size")
            cache_size = (await cursor.fetchone())[0]
            stats['cache_size'] = cache_size
        
        return stats
    
    async def analyze_query_performance(self, query, params=None):
        async with self.db.connection_pool.acquire() as conn:
            # Enable query analysis
            await conn.execute("PRAGMA query_only = ON")
            
            # Explain query plan
            explain_query = f"EXPLAIN QUERY PLAN {query}"
            cursor = await conn.execute(explain_query, params or [])
            plan = await cursor.fetchall()
            
            await conn.execute("PRAGMA query_only = OFF")
            
            return plan
```

### Maintenance Tasks

**Regular Maintenance:**
```python
class MaintenanceManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    async def run_maintenance(self):
        async with self.db.connection_pool.acquire() as conn:
            # Analyze tables for query optimization
            await conn.execute("ANALYZE")
            
            # Update statistics
            tables = ['tickers', 'arbitrage_signals', 'trades']
            for table in tables:
                await conn.execute(f"ANALYZE {table}")
            
            # Vacuum database (reclaim space)
            await conn.execute("VACUUM")
            
            # Reindex if needed
            await conn.execute("REINDEX")
            
            await conn.commit()
    
    async def check_integrity(self):
        async with self.db.connection_pool.acquire() as conn:
            cursor = await conn.execute("PRAGMA integrity_check")
            result = await cursor.fetchone()
            
            if result[0] == 'ok':
                return True, "Database integrity check passed"
            else:
                return False, f"Database integrity issues: {result[0]}"
```

!!! tip "Database Optimization"
    Enable WAL mode (Write-Ahead Logging) for better concurrency and set appropriate cache sizes based on your available memory for optimal performance.

!!! warning "Backup Important"
    Always backup your database before performing maintenance operations like VACUUM or major schema changes. Use the automated backup system for regular protection.

!!! note "Performance Monitoring"
    Monitor database file size growth and query performance regularly. Set up alerts for unusual patterns that might indicate issues with data retention or query efficiency.