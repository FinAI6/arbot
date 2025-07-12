# Settings Panel Guide

The ArBot Settings Panel provides comprehensive configuration options for all aspects of the trading bot. This guide covers every setting and how to optimize them for your trading strategy.

## Accessing Settings

**From GUI:**
1. Click the **"Settings"** button in the main toolbar
2. Use keyboard shortcut **Ctrl+,** (Ctrl+Comma)
3. Settings window opens with tabbed interface

**Settings Window Layout:**
- **Tabbed Interface**: Navigate between different configuration categories
- **Scrollable Panels**: All panels support scrolling for long lists of options
- **Real-time Validation**: Settings are validated as you type
- **Save/Cancel**: Apply changes or revert to previous values

## Trading Tab

Core arbitrage and trading configuration.

### Basic Trading Settings

#### Trading Mode
```
Trading Mode: [Simulation ▼]
Options: Simulation, Live
```
- **Simulation**: Paper trading with live data
- **Live**: Real trading with actual funds
- **Recommendation**: Always test in simulation first

#### Trade Amount
```
Trade Amount (USD): [100.00]
Range: 10.00 - 10000.00
```
- **Purpose**: Standard size for each arbitrage trade
- **Impact**: Larger amounts = higher profits but more risk
- **Recommendation**: Start with 50-100 USD

#### Min Profit Threshold
```
Min Profit Threshold (%): [0.50]
Range: 0.10 - 10.00
```
- **Purpose**: Minimum profit percentage to trigger trade
- **Impact**: Lower = more opportunities, higher = better quality
- **Recommendation**: 0.3-0.8% for active trading, 1.0%+ for conservative

### Advanced Settings

#### Max Position Size
```
Max Position Size (USD): [1000.00]
Range: 50.00 - 100000.00
```
- **Purpose**: Maximum USD amount per single trade
- **Risk Control**: Prevents over-exposure on large opportunities
- **Recommendation**: 5-10x your typical trade amount

#### Slippage Tolerance
```
Slippage Tolerance (%): [0.10]
Range: 0.01 - 1.00
```
- **Purpose**: Expected price movement during execution
- **Market Impact**: Higher in volatile markets
- **Recommendation**: 0.05-0.15% for stable pairs, 0.2-0.5% for volatile

#### Max Spread Age
```
Max Spread Age (seconds): [5.0]
Range: 1.0 - 60.0
```
- **Purpose**: Maximum age of price data for arbitrage calculation
- **Freshness**: Ensures prices are recent
- **Recommendation**: 2-5 seconds for active markets

#### Max Trades Per Hour
```
Max Trades Per Hour: [50]
Range: 1 - 500
```
- **Purpose**: Rate limiting to prevent overtrading
- **Risk Management**: Controls frequency of execution
- **Recommendation**: 20-50 for conservative, 50-100 for aggressive

#### Max Spread Threshold
```
Max Spread Threshold (%): [200.0]
Range: 10.0 - 1000.0
```
- **Purpose**: Filter out unrealistic spreads (likely errors)
- **Anomaly Detection**: Prevents trading on bad data
- **Recommendation**: 100-300% depending on market volatility

### Symbol Management

#### Max Symbols to Monitor
```
Max Symbols to Monitor: [200]
Range: 10 - 1000
```
- **Performance**: More symbols = more CPU/memory usage
- **Opportunities**: More symbols = more chances for arbitrage
- **Recommendation**: 50-100 for most systems, 200+ for powerful hardware

#### Dynamic Symbol Selection
```
☑ Use Dynamic Symbols (auto-detect high volume pairs)
```
- **When Enabled**: Bot selects high-volume pairs automatically
- **When Disabled**: Uses manually configured symbol list
- **Recommendation**: Keep enabled for best opportunities

#### Moving Average Settings
```
Moving Average Periods (seconds): [30]
Range: 5 - 300
```
- **Purpose**: Time window for trend calculation
- **Responsiveness**: Lower = more reactive, higher = smoother
- **Recommendation**: 15-30s for active trading, 60s+ for stable trends

### Quote Currency Filtering

Control which quote currencies to monitor:

```
Quote Currency Settings:
☑ USDT    ☑ USDC    ☐ BTC
☐ BUSD    ☐ ETH     ☐ BNB
```

