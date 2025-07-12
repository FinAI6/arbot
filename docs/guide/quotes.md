# Quote Currency Management

ArBot's quote currency system allows you to focus arbitrage opportunities on specific base currencies, optimizing for liquidity, stability, and regional preferences. The system supports multiple quote currencies simultaneously and provides intelligent filtering based on market conditions.

## Overview

### Supported Quote Currencies

**Primary Stablecoins:**
- **USDT** (Tether) - Most liquid, widely supported
- **USDC** (USD Coin) - Regulated, institutional grade
- **BUSD** (Binance USD) - Exchange-specific advantages
- **DAI** (MakerDAO) - Decentralized stablecoin

**Major Cryptocurrencies:**
- **BTC** (Bitcoin) - Crypto base pairs
- **ETH** (Ethereum) - DeFi ecosystem pairs
- **BNB** (Binance Coin) - Exchange token pairs

### Quote Currency Strategy Benefits

**Stablecoin Focus:**
- Reduced volatility risk
- Easier profit calculations
- Better regulatory compliance
- Lower correlation to crypto markets

**Multi-Currency Approach:**
- More arbitrage opportunities
- Geographic diversification
- Market condition adaptation
- Enhanced profit potential

## Configuration

### Basic Setup

```json
{
  "arbitrage": {
    "enabled_quote_currencies": ["USDT", "USDC"],
    "available_quote_currencies": [
      "USDT", "BUSD", "USDC", "DAI",
      "BTC", "ETH", "BNB"
    ],
    "quote_currency_priority": {
      "USDT": 1.0,
      "USDC": 0.9,
      "BUSD": 0.8,
      "BTC": 0.7,
      "ETH": 0.6
    }
  }
}
```

### Priority-Based Selection

**Priority Weighting:**
```python
def calculate_quote_priority(symbol, quote_currencies):
    priorities = []
    
    for quote in quote_currencies:
        if symbol.endswith(quote):
            priority = config.quote_currency_priority.get(quote, 0.5)
            volume_24h = get_symbol_volume(symbol)
            
            # Adjust priority by volume
            volume_weight = min(volume_24h / 10000000, 2.0)  # Cap at 2x
            final_priority = priority * volume_weight
            
            priorities.append((symbol, quote, final_priority))
    
    return sorted(priorities, key=lambda x: x[2], reverse=True)
```

### Dynamic Quote Selection

**Market Condition Adaptation:**
```python
def adapt_quote_currencies(market_conditions):
    base_quotes = config.enabled_quote_currencies
    
    if market_conditions.volatility > HIGH_VOLATILITY_THRESHOLD:
        # Prefer stablecoins during high volatility
        return [q for q in base_quotes if q in STABLECOINS]
    
    elif market_conditions.trend == "bull_market":
        # Include crypto pairs during bull markets
        return base_quotes + ["BTC", "ETH"]
    
    elif market_conditions.liquidity < LOW_LIQUIDITY_THRESHOLD:
        # Focus on most liquid pairs
        return ["USDT"]  # Most liquid quote currency
    
    return base_quotes
```

## Quote Currency Analysis

### USDT (Tether)

**Market Dominance:**
- 60-70% of total crypto trading volume
- Available on all major exchanges
- Highest liquidity across all pairs
- Most arbitrage opportunities

**Advantages:**
- Maximum liquidity
- Widest exchange support
- Fastest execution
- Most stable spreads

**Considerations:**
- Regulatory scrutiny
- Centralization concerns
- Price stability questions

**Configuration:**
```json
{
  "quote_analysis": {
    "USDT": {
      "market_share": 0.65,
      "liquidity_score": 1.0,
      "stability_score": 0.95,
      "availability_score": 1.0
    }
  }
}
```

### USDC (USD Coin)

**Institutional Grade:**
- Regulated by US authorities
- Monthly attestation reports
- Growing institutional adoption
- Strong compliance framework

**Advantages:**
- Regulatory compliance
- Institutional trust
- Stable backing
- Growing liquidity

**Considerations:**
- Lower liquidity than USDT
- Fewer exchange pairs
- Geographic restrictions

