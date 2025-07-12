# Testing Guide

ArBot implements a comprehensive testing strategy covering unit tests, integration tests, and end-to-end testing scenarios. This guide covers testing methodologies, frameworks, and best practices for ensuring system reliability.

## Testing Strategy Overview

### Testing Pyramid

```
       /\     End-to-End Tests
      /  \    (Few, Slow, Expensive)
     /____\   
    /      \  Integration Tests
   /        \ (Some, Medium Speed)
  /__________\
 /            \ Unit Tests
/______________\ (Many, Fast, Cheap)
```

**Test Distribution:**
- **Unit Tests**: 70% - Fast, isolated component testing
- **Integration Tests**: 20% - Component interaction testing
- **End-to-End Tests**: 10% - Full system workflow testing

### Testing Framework Stack

**Core Testing Tools:**
- **pytest**: Primary testing framework
- **pytest-asyncio**: Async test support
- **pytest-mock**: Mocking capabilities
- **pytest-cov**: Coverage reporting
- **httpx**: HTTP client testing
- **websockets**: WebSocket testing

**Installation:**
```bash
pip install pytest pytest-asyncio pytest-mock pytest-cov
pip install httpx websockets aioresponses
```

## Unit Testing

### Exchange Adapter Testing

**Test Structure:**
```python
# tests/test_exchanges/test_binance.py
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from arbot.exchanges.binance import BinanceExchange
from arbot.models import Ticker, OrderBook

class TestBinanceExchange:
    @pytest.fixture
    def exchange(self):
        config = {
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'testnet': True
        }
        return BinanceExchange(config)
    
    @pytest.mark.asyncio
    async def test_get_ticker_success(self, exchange):
        # Mock API response
        mock_response = {
            'symbol': 'BTCUSDT',
            'bidPrice': '43250.50',
            'askPrice': '43251.00',
            'bidQty': '2.5',
            'askQty': '1.8'
        }
        
        with patch.object(exchange, '_make_request', return_value=mock_response):
            ticker = await exchange.get_ticker('BTCUSDT')
            
            assert ticker.symbol == 'BTCUSDT'
            assert ticker.bid == 43250.50
            assert ticker.ask == 43251.00
            assert ticker.bid_size == 2.5
            assert ticker.ask_size == 1.8
    
    @pytest.mark.asyncio
    async def test_get_ticker_api_error(self, exchange):
        with patch.object(exchange, '_make_request', side_effect=Exception("API Error")):
            with pytest.raises(Exception, match="API Error"):
                await exchange.get_ticker('BTCUSDT')
    
    @pytest.mark.asyncio
    async def test_place_order_success(self, exchange):
        mock_response = {
            'orderId': 123456,
            'status': 'NEW',
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'type': 'MARKET',
            'quantity': '0.1'
        }
        
        with patch.object(exchange, '_make_request', return_value=mock_response):
            order = await exchange.place_order(
                symbol='BTCUSDT',
                side='BUY',
                order_type='MARKET',
                quantity=0.1
            )
            
            assert order.order_id == '123456'
            assert order.status == 'NEW'
            assert order.symbol == 'BTCUSDT'
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self, exchange):
        mock_websocket = AsyncMock()
        
        with patch('websockets.connect', return_value=mock_websocket):
            await exchange.connect_websocket()
            assert exchange.websocket is not None
    
    def test_rate_limit_compliance(self, exchange):
        # Test rate limiting logic
        exchange.last_request_time = asyncio.get_event_loop().time()
        
        # Should wait if requests are too frequent
        with patch('asyncio.sleep') as mock_sleep:
            exchange._check_rate_limit()
            mock_sleep.assert_called_once()
```

### Arbitrage Strategy Testing

