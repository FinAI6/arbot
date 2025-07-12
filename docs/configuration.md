# Configuration Guide

ArBot uses a flexible configuration system that supports multiple sources and environments. This guide covers all configuration options and best practices.

## Configuration Sources

ArBot loads configuration from multiple sources in this order (later sources override earlier ones):

1. **Default Configuration** - Built-in defaults
2. **Main Config File** - `config.json`
3. **Local Config File** - `config.local.json` (git-ignored)
4. **Environment Variables** - `.env` file and system environment

## Configuration Files

### Main Configuration (`config.json`)

The primary configuration file that should be committed to version control:

```json
{
  "trading_mode": "simulation",
  "exchanges": {
    "binance": {
      "enabled": true,
      "arbitrage_enabled": true,
      "testnet": false,
      "region": "global",
      "premium_baseline": 0.0
    },
    "bybit": {
      "enabled": true,
      "arbitrage_enabled": true,
      "testnet": false,
      "region": "global",
      "premium_baseline": 0.0
    }
  },
  "arbitrage": {
    "min_profit_threshold": 0.005,
    "max_position_size": 1000.0,
    "trade_amount_usd": 100.0,
    "max_symbols": 200,
    "slippage_tolerance": 0.001,
    "max_spread_age_seconds": 5.0,
    "use_dynamic_symbols": true,
    "max_spread_threshold": 2.0,
    "enabled_quote_currencies": ["USDT"],
    "available_quote_currencies": ["USDT", "BUSD", "USDC", "BTC", "ETH", "BNB"],
    "moving_average_periods": 30,
    "use_trend_filter": true,
    "trend_filter_mode": "uptrend_buy_low",
    "trend_confirmation_threshold": 0.001,
    "premium_detection": {
      "enabled": true,
      "lookback_periods": 100,
      "min_samples": 70,
      "outlier_threshold": 2.0
    }
  },
  "risk_management": {
    "max_drawdown_percent": 5.0,
    "stop_loss_percent": 2.0,
    "position_sizing_method": "fixed",
    "max_concurrent_trades": 3,
    "balance_threshold_percent": 10.0
  },
  "database": {
    "db_path": "arbot.db",
    "backup_interval_hours": 24,
    "max_history_days": 30
  },
  "ui": {
    "refresh_rate_ms": 500,
    "enable_notifications": true,
    "log_level": "INFO",
    "theme": "dark"
  },
  "backtest": {
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "initial_balance": 10000.0,
    "data_source": "database"
  }
}
```

### Local Configuration (`config.local.json`)

Personal settings that override main config (not committed to git):

```json
{
  "trading_mode": "live",
  "arbitrage": {
    "min_profit_threshold": 0.01,
    "trade_amount_usd": 250.0,
    "max_symbols": 100
  },
  "exchanges": {
    "okx": {
      "enabled": true,
      "arbitrage_enabled": true
    },
    "bitget": {
      "enabled": false,
      "arbitrage_enabled": false
    }
  },
  "risk_management": {
    "max_drawdown_percent": 3.0,
    "stop_loss_percent": 1.5
  }
}
```

### Environment Variables (`.env`)

Sensitive configuration like API keys:

```bash
# Exchange API Keys
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_secret_here
BINANCE_TESTNET=false

BYBIT_API_KEY=your_bybit_api_key_here
BYBIT_API_SECRET=your_bybit_secret_here
BYBIT_TESTNET=false

OKX_API_KEY=your_okx_api_key_here
OKX_API_SECRET=your_okx_secret_here
OKX_TESTNET=false

BITGET_API_KEY=your_bitget_api_key_here
BITGET_API_SECRET=your_bitget_secret_here
BITGET_TESTNET=false

# Application Settings
TRADING_MODE=simulation
DATABASE_PATH=data/arbot.db
LOG_LEVEL=INFO
```

## Configuration Sections

### Trading Mode

Controls the bot's operational mode:

```json
{
  "trading_mode": "simulation"
}
```

**Options:**
- `"simulation"` - Paper trading with live data
- `"live"` - Real trading with real money
- `"backtest"` - Historical data analysis

