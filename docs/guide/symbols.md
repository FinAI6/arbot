# Symbol Management

ArBot's symbol management system automatically selects and monitors the most profitable trading pairs for arbitrage opportunities. This intelligent system balances opportunity discovery with system performance through dynamic symbol selection and filtering.

## Overview

### Dynamic vs Static Symbol Selection

**Dynamic Symbol Selection (Recommended):**
- Automatically selects high-volume trading pairs
- Adapts to changing market conditions
- Focuses on most liquid and profitable opportunities
- Updates symbol list periodically

**Static Symbol Selection:**
- Uses a fixed list of predefined symbols
- Consistent monitoring of specific pairs
- Useful for focused strategies
- Manual control over monitored assets

### Key Benefits

**Optimized Performance:**
- Monitor only the most active trading pairs
- Reduce computational overhead
- Focus on highest probability opportunities
- Adapt to market changes automatically

## Configuration Options

### Basic Symbol Settings

```json
{
  "arbitrage": {
    "use_dynamic_symbols": true,
    "max_symbols": 200,
    "symbols": ["BTCUSDT", "ETHUSDT", "ADAUSDT"],
    "symbol_update_interval": 3600
  }
}
```

### Dynamic Symbol Selection

**When Enabled:**
```json
{
  "arbitrage": {
    "use_dynamic_symbols": true,
    "max_symbols": 200,
    "min_volume_24h": 1000000,
    "min_exchanges": 2
  }
}
```

**Selection Process:**
1. **Fetch Available Symbols** from all enabled exchanges
2. **Filter by Quote Currency** (USDT, USDC, etc.)
3. **Sort by 24h Volume** (highest first)
4. **Select Top N Symbols** up to max_symbols limit
5. **Update Periodically** (default: every hour)

### Static Symbol Selection

**When Disabled:**
```json
{
  "arbitrage": {
    "use_dynamic_symbols": false,
    "symbols": [
      "BTCUSDT", "ETHUSDT", "BNBUSDT",
      "ADAUSDT", "DOTUSDT", "LINKUSDT",
      "LTCUSDT", "BCHUSDT", "XLMUSDT"
    ]
  }
}
```

**Manual Symbol List:**
- Define exactly which pairs to monitor
- Consistent monitoring regardless of volume changes
- Useful for specific trading strategies
- Requires manual updates for optimization

## Quote Currency Filtering

### Supported Quote Currencies

**Primary Stablecoins:**
- **USDT** - Tether (most liquid)
- **USDC** - USD Coin (regulatory compliant)
- **BUSD** - Binance USD (exchange-specific)

**Cryptocurrency Bases:**
- **BTC** - Bitcoin pairs
- **ETH** - Ethereum pairs
- **BNB** - Binance Coin pairs

### Configuration

```json
{
  "arbitrage": {
    "enabled_quote_currencies": ["USDT", "USDC"],
    "available_quote_currencies": [
      "USDT", "BUSD", "USDC", 
      "BTC", "ETH", "BNB"
    ]
  }
}
```

### Quote Currency Strategy

**Stablecoin Focus (Recommended):**
```json
{
  "enabled_quote_currencies": ["USDT", "USDC"]
}
```
- **Benefits**: Lower volatility, easier profit calculation
- **Use Case**: Conservative arbitrage strategies

**Multi-Currency Approach:**
```json
{
  "enabled_quote_currencies": ["USDT", "USDC", "BTC", "ETH"]
}
```
- **Benefits**: More opportunities, diversified exposure
- **Use Case**: Aggressive arbitrage strategies

**Single Currency Focus:**
```json
{
  "enabled_quote_currencies": ["USDT"]
}
```
- **Benefits**: Simplified calculations, highest liquidity
- **Use Case**: High-frequency strategies

## Volume-Based Selection

### Volume Criteria

**Minimum Volume Thresholds:**
```python
# Volume-based filtering
def filter_by_volume(symbols, min_volume_24h=1000000):
    filtered_symbols = []
    
    for symbol in symbols:
        volume_24h = get_24h_volume(symbol)
        if volume_24h >= min_volume_24h:
            filtered_symbols.append(symbol)
    
    return filtered_symbols
```

**Volume Tiers:**
- **Tier 1**: >$100M daily volume (BTC, ETH majors)
- **Tier 2**: $10M-$100M daily volume (Large altcoins)
- **Tier 3**: $1M-$10M daily volume (Mid-cap altcoins)
- **Tier 4**: <$1M daily volume (Small-cap, avoid)

### Selection Algorithm