```python
# tests/test_strategy.py
import pytest
from unittest.mock import MagicMock
from arbot.strategy import ArbitrageStrategy
from arbot.models import Ticker, ArbitrageSignal

class TestArbitrageStrategy:
    @pytest.fixture
    def strategy(self):
        config = {
            'min_profit_threshold': 0.005,
            'max_position_size': 1000.0,
            'slippage_tolerance': 0.001
        }
        return ArbitrageStrategy(config)
    
    def test_calculate_arbitrage_profit(self, strategy):
        # Test profitable scenario
        buy_ticker = Ticker(
            symbol='BTCUSDT',
            exchange='bybit',
            bid=43249.00,
            ask=43250.00,
            bid_size=5.0,
            ask_size=3.0,
            timestamp=1640995200.0
        )
        
        sell_ticker = Ticker(
            symbol='BTCUSDT',
            exchange='binance',
            bid=43260.00,
            ask=43261.00,
            bid_size=4.0,
            ask_size=2.0,
            timestamp=1640995200.0
        )
        
        profit = strategy.calculate_arbitrage(
            buy_exchange_ticker=buy_ticker,
            sell_exchange_ticker=sell_ticker
        )
        
        # Should buy at 43250 (ask) and sell at 43260 (bid)
        expected_gross_profit = 43260.00 - 43250.00  # 10.00
        expected_fees = (43250.00 * 0.001) + (43260.00 * 0.001)  # ~86.51
        expected_net_profit = expected_gross_profit - expected_fees
        
        assert abs(profit.net_profit - expected_net_profit) < 0.01
        assert profit.profit_percent > 0
    
    def test_insufficient_profit(self, strategy):
        # Test scenario with insufficient profit
        buy_ticker = Ticker(
            symbol='BTCUSDT',
            exchange='bybit',
            bid=43249.00,
            ask=43250.00,
            bid_size=5.0,
            ask_size=3.0,
            timestamp=1640995200.0
        )
        
        sell_ticker = Ticker(
            symbol='BTCUSDT',
            exchange='binance',
            bid=43251.00,  # Only 1 USD spread
            ask=43252.00,
            bid_size=4.0,
            ask_size=2.0,
            timestamp=1640995200.0
        )
        
        profit = strategy.calculate_arbitrage(
            buy_exchange_ticker=buy_ticker,
            sell_exchange_ticker=sell_ticker
        )
        
        # Should not be profitable after fees
        assert profit.profit_percent < strategy.config['min_profit_threshold']
    
    def test_trend_filter(self, strategy):
        strategy.config['use_trend_filter'] = True
        strategy.config['trend_filter_mode'] = 'uptrend_buy_low'
        
        # Mock trend detection
        with patch.object(strategy, 'detect_trend', return_value='uptrend'):
            result = strategy.should_execute_based_on_trend('BTCUSDT')
            assert result is True
        
        with patch.object(strategy, 'detect_trend', return_value='downtrend'):
            result = strategy.should_execute_based_on_trend('BTCUSDT')
            assert result is False
    
    def test_signal_generation(self, strategy):
        tickers = {
            'binance': {
                'BTCUSDT': Ticker(
                    symbol='BTCUSDT',
                    exchange='binance',
                    bid=43260.00,
                    ask=43261.00,
                    bid_size=4.0,
                    ask_size=2.0,
                    timestamp=1640995200.0
                )
            },
            'bybit': {
                'BTCUSDT': Ticker(
                    symbol='BTCUSDT',
                    exchange='bybit',
                    bid=43249.00,
                    ask=43250.00,
                    bid_size=5.0,
                    ask_size=3.0,
                    timestamp=1640995200.0
                )
            }
        }
        
        signals = strategy.generate_signals(tickers)
        
        assert len(signals) > 0
        signal = signals[0]
        assert signal.symbol == 'BTCUSDT'
        assert signal.buy_exchange == 'bybit'
        assert signal.sell_exchange == 'binance'
        assert signal.profit_percent > strategy.config['min_profit_threshold']
```

### Database Testing