**Recommendations by Strategy:**
- **Stable Trading**: USDT, USDC only
- **Diversified**: USDT, USDC, BUSD
- **All Markets**: Enable all options

### Premium Detection

Statistical analysis of exchange pricing patterns:

```
☑ Enable Premium Detection
Lookback Periods: [100]
Min Samples: [50]
Outlier Threshold: [2.0]
```

**Parameters:**
- **Lookback Periods**: Historical data points to analyze
- **Min Samples**: Minimum data required for analysis
- **Outlier Threshold**: Standard deviations for outlier detection

## Exchanges Tab

Configure exchange connections and regional settings.

### Exchange Configuration

Each exchange has individual settings:

```
┌─ Binance ────────────────────────┐
│ ☑ Enabled                        │
│ ☑ Arbitrage Enabled              │
│ Region: [Global ▼]               │
│ Premium Baseline: [0.0]          │
└──────────────────────────────────┘
```

#### Enable/Disable Exchanges
- **Enabled**: Connect to exchange for data
- **Arbitrage Enabled**: Include in arbitrage calculations
- **Recommendation**: Enable at least 2 exchanges for arbitrage

#### Regional Settings
- **Global**: Standard international access
- **US**: US-specific endpoints (where available)
- **Impact**: May affect available trading pairs

#### Premium Baseline
- **Purpose**: Expected premium/discount for this exchange
- **Usage**: Adjusts arbitrage calculations
- **Default**: 0.0 (no expected premium)

### API Configuration

API keys are configured through environment variables:

```bash
# .env file
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here
```

**API Permissions Required:**
- **Read Market Data**: For price feeds
- **Trade**: For order execution (live mode only)

## Risk Management Tab

Protect your capital with comprehensive risk controls.

### Drawdown Protection

```
Max Drawdown (%): [5.0]
Range: 1.0 - 50.0
```
- **Purpose**: Stop trading if losses exceed this percentage
- **Calculation**: Based on peak portfolio value
- **Recommendation**: 3-10% depending on risk tolerance

### Position Risk

```
Stop Loss (%): [2.0]
Range: 0.5 - 20.0
```
- **Purpose**: Maximum loss per individual trade
- **Application**: Automatic position closure
- **Recommendation**: 1-3% for conservative, 3-5% for aggressive

### Position Sizing

```
Position Sizing Method: [Fixed ▼]
Options: Fixed, Kelly
```
- **Fixed**: Use configured trade amount
- **Kelly**: Size based on Kelly Criterion (advanced)
- **Recommendation**: Start with Fixed sizing

### Concurrent Trades

```
Max Concurrent Trades: [3]
Range: 1 - 20
```
- **Purpose**: Limit simultaneous open positions
- **Risk Control**: Prevents overexposure
- **Recommendation**: 2-5 for most strategies

### Balance Protection

```
Balance Threshold (%): [10.0]
Range: 5.0 - 50.0
```
- **Purpose**: Stop trading if balance falls below threshold
- **Safety Net**: Preserves minimum funds
- **Recommendation**: 10-20% of starting balance

## Database Tab

Configure data storage and management.

### Database Configuration

```
Database Path: [data/arbot.db]
Backup Interval (hours): [24]
Max History Days: [30]
```

#### Database Path
- **Purpose**: Location of SQLite database file
- **Recommendation**: Keep in data/ directory
- **Backup**: Regular backups recommended

#### Backup Settings
- **Backup Interval**: How often to backup database
- **Max History**: How long to keep historical data
- **Storage Impact**: Longer history = larger database

### Data Management

**Automatic Cleanup:**
- Old ticker data removed based on max_history_days
- Trade records preserved indefinitely
- Performance metrics kept for analysis

## Backtest Tab

Configure historical testing parameters.

### Date Range

```
Start Date (YYYY-MM-DD): [2024-01-01]
End Date (YYYY-MM-DD): [2024-12-31]
```
- **Format**: ISO date format (YYYY-MM-DD)
- **Range**: Based on available data
- **Recommendation**: At least 1-3 months for meaningful results

### Initial Conditions