```python
def select_dynamic_symbols(max_symbols=200):
    # Step 1: Get all symbols from exchanges
    all_symbols = []
    for exchange in enabled_exchanges:
        symbols = exchange.get_all_symbols()
        all_symbols.extend(symbols)
    
    # Step 2: Remove duplicates and filter
    unique_symbols = list(set(all_symbols))
    quote_filtered = filter_by_quote_currency(unique_symbols)
    
    # Step 3: Get volume data
    symbols_with_volume = []
    for symbol in quote_filtered:
        volume_24h = get_aggregated_volume(symbol)
        symbols_with_volume.append((symbol, volume_24h))
    
    # Step 4: Sort by volume and select top N
    sorted_symbols = sorted(symbols_with_volume, 
                           key=lambda x: x[1], reverse=True)
    
    selected_symbols = [symbol for symbol, volume 
                       in sorted_symbols[:max_symbols]]
    
    return selected_symbols
```

## Exchange Coverage

### Multi-Exchange Requirements

**Minimum Exchange Coverage:**
```python
def validate_symbol_coverage(symbol, exchanges):
    coverage = 0
    for exchange in exchanges:
        if exchange.has_symbol(symbol):
            coverage += 1
    
    # Require at least 2 exchanges for arbitrage
    return coverage >= 2
```

**Coverage Analysis:**
- **2 Exchanges**: Basic arbitrage possible
- **3 Exchanges**: Better opportunity detection
- **4+ Exchanges**: Optimal arbitrage possibilities

### Exchange-Specific Symbols

**Symbol Availability by Exchange:**
```python
{
    "BTCUSDT": ["binance", "bybit", "okx", "bitget"],
    "ETHUSDT": ["binance", "bybit", "okx", "bitget"],
    "ADAUSDT": ["binance", "bybit", "okx"],
    "DOGEUSDT": ["binance", "bybit", "bitget"],
    "NEWTOKEN": ["binance"]  # Single exchange - excluded
}
```

## Symbol Performance Analytics

### Performance Tracking

**Symbol Metrics:**
```python
def analyze_symbol_performance(symbol, period_days=30):
    opportunities = get_arbitrage_history(symbol, period_days)
    
    metrics = {
        "opportunity_count": len(opportunities),
        "avg_spread": calculate_average_spread(opportunities),
        "max_spread": max([opp.spread for opp in opportunities]),
        "frequency": len(opportunities) / period_days,
        "profitability": calculate_total_profit(opportunities),
        "success_rate": calculate_success_rate(opportunities)
    }
    
    return metrics
```

**Performance-Based Selection:**
```python
def select_by_performance(symbols, top_n=200):
    performance_scores = []
    
    for symbol in symbols:
        metrics = analyze_symbol_performance(symbol)
        
        # Calculate composite score
        score = (
            metrics["frequency"] * 0.3 +
            metrics["avg_spread"] * 0.3 +
            metrics["success_rate"] * 0.4
        )
        
        performance_scores.append((symbol, score))
    
    # Sort by performance score
    sorted_symbols = sorted(performance_scores, 
                           key=lambda x: x[1], reverse=True)
    
    return [symbol for symbol, score in sorted_symbols[:top_n]]
```

### Historical Analysis

**Symbol Lifecycle Management:**
```python
def manage_symbol_lifecycle():
    current_symbols = get_current_symbols()
    
    for symbol in current_symbols:
        performance = analyze_symbol_performance(symbol, 7)  # Last 7 days
        
        # Remove underperforming symbols
        if performance["opportunity_count"] < 5:
            remove_symbol(symbol)
            logger.info(f"Removed underperforming symbol: {symbol}")
        
        # Flag symbols for review
        elif performance["success_rate"] < 0.5:
            flag_for_review(symbol)
```

## Configuration Strategies

### Conservative Strategy

**High-Quality Symbols Only:**
```json
{
  "arbitrage": {
    "use_dynamic_symbols": true,
    "max_symbols": 50,
    "min_volume_24h": 50000000,
    "enabled_quote_currencies": ["USDT"],
    "min_exchanges": 3
  }
}
```

**Characteristics:**
- Fewer symbols (50)
- High volume requirement ($50M+)
- Single quote currency
- Minimum 3 exchange coverage

### Aggressive Strategy

**Maximum Opportunity Coverage:**
```json
{
  "arbitrage": {
    "use_dynamic_symbols": true,
    "max_symbols": 300,
    "min_volume_24h": 1000000,
    "enabled_quote_currencies": ["USDT", "USDC", "BTC"],
    "min_exchanges": 2
  }
}
```

**Characteristics:**
- More symbols (300)
- Lower volume requirement ($1M+)
- Multiple quote currencies
- Minimum 2 exchange coverage

### Balanced Strategy

**Optimal Risk-Reward:**
```json
{
  "arbitrage": {
    "use_dynamic_symbols": true,
    "max_symbols": 150,
    "min_volume_24h": 10000000,
    "enabled_quote_currencies": ["USDT", "USDC"],
    "min_exchanges": 2
  }
}
```