```python
# tests/test_database.py
import pytest
import asyncio
import tempfile
import os
from arbot.database import DatabaseManager
from arbot.models import Ticker, Trade

class TestDatabaseManager:
    @pytest.fixture
    async def db_manager(self):
        # Use temporary database for testing
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.close()
        
        db = DatabaseManager(temp_file.name)
        await db.initialize()
        
        yield db
        
        await db.close()
        os.unlink(temp_file.name)
    
    @pytest.mark.asyncio
    async def test_insert_ticker(self, db_manager):
        ticker = Ticker(
            symbol='BTCUSDT',
            exchange='binance',
            bid=43250.50,
            ask=43251.00,
            bid_size=2.5,
            ask_size=1.8,
            timestamp=1640995200.0
        )
        
        await db_manager.insert_ticker(ticker)
        
        # Verify insertion
        retrieved = await db_manager.get_latest_ticker('BTCUSDT', 'binance')
        assert retrieved.symbol == ticker.symbol
        assert retrieved.bid == ticker.bid
        assert retrieved.ask == ticker.ask
    
    @pytest.mark.asyncio
    async def test_get_price_history(self, db_manager):
        # Insert test data
        tickers = [
            Ticker('BTCUSDT', 'binance', 43250.0, 43251.0, 2.5, 1.8, 1640995200.0),
            Ticker('BTCUSDT', 'binance', 43255.0, 43256.0, 2.3, 1.9, 1640995260.0),
            Ticker('BTCUSDT', 'binance', 43260.0, 43261.0, 2.1, 2.0, 1640995320.0)
        ]
        
        for ticker in tickers:
            await db_manager.insert_ticker(ticker)
        
        # Query history
        history = await db_manager.get_price_history(
            symbol='BTCUSDT',
            exchange='binance',
            start_time=1640995200.0,
            end_time=1640995400.0
        )
        
        assert len(history) == 3
        assert history[0].timestamp == 1640995200.0
        assert history[-1].timestamp == 1640995320.0
    
    @pytest.mark.asyncio
    async def test_trade_lifecycle(self, db_manager):
        # Create a trade
        trade_data = {
            'symbol': 'BTCUSDT',
            'buy_exchange': 'bybit',
            'sell_exchange': 'binance',
            'planned_buy_price': 43250.0,
            'planned_sell_price': 43260.0,
            'quantity': 0.1,
            'planned_profit': 1.0
        }
        
        trade_id = await db_manager.create_trade(trade_data)
        assert trade_id is not None
        
        # Update trade execution
        execution_data = {
            'actual_buy_price': 43250.5,
            'actual_sell_price': 43259.5,
            'actual_profit': 0.9,
            'fees_paid': 0.1,
            'status': 'completed'
        }
        
        await db_manager.update_trade_execution(trade_id, execution_data)
        
        # Verify trade
        trade = await db_manager.get_trade(trade_id)
        assert trade.status == 'completed'
        assert trade.actual_profit == 0.9
```

## Integration Testing

### Exchange Integration Tests

```python
# tests/integration/test_exchange_integration.py
import pytest
import asyncio
from arbot.exchanges import ExchangeManager
from arbot.config import Config

class TestExchangeIntegration:
    @pytest.fixture
    async def exchange_manager(self):
        config = Config()
        config.exchanges = {
            'binance': {'enabled': True, 'testnet': True},
            'bybit': {'enabled': True, 'testnet': True}
        }
        
        manager = ExchangeManager(config)
        await manager.initialize()
        
        yield manager
        
        await manager.close()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multi_exchange_price_collection(self, exchange_manager):
        """Test collecting prices from multiple exchanges simultaneously"""
        
        # Start price collection
        await exchange_manager.start_price_collection(['BTCUSDT'])
        
        # Wait for some data
        await asyncio.sleep(5)
        
        # Check that we received data from both exchanges
        binance_ticker = exchange_manager.get_latest_ticker('BTCUSDT', 'binance')
        bybit_ticker = exchange_manager.get_latest_ticker('BTCUSDT', 'bybit')
        
        assert binance_ticker is not None
        assert bybit_ticker is not None
        assert binance_ticker.bid > 0
        assert bybit_ticker.bid > 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_order_book_synchronization(self, exchange_manager):
        """Test that order books are properly synchronized"""
        
        # Get order books from both exchanges
        binance_book = await exchange_manager.get_order_book('BTCUSDT', 'binance')
        bybit_book = await exchange_manager.get_order_book('BTCUSDT', 'bybit')
        
        # Verify order book structure
        assert len(binance_book.bids) > 0
        assert len(binance_book.asks) > 0
        assert len(bybit_book.bids) > 0
        assert len(bybit_book.asks) > 0
        
        # Verify price ordering
        assert binance_book.bids[0]['price'] >= binance_book.bids[-1]['price']
        assert binance_book.asks[0]['price'] <= binance_book.asks[-1]['price']
```

### End-to-End Trading Flow

```python
# tests/integration/test_trading_flow.py
import pytest
import asyncio
from unittest.mock import patch
from arbot.main import ArbitrageTradingBot
from arbot.config import Config

class TestTradingFlow:
    @pytest.fixture
    async def trading_bot(self):
        config = Config()
        config.trading_mode = 'simulation'
        config.arbitrage.min_profit_threshold = 0.001  # Lower threshold for testing
        
        bot = ArbitrageTradingBot(config)
        await bot.initialize()
        
        yield bot
        
        await bot.shutdown()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_complete_arbitrage_cycle(self, trading_bot):
        """Test complete arbitrage detection and execution cycle"""
        
        # Mock price data that creates arbitrage opportunity
        mock_tickers = {
            'binance': {
                'BTCUSDT': create_mock_ticker('BTCUSDT', 'binance', 43260, 43261)
            },
            'bybit': {
                'BTCUSDT': create_mock_ticker('BTCUSDT', 'bybit', 43250, 43251)
            }
        }
        
        # Start the bot
        trading_task = asyncio.create_task(trading_bot.run())
        
        # Inject mock data
        with patch.object(trading_bot.strategy, 'get_current_tickers', return_value=mock_tickers):
            # Wait for signal generation and execution
            await asyncio.sleep(10)
        
        # Stop the bot
        trading_bot.stop()
        await trading_task
        
        # Verify that trades were executed
        trades = await trading_bot.database.get_recent_trades(limit=10)
        assert len(trades) > 0
        
        # Verify trade details
        trade = trades[0]
        assert trade.symbol == 'BTCUSDT'
        assert trade.buy_exchange == 'bybit'
        assert trade.sell_exchange == 'binance'
        assert trade.status in ['completed', 'pending']

def create_mock_ticker(symbol, exchange, bid, ask):
    return Ticker(
        symbol=symbol,
        exchange=exchange,
        bid=bid,
        ask=ask,
        bid_size=5.0,
        ask_size=3.0,
        timestamp=time.time()
    )
```