### Exchange Configuration

Configure which exchanges to use and how:

```json
{
  "exchanges": {
    "binance": {
      "enabled": true,
      "arbitrage_enabled": true,
      "testnet": false,
      "region": "global",
      "premium_baseline": 0.0
    }
  }
}
```

**Parameters:**
- `enabled`: Whether to connect to this exchange
- `arbitrage_enabled`: Include in arbitrage calculations
- `testnet`: Use testnet/sandbox environment
- `region`: Exchange region (global, us, etc.)
- `premium_baseline`: Expected premium for this exchange

### Arbitrage Settings

Core arbitrage detection parameters:

```json
{
  "arbitrage": {
    "min_profit_threshold": 0.005,
    "max_position_size": 1000.0,
    "trade_amount_usd": 100.0,
    "max_symbols": 200,
    "slippage_tolerance": 0.001,
    "max_spread_age_seconds": 5.0
  }
}
```

**Key Parameters:**

| Parameter | Description | Default | Range |
|-----------|-------------|---------|-------|
| `min_profit_threshold` | Minimum profit % to trigger trade | 0.005 | 0.001-0.1 |
| `max_position_size` | Maximum USD per trade | 1000.0 | 10-100000 |
| `trade_amount_usd` | Standard trade size | 100.0 | 10-10000 |
| `max_symbols` | Maximum pairs to monitor | 200 | 10-1000 |
| `slippage_tolerance` | Expected slippage % | 0.001 | 0.0001-0.01 |
| `max_spread_age_seconds` | Max age of price data | 5.0 | 1.0-60.0 |

### Symbol Management

Control which trading pairs to monitor:

```json
{
  "arbitrage": {
    "use_dynamic_symbols": true,
    "max_symbols": 200,
    "enabled_quote_currencies": ["USDT"],
    "available_quote_currencies": ["USDT", "BUSD", "USDC", "BTC", "ETH", "BNB"]
  }
}
```

**Dynamic Symbol Selection:**
- When `use_dynamic_symbols` is `true`, bot auto-selects high-volume pairs
- `max_symbols` limits total number monitored
- Only pairs with `enabled_quote_currencies` are included

### Moving Averages and Trends

Configure trend analysis:

```json
{
  "arbitrage": {
    "moving_average_periods": 30,
    "use_trend_filter": true,
    "trend_filter_mode": "uptrend_buy_low",
    "trend_confirmation_threshold": 0.001
  }
}
```

**Trend Filter Modes:**
- `"uptrend_buy_low"` - Only trade during uptrends
- `"downtrend_sell_high"` - Only trade during downtrends  
- `"both"` - Trade in any trend direction
- `"disabled"` - No trend filtering

### Premium Detection

Identify exchange-specific pricing patterns:

```json
{
  "arbitrage": {
    "premium_detection": {
      "enabled": true,
      "lookback_periods": 100,
      "min_samples": 70,
      "outlier_threshold": 2.0
    }
  }
}
```

**Parameters:**
- `lookback_periods`: Historical periods to analyze
- `min_samples`: Minimum data points required
- `outlier_threshold`: Standard deviations for outlier detection

### Risk Management

Protect against losses:

```json
{
  "risk_management": {
    "max_drawdown_percent": 5.0,
    "stop_loss_percent": 2.0,
    "position_sizing_method": "fixed",
    "max_concurrent_trades": 3,
    "balance_threshold_percent": 10.0
  }
}
```

**Risk Controls:**
- `max_drawdown_percent`: Stop trading if losses exceed this %
- `stop_loss_percent`: Individual trade stop loss
- `position_sizing_method`: "fixed" or "kelly" criterion
- `max_concurrent_trades`: Limit simultaneous positions
- `balance_threshold_percent`: Stop if balance falls below this %

### Database Configuration

Data storage settings:

```json
{
  "database": {
    "db_path": "data/arbot.db",
    "backup_interval_hours": 24,
    "max_history_days": 30
  }
}
```

### UI Settings

