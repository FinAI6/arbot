# Trend Filtering

ArBot's trend filtering system analyzes price momentum to improve arbitrage timing and reduce risk. By only trading during favorable market conditions, the system enhances profitability and minimizes exposure to adverse price movements.

## How Trend Filtering Works

### Core Concept

**Traditional Arbitrage Problem:**
- Prices can move against you during execution
- Market volatility can eliminate spreads quickly
- Timing becomes crucial for profitability

**Trend-Enhanced Solution:**
- Only trade when price momentum is favorable
- Reduce risk of adverse price movements
- Improve overall success rates

### Mathematical Foundation

**Moving Average Calculation:**
```python
# 30-second moving average with 1-second updates
prices = deque(maxlen=30)  # Store 30 price points
prices.append(current_price)
moving_average = sum(prices) / len(prices)
```

**Trend Determination:**
```python
# Split data into two halves for trend analysis
first_half = prices[:15]   # First 15 seconds
second_half = prices[15:]  # Last 15 seconds

avg_first = sum(first_half) / len(first_half)
avg_second = sum(second_half) / len(second_half)

change_percent = (avg_second - avg_first) / avg_first

if change_percent > threshold:
    trend = "↗"  # Uptrend
elif change_percent < -threshold:
    trend = "↘"  # Downtrend
else:
    trend = "→"  # Neutral
```

## Trend Filter Modes

### 1. Uptrend Buy Low (`uptrend_buy_low`)

**Strategy:** Only execute arbitrage during upward price trends by buying from the lower-priced exchange.

**Logic:**
- When prices are rising, buy from cheaper exchange
- Sell to more expensive exchange
- Price momentum helps secure profits

**Example Scenario:**
```
BTC Price Trend: ↗ (Rising)
Binance: $43,300 (higher)
Bybit: $43,250 (lower)

Action: Buy from Bybit, Sell on Binance
Rationale: Rising prices favor buying low
```

**Configuration:**
```json
{
  "arbitrage": {
    "use_trend_filter": true,
    "trend_filter_mode": "uptrend_buy_low",
    "trend_confirmation_threshold": 0.001
  }
}
```

### 2. Downtrend Sell High (`downtrend_sell_high`)

**Strategy:** Only execute arbitrage during downward price trends by selling to the higher-priced exchange.

**Logic:**
- When prices are falling, sell to more expensive exchange
- Buy from cheaper exchange
- Downward momentum helps maintain spreads

**Example Scenario:**
```
ETH Price Trend: ↘ (Falling)
OKX: $2,850 (higher)
Bitget: $2,835 (lower)

Action: Sell on OKX, Buy from Bitget
Rationale: Falling prices favor selling high
```

### 3. Both Directions (`both`)

**Strategy:** Trade in any trending market (up or down) but avoid neutral/sideways markets.

**Logic:**
- Momentum in any direction is preferable to stagnation
- Avoids trading in choppy, directionless markets
- Requires strong trend confirmation

**Example:**
```
# Trade in uptrend
ADA Trend: ↗ → Execute arbitrage

# Trade in downtrend  
ADA Trend: ↘ → Execute arbitrage

# Skip neutral markets
ADA Trend: → → Skip opportunity
```

### 4. Disabled (`disabled`)

**Strategy:** No trend filtering - trade all opportunities that meet profit thresholds.

**Use Cases:**
- High-frequency strategies
- Very short-term arbitrage
- Markets with consistent liquidity
- When trend analysis is unreliable

## Configuration Parameters

### Trend Confirmation Threshold

**Purpose:** Minimum price change required to confirm a trend

```json
{
  "trend_confirmation_threshold": 0.001  // 0.1% minimum change
}
```

**Values:**
- `0.0005` (0.05%) - Very sensitive, catches small trends
- `0.001` (0.1%) - Default, balanced sensitivity
- `0.002` (0.2%) - Conservative, only strong trends
- `0.005` (0.5%) - Very conservative, major trends only

**Impact on Trading:**
```python
# Example with different thresholds
Price change: 0.08%

threshold = 0.0005 → Trend detected ✅
threshold = 0.001  → No trend detected ❌
threshold = 0.002  → No trend detected ❌
```

### Moving Average Period

**Purpose:** Time window for trend calculation

```json
{
  "moving_average_periods": 30  // 30 seconds
}
```

**Common Values:**
- `15` seconds - Very responsive, noisy
- `30` seconds - Default, good balance
- `60` seconds - Smoother, less responsive
- `120` seconds - Very smooth, slow to react

### Implementation in Strategy

```python
def should_allow_arbitrage(symbol, higher_exchange, lower_exchange, 
                          exchange1, exchange2):
    """Determine if arbitrage should be executed based on trend filter"""
    
    if not config.use_trend_filter:
        return True
    
    # Get trends for both exchanges
    trend1 = get_price_trend(f"{symbol}_{exchange1}")
    trend2 = get_price_trend(f"{symbol}_{exchange2}")
    
    # Determine which exchange has higher price
    is_exchange1_higher = higher_exchange == exchange1.upper()
    
    if config.trend_filter_mode == "uptrend_buy_low":
        # Only allow arbitrage in uptrend
        return trend1 == "↗" or trend2 == "↗"
    
    elif config.trend_filter_mode == "downtrend_sell_high":
        # Only allow arbitrage in downtrend
        return trend1 == "↘" or trend2 == "↘"
    
    elif config.trend_filter_mode == "both":
        # Allow any trend except neutral
        return (trend1 != "→" or trend2 != "→")
    
    return True  # Disabled mode
```