**Configuration:**
```json
{
  "quote_analysis": {
    "USDC": {
      "market_share": 0.15,
      "liquidity_score": 0.8,
      "stability_score": 0.98,
      "compliance_score": 1.0
    }
  }
}
```

### BTC (Bitcoin)

**Crypto Base Pairs:**
- Traditional crypto trading
- Established market patterns
- High correlation opportunities
- Institutional interest

**Advantages:**
- Deep historical data
- Predictable patterns
- High-value opportunities
- Global acceptance

**Considerations:**
- High volatility
- Complex calculations
- Correlation risks
- Timing sensitivity

**Configuration:**
```json
{
  "quote_analysis": {
    "BTC": {
      "market_share": 0.10,
      "volatility_score": 0.7,
      "opportunity_multiplier": 1.5,
      "correlation_risk": 0.8
    }
  }
}
```

## Regional Preferences

### Geographic Quote Patterns

**Asia-Pacific:**
- Strong USDT preference
- Growing USDC adoption
- Local stablecoin integration

**Europe:**
- USDC preference for compliance
- EUR stablecoin interest
- Regulatory-friendly options

**Americas:**
- USDC institutional adoption
- USDT retail preference
- Regulatory compliance focus

**Configuration by Region:**
```json
{
  "regional_preferences": {
    "asia_pacific": {
      "primary_quotes": ["USDT", "USDC"],
      "weight_multiplier": 1.2
    },
    "europe": {
      "primary_quotes": ["USDC", "USDT"],
      "compliance_required": true
    },
    "americas": {
      "primary_quotes": ["USDC", "USDT"],
      "institutional_focus": true
    }
  }
}
```

## Performance Optimization

### Quote Currency Performance Metrics

**Tracking Performance:**
```python
def analyze_quote_performance(quote_currency, period_days=30):
    trades = get_trades_by_quote(quote_currency, period_days)
    
    metrics = {
        "total_trades": len(trades),
        "success_rate": calculate_success_rate(trades),
        "avg_profit_pct": calculate_average_profit(trades),
        "total_volume": sum(trade.volume for trade in trades),
        "avg_execution_time": calculate_avg_execution_time(trades),
        "slippage_rate": calculate_slippage_rate(trades)
    }
    
    return metrics
```

**Performance Ranking:**
```python
def rank_quote_currencies():
    rankings = []
    
    for quote in config.available_quote_currencies:
        performance = analyze_quote_performance(quote)
        
        # Calculate composite score
        score = (
            performance["success_rate"] * 0.3 +
            performance["avg_profit_pct"] * 0.3 +
            (performance["total_trades"] / 100) * 0.2 +
            (1 - performance["slippage_rate"]) * 0.2
        )
        
        rankings.append((quote, score, performance))
    
    return sorted(rankings, key=lambda x: x[1], reverse=True)
```

### Optimization Strategies

**Volume-Weighted Selection:**
```python
def optimize_quote_selection(target_volume):
    quote_volumes = {}
    
    for quote in config.enabled_quote_currencies:
        daily_volume = get_daily_volume_by_quote(quote)
        quote_volumes[quote] = daily_volume
    
    # Sort by volume and select top performers
    sorted_quotes = sorted(quote_volumes.items(), 
                          key=lambda x: x[1], reverse=True)
    
    selected_quotes = []
    cumulative_volume = 0
    
    for quote, volume in sorted_quotes:
        selected_quotes.append(quote)
        cumulative_volume += volume
        
        if cumulative_volume >= target_volume:
            break
    
    return selected_quotes
```

## Risk Management

### Quote Currency Risk Factors

**Stablecoin Risks:**
- Regulatory changes
- Backing asset issues
- Liquidity crises
- Technical failures

**Crypto Quote Risks:**
- High volatility
- Correlation effects
- Market manipulation
- Timing risks

**Risk Mitigation:**
```python
def assess_quote_currency_risk(quote_currency):
    risk_factors = {
        "regulatory_risk": get_regulatory_score(quote_currency),
        "liquidity_risk": get_liquidity_score(quote_currency),
        "volatility_risk": get_volatility_score(quote_currency),
        "concentration_risk": get_concentration_score(quote_currency)
    }
    
    # Calculate overall risk score
    risk_score = sum(risk_factors.values()) / len(risk_factors)
    
    return risk_score, risk_factors
```

