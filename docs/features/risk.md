# Risk Management

ArBot implements a comprehensive risk management framework designed to protect your capital while maximizing arbitrage opportunities. The system operates at multiple levels - from individual trade risk to portfolio-wide exposure management.

## Risk Management Philosophy

### Multi-Layer Protection

**Defense in Depth:**
1. **Position Level**: Individual trade risk controls
2. **Portfolio Level**: Overall exposure management  
3. **System Level**: Technical and operational safeguards
4. **Market Level**: External condition monitoring

**Risk-First Approach:**
- Capital preservation over profit maximization
- Controlled exposure to market volatility
- Systematic risk measurement and monitoring
- Automated risk response mechanisms

## Position-Level Risk Controls

### Stop Loss Management

**Automatic Stop Losses:**
```json
{
  "risk_management": {
    "stop_loss_percent": 2.0,
    "enable_trailing_stops": true,
    "stop_loss_method": "percentage"
  }
}
```

**Stop Loss Mechanisms:**
- **Percentage-based**: Fixed percentage from entry price
- **Volatility-based**: Based on market volatility (ATR)
- **Time-based**: Maximum holding period limits
- **Trailing stops**: Dynamic adjustment with favorable moves

**Implementation:**
```python
def check_stop_loss(position, current_price):
    entry_price = position.entry_price
    stop_loss_threshold = config.stop_loss_percent / 100
    
    if position.side == "long":
        stop_price = entry_price * (1 - stop_loss_threshold)
        if current_price <= stop_price:
            return True  # Trigger stop loss
    
    elif position.side == "short":
        stop_price = entry_price * (1 + stop_loss_threshold)
        if current_price >= stop_price:
            return True  # Trigger stop loss
    
    return False
```

### Position Sizing

**Fixed Position Sizing:**
```json
{
  "arbitrage": {
    "trade_amount_usd": 100.0,
    "max_position_size": 1000.0
  }
}
```

**Dynamic Position Sizing:**
```python
def calculate_position_size(signal, account_balance):
    # Kelly Criterion implementation
    win_rate = get_historical_win_rate()
    avg_win = get_average_win()
    avg_loss = get_average_loss()
    
    kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
    
    # Apply safety factor
    safe_kelly = kelly_fraction * 0.25  # Use 25% of Kelly
    
    # Calculate position size
    position_size = account_balance * safe_kelly
    
    # Apply maximum limits
    return min(position_size, config.max_position_size)
```

**Position Sizing Methods:**
- **Fixed Amount**: Consistent USD amount per trade
- **Percentage of Balance**: Fixed percentage of total capital
- **Kelly Criterion**: Mathematically optimal sizing
- **Risk Parity**: Equal risk contribution per position

### Slippage Protection

**Slippage Estimation:**
```python
def estimate_slippage(symbol, trade_size, market_impact_model):
    # Get order book depth
    orderbook = get_orderbook(symbol)
    
    # Calculate market impact
    available_liquidity = sum(orderbook.bids[:10])  # Top 10 levels
    size_ratio = trade_size / available_liquidity
    
    # Estimate slippage based on size and volatility
    base_slippage = config.slippage_tolerance
    impact_slippage = size_ratio * market_impact_model.coefficient
    
    return base_slippage + impact_slippage
```

**Slippage Controls:**
- **Pre-trade estimation**: Calculate expected slippage
- **Dynamic adjustment**: Adjust for market conditions
- **Size limits**: Limit trades based on liquidity
- **Execution monitoring**: Track actual vs expected slippage

## Portfolio-Level Risk Management

### Drawdown Protection

**Maximum Drawdown Limits:**
```json
{
  "risk_management": {
    "max_drawdown_percent": 5.0,
    "drawdown_calculation": "peak_to_trough",
    "recovery_threshold": 50.0
  }
}
```

**Drawdown Monitoring:**
```python
class DrawdownMonitor:
    def __init__(self, max_drawdown_percent):
        self.max_drawdown = max_drawdown_percent / 100
        self.peak_balance = 0
        self.current_drawdown = 0
        
    def update(self, current_balance):
        # Update peak balance
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
        
        # Calculate current drawdown
        self.current_drawdown = (self.peak_balance - current_balance) / self.peak_balance
        
        # Check if limit exceeded
        if self.current_drawdown > self.max_drawdown:
            return "STOP_TRADING"  # Emergency stop
        
        return "CONTINUE"
```

**Drawdown Response Actions:**
1. **Warning Level (50% of limit)**: Reduce position sizes
2. **Critical Level (80% of limit)**: Stop new positions
3. **Maximum Level (100% of limit)**: Close all positions

### Concentration Risk

