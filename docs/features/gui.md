# GUI Interface

ArBot features a comprehensive tkinter-based GUI that provides real-time monitoring, configuration, and control of arbitrage trading operations.

## Main Dashboard

### Header Information Bar

The top section displays critical system information:

| Element | Description | Example |
|---------|-------------|---------|
| **Status** | Current bot state | `🟢 Running` / `🔴 Stopped` |
| **Mode** | Trading mode | `🎮 Simulation` / `💰 Live` |
| **Exchanges** | Active exchanges | `📊 2/4 exchanges` |
| **Profit** | Cumulative P&L | `💰 $45.67` |
| **Last Update** | Data freshness | `📱 2s ago` |

### Control Buttons

| Button | Function | Shortcut |
|--------|----------|----------|
| **Start/Stop Trading** | Toggle bot operation | `Ctrl+S` |
| **Settings** | Open configuration panel | `Ctrl+,` |
| **Export Data** | Save trading data | `Ctrl+E` |
| **Refresh** | Force data update | `F5` |

## Price Monitoring Table

### Column Details

#### Symbol Column
- **Format**: `BTCUSDT`, `ETHUSDT`, etc.
- **Sorting**: Alphabetical A-Z or Z-A
- **Click**: Sort by symbol name

#### Higher Exchange Column
- **Shows**: Exchange name with highest current price
- **Format**: `BINANCE`, `BYBIT`, `OKX`, `BITGET`
- **Color Coding**: 
  - 🟢 Green: Reliable exchange
  - 🟡 Yellow: Moderate reliability
  - 🔴 Red: Connection issues

#### Price(±Diff) Column
- **Format**: `$43,250.50 (+$125.30)`
- **Components**:
  - Base price: Current price on higher exchange
  - Difference: Amount higher than lower exchange
  - Positive values: Arbitrage opportunity exists
- **Sorting**: By price difference amount

#### MA30s Column
- **Moving Average**: 30-second period (configurable)
- **Format**: `$43,180.20`
- **Purpose**: Smooth out price volatility
- **Configuration**: Adjustable in Settings → Trading

#### Trend Column
- **Indicators**:
  - `↗` **Uptrend**: Price increasing
  - `↘` **Downtrend**: Price decreasing  
  - `→` **Neutral**: Sideways movement
- **Calculation**: Based on first vs second half of MA period
- **Threshold**: Configurable (default 0.1%)

#### Spread % Column
- **Calculation**: `(Higher Price - Lower Price) / Lower Price × 100`
- **Format**: `0.29%`, `1.45%`
- **Color Coding**:
  - 🟢 Green: Above minimum threshold
  - 🟡 Yellow: Close to threshold
  - 🔴 Red: Below threshold
- **Sorting**: Default descending order

### Interactive Features

#### Column Sorting
1. **Click any column header** to sort
2. **Visual indicators**:
   - `Column Name ↑` - Ascending order
   - `Column Name ↓` - Descending order
3. **Click again** to reverse sort order
4. **Default**: Spread % descending (highest opportunities first)

#### Row Selection
- **Single click**: Select row for details
- **Double click**: Open detailed analysis (future feature)
- **Right click**: Context menu with options

## Settings Panel

Comprehensive configuration interface with tabbed organization:

### Trading Tab

#### Basic Settings
```
Trading Mode: [Simulation ▼]
Trade Amount (USD): [100.00]
Min Profit Threshold (%): [0.50]
Max Position Size (USD): [1000.00]
```

#### Advanced Settings
```
Slippage Tolerance (%): [0.10]
Max Spread Age (seconds): [5.0]
Max Trades Per Hour: [50]
Max Spread Threshold (%): [200.0]
Max Symbols to Monitor: [200]
Moving Average Periods (seconds): [30]
```

#### Symbol Management
```
☑ Use Dynamic Symbols (auto-detect high volume pairs)
```

#### Quote Currency Settings
```
Quote Currency Settings:
☑ USDT    ☑ USDC    ☐ BTC
☐ BUSD    ☐ ETH     ☐ BNB
```

#### Premium Detection Settings
```
☑ Enable Premium Detection
Lookback Periods: [100]
Min Samples: [50]
Outlier Threshold: [2.0]
```

### Exchanges Tab

Configure exchange connections and settings:

```
Exchange Configuration:

┌─ Binance ────────────────────────┐
│ ☑ Enabled                        │
│ ☑ Arbitrage Enabled              │
│ Region: [Global ▼]               │
│ Premium Baseline: [0.0]          │
└──────────────────────────────────┘

┌─ Bybit ──────────────────────────┐
│ ☑ Enabled                        │
│ ☑ Arbitrage Enabled              │
│ Region: [Global ▼]               │
│ Premium Baseline: [0.0]          │
└──────────────────────────────────┘
```