```
Initial Balance (USD): [10000.0]
Range: 100.0 - 1000000.0
```
- **Purpose**: Starting portfolio value for backtest
- **Scaling**: Results scale proportionally
- **Recommendation**: Use realistic starting amount

### Data Source

```
Data Source: [Database ▼]
Options: Database, CSV
CSV Path (if using CSV): [path/to/file.csv]
```
- **Database**: Use ArBot's historical data
- **CSV**: Import external data files
- **Format**: Standard OHLCV format for CSV

## General Tab

UI and system preferences.

### Interface Settings

```
UI Refresh Rate (ms): [500]
Range: 100 - 5000
```
- **Purpose**: How often GUI updates
- **Performance**: Lower = more responsive, higher = less CPU
- **Recommendation**: 300-1000ms for most systems

### Logging

```
Log Level: [INFO ▼]
Options: DEBUG, INFO, WARNING, ERROR
```
- **DEBUG**: Detailed system information
- **INFO**: Normal operation events  
- **WARNING**: Potential issues
- **ERROR**: Critical problems only

### Notifications

```
☑ Enable Notifications
```
- **System Notifications**: Desktop alerts for important events
- **Recommendations**: Enable for monitoring alerts

### Theme

```
Theme: [Dark ▼]
Options: Dark, Light
```
- **Dark**: Professional dark theme (default)
- **Light**: High contrast light theme

## Regional Tab

Configure regional premium tracking.

### Regional Premium Settings

Track premiums for specific geographic regions:

```
┌─ Korea (Kimchi Premium) ─────────┐
│ Exchanges: [upbit, bithumb]      │
│ Typical Premium: [2.5%]          │
│ ☐ Enable Premium Tracking       │
└──────────────────────────────────┘
```

**Use Cases:**
- Research geographic arbitrage opportunities
- Filter out regional premium effects
- Academic analysis of market efficiency

## Settings Optimization

### Conservative Strategy Settings

**Risk-Averse Configuration:**
```json
{
  "min_profit_threshold": 1.0,
  "max_position_size": 500.0,
  "max_concurrent_trades": 2,
  "max_drawdown_percent": 3.0,
  "stop_loss_percent": 1.5,
  "use_trend_filter": true
}
```

### Aggressive Strategy Settings

**High-Frequency Configuration:**
```json
{
  "min_profit_threshold": 0.3,
  "max_symbols": 300,
  "max_spread_age_seconds": 2.0,
  "refresh_rate_ms": 200,
  "max_trades_per_hour": 100
}
```

### Balanced Strategy Settings

**Moderate Risk Configuration:**
```json
{
  "min_profit_threshold": 0.5,
  "max_position_size": 1000.0,
  "max_concurrent_trades": 3,
  "max_drawdown_percent": 5.0,
  "stop_loss_percent": 2.0
}
```

## Common Configuration Patterns

### Market Condition Adaptations

**High Volatility Markets:**
- Increase slippage tolerance (0.3-0.5%)
- Reduce max spread age (2-3 seconds)
- Lower position sizes
- Stricter risk controls

**Low Volatility Markets:**
- Decrease profit threshold (0.2-0.4%)
- Increase max symbols (200+)
- Longer spread age tolerance (5-10 seconds)
- Higher position sizes

**Trending Markets:**
- Enable trend filtering
- Adjust trend confirmation threshold
- Use appropriate trend filter mode
- Monitor moving average periods

## Troubleshooting Settings

### Performance Issues

**High CPU Usage:**
- Reduce max_symbols (50-100)
- Increase refresh_rate_ms (1000+)
- Disable unnecessary exchanges

**Memory Issues:**
- Reduce moving_average_periods (15-20)
- Lower max_history_days (7-14)
- Limit max_symbols (50)

### Trading Issues

**No Opportunities Found:**
- Lower min_profit_threshold
- Increase max_symbols
- Check exchange connectivity
- Verify quote currency settings

**Too Many False Signals:**
- Increase min_profit_threshold
- Enable premium detection
- Use trend filtering
- Stricter risk parameters

!!! tip "Settings Backup"
    Export your optimized settings and keep backups. Settings that work well in certain market conditions may need adjustment when markets change.

!!! warning "Live Trading Caution"
    Always test new settings thoroughly in simulation mode before applying them to live trading. Small changes can have significant impacts on performance and risk.