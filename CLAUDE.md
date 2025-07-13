# CLAUDE.md - ArBot Technical Reference

## Core Architecture
```
arbot/
├── main.py          # Entry: live|sim|ui|backtest modes, exchange init, symbol detection
├── config.py        # Config: API keys, thresholds, DB settings from config.json
├── database.py      # SQLite: batch ticker storage, Unix timestamps
├── strategy.py      # Logic: arbitrage detection, fee calculation, signal generation
├── trader.py        # Live: real order execution
├── simulator.py     # Mock: simulated trading
├── backtester.py    # Historical: replay data for testing
├── ui.py           # Terminal: Textual-based TUI (deprecated)
├── gui.py          # GUI: tkinter-based real-time interface (primary UI)
└── exchanges/
    ├── base.py      # BaseExchange: abstract class, callback system
    ├── binance.py   # Binance: WebSocket streams, rate limit handling
    └── bybit.py     # Bybit: WebSocket streams, symbol validation
```

## Key Data Structures
```python
# exchanges/base.py
@dataclass
class Ticker:
    symbol: str; bid: float; ask: float; bid_size: float; ask_size: float; timestamp: float

@dataclass  
class ArbitrageSignal:
    symbol: str; buy_exchange: str; sell_exchange: str
    buy_price: float; sell_price: float; profit: float; profit_percent: float
    buy_size: float; sell_size: float; timestamp: float; confidence: float

# database.py
@dataclass
class TickerRecord:
    exchange: str; symbol: str; bid: float; ask: float; bid_size: float; ask_size: float
    timestamp: float  # Unix timestamp

@dataclass
class TradeRecord:
    symbol: str; buy_exchange: str; sell_exchange: str
    buy_price: float; sell_price: float; quantity: float; profit: float; profit_percent: float
    status: str; timestamp: float

@dataclass
class BalanceRecord:
    exchange: str; asset: str; free: float; locked: float; total: float
    usd_value: Optional[float]; timestamp: float
```

## Exchange Interface (BaseExchange)
```python
# Required methods
async def connect_ws(symbols: List[str]) -> None    # WebSocket subscribe
async def disconnect_ws() -> None                   # Cleanup WebSocket
async def get_ticker(symbol: str) -> Ticker         # REST API backup
async def get_orderbook(symbol: str) -> OrderBook   # Bid/ask data
async def place_order(...) -> Order                 # Trade execution
async def cancel_order(order_id: str, symbol: str) -> bool
async def get_order_status(order_id: str, symbol: str) -> Order
async def get_balance() -> Dict[str, Balance]       # Account info
async def get_trading_fees(symbol: str) -> Dict     # Maker/taker fees
async def get_symbols() -> List[str]                # Available symbols
async def get_all_tickers() -> List[Dict]           # Volume data

# Callback system
def on_ticker(callback: callable) -> None           # Register ticker handler
def on_orderbook(callback: callable) -> None        # Register orderbook handler
await self._emit_ticker(ticker)                     # Trigger callbacks
```

## Main Entry Points
```python
# main.py
def main():
    modes = ["live", "sim", "ui", "backtest"]
    # Exchange initialization with API validation
    # Dynamic symbol detection via get_common_symbols_with_volume()
    # Single exchange fallback to all available symbols

def get_common_symbols_with_volume(exchanges, min_volume_usd=100000):
    # Cross-exchange symbol validation and volume filtering
    # Returns intersection of tradeable symbols
```

## Configuration System
```python
# config.py
class Config:
    def load_from_file(filename="config.json")
    # Environment variable override support
    # API key validation and demo credential handling

# config.json structure
{
  "exchanges": {
    "binance": {"api_key": "...", "api_secret": "...", "enabled": true},
    "bybit": {"api_key": "...", "api_secret": "...", "enabled": true}
  },
  "arbitrage": {
    "min_profit_threshold": 0.001,      # 0.1% minimum
    "max_trade_amount": 1000,
    "fee_buffer": 0.0001                # Extra fee buffer
  },
  "database": {
    "db_path": "arbot.db",
    "ticker_storage_interval_seconds": 10,
    "batch_size": 100,
    "cleanup_days": 30
  },
  "ui": {
    "update_interval_ms": 500,
    "max_opportunities_display": 20
  }
}
```