Interface preferences:

```json
{
  "ui": {
    "refresh_rate_ms": 500,
    "enable_notifications": true,
    "log_level": "INFO",
    "theme": "dark"
  }
}
```

**Options:**
- `refresh_rate_ms`: How often to update display (100-5000ms)
- `log_level`: "DEBUG", "INFO", "WARNING", "ERROR"
- `theme`: "dark" or "light"

## Configuration Presets

### High-Frequency Trading

```json
{
  "arbitrage": {
    "min_profit_threshold": 0.001,
    "max_spread_age_seconds": 1.0,
    "max_symbols": 500
  },
  "ui": {
    "refresh_rate_ms": 100
  }
}
```

### Conservative Trading

```json
{
  "arbitrage": {
    "min_profit_threshold": 0.01,
    "max_spread_age_seconds": 10.0,
    "use_trend_filter": true,
    "trend_filter_mode": "uptrend_buy_low"
  },
  "risk_management": {
    "max_drawdown_percent": 2.0,
    "stop_loss_percent": 1.0,
    "max_concurrent_trades": 1
  }
}
```

### Simulation Mode

```json
{
  "trading_mode": "simulation",
  "arbitrage": {
    "min_profit_threshold": 0.005,
    "trade_amount_usd": 100.0
  },
  "ui": {
    "refresh_rate_ms": 1000
  }
}
```

## Configuration Validation

ArBot automatically validates configuration on startup:

### Common Validation Errors

```bash
❌ No exchanges configured
❌ At least 2 exchanges must be enabled for arbitrage
❌ API key missing for binance
❌ API secret missing for bybit
❌ No trading symbols configured
❌ Minimum profit threshold must be positive
❌ Trade amount must be positive
```

### Manual Validation

Test your configuration:

```bash
python scripts/debug_config.py
```

## Environment-Specific Configurations

### Development Environment

```json
{
  "trading_mode": "simulation",
  "arbitrage": {
    "max_symbols": 50,
    "min_profit_threshold": 0.001
  },
  "ui": {
    "log_level": "DEBUG",
    "refresh_rate_ms": 1000
  }
}
```

### Production Environment

```json
{
  "trading_mode": "live",
  "arbitrage": {
    "min_profit_threshold": 0.01,
    "use_trend_filter": true
  },
  "risk_management": {
    "max_drawdown_percent": 3.0,
    "stop_loss_percent": 1.5
  },
  "ui": {
    "log_level": "INFO",
    "refresh_rate_ms": 500
  }
}
```

## Configuration Management Best Practices

### 1. Version Control
- ✅ Commit `config.json` to git
- ❌ Never commit `config.local.json` or `.env`
- ✅ Use `.gitignore` to exclude sensitive files

### 2. Security
- ✅ Store API keys in `.env` file only
- ✅ Use different API keys for testing vs production
- ✅ Enable IP restrictions on exchange APIs
- ❌ Never hardcode secrets in configuration files

### 3. Environment Separation
- ✅ Use `config.local.json` for personal settings
- ✅ Use environment variables for deployment-specific settings
- ✅ Document all configuration options

### 4. Testing
- ✅ Test configuration changes in simulation mode first
- ✅ Validate configuration syntax before deployment
- ✅ Monitor logs for configuration-related errors

## Troubleshooting Configuration

### Configuration Not Loading
1. Check file syntax with JSON validator
2. Verify file permissions
3. Check for typos in parameter names
4. Review logs for specific error messages

### API Connection Issues
1. Verify API keys in `.env` file
2. Check API key permissions on exchange
3. Confirm IP whitelist settings
4. Test with exchange API documentation

### Performance Issues
1. Reduce `max_symbols` if using too much CPU
2. Increase `refresh_rate_ms` if GUI is slow
3. Adjust `max_spread_age_seconds` for network latency
4. Consider reducing `moving_average_periods`

!!! tip "Configuration Tips"
    - Start with default settings and modify incrementally
    - Use simulation mode to test configuration changes
    - Keep backups of working configurations
    - Monitor logs when changing critical parameters