**Exposure Limits:**
```json
{
  "risk_management": {
    "max_concurrent_trades": 3,
    "max_symbol_exposure": 0.2,
    "max_exchange_exposure": 0.4,
    "correlation_threshold": 0.7
  }
}
```

**Concentration Monitoring:**
```python
def check_concentration_risk(new_position, current_portfolio):
    # Check symbol concentration
    symbol_exposure = calculate_symbol_exposure(new_position.symbol, current_portfolio)
    if symbol_exposure > config.max_symbol_exposure:
        return False
    
    # Check exchange concentration
    exchange_exposure = calculate_exchange_exposure(new_position.exchange, current_portfolio)
    if exchange_exposure > config.max_exchange_exposure:
        return False
    
    # Check correlation risk
    if check_correlation_risk(new_position, current_portfolio):
        return False
    
    return True
```

### Balance Protection

**Minimum Balance Threshold:**
```json
{
  "risk_management": {
    "balance_threshold_percent": 10.0,
    "reserve_balance": 1000.0,
    "emergency_liquidation": true
  }
}
```

**Balance Monitoring:**
- **Threshold alerts**: Warn when approaching minimum
- **Trading suspension**: Stop new trades below threshold
- **Emergency procedures**: Automated position closure

## System-Level Risk Controls

### Technical Risk Management

**Connection Monitoring:**
```python
class ConnectionHealthMonitor:
    def __init__(self):
        self.exchange_status = {}
        self.last_heartbeat = {}
        
    def monitor_exchanges(self):
        for exchange in self.exchanges:
            # Check WebSocket connection
            if not exchange.is_connected():
                self.handle_disconnection(exchange)
            
            # Check API response times
            if exchange.latency > MAX_LATENCY:
                self.handle_high_latency(exchange)
            
            # Check data freshness
            if time.time() - exchange.last_update > MAX_DATA_AGE:
                self.handle_stale_data(exchange)
```

**Risk Mitigation:**
- **Redundant connections**: Multiple data feeds
- **Circuit breakers**: Automatic trading suspension
- **Failover mechanisms**: Backup systems activation
- **Data validation**: Quality checks on all inputs

### Operational Risk

**Error Handling:**
```python
def handle_trading_error(error, context):
    error_severity = classify_error(error)
    
    if error_severity == "CRITICAL":
        # Stop all trading immediately
        emergency_stop()
        send_alert("Critical error - trading stopped")
        
    elif error_severity == "HIGH":
        # Suspend affected exchange/symbol
        suspend_trading(context.exchange, context.symbol)
        
    elif error_severity == "MEDIUM":
        # Reduce position sizes
        reduce_position_sizes(factor=0.5)
        
    # Log all errors for analysis
    log_error(error, context, error_severity)
```

**Error Classification:**
- **Critical**: System failures, API key issues
- **High**: Exchange disconnections, order failures
- **Medium**: Network delays, data inconsistencies
- **Low**: Minor warnings, performance issues

### Regulatory Risk

**Compliance Monitoring:**
```python
def check_regulatory_compliance(trade):
    # Check position limits
    if trade.size > REGULATORY_POSITION_LIMIT:
        return False
    
    # Check geographic restrictions
    if trade.exchange in RESTRICTED_EXCHANGES:
        return False
    
    # Check token restrictions
    if trade.symbol in RESTRICTED_SYMBOLS:
        return False
    
    return True
```

## Risk Metrics and Monitoring

### Real-Time Risk Metrics

**Portfolio Risk Dashboard:**
```python
{
    "current_drawdown": 2.3,
    "max_drawdown": 5.0,
    "var_95": -0.8,  # 95% Value at Risk
    "expected_shortfall": -1.2,
    "sharpe_ratio": 2.1,
    "sortino_ratio": 3.2,
    "beta": 0.3,
    "correlation_btc": 0.15
}
```

**Position-Level Metrics:**
```python
{
    "unrealized_pnl": 45.67,
    "unrealized_pnl_percent": 0.89,
    "time_in_position": 3600,  # seconds
    "stop_loss_distance": 1.2,
    "profit_target_distance": 2.8
}
```

### Risk Reporting

**Daily Risk Report:**
- Portfolio performance summary
- Risk metric trends
- Violation alerts and responses
- Market condition analysis

**Weekly Risk Review:**
- Strategy performance analysis
- Risk parameter optimization
- Stress test results
- Regulatory compliance check

## Advanced Risk Features

### Stress Testing