## Database Schema & Migration
```python
# database.py
class Database:
    async def _create_tables():
        # Creates database tables with standard REAL timestamp columns
        
    async def insert_tickers_batch(tickers: List[TickerRecord]):
        # Batch operations for performance
        
    async def cleanup_old_data(days=30):
        # Automatic cleanup of old ticker data

# Timestamp storage
# Uses Unix timestamps (float) for efficient storage and processing
```

## Strategy Implementation
```python
# strategy.py
class ArbitrageStrategy:
    def __init__(config, exchanges, database):
        self.min_profit_threshold = config.arbitrage.min_profit_threshold
        self.exchange_fees = {}  # Cached fee structures
        
    async def analyze_arbitrage(ticker_data):
        # Cross-exchange price comparison
        # Fee calculation and profit validation
        # Signal generation with confidence scoring
        
    async def _calculate_arbitrage_profit(buy_ticker, sell_ticker, fees):
        # Profit = sell_price * (1 - sell_fee) - buy_price * (1 + buy_fee)
        # Accounts for maker/taker fees per exchange
        
    async def load_trading_fees():
        # Cache trading fees with 24h expiry
        # Fallback to default 0.1% if API fails
```

## WebSocket Implementation Details
```python
# exchanges/binance.py
class BinanceExchange:
    async def connect_ws(symbols):
        # Max 200 symbols per connection
        # Stream format: f"{symbol.lower()}@ticker"
        # Handles both combined and individual message formats
        # Auto-reconnection with exponential backoff
        
    async def _handle_ticker_data(data):
        # Processes both formats:
        # Combined: {'stream': 'btcusdt@ticker', 'data': {...}}
        # Individual: {'e': '24hrTicker', 's': 'BTCUSDT', ...}

# exchanges/bybit.py  
class BybitExchange:
    async def connect_ws(symbols):
        # Subscription: f"tickers.{symbol}" and f"orderbook.1.{symbol}"
        # Handles invalid symbol errors gracefully
        # Connection tracking with subscription counting
```

## GUI Architecture
```python
# gui.py
class ArBotGUI:
    def __init__(exchanges=None):
        # Accepts pre-initialized exchanges for UI mode
        # Dual callback system for spreads and storage
        
    # Core displays
    def update_spreads_display():           # Real-time arbitrage spreads
        # Single exchange: bid-ask spread display
        # Multi exchange: cross-exchange arbitrage
        
    def update_balance_display():           # Account balances with USD values
    def update_opportunities_display():     # Top arbitrage signals sorted by profit
    def update_trades_display():           # Trade history with P&L
    def update_status_display():           # Connection status and statistics
    
    # Data flow callbacks
    async def _on_ticker_for_spreads(ticker, exchange_name):
        # Real-time spread calculation and GUI updates
        # Maintains latest ticker cache per exchange
        
    async def _on_ticker_for_storage(ticker, exchange_name):
        # Batch storage with configurable intervals
        # Unix timestamp storage
        # Batch size management and auto-flush
        
    async def _on_arbitrage_signal(signal):
        # Signal processing and opportunity tracking
        # Profit-based sorting and display limiting
        
    # WebSocket management
    def start_trading():
        # Initiates WebSocket connections for all enabled exchanges
        # Registers ticker callbacks with exchange name closure
        
    def stop_trading():
        # Graceful WebSocket disconnection
        # Flushes pending batch data
        
    # Controls and settings
    def toggle_auto_trade():               # Enable/disable automatic trading
    def refresh_balances():               # Manual balance refresh
    def clear_opportunities():            # Clear opportunity history
```

## Exchange-Specific Implementation
```python
# Binance specifics
- Rate limit: Aggressive IP bans for REST API overuse
- WebSocket limit: 200 streams per connection max
- Message format: Both combined stream and individual ticker
- Fee structure: makerCommission/takerCommission from account API
- Symbol filter: Active trading status required

# Bybit specifics  
- WebSocket: tickers.{symbol} and orderbook.1.{symbol}
- Invalid symbols: Graceful error handling with regex parsing
- Fee structure: makerFeeRate/takerFeeRate from fee API
- Subscription tracking: Success/failure counting for status display
```