### Risk Management Tab

```
Risk Management Configuration:

Max Drawdown (%): [5.0]
Stop Loss (%): [2.0]
Position Sizing Method: [Fixed ▼]
Max Concurrent Trades: [3]
Balance Threshold (%): [10.0]
```

### Database Tab

```
Database Configuration:

Database Path: [data/arbot.db]
Backup Interval (hours): [24]
Max History Days: [30]
```

### Backtest Tab

```
Backtest Configuration:

Start Date (YYYY-MM-DD): [2024-01-01]
End Date (YYYY-MM-DD): [2024-12-31]
Initial Balance (USD): [10000.0]
Data Source: [Database ▼]
CSV Path (if using CSV): [path/to/file.csv]
```

### General Tab

```
UI & General Configuration:

UI Refresh Rate (ms): [500]
Log Level: [INFO ▼]
☑ Enable Notifications
Theme: [Dark ▼]
```

### Regional Tab

Regional premium settings for specific markets:

```
Regional Premiums Configuration:

┌─ Korea (Kimchi Premium) ─────────┐
│ Exchanges: [upbit, bithumb]      │
│ Typical Premium: [2.5%]          │
│ ☐ Enable Premium Tracking       │
└──────────────────────────────────┘

┌─ Japan ──────────────────────────┐
│ Exchanges: [bitflyer, coincheck] │
│ Typical Premium: [1.5%]          │
│ ☐ Enable Premium Tracking       │
└──────────────────────────────────┘
```

## Data Export Features

### Export Options

1. **Arbitrage Opportunities**
   - CSV format with timestamps
   - Includes all detected opportunities
   - Filterable by date range

2. **Trading History**
   - Executed trades (simulation or live)
   - P&L calculations
   - Performance metrics

3. **Price Data**
   - Raw ticker data from exchanges
   - OHLCV format support
   - Multiple timeframes

### Export Process

1. Click **"Export Data"** button
2. Select data type and date range
3. Choose file location
4. Data saved in CSV format

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Start/Stop trading |
| `Ctrl+,` | Open settings |
| `Ctrl+E` | Export data |
| `F5` | Refresh display |
| `Ctrl+Q` | Quit application |
| `Ctrl+R` | Reset to defaults |
| `Space` | Pause/Resume updates |

## Visual Indicators

### Status Colors

| Color | Meaning |
|-------|---------|
| 🟢 Green | Normal operation, profitable |
| 🟡 Yellow | Warning, attention needed |
| 🔴 Red | Error, immediate action required |
| 🔵 Blue | Information, neutral status |

### Connection Status

| Indicator | Exchange Status |
|-----------|----------------|
| ●●● | Excellent connection |
| ●●○ | Good connection |
| ●○○ | Poor connection |
| ○○○ | Disconnected |

## Performance Optimization

### For High-Frequency Trading

```json
{
  "ui": {
    "refresh_rate_ms": 100
  },
  "arbitrage": {
    "max_symbols": 200,
    "max_spread_age_seconds": 1.0
  }
}
```

### For Lower Resource Usage

```json
{
  "ui": {
    "refresh_rate_ms": 2000
  },
  "arbitrage": {
    "max_symbols": 50,
    "max_spread_age_seconds": 5.0
  }
}
```

## Troubleshooting GUI Issues

### Common Problems

#### GUI Won't Start
```bash
# Check tkinter installation
python -c "import tkinter; print('GUI available')"

# On Ubuntu/Debian
sudo apt-get install python3-tk

# On macOS with Homebrew
brew install python-tk
```

#### Display Issues
- **Blurry text**: Adjust DPI settings in OS
- **Wrong scaling**: Set DPI awareness in Windows
- **Missing elements**: Update to latest Python/tkinter

#### Performance Issues
- **Slow updates**: Increase refresh rate
- **High CPU usage**: Reduce max symbols
- **Memory leaks**: Restart application periodically

## Customization Options

### Theme Customization
- **Dark mode**: Default professional appearance
- **Light mode**: High contrast for bright environments
- **Custom colors**: Modify theme in settings

### Layout Preferences
- **Column widths**: Drag to resize
- **Window size**: Remembers last position
- **Panel layouts**: Collapsible sections

## Future Enhancements

Planned GUI improvements:

- 📊 **Advanced Charts**: Integrated price charts
- 🔔 **Desktop Notifications**: System-level alerts
- 🌐 **Web Interface**: Browser-based alternative
- 📱 **Mobile View**: Responsive design
- 🎨 **Custom Themes**: User-defined color schemes

!!! tip "Pro Tip"
    Use the keyboard shortcuts to navigate quickly between functions, especially during active trading sessions.