## Visual Indicators

### GUI Display

**Trend Column in Price Table:**
| Symbol | Higher Exchange | Price(±Diff) | MA30s | **Trend** | Spread % |
|--------|----------------|--------------|-------|-----------|----------|
| BTCUSDT | BINANCE | $43,250(+$45) | $43,205 | **↗** | 0.18% |
| ETHUSDT | BYBIT | $2,845(+$12) | $2,850 | **↘** | 0.42% |
| ADAUSDT | OKX | $0.485(+$0.002) | $0.484 | **→** | 0.35% |

**Trend Indicators:**
- **↗** Green upward arrow - Bullish trend
- **↘** Red downward arrow - Bearish trend  
- **→** Yellow horizontal arrow - Neutral/sideways

### Real-Time Updates

**Trend Calculation Updates:**
- Recalculated every second with new price data
- Visual indicators update immediately
- Filtered opportunities disappear/appear based on trends

## Strategy Examples

### Conservative Uptrend Strategy

**Goal:** Only trade during clear uptrends with high confidence

```json
{
  "arbitrage": {
    "use_trend_filter": true,
    "trend_filter_mode": "uptrend_buy_low",
    "trend_confirmation_threshold": 0.002,
    "min_profit_threshold": 0.01,
    "moving_average_periods": 60
  }
}
```

**Characteristics:**
- High threshold requires strong uptrends
- Longer MA period reduces noise
- Higher profit threshold for quality opportunities

### Aggressive Both-Direction Strategy

**Goal:** Capture trends in either direction quickly

```json
{
  "arbitrage": {
    "use_trend_filter": true,
    "trend_filter_mode": "both",
    "trend_confirmation_threshold": 0.0005,
    "min_profit_threshold": 0.005,
    "moving_average_periods": 15
  }
}
```

**Characteristics:**
- Low threshold catches small trends
- Shorter MA period for quick response
- Moderate profit threshold for more opportunities

### Market-Neutral Strategy

**Goal:** Trade regardless of market direction

```json
{
  "arbitrage": {
    "use_trend_filter": false,
    "min_profit_threshold": 0.008,
    "max_spread_age_seconds": 2.0
  }
}
```

**Characteristics:**
- No trend filtering
- Higher profit threshold compensates for risk
- Fast execution required

## Performance Impact

### Benefits of Trend Filtering

**Improved Success Rates:**
```
Without Trend Filter: 78% success rate
With Uptrend Filter: 85% success rate
Improvement: +7 percentage points
```

**Reduced Risk:**
- Lower exposure to adverse price movements
- Better timing of entries and exits
- Reduced maximum drawdown

**Quality over Quantity:**
- Fewer total trades
- Higher average profit per trade
- Better risk-adjusted returns

### Trade-offs

**Opportunity Cost:**
- May miss profitable opportunities in neutral markets
- Reduced trading frequency
- Potential for over-filtering

**Market Dependency:**
- Effectiveness varies by market conditions
- May perform poorly in ranging markets
- Requires parameter optimization

## Optimization Guidelines

### Backtesting Different Settings

**Parameter Sensitivity Analysis:**
```python
# Test different thresholds
thresholds = [0.0005, 0.001, 0.002, 0.005]
periods = [15, 30, 60, 120]

for threshold in thresholds:
    for period in periods:
        results = backtest_with_settings(threshold, period)
        print(f"Threshold: {threshold}, Period: {period}, "
              f"Return: {results.total_return}, "
              f"Drawdown: {results.max_drawdown}")
```

### Market Condition Adaptation

**Bull Market Settings:**
```json
{
  "trend_filter_mode": "uptrend_buy_low",
  "trend_confirmation_threshold": 0.001,
  "moving_average_periods": 30
}
```

**Bear Market Settings:**
```json
{
  "trend_filter_mode": "downtrend_sell_high",
  "trend_confirmation_threshold": 0.0015,
  "moving_average_periods": 45
}
```

**Sideways Market Settings:**
```json
{
  "use_trend_filter": false,
  "min_profit_threshold": 0.012
}
```

## Troubleshooting

### Common Issues

**No Opportunities with Trend Filter:**
1. Lower `trend_confirmation_threshold`
2. Try `both` mode instead of directional
3. Check if market is truly trending
4. Verify moving average calculation

**Too Many False Signals:**
1. Increase `trend_confirmation_threshold`
2. Use longer `moving_average_periods`
3. Add additional filters
4. Check for data quality issues

**Poor Performance:**
1. Backtest different parameter combinations
2. Consider market regime changes
3. Monitor for over-optimization
4. Validate with out-of-sample data

### Monitoring Trend Filter Effectiveness

**Key Metrics to Track:**
- Win rate with vs without trend filtering
- Average profit per trade
- Maximum drawdown
- Total number of opportunities

**Performance Dashboard:**
```python
{
  "trend_filter_stats": {
    "opportunities_found": 1247,
    "opportunities_filtered": 623,
    "filter_rate": 49.9,
    "avg_profit_filtered": 0.0087,
    "avg_profit_unfiltered": 0.0061,
    "improvement": 42.6
  }
}
```

!!! tip "Optimization Strategy"
    Start with default settings and gradually adjust based on your market analysis and risk tolerance. Monitor performance metrics closely and be prepared to adapt to changing market conditions.

!!! warning "Market Adaptation"
    Trend filtering effectiveness varies with market conditions. What works in trending markets may not work in ranging markets. Regular monitoring and adjustment is essential.