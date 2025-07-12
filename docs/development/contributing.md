# Contributing to ArBot

We welcome contributions to ArBot! Whether you're fixing bugs, adding features, improving documentation, or helping with testing, your contributions make ArBot better for everyone.

## How to Contribute

### 🐛 Reporting Bugs

**Before submitting a bug report:**
1. Check if the issue already exists in [GitHub Issues](https://github.com/FinAI6/arbot/issues)
2. Test with the latest version of ArBot
3. Reproduce the issue in simulation mode if possible

**When submitting a bug report, include:**
- ArBot version and Python version
- Operating system and environment details
- Clear steps to reproduce the issue
- Expected vs actual behavior
- Relevant log files or error messages
- Configuration settings (remove sensitive data)

**Bug Report Template:**
```markdown
## Bug Description
Brief description of the issue

## Environment
- ArBot version: 1.2.0
- Python version: 3.11.5
- OS: Ubuntu 22.04
- Exchange APIs: Binance, Bybit

## Steps to Reproduce
1. Configure settings with...
2. Start the bot in simulation mode
3. Wait for 5 minutes
4. Observe the error

## Expected Behavior
The bot should continue monitoring without errors

## Actual Behavior
Error message appears and monitoring stops

## Logs
```
[Include relevant log entries]
```

## Additional Context
Any other relevant information
```

### 💡 Suggesting Features

**Feature Request Guidelines:**
- Explain the problem your feature would solve
- Describe the proposed solution clearly
- Consider alternative approaches
- Think about potential impacts on existing functionality

**Feature Request Template:**
```markdown
## Feature Description
Clear description of the proposed feature

## Problem Statement
What problem does this solve?

## Proposed Solution
How would this feature work?

## Alternatives Considered
What other approaches did you consider?

## Additional Context
Screenshots, mockups, or examples
```

### 🔧 Contributing Code

#### Setting Up Development Environment

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/arbot.git
   cd arbot
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

4. **Install Pre-commit Hooks**
   ```bash
   pre-commit install
   ```

#### Development Workflow

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Follow the coding standards (see below)
   - Add tests for new functionality
   - Update documentation as needed

3. **Test Your Changes**
   ```bash
   # Run tests
   python -m pytest tests/
   
   # Run specific test
   python -m pytest tests/test_strategy.py
   
   # Test in simulation mode
   python -m arbot.main --mode=gui
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add trend filtering for arbitrage signals"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

#### Pull Request Guidelines

**Before submitting a PR:**
- ✅ All tests pass
- ✅ Code follows style guidelines
- ✅ Documentation is updated
- ✅ Changes are well-tested
- ✅ Commit messages follow conventions

**PR Description Template:**
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed
- [ ] Tested in simulation mode
- [ ] Tested with multiple exchanges

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or breaking changes documented)
```

## Coding Standards

### Python Style Guide

**Follow PEP 8 with these specifics:**

```python
# Line length: 88 characters (Black formatter default)
# Use type hints
def calculate_spread(higher_price: float, lower_price: float) -> float:
    return (higher_price - lower_price) / lower_price

# Docstrings for all public methods
def process_arbitrage_signal(self, signal: ArbitrageSignal) -> bool:
    """
    Process an arbitrage signal and determine if trade should execute.
    
    Args:
        signal: Arbitrage signal with price and exchange data
        
    Returns:
        bool: True if trade should be executed, False otherwise
        
    Raises:
        ValueError: If signal data is invalid
    """
    pass

# Use meaningful variable names
is_profitable_opportunity = signal.profit_percent > threshold
exchange_with_higher_price = signal.sell_exchange

# Constants in UPPER_CASE
DEFAULT_PROFIT_THRESHOLD = 0.005
MAX_CONCURRENT_TRADES = 3
```

### Code Organization

**File Structure:**
```
arbot/
├── __init__.py          # Package initialization
├── main.py              # Application entry point
├── config.py            # Configuration management
├── strategy.py          # Core arbitrage logic
├── trader.py            # Trade execution
├── simulator.py         # Simulation mode
├── gui.py               # User interface
├── database.py          # Data persistence
└── exchanges/           # Exchange adapters
    ├── __init__.py
    ├── base.py          # Base exchange interface
    ├── binance.py       # Binance implementation
    └── bybit.py         # Bybit implementation
```

**Import Organization:**
```python
# Standard library imports
import asyncio
import time
from typing import Dict, List, Optional

# Third-party imports
import aiohttp
import numpy as np

# Local imports
from .config import Config
from .database import Database
from .exchanges.base import BaseExchange
```

### Async/Await Patterns

**Consistent Async Patterns:**
```python
# Use async/await consistently
async def fetch_price_data(self, symbol: str) -> Dict[str, float]:
    async with self.session.get(f"/api/ticker/{symbol}") as response:
        data = await response.json()
        return data

# Handle exceptions in async code
async def safe_api_call(self, func, *args, **kwargs):
    try:
        return await func(*args, **kwargs)
    except aiohttp.ClientError as e:
        logger.error(f"API call failed: {e}")
        return None

# Use asyncio.gather for concurrent operations
async def fetch_all_prices(self, symbols: List[str]):
    tasks = [self.fetch_price_data(symbol) for symbol in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### Error Handling

**Consistent Error Handling:**
```python
# Use specific exception types
class ArbitrageError(Exception):
    """Base exception for arbitrage-related errors"""
    pass

class InsufficientLiquidityError(ArbitrageError):
    """Raised when liquidity is insufficient for trade"""
    pass

# Handle errors appropriately
async def execute_trade(self, signal: ArbitrageSignal):
    try:
        await self.validate_signal(signal)
        result = await self.place_orders(signal)
        return result
    except InsufficientLiquidityError:
        logger.warning(f"Skipping trade due to low liquidity: {signal.symbol}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in trade execution: {e}")
        raise
```

### Testing Guidelines

#### Unit Tests

**Test Structure:**
```python
import pytest
from unittest.mock import Mock, patch, AsyncMock
from arbot.strategy import ArbitrageStrategy

class TestArbitrageStrategy:
    @pytest.fixture
    def strategy(self, mock_config, mock_database):
        return ArbitrageStrategy(mock_config, mock_database)
    
    @pytest.mark.asyncio
    async def test_calculate_arbitrage_profitable(self, strategy):
        # Arrange
        buy_exchange = Mock()
        buy_exchange.ticker.ask = 100.0
        sell_exchange = Mock()
        sell_exchange.ticker.bid = 102.0
        
        # Act
        signal = strategy._calculate_arbitrage(buy_exchange, sell_exchange, "BTCUSDT")
        
        # Assert
        assert signal is not None
        assert signal.profit_percent > 0
```

#### Integration Tests

**Test Real Scenarios:**
```python
@pytest.mark.integration
class TestArbitrageIntegration:
    @pytest.mark.asyncio
    async def test_full_arbitrage_detection_flow(self, test_config):
        # Setup real strategy with test configuration
        strategy = ArbitrageStrategy(test_config, test_database)
        
        # Simulate real ticker data
        ticker1 = Ticker("BTCUSDT", "binance", 100.0, 100.1, time.time())
        ticker2 = Ticker("BTCUSDT", "bybit", 102.0, 102.1, time.time())
        
        # Test detection flow
        await strategy._on_ticker_update(ticker1)
        await strategy._on_ticker_update(ticker2)
        
        # Verify arbitrage detected
        assert len(strategy.recent_signals) > 0
```

### Documentation Standards

#### Code Documentation

**Docstring Format:**
```python
def calculate_moving_average(self, prices: List[float], period: int) -> float:
    """
    Calculate simple moving average for given prices.
    
    Args:
        prices: List of price values, must be non-empty
        period: Number of periods for moving average, must be positive
        
    Returns:
        float: Simple moving average of the last 'period' prices
        
    Raises:
        ValueError: If prices is empty or period is not positive
        
    Example:
        >>> strategy = ArbitrageStrategy(config, db)
        >>> prices = [100.0, 101.0, 102.0, 103.0, 104.0]
        >>> ma = strategy.calculate_moving_average(prices, 3)
        >>> print(f"MA(3): {ma}")
        MA(3): 103.0
    """
```

#### Configuration Documentation

**Document All Config Options:**
```python
@dataclass
class ArbitrageConfig:
    min_profit_threshold: float = 0.005
    """Minimum profit percentage required to trigger arbitrage trade.
    
    Range: 0.001 - 0.1 (0.1% - 10%)
    Default: 0.005 (0.5%)
    
    Lower values increase trade frequency but may reduce profitability
    due to fees and slippage. Higher values reduce opportunities but
    improve profit quality.
    """
```

## Development Tools

### Required Tools

**Code Quality:**
```bash
# Install development dependencies
pip install black isort flake8 mypy pytest pytest-asyncio
```

**Pre-commit Configuration (`.pre-commit-config.yaml`):**
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.9.1
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
```

### Development Commands

**Code Formatting:**
```bash
# Format code with Black
black arbot/ tests/

# Sort imports with isort
isort arbot/ tests/

# Check code style with flake8
flake8 arbot/ tests/

# Type checking with mypy
mypy arbot/
```

**Testing:**
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=arbot tests/

# Run specific test file
pytest tests/test_strategy.py

# Run tests with specific markers
pytest -m integration
```

## Exchange Integration

### Adding New Exchange Support

**Step-by-Step Guide:**

1. **Create Exchange Adapter**
   ```python
   # arbot/exchanges/newexchange.py
   from .base import BaseExchange
   
   class NewExchangeExchange(BaseExchange):
       def __init__(self, config: ExchangeConfig):
           super().__init__(config)
           # Initialize exchange-specific client
       
       async def connect_ws(self):
           # Implement WebSocket connection
           pass
       
       async def place_order(self, symbol, side, amount, price):
           # Implement order placement
           pass
   ```

2. **Update Factory**
   ```python
   # arbot/exchanges/__init__.py
   from .newexchange import NewExchangeExchange
   
   SUPPORTED_EXCHANGES = {
       'binance': BinanceExchange,
       'bybit': BybitExchange,
       'newexchange': NewExchangeExchange,  # Add here
   }
   ```

3. **Add Configuration**
   ```python
   # Update config.py with new exchange settings
   # Add environment variable support
   # Update validation logic
   ```

4. **Write Tests**
   ```python
   # tests/exchanges/test_newexchange.py
   class TestNewExchangeExchange:
       def test_initialization(self):
           # Test exchange initialization
           pass
       
       @pytest.mark.asyncio
       async def test_websocket_connection(self):
           # Test WebSocket connectivity
           pass
   ```

5. **Update Documentation**
   - Add exchange to supported list
   - Document API key requirements
   - Update configuration examples

## Release Process

### Version Numbering

**Semantic Versioning (semver.org):**
- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Commit Message Convention

**Format:**
```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

**Examples:**
```bash
feat(strategy): add trend filtering for arbitrage signals
fix(gui): resolve column sorting issue in price table
docs(api): update exchange integration guide
```

## Community Guidelines

### Code of Conduct

**Our Standards:**
- Use welcoming and inclusive language
- Be respectful of differing viewpoints
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards other members

### Getting Help

**Resources:**
- 📖 [Documentation](https://finai6.github.io/arbot/)
- 🐛 [GitHub Issues](https://github.com/FinAI6/arbot/issues)
- 💬 [Discussions](https://github.com/FinAI6/arbot/discussions)
- 📧 [Email Support](mailto:geniuskey@gmail.com)

### Recognition

**Contributors are recognized through:**
- GitHub contributors page
- Release notes acknowledgments
- Documentation credits
- Community highlights

## Roadmap

### Current Priorities (v1.3.0)
- Advanced charting integration
- Machine learning price prediction
- Enhanced backtesting engine
- Mobile-responsive interface

### Future Vision (v2.0.0)
- Cross-chain arbitrage
- DeFi protocol integration
- Advanced portfolio management
- Cloud-native deployment

---

!!! tip "Getting Started"
    Start with small contributions like documentation improvements or bug fixes to familiarize yourself with the codebase before tackling major features.

!!! info "Questions?"
    Don't hesitate to ask questions in GitHub Discussions or open an issue for clarification on contribution guidelines.