## Performance Considerations

### System Resource Impact

**CPU Usage by Symbol Count:**
- **50 symbols**: Low CPU usage (~10-20%)
- **100 symbols**: Moderate CPU usage (~20-40%)
- **200 symbols**: High CPU usage (~40-70%)
- **300+ symbols**: Very high CPU usage (>70%)

**Memory Usage:**
```python
# Approximate memory usage per symbol
memory_per_symbol = {
    "price_history": "~50KB",
    "orderbook_data": "~20KB", 
    "moving_averages": "~10KB",
    "metadata": "~5KB"
}

total_memory_mb = num_symbols * 0.085  # ~85KB per symbol
```

### Network Bandwidth

**WebSocket Connections:**
- Each symbol requires continuous price updates
- More symbols = more network traffic
- Consider connection limits per exchange

**Optimization Strategies:**
```python
# Batch processing for efficiency
def process_symbols_in_batches(symbols, batch_size=50):
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        process_symbol_batch(batch)
        
        # Rate limiting
        time.sleep(0.1)  # Prevent API overload
```

## Monitoring and Maintenance

### Symbol Health Monitoring

**Health Check Metrics:**
```python
def check_symbol_health(symbol):
    checks = {
        "data_freshness": check_recent_updates(symbol),
        "exchange_coverage": check_exchange_availability(symbol),
        "volume_stability": check_volume_consistency(symbol),
        "spread_quality": check_spread_history(symbol),
        "error_rate": check_error_frequency(symbol)
    }
    
    health_score = sum(checks.values()) / len(checks)
    return health_score
```

**Automated Maintenance:**
```python
def daily_symbol_maintenance():
    current_symbols = get_current_symbols()
    
    # Health check all symbols
    unhealthy_symbols = []
    for symbol in current_symbols:
        health_score = check_symbol_health(symbol)
        if health_score < 0.7:  # 70% threshold
            unhealthy_symbols.append(symbol)
    
    # Remove unhealthy symbols
    for symbol in unhealthy_symbols:
        remove_symbol(symbol)
        logger.warning(f"Removed unhealthy symbol: {symbol}")
    
    # Refresh symbol list if dynamic selection enabled
    if config.use_dynamic_symbols:
        refresh_dynamic_symbols()
```

### Performance Optimization

**Symbol Selection Optimization:**
```python
def optimize_symbol_selection():
    # Analyze performance of current symbols
    performance_data = analyze_all_symbols()
    
    # Find optimal symbol count for current hardware
    optimal_count = find_optimal_symbol_count(performance_data)
    
    # Adjust max_symbols if needed
    if optimal_count != config.max_symbols:
        config.max_symbols = optimal_count
        logger.info(f"Optimized symbol count to {optimal_count}")
```

## Troubleshooting

### Common Issues

**No Symbols Selected:**
1. Check quote currency settings
2. Verify exchange connections
3. Review volume thresholds
4. Check exchange symbol availability

**Poor Performance:**
1. Reduce max_symbols count
2. Increase volume thresholds
3. Focus on fewer quote currencies
4. Optimize hardware resources

**Missing Opportunities:**
1. Increase max_symbols count
2. Lower volume thresholds
3. Add more quote currencies
4. Review symbol filtering logic

### Debug Commands

**Symbol Analysis:**
```python
# Debug symbol selection
def debug_symbol_selection():
    all_symbols = get_all_available_symbols()
    filtered_symbols = apply_filters(all_symbols)
    selected_symbols = select_top_symbols(filtered_symbols)
    
    print(f"Total available: {len(all_symbols)}")
    print(f"After filtering: {len(filtered_symbols)}")
    print(f"Selected: {len(selected_symbols)}")
    
    return {
        "available": all_symbols,
        "filtered": filtered_symbols,
        "selected": selected_symbols
    }
```

**Performance Analysis:**
```python
# Analyze symbol performance impact
def analyze_performance_impact():
    symbol_counts = [50, 100, 150, 200, 250]
    
    for count in symbol_counts:
        start_time = time.time()
        simulate_symbol_processing(count)
        duration = time.time() - start_time
        
        print(f"Symbols: {count}, Processing time: {duration:.2f}s")
```

!!! tip "Symbol Optimization"
    Start with a conservative symbol count (50-100) and gradually increase based on your system's performance and the quality of opportunities detected.

!!! warning "Resource Monitoring"
    Monitor CPU and memory usage when increasing symbol counts. Too many symbols can degrade performance and miss time-sensitive arbitrage opportunities.

!!! note "Market Adaptation"
    Symbol performance can change rapidly in crypto markets. Regular analysis and optimization of your symbol selection criteria is essential for maintaining profitability.