**Scenario Analysis:**
```python
def stress_test_portfolio(portfolio, scenarios):
    results = {}
    
    for scenario_name, scenario in scenarios.items():
        # Apply market shock
        shocked_prices = apply_shock(current_prices, scenario)
        
        # Calculate portfolio impact
        portfolio_pnl = calculate_portfolio_pnl(portfolio, shocked_prices)
        
        results[scenario_name] = {
            "portfolio_pnl": portfolio_pnl,
            "worst_position": find_worst_position(portfolio, shocked_prices),
            "recovery_time": estimate_recovery_time(portfolio_pnl)
        }
    
    return results
```

**Stress Scenarios:**
- **Market Crash**: -20% across all assets
- **Crypto Winter**: -50% sustained decline
- **Exchange Hack**: Single exchange shutdown
- **Regulatory Ban**: Specific region/token restrictions

### Dynamic Risk Adjustment

**Market Regime Detection:**
```python
def detect_market_regime(price_history, volatility_history):
    current_volatility = calculate_current_volatility()
    volatility_percentile = get_volatility_percentile(current_volatility)
    
    if volatility_percentile > 90:
        return "HIGH_VOLATILITY"
    elif volatility_percentile < 10:
        return "LOW_VOLATILITY"
    else:
        return "NORMAL"

def adjust_risk_parameters(market_regime):
    if market_regime == "HIGH_VOLATILITY":
        # Reduce position sizes and increase stops
        config.trade_amount_usd *= 0.5
        config.stop_loss_percent *= 0.8
        
    elif market_regime == "LOW_VOLATILITY":
        # Increase position sizes slightly
        config.trade_amount_usd *= 1.2
        config.min_profit_threshold *= 0.8
```

### Risk-Adjusted Performance

**Performance Metrics:**
```python
def calculate_risk_adjusted_returns(returns, risk_free_rate=0.02):
    excess_returns = returns - risk_free_rate
    
    metrics = {
        "sharpe_ratio": excess_returns.mean() / returns.std(),
        "sortino_ratio": excess_returns.mean() / returns[returns < 0].std(),
        "calmar_ratio": returns.mean() / max_drawdown,
        "omega_ratio": calculate_omega_ratio(returns),
        "tail_ratio": calculate_tail_ratio(returns)
    }
    
    return metrics
```

## Risk Configuration Examples

### Conservative Profile

**Ultra-Safe Settings:**
```json
{
  "risk_management": {
    "max_drawdown_percent": 2.0,
    "stop_loss_percent": 1.0,
    "max_concurrent_trades": 1,
    "balance_threshold_percent": 20.0,
    "position_sizing_method": "fixed"
  },
  "arbitrage": {
    "min_profit_threshold": 0.015,
    "max_position_size": 500.0,
    "use_trend_filter": true
  }
}
```

### Moderate Profile

**Balanced Risk-Reward:**
```json
{
  "risk_management": {
    "max_drawdown_percent": 5.0,
    "stop_loss_percent": 2.0,
    "max_concurrent_trades": 3,
    "balance_threshold_percent": 10.0,
    "position_sizing_method": "percentage"
  },
  "arbitrage": {
    "min_profit_threshold": 0.005,
    "max_position_size": 1000.0
  }
}
```

### Aggressive Profile

**Higher Risk Tolerance:**
```json
{
  "risk_management": {
    "max_drawdown_percent": 10.0,
    "stop_loss_percent": 3.0,
    "max_concurrent_trades": 5,
    "balance_threshold_percent": 5.0,
    "position_sizing_method": "kelly"
  },
  "arbitrage": {
    "min_profit_threshold": 0.003,
    "max_position_size": 2000.0
  }
}
```

## Best Practices

### Risk Management Principles

1. **Never Risk More Than You Can Afford to Lose**
2. **Diversify Across Exchanges and Symbols**
3. **Monitor Risk Metrics Continuously**
4. **Adjust Parameters Based on Market Conditions**
5. **Have Emergency Procedures Ready**

### Implementation Guidelines

**Daily Procedures:**
- Review overnight positions
- Check risk metric alerts
- Validate system connectivity
- Monitor market conditions

**Weekly Reviews:**
- Analyze performance vs risk
- Optimize risk parameters
- Stress test portfolio
- Review correlation patterns

**Monthly Analysis:**
- Comprehensive risk assessment
- Strategy performance review
- Risk parameter backtesting
- Regulatory compliance audit

!!! danger "Risk Warning"
    Cryptocurrency trading involves substantial risk of loss. Past performance does not guarantee future results. Never trade with funds you cannot afford to lose.

!!! tip "Risk Monitoring"
    Set up automated alerts for all risk metrics. Real-time monitoring is essential for effective risk management in fast-moving crypto markets.

!!! note "Risk vs Reward"
    Higher returns typically come with higher risks. Find the right balance for your risk tolerance and investment objectives through careful backtesting and gradual position size increases.