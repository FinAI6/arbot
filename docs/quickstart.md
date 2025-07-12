# Quick Start Guide

Get ArBot running in under 5 minutes! This guide walks you through the essential steps to start monitoring arbitrage opportunities.

## Step 1: Launch ArBot

After installation, start the GUI interface:

```bash
python -m arbot.main --mode=gui
```

The ArBot interface will open with the main dashboard.

## Step 2: Initial Configuration

### Basic Settings

1. **Click the "Settings" button** in the top toolbar
2. **Navigate to the "Trading" tab**
3. **Configure basic parameters**:
   - **Trading Mode**: Keep as "simulation" for testing
   - **Trade Amount**: Set to $100 (or your preferred amount)
   - **Min Profit Threshold**: Start with 0.5% (0.005)

### Exchange Configuration

1. **Go to the "Exchanges" tab**
2. **Enable exchanges** you want to monitor:
   - ✅ Binance (enabled by default)
   - ✅ Bybit (enabled by default)
   - ⬜ OKX (enable if you have API access)
   - ⬜ Bitget (enable if you have API access)

### API Keys (Optional for Simulation)

!!! note "Simulation Mode"
    API keys are not required for simulation mode. The bot will use public market data.

For live trading, add your API keys in `.env` file:
```bash
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_secret_here
```

## Step 3: Start Monitoring

1. **Click "Start Trading"** in the main interface
2. **Watch the dashboard populate** with real-time data:
   - **Symbols**: Trading pairs being monitored
   - **Exchanges**: Live price feeds from each exchange
   - **Spreads**: Price differences between exchanges

### Understanding the Interface

#### Main Dashboard Elements

| Element | Description |
|---------|-------------|
| **Status** | Current bot status (Running/Stopped) |
| **Mode** | Trading mode (Simulation/Live) |
| **Exchanges** | Number of active exchanges |
| **Profit** | Total simulated profit |

#### Price Monitoring Table

| Column | Description |
|---------|-------------|
| **Symbol** | Trading pair (e.g., BTCUSDT) |
| **Higher Exchange** | Exchange with higher price |
| **Price(±Diff)** | Price and difference amount |
| **MA30s** | 30-second moving average |
| **Trend** | Price trend indicator (↗↘→) |
| **Spread %** | Percentage spread between exchanges |

## Step 4: Monitor Arbitrage Opportunities

### Reading the Data

**Good Arbitrage Opportunity:**
```
BTCUSDT | BINANCE | $43,250.50 (+$125.30) | $43,180.20 | ↗ | 0.29%
```
- Higher price on Binance: $43,250.50
- Difference: +$125.30 vs other exchange
- Upward trend: ↗
- Spread: 0.29% (above minimum threshold)

**Poor Arbitrage Opportunity:**
```
ETHUSDT | BYBIT | $2,845.20 (+$5.50) | $2,840.15 | → | 0.19%
```
- Small difference: Only $5.50
- Neutral trend: →
- Low spread: 0.19% (below threshold)

### Sorting and Filtering

1. **Click column headers** to sort:
   - **Spread %**: Sort by highest spreads first
   - **Symbol**: Alphabetical sorting
   - **Price(±Diff)**: Sort by price differences

2. **Look for these indicators**:
   - ✅ **Green spread %**: Above your minimum threshold
   - ✅ **Upward trend ↗**: Favorable for buying low exchange
   - ✅ **Large price difference**: More profit potential

## Step 5: Customize Your Strategy

### Quote Currency Filtering

Focus on specific quote currencies:

1. **Go to Settings → Trading tab**
2. **Find "Quote Currency Settings"**
3. **Enable/disable currencies**:
   - ✅ USDT (most liquid)
   - ✅ USDC (stable alternative)
   - ⬜ BTC (for BTC pairs)
   - ⬜ ETH (for ETH pairs)

### Trend Filtering

Configure trend-based arbitrage:

1. **Enable "Use Trend Filter"**
2. **Set trend mode**:
   - **uptrend_buy_low**: Only trade during uptrends
   - **downtrend_sell_high**: Only trade during downtrends
   - **both**: Trade in any trend
   - **disabled**: No trend filtering

### Symbol Management

Control which pairs to monitor:

1. **Set "Max Symbols"**: Start with 50-100
2. **Enable "Dynamic Symbols"**: Auto-detect high volume pairs
3. **Monitor the symbol count** in the interface

## Step 6: Analyze Performance

### Real-Time Metrics

Monitor these key metrics:

- **Opportunities Found**: Number of arbitrage signals
- **Simulated Trades**: Executed trades in simulation
- **Total Profit**: Cumulative simulated profit
- **Success Rate**: Percentage of profitable trades

### Historical Data

The bot automatically stores:
- Price data from all exchanges
- Arbitrage opportunities found
- Trade execution history
- Performance metrics

Access this data through the database at `data/arbot.db`.

## Advanced Quick Setup

### High-Frequency Configuration

For aggressive arbitrage detection:

```json
{
  "arbitrage": {
    "min_profit_threshold": 0.001,
    "max_spread_age_seconds": 1.0,
    "max_symbols": 200
  },
  "ui": {
    "refresh_rate_ms": 100
  }
}
```

### Conservative Configuration

For safer, less frequent opportunities:

```json
{
  "arbitrage": {
    "min_profit_threshold": 0.01,
    "max_spread_age_seconds": 5.0,
    "max_symbols": 50,
    "use_trend_filter": true,
    "trend_filter_mode": "uptrend_buy_low"
  }
}
```

## Troubleshooting Quick Start

### No Data Appearing?

1. **Check internet connection**
2. **Verify exchanges are enabled** in settings
3. **Look for error messages** in the status bar
4. **Restart the application**

### No Arbitrage Opportunities?

1. **Lower the minimum profit threshold** (try 0.1%)
2. **Increase max symbols** to monitor more pairs
3. **Disable trend filtering** temporarily
4. **Check if markets are volatile enough**

### Performance Issues?

1. **Reduce max symbols** to 50
2. **Increase refresh rate** to 1000ms
3. **Close other applications** using network/CPU
4. **Consider running on a dedicated machine**

## Next Steps

Now that ArBot is running:

1. **📊 [Learn the GUI](features/gui.md)**: Master all interface features
2. **⚙️ [Configure Settings](guide/settings.md)**: Fine-tune your strategy
3. **📈 [Understand Risk Management](features/risk.md)**: Protect your capital
4. **🔄 [Explore Trading Modes](guide/trading-modes.md)**: Move from simulation to live

!!! success "You're All Set!"
    ArBot is now monitoring arbitrage opportunities in real-time. Watch the dashboard and familiarize yourself with the patterns before moving to live trading.

!!! warning "Remember"
    Always test thoroughly in simulation mode before risking real funds. Arbitrage trading involves risks including network latency, slippage, and market volatility.