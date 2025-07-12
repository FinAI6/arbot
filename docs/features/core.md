# Core Features

ArBot provides a comprehensive suite of features for cryptocurrency arbitrage trading. This page details the core functionality that makes ArBot a powerful and reliable trading tool.

## Real-Time Arbitrage Detection

### Multi-Exchange Price Monitoring

ArBot simultaneously monitors prices across multiple cryptocurrency exchanges:

- **Binance** - World's largest exchange by volume
- **Bybit** - Leading derivatives and spot exchange  
- **OKX** - Major global exchange with deep liquidity
- **Bitget** - Fast-growing exchange with competitive rates

**WebSocket Connections**
- Real-time price feeds with sub-second latency
- Automatic reconnection and error handling
- Redundant data sources for reliability

**Price Data Collection**
```python
# Example of collected data structure
{
    "symbol": "BTCUSDT",
    "exchange": "binance",
    "bid": 43250.50,
    "ask": 43251.00,
    "bid_size": 2.5,
    "ask_size": 1.8,
    "timestamp": 1640995200.123
}
```

### Spread Calculation Engine

**Real-Time Spread Analysis**
- Continuous calculation of price differences between exchanges
- Accounts for trading fees and slippage
- Filters out anomalous spreads (outlier detection)

**Spread Formula**
```
Gross Spread = (Higher Exchange Ask - Lower Exchange Bid) / Lower Exchange Bid × 100
Net Spread = Gross Spread - (Buy Fee + Sell Fee + Slippage)
```

**Profitability Calculation**
- Includes maker/taker fees for each exchange
- Adjusts for expected slippage
- Considers minimum trade sizes and liquidity

## Dynamic Symbol Management

### Intelligent Symbol Selection

**Volume-Based Prioritization**
- Automatically identifies high-volume trading pairs
- Ranks symbols by 24h trading volume
- Focuses monitoring on most liquid markets

**Quote Currency Filtering**
- Configurable focus on specific quote currencies
- Default: USDT pairs for maximum liquidity
- Support for BUSD, USDC, BTC, ETH, BNB pairs

**Adaptive Monitoring**
```python
# Symbol selection process
1. Fetch all available symbols from exchanges
2. Filter by enabled quote currencies
3. Sort by 24h volume (descending)
4. Select top N symbols (configurable limit)
5. Update monitoring list every hour
```

### Symbol Performance Tracking

**Historical Analysis**
- Track symbol performance over time
- Identify consistently profitable pairs
- Remove underperforming symbols automatically

**Liquidity Monitoring**
- Monitor order book depth for each symbol
- Avoid symbols with insufficient liquidity
- Adjust position sizes based on available liquidity

## Moving Average Integration

### 30-Second Moving Averages

**Real-Time Calculation**
- Maintains rolling 30-second price history
- Calculates simple moving average for trend analysis
- Updates every second for responsive trend detection

**Trend Identification**
```python
# Trend calculation logic
first_half_avg = average(prices[0:15])  # First 15 seconds
second_half_avg = average(prices[15:30])  # Last 15 seconds
change_percent = (second_half_avg - first_half_avg) / first_half_avg

if change_percent > threshold:
    trend = "↗"  # Uptrend
elif change_percent < -threshold:
    trend = "↘"  # Downtrend
else:
    trend = "→"  # Neutral
```

**Configurable Parameters**
- Moving average period (default: 30 seconds)
- Trend confirmation threshold (default: 0.1%)
- Trend filter modes for different strategies

## Trend-Based Arbitrage Filtering

### Smart Opportunity Selection

**Trend-Aware Trading**
- Only execute arbitrage during favorable trends
- Reduces risk of adverse price movements
- Improves overall success rate

**Filter Modes**
1. **Uptrend Buy Low** - Buy from lower-priced exchange during uptrends
2. **Downtrend Sell High** - Sell to higher-priced exchange during downtrends
3. **Both Directions** - Trade in any trend direction
4. **Disabled** - No trend filtering

**Implementation Logic**
```python
def should_allow_arbitrage(symbol, higher_exchange, lower_exchange):
    if not use_trend_filter:
        return True
    
    trend_higher = get_price_trend(symbol, higher_exchange)
    trend_lower = get_price_trend(symbol, lower_exchange)
    
    if trend_filter_mode == "uptrend_buy_low":
        return trend_higher == "↗" or trend_lower == "↗"
    
    elif trend_filter_mode == "downtrend_sell_high":
        return trend_higher == "↘" or trend_lower == "↘"
    
    return True
```

