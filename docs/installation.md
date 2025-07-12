# Installation Guide

This guide will help you install and set up ArBot on your system.

## Prerequisites

### System Requirements
- **Python**: 3.8 or higher
- **Operating System**: Windows, macOS, or Linux
- **Memory**: Minimum 2GB RAM (4GB recommended)
- **Storage**: 1GB free space for data and logs

### Exchange API Access
- API keys for supported exchanges (Binance, Bybit, OKX, Bitget)
- API permissions: Read market data, Execute trades (for live mode)

## Installation Methods

### Method 1: From Source (Recommended)

1. **Clone the Repository**
   ```bash
   git clone https://github.com/FinAI6/arbot.git
   cd arbot
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install ArBot**
   ```bash
   pip install -e .
   ```

### Method 2: Using Docker

1. **Pull and Run**
   ```bash
   docker pull finai6/arbot:latest
   docker run -d --name arbot \
     -v $(pwd)/config:/app/config \
     -v $(pwd)/data:/app/data \
     finai6/arbot:latest
   ```

2. **Or Build from Source**
   ```bash
   git clone https://github.com/FinAI6/arbot.git
   cd arbot
   docker build -t arbot .
   docker run -d --name arbot -v $(pwd)/data:/app/data arbot
   ```

### Method 3: PyPI Package (Future)

```bash
pip install arbot-trading
```

!!! note "Coming Soon"
    PyPI package distribution is planned for future releases.

## Configuration Setup

### 1. Environment Variables

Create a `.env` file in the project root:

```bash
# Exchange API Keys
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_secret

BYBIT_API_KEY=your_bybit_api_key
BYBIT_API_SECRET=your_bybit_secret

OKX_API_KEY=your_okx_api_key
OKX_API_SECRET=your_okx_secret

BITGET_API_KEY=your_bitget_api_key
BITGET_API_SECRET=your_bitget_secret

# Trading Configuration
TRADING_MODE=simulation
LOG_LEVEL=INFO
```

### 2. Configuration File

The `config.json` file will be created automatically with default settings:

```json
{
  "trading_mode": "simulation",
  "arbitrage": {
    "min_profit_threshold": 0.005,
    "max_symbols": 200,
    "enabled_quote_currencies": ["USDT"],
    "moving_average_periods": 30,
    "use_trend_filter": true,
    "trend_filter_mode": "uptrend_buy_low"
  },
  "exchanges": {
    "binance": {
      "enabled": true,
      "arbitrage_enabled": true
    },
    "bybit": {
      "enabled": true,
      "arbitrage_enabled": true
    }
  }
}
```

### 3. Local Configuration Override

Create `config.local.json` for personal settings that won't be committed to git:

```json
{
  "arbitrage": {
    "min_profit_threshold": 0.01,
    "trade_amount_usd": 250.0
  },
  "exchanges": {
    "okx": {
      "enabled": true,
      "arbitrage_enabled": true
    }
  }
}
```

## Verification

### Test Installation

```bash
python -c "import arbot; print('ArBot installed successfully!')"
```

### Run Basic Test

```bash
python -m arbot.main --help
```

Expected output:
```
usage: main.py [-h] [--mode {gui,cli,backtest}] [--config CONFIG]

ArBot - Arbitrage Trading Bot

optional arguments:
  -h, --help            show this help message and exit
  --mode {gui,cli,backtest}
                        Run mode (default: gui)
  --config CONFIG       Config file path (default: config.json)
```

### Test GUI Mode

```bash
python -m arbot.main --mode=gui
```

This should open the ArBot GUI interface.

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# If you see import errors, ensure all dependencies are installed
pip install -r requirements.txt --upgrade
```

#### Permission Errors
```bash
# On macOS/Linux, you might need to adjust permissions
chmod +x run.py
```

#### GUI Display Issues
```bash
# On headless servers, use CLI mode instead
python -m arbot.main --mode=cli
```

#### API Connection Issues
```bash
# Test your internet connection and API keys
python scripts/debug_config.py
```

### Performance Optimization

#### For High-Frequency Trading
```json
{
  "ui": {
    "refresh_rate_ms": 100
  },
  "arbitrage": {
    "max_spread_age_seconds": 1.0
  }
}
```

#### For Lower Resource Usage
```json
{
  "ui": {
    "refresh_rate_ms": 2000
  },
  "arbitrage": {
    "max_symbols": 50
  }
}
```

## Next Steps

1. **Configure API Keys**: Set up your exchange API credentials
2. **Customize Settings**: Adjust trading parameters in the GUI
3. **Start in Simulation**: Test with paper trading first
4. **Monitor Performance**: Watch the dashboard for opportunities

!!! tip "Safety First"
    Always start with simulation mode to familiarize yourself with the bot's behavior before using real funds.

Continue to [Quick Start Guide](quickstart.md) to begin trading!