### Diversification Strategies

**Multi-Quote Diversification:**
```json
{
  "diversification": {
    "max_quote_concentration": 0.6,
    "min_quote_allocation": 0.1,
    "rebalance_threshold": 0.15,
    "correlation_limit": 0.8
  }
}
```

**Dynamic Rebalancing:**
```python
def rebalance_quote_allocation():
    current_allocation = get_current_quote_allocation()
    target_allocation = calculate_optimal_allocation()
    
    for quote in config.enabled_quote_currencies:
        current_pct = current_allocation.get(quote, 0)
        target_pct = target_allocation.get(quote, 0)
        
        deviation = abs(current_pct - target_pct)
        
        if deviation > config.rebalance_threshold:
            adjust_quote_allocation(quote, target_pct)
```

## Advanced Features

### Cross-Quote Arbitrage

**Multi-Hop Opportunities:**
```python
def find_cross_quote_arbitrage():
    # Example: USDT -> BTC -> ETH -> USDC -> USDT
    opportunities = []
    
    for path in generate_currency_paths():
        if len(path) <= MAX_HOP_COUNT:
            profit = calculate_multi_hop_profit(path)
            
            if profit > config.min_profit_threshold:
                opportunities.append({
                    "path": path,
                    "profit": profit,
                    "complexity": len(path)
                })
    
    return sorted(opportunities, key=lambda x: x["profit"], reverse=True)
```

### Smart Quote Selection

**Machine Learning Integration:**
```python
def predict_optimal_quotes(market_features):
    # Use trained model to predict best quote currencies
    prediction = quote_selection_model.predict(market_features)
    
    # Convert predictions to quote currency weights
    quote_weights = {
        "USDT": prediction[0],
        "USDC": prediction[1],
        "BTC": prediction[2],
        "ETH": prediction[3]
    }
    
    return quote_weights
```

## Configuration Examples

### Conservative Strategy

**Stablecoin Focus:**
```json
{
  "arbitrage": {
    "enabled_quote_currencies": ["USDT", "USDC"],
    "quote_currency_priority": {
      "USDT": 1.0,
      "USDC": 0.9
    },
    "max_quote_volatility": 0.01,
    "require_stablecoin": true
  }
}
```

### Aggressive Strategy

**Multi-Currency Approach:**
```json
{
  "arbitrage": {
    "enabled_quote_currencies": ["USDT", "USDC", "BTC", "ETH"],
    "dynamic_quote_selection": true,
    "volatility_tolerance": 0.05,
    "cross_quote_arbitrage": true
  }
}
```

### Balanced Strategy

**Risk-Adjusted Selection:**
```json
{
  "arbitrage": {
    "enabled_quote_currencies": ["USDT", "USDC", "BTC"],
    "quote_currency_priority": {
      "USDT": 1.0,
      "USDC": 0.8,
      "BTC": 0.6
    },
    "risk_adjusted_weights": true,
    "max_crypto_quote_allocation": 0.3
  }
}
```

## Monitoring and Analytics

### Quote Currency Dashboard

**Real-Time Metrics:**
- Volume by quote currency
- Spread analysis by quote
- Performance comparison
- Risk metrics

**Historical Analysis:**
- Quote currency trends
- Seasonal patterns
- Performance correlation
- Risk-adjusted returns

### Performance Reports

**Daily Reports:**
```python
def generate_quote_performance_report():
    report = {
        "date": datetime.now().date(),
        "quote_performance": {},
        "top_performers": [],
        "risk_analysis": {}
    }
    
    for quote in config.enabled_quote_currencies:
        performance = analyze_quote_performance(quote, 1)
        report["quote_performance"][quote] = performance
    
    return report
```

!!! tip "Quote Optimization"
    Start with USDT and USDC for maximum liquidity and stability. Gradually add other quote currencies based on your risk tolerance and market opportunities.

!!! warning "Volatility Risk"
    Crypto quote currencies (BTC, ETH) add significant volatility to your arbitrage returns. Use appropriate position sizing and risk management when trading these pairs.

!!! note "Market Evolution"
    Quote currency preferences evolve with market conditions and regulations. Regularly review and optimize your quote currency selection based on performance data and market changes.