## Premium Detection System

### Exchange Premium Analysis

**Statistical Analysis**
- Analyzes historical price differences between exchanges
- Identifies exchanges that consistently trade at premium/discount
- Adjusts arbitrage thresholds accordingly

**Outlier Detection**
- Uses statistical methods to identify unusual spreads
- Filters out market manipulation or data errors
- Prevents trading on unreliable price differences

**Regional Premium Tracking**
- Monitors region-specific premiums (e.g., Kimchi Premium)
- Tracks premium patterns over time
- Provides insights for long-term strategy

### Premium Calculation

**Lookback Analysis**
```python
# Premium detection parameters
lookback_periods = 100  # Historical periods to analyze
min_samples = 70       # Minimum data points required
outlier_threshold = 2.0 # Standard deviations for outliers

# Calculate baseline premium
historical_spreads = get_historical_spreads(symbol, lookback_periods)
baseline_premium = median(historical_spreads)
spread_std = standard_deviation(historical_spreads)

# Identify outliers
for spread in current_spreads:
    z_score = (spread - baseline_premium) / spread_std
    if abs(z_score) > outlier_threshold:
        mark_as_outlier(spread)
```

## Risk Management Framework

### Multi-Layer Protection

**Position-Level Risk**
- Individual trade stop losses
- Maximum position sizes
- Slippage tolerance limits

**Portfolio-Level Risk**
- Maximum drawdown protection
- Concurrent trade limits
- Balance threshold monitoring

**System-Level Risk**
- API rate limiting
- Connection timeout handling
- Error recovery mechanisms

### Risk Metrics Tracking

**Real-Time Monitoring**
- Current drawdown percentage
- Win/loss ratio
- Average profit per trade
- Risk-adjusted returns

**Performance Analytics**
```python
# Key risk metrics
{
    "total_trades": 156,
    "winning_trades": 142,
    "losing_trades": 14,
    "win_rate": 91.0,
    "average_profit": 0.0087,
    "max_drawdown": 2.3,
    "sharpe_ratio": 2.8,
    "profit_factor": 4.2
}
```

## Data Management System

### SQLite Database Storage

**Efficient Data Storage**
- Ticker data from all exchanges
- Arbitrage opportunities detected
- Trade execution history
- Performance metrics

**Automated Cleanup**
- Configurable data retention periods
- Automatic old data removal
- Database optimization routines

**Data Export Capabilities**
- CSV export for analysis
- Historical data backups
- Performance reporting

### Real-Time Data Processing

**Asynchronous Architecture**
- Non-blocking data collection
- Concurrent processing of multiple exchanges
- Real-time arbitrage detection

**Performance Optimization**
- Efficient data structures
- Memory management
- CPU usage optimization

## Configuration System

### Flexible Configuration

**Multiple Configuration Sources**
1. Default built-in settings
2. Main configuration file (config.json)
3. Local override file (config.local.json)
4. Environment variables

**Hot Configuration Reload**
- Update settings without restart
- Real-time parameter adjustment
- Safe configuration validation

### Environment Adaptation

**Development vs Production**
- Different default settings
- Appropriate logging levels
- Resource usage optimization

**User Customization**
- Personal trading preferences
- Risk tolerance settings
- UI customization options

## Error Handling and Resilience

### Robust Error Recovery

**Connection Management**
- Automatic reconnection to exchanges
- Fallback data sources
- Graceful degradation

**Data Validation**
- Price data sanity checks
- Timestamp validation
- Missing data handling

**System Recovery**
- Automatic restart on critical errors
- State preservation
- Transaction rollback

### Comprehensive Logging

**Multi-Level Logging**
- DEBUG: Detailed system information
- INFO: Normal operation events
- WARNING: Potential issues
- ERROR: Critical problems

**Log Management**
- Automatic log rotation
- Configurable log levels
- Structured log formats

## Performance Monitoring

### Real-Time Metrics

**System Performance**
- CPU and memory usage
- Network latency measurements
- Data processing rates

**Trading Performance**
- Arbitrage opportunities found
- Execution success rates
- Profit/loss tracking

### Performance Optimization

**Adaptive Parameters**
- Automatic parameter tuning
- Performance-based adjustments
- Resource usage optimization

**Monitoring Dashboard**
- Real-time performance metrics
- Historical performance charts
- System health indicators

!!! tip "Performance Tuning"
    For optimal performance, monitor system resources and adjust `max_symbols`, `refresh_rate_ms`, and `max_spread_age_seconds` based on your hardware capabilities and network latency.