## Performance Testing

### Load Testing

```python
# tests/performance/test_load.py
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from arbot.exchanges.binance import BinanceExchange

class TestPerformance:
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_api_requests(self):
        """Test handling of concurrent API requests"""
        
        exchange = BinanceExchange({'testnet': True})
        
        async def make_request():
            return await exchange.get_ticker('BTCUSDT')
        
        # Test with 50 concurrent requests
        start_time = time.time()
        tasks = [make_request() for _ in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Check that most requests succeeded
        successful_requests = sum(1 for r in results if not isinstance(r, Exception))
        assert successful_requests >= 45  # Allow for some failures
        
        # Check performance
        avg_time_per_request = (end_time - start_time) / len(tasks)
        assert avg_time_per_request < 1.0  # Should be under 1 second per request
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_database_performance(self):
        """Test database performance under load"""
        
        db_manager = DatabaseManager(':memory:')  # In-memory for speed
        await db_manager.initialize()
        
        # Insert many tickers rapidly
        start_time = time.time()
        
        tasks = []
        for i in range(1000):
            ticker = Ticker(
                symbol='BTCUSDT',
                exchange='binance',
                bid=43250.0 + i,
                ask=43251.0 + i,
                bid_size=2.5,
                ask_size=1.8,
                timestamp=time.time() + i
            )
            tasks.append(db_manager.insert_ticker(ticker))
        
        await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Should handle 1000 inserts in under 5 seconds
        assert (end_time - start_time) < 5.0
        
        # Verify data integrity
        count = await db_manager.count_tickers()
        assert count == 1000
```

### Memory Usage Testing

```python
# tests/performance/test_memory.py
import pytest
import psutil
import gc
from arbot.strategy import ArbitrageStrategy

class TestMemoryUsage:
    @pytest.mark.performance
    def test_memory_leak_detection(self):
        """Test for memory leaks in long-running operations"""
        
        strategy = ArbitrageStrategy({})
        process = psutil.Process()
        
        # Baseline memory usage
        initial_memory = process.memory_info().rss
        
        # Simulate long-running operation
        for i in range(1000):
            # Create and process many ticker objects
            tickers = {
                'binance': {
                    'BTCUSDT': create_mock_ticker('BTCUSDT', 'binance', 43250 + i, 43251 + i)
                },
                'bybit': {
                    'BTCUSDT': create_mock_ticker('BTCUSDT', 'bybit', 43260 + i, 43261 + i)
                }
            }
            
            signals = strategy.generate_signals(tickers)
            
            # Periodically force garbage collection
            if i % 100 == 0:
                gc.collect()
        
        # Final memory usage
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024
```

## Test Configuration

### pytest.ini

```ini
[tool:pytest]
addopts = 
    --strict-markers
    --strict-config
    --cov=arbot
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80

markers =
    integration: Integration tests
    performance: Performance tests
    slow: Slow-running tests
    unit: Unit tests (default)

testpaths = tests

python_files = test_*.py
python_classes = Test*
python_functions = test_*

filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning

log_cli = true
log_cli_level = INFO
log_cli_format = %(asctime)s [%(levelname)8s] %(message)s
log_cli_date_format = %Y-%m-%d %H:%M:%S
```

### Test Fixtures