## Error Handling Patterns
```python
# Common error scenarios and solutions:
1. Rate limit errors (Binance -1003):
   - Solution: WebSocket-only data feeds, no REST polling
   
2. Invalid symbols (Bybit):
   - Solution: Exchange-specific symbol filtering and fallback lists
   
3. WebSocket disconnections:
   - Solution: Auto-reconnection with exponential backoff
   
4. AttributeError on data structures:
   - Common: profit_percentage -> profit_percent
   - Common: amount -> profit
   
5. Timestamp format inconsistencies:
   - Solution: Standardized Unix timestamp format
```

## Performance Optimizations
```python
# Batch operations
- Ticker storage: Configurable batch size (default 100)
- Database writes: Batch inserts with single transaction
- GUI updates: Rate-limited to prevent UI freezing

# Memory management
- Opportunity history: Limited to last 10 signals
- Price history: Circular buffers with configurable periods
- Database cleanup: Automatic old data removal

# Network efficiency
- WebSocket-only data feeds (no REST polling)
- Connection pooling for REST API calls
- Compressed data structures for real-time processing
```

## Operational Modes Deep Dive
```python
# live mode
python -m arbot.main live --exchanges binance,bybit
# Real API keys, actual trading, full order execution

# sim mode  
python -m arbot.main sim --exchanges binance,bybit
# Live prices, mock orders, simulated fills and P&L

# ui mode
python -m arbot.main ui
# GUI interface with real-time displays, uses pre-initialized exchanges

# backtest mode
python -m arbot.main backtest --start 2024-01-01 --end 2024-01-31
# Historical data replay with strategy validation
```

## Symbol Management
```python
# Dynamic symbol detection (current implementation)
def get_common_symbols_with_volume(exchanges, min_volume_usd=100000):
    # 1. Get all symbols from each exchange
    # 2. Find intersection of symbols between exchanges  
    # 3. Filter by minimum volume requirement
    # 4. Fallback to exchange-specific symbols for single exchange
    
# Exchange-specific filtering
BINANCE_PROBLEMATIC_SYMBOLS = []  # Currently none
BYBIT_PROBLEMATIC_SYMBOLS = [
    "MLNUSDT", "DEXEUSDT", "STORJUSDT", "KNCUSDT", ...
]
```

## Debugging and Monitoring
```python
# Logging patterns
logger.info(f"✅ {exchange} WebSocket connected: {len(symbols)} symbols")
logger.error(f"❌ {exchange} WebSocket failed: {error}")
logger.debug(f"🔍 Ticker data: {symbol} = {bid}/{ask}")

# Status indicators
print(f"✅ Binance 구독 완료: {symbol_count}개 심볼 (총 {stream_count}개 채널)")
print(f"⚠️ Bybit 구독 실패: Invalid symbol [{symbol}]")

# Performance metrics
- WebSocket message rates per exchange
- Arbitrage opportunity detection frequency
- Database batch operation timing
- GUI update rates and responsiveness
```

## Known Issues and Workarounds
```python
# 1. Binance rate limits
Problem: REST API requests trigger IP bans
Solution: WebSocket-only architecture, no REST ticker polling

# 2. Bybit invalid symbols
Problem: Some symbols not available on Bybit WebSocket
Solution: Pre-filtered symbol lists and graceful error handling  

# 3. GUI freezing
Problem: High-frequency ticker updates block UI thread
Solution: Rate-limited GUI updates and async callback processing

# 4. Database timestamp migration
Problem: Existing REAL timestamps need conversion to TEXT
Solution: Automatic migration on database initialization

# 5. Exchange disconnections
Problem: WebSocket connections drop unexpectedly
Solution: Auto-reconnection with exponential backoff and connection monitoring
```

## Testing and Validation
```python
# Unit tests focus areas:
- Symbol intersection logic
- Fee calculation accuracy
- Timestamp conversion correctness
- WebSocket message parsing
- Database migration integrity

# Integration tests:
- Exchange WebSocket connectivity
- Real-time data flow validation
- GUI responsiveness under load
- Multi-exchange arbitrage calculation

# Performance benchmarks:
- 200 symbols per exchange handling
- Batch storage operation timing
- Memory usage with extended runtime
- CPU utilization during peak data flow
```