```python
# tests/conftest.py
import pytest
import asyncio
import tempfile
import os
from unittest.mock import MagicMock

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_config():
    """Provide a mock configuration for testing."""
    return {
        'arbitrage': {
            'min_profit_threshold': 0.005,
            'max_position_size': 1000.0,
            'trade_amount_usd': 100.0
        },
        'exchanges': {
            'binance': {'enabled': True, 'testnet': True},
            'bybit': {'enabled': True, 'testnet': True}
        },
        'database': {
            'url': ':memory:'  # Use in-memory database for tests
        }
    }

@pytest.fixture
def temp_database():
    """Provide a temporary database file for testing."""
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.close()
    
    yield temp_file.name
    
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)

@pytest.fixture
def mock_exchange_response():
    """Provide mock exchange API responses."""
    return {
        'ticker': {
            'symbol': 'BTCUSDT',
            'bidPrice': '43250.50',
            'askPrice': '43251.00',
            'bidQty': '2.5',
            'askQty': '1.8'
        },
        'balance': {
            'USDT': {'free': '10000.00', 'locked': '0.00'},
            'BTC': {'free': '0.5', 'locked': '0.0'}
        },
        'order': {
            'orderId': 123456,
            'status': 'NEW',
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'type': 'MARKET',
            'quantity': '0.1'
        }
    }
```

## Continuous Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run unit tests
      run: |
        pytest tests/unit/ -v --cov=arbot --cov-report=xml
    
    - name: Run integration tests
      run: |
        pytest tests/integration/ -v -m "not slow"
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

  performance:
    runs-on: ubuntu-latest
    needs: test
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run performance tests
      run: |
        pytest tests/performance/ -v --tb=short
```

## Test Data Management

### Test Data Fixtures

```python
# tests/data/fixtures.py
from datetime import datetime, timedelta
from arbot.models import Ticker, Trade, ArbitrageSignal

class TestDataFactory:
    @staticmethod
    def create_ticker(symbol='BTCUSDT', exchange='binance', **kwargs):
        defaults = {
            'bid': 43250.00,
            'ask': 43251.00,
            'bid_size': 2.5,
            'ask_size': 1.8,
            'timestamp': datetime.now().timestamp()
        }
        defaults.update(kwargs)
        
        return Ticker(
            symbol=symbol,
            exchange=exchange,
            **defaults
        )
    
    @staticmethod
    def create_arbitrage_signal(**kwargs):
        defaults = {
            'symbol': 'BTCUSDT',
            'buy_exchange': 'bybit',
            'sell_exchange': 'binance',
            'buy_price': 43250.00,
            'sell_price': 43260.00,
            'profit': 10.00,
            'profit_percent': 0.023,
            'confidence': 0.85,
            'timestamp': datetime.now().timestamp()
        }
        defaults.update(kwargs)
        
        return ArbitrageSignal(**defaults)
    
    @staticmethod
    def create_trade(**kwargs):
        defaults = {
            'symbol': 'BTCUSDT',
            'buy_exchange': 'bybit',
            'sell_exchange': 'binance',
            'quantity': 0.1,
            'planned_profit': 2.50,
            'actual_profit': 2.35,
            'status': 'completed',
            'started_at': datetime.now(),
            'completed_at': datetime.now() + timedelta(seconds=45)
        }
        defaults.update(kwargs)
        
        return Trade(**defaults)
```

## Running Tests

### Command Line Usage

```bash
# Run all tests
pytest

# Run only unit tests
pytest tests/unit/

# Run tests with coverage
pytest --cov=arbot --cov-report=html

# Run specific test file
pytest tests/test_strategy.py

# Run tests matching pattern
pytest -k "test_arbitrage"

# Run tests with specific markers
pytest -m integration
pytest -m "not slow"

# Run tests in parallel
pytest -n auto  # Requires pytest-xdist

# Run with verbose output
pytest -v

# Run with specific log level
pytest --log-cli-level=DEBUG
```

### Test Organization

```
tests/
├── conftest.py              # Global fixtures
├── unit/
│   ├── test_strategy.py     # Strategy unit tests
│   ├── test_exchanges/      # Exchange adapter tests
│   │   ├── test_binance.py
│   │   └── test_bybit.py
│   ├── test_database.py     # Database tests
│   └── test_models.py       # Data model tests
├── integration/
│   ├── test_exchange_integration.py
│   ├── test_trading_flow.py
│   └── test_api_integration.py
├── performance/
│   ├── test_load.py         # Load testing
│   └── test_memory.py       # Memory usage tests
└── data/
    ├── fixtures.py          # Test data factories
    └── sample_data/         # Sample data files
```

!!! tip "Test-Driven Development"
    Write tests before implementing features. This ensures better design and helps catch issues early in the development process.

!!! warning "Test Data Security"
    Never use real API keys or production data in tests. Always use testnet environments and mock data for testing.

!!! note "Performance Testing"
    Run performance tests regularly to catch performance regressions early. Set up automated performance benchmarks in CI/CD pipeline.