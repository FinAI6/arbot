# API Reference

ArBot provides a comprehensive REST API for programmatic access to trading functionality, historical data, and system monitoring. This API enables integration with external systems, custom dashboards, and automated trading workflows.

## API Overview

### Base Configuration

**Default Settings:**
```json
{
  "api": {
    "enabled": true,
    "host": "127.0.0.1",
    "port": 8080,
    "cors_enabled": true,
    "rate_limit": 100,
    "auth_required": false
  }
}
```

**Production Settings:**
```json
{
  "api": {
    "enabled": true,
    "host": "0.0.0.0",
    "port": 8080,
    "cors_enabled": false,
    "rate_limit": 1000,
    "auth_required": true,
    "ssl_cert": "/path/to/cert.pem",
    "ssl_key": "/path/to/key.pem"
  }
}
```

### Authentication

**API Key Authentication:**
```bash
# Set API key in environment
export ARBOT_API_KEY="your-secret-api-key"

# Include in requests
curl -H "X-API-Key: your-secret-api-key" http://localhost:8080/api/v1/status
```

**JWT Token Authentication:**
```python
# Login to get token
response = requests.post('http://localhost:8080/api/v1/auth/login', {
    'username': 'admin',
    'password': 'your-password'
})
token = response.json()['access_token']

# Use token in subsequent requests
headers = {'Authorization': f'Bearer {token}'}
response = requests.get('http://localhost:8080/api/v1/trades', headers=headers)
```

## Core Endpoints

### System Status

#### GET /api/v1/status

**Description:** Get current system status and health metrics.

**Response:**
```json
{
  "status": "running",
  "uptime": 3600,
  "version": "1.0.0",
  "mode": "live",
  "exchanges": {
    "binance": {
      "connected": true,
      "last_update": 1640995200.123,
      "latency_ms": 45
    },
    "bybit": {
      "connected": true,
      "last_update": 1640995200.100,
      "latency_ms": 52
    }
  },
  "active_symbols": 150,
  "signals_last_hour": 47,
  "trades_today": 12
}
```

**Example Usage:**
```python
import requests

response = requests.get('http://localhost:8080/api/v1/status')
status = response.json()

if status['status'] == 'running':
    print(f"ArBot is running with {status['active_symbols']} symbols")
else:
    print(f"ArBot status: {status['status']}")
```

#### GET /api/v1/health

**Description:** Detailed health check for monitoring systems.

**Response:**
```json
{
  "healthy": true,
  "checks": {
    "database": {
      "status": "pass",
      "response_time_ms": 2
    },
    "exchanges": {
      "status": "pass",
      "connected_count": 4,
      "total_count": 4
    },
    "memory": {
      "status": "pass",
      "usage_percent": 45.2
    },
    "disk": {
      "status": "pass",
      "free_space_gb": 125.6
    }
  }
}
```

### Trading Control

#### POST /api/v1/trading/start

**Description:** Start the arbitrage trading engine.

**Request Body:**
```json
{
  "mode": "live",  // "live", "simulation", "backtest"
  "symbols": ["BTCUSDT", "ETHUSDT"],  // Optional: specific symbols
  "exchanges": ["binance", "bybit"]   // Optional: specific exchanges
}
```

**Response:**
```json
{
  "success": true,
  "message": "Trading started successfully",
  "mode": "live",
  "start_time": "2024-01-01T12:00:00Z",
  "symbols_count": 150,
  "exchanges_count": 4
}
```

#### POST /api/v1/trading/stop

**Description:** Stop the trading engine gracefully.

**Response:**
```json
{
  "success": true,
  "message": "Trading stopped successfully",
  "stop_time": "2024-01-01T13:30:00Z",
  "trades_completed": 8,
  "pending_trades": 0
}
```

#### GET /api/v1/trading/config

**Description:** Get current trading configuration.

**Response:**
```json
{
  "arbitrage": {
    "min_profit_threshold": 0.005,
    "max_position_size": 1000.0,
    "trade_amount_usd": 100.0,
    "use_trend_filter": true,
    "trend_filter_mode": "both"
  },
  "risk_management": {
    "max_drawdown_percent": 5.0,
    "stop_loss_percent": 2.0,
    "max_concurrent_trades": 3
  },
  "exchanges": {
    "binance": {"enabled": true},
    "bybit": {"enabled": true}
  }
}
```

#### PUT /api/v1/trading/config

**Description:** Update trading configuration.

**Request Body:**
```json
{
  "arbitrage": {
    "min_profit_threshold": 0.006,
    "max_position_size": 1500.0
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Configuration updated successfully",
  "updated_fields": ["min_profit_threshold", "max_position_size"]
}
```

## Data Endpoints

### Price Data

#### GET /api/v1/prices/current

**Description:** Get current prices across all exchanges.

**Query Parameters:**
- `symbol` (optional): Filter by specific symbol
- `exchange` (optional): Filter by specific exchange

**Response:**
```json
{
  "timestamp": 1640995200.123,
  "prices": {
    "BTCUSDT": {
      "binance": {
        "bid": 43250.50,
        "ask": 43251.00,
        "bid_size": 2.5,
        "ask_size": 1.8,
        "timestamp": 1640995200.120
      },
      "bybit": {
        "bid": 43249.00,
        "ask": 43250.50,
        "bid_size": 3.2,
        "ask_size": 2.1,
        "timestamp": 1640995200.115
      }
    }
  }
}
```

#### GET /api/v1/prices/history

**Description:** Get historical price data.

**Query Parameters:**
- `symbol` (required): Trading symbol
- `exchange` (optional): Specific exchange
- `start_time` (required): Start timestamp
- `end_time` (required): End timestamp
- `interval` (optional): Data interval (1m, 5m, 1h, 1d)

**Response:**
```json
{
  "symbol": "BTCUSDT",
  "exchange": "binance",
  "interval": "1h",
  "data": [
    {
      "timestamp": 1640995200,
      "open": 43200.00,
      "high": 43350.00,
      "low": 43150.00,
      "close": 43250.00,
      "volume": 125.67
    }
  ]
}
```

#### GET /api/v1/spreads/current

**Description:** Get current arbitrage spreads.

**Query Parameters:**
- `symbol` (optional): Filter by symbol
- `min_profit` (optional): Minimum profit threshold

**Response:**
```json
{
  "timestamp": 1640995200.123,
  "spreads": [
    {
      "symbol": "BTCUSDT",
      "buy_exchange": "bybit",
      "sell_exchange": "binance",
      "buy_price": 43249.00,
      "sell_price": 43251.00,
      "spread": 2.00,
      "spread_percent": 0.0046,
      "profit_after_fees": 0.85,
      "profit_percent": 0.002
    }
  ]
}
```

### Trading Data

#### GET /api/v1/trades

**Description:** Get trade history.

**Query Parameters:**
- `start_date` (optional): Start date (YYYY-MM-DD)
- `end_date` (optional): End date (YYYY-MM-DD)
- `symbol` (optional): Filter by symbol
- `status` (optional): Filter by status
- `limit` (optional): Maximum number of results (default: 100)
- `offset` (optional): Pagination offset

**Response:**
```json
{
  "trades": [
    {
      "id": 123,
      "symbol": "BTCUSDT",
      "buy_exchange": "bybit",
      "sell_exchange": "binance",
      "quantity": 0.1,
      "planned_profit": 2.50,
      "actual_profit": 2.35,
      "fees_paid": 0.15,
      "status": "completed",
      "started_at": "2024-01-01T12:00:00Z",
      "completed_at": "2024-01-01T12:00:45Z"
    }
  ],
  "total_count": 1,
  "pagination": {
    "limit": 100,
    "offset": 0,
    "has_more": false
  }
}
```

#### GET /api/v1/trades/{trade_id}

**Description:** Get detailed information about a specific trade.

**Response:**
```json
{
  "id": 123,
  "signal_id": 456,
  "symbol": "BTCUSDT",
  "buy_exchange": "bybit",
  "sell_exchange": "binance",
  "buy_order_id": "buy_order_123",
  "sell_order_id": "sell_order_456",
  "planned_buy_price": 43249.00,
  "planned_sell_price": 43251.00,
  "actual_buy_price": 43249.50,
  "actual_sell_price": 43250.75,
  "quantity": 0.1,
  "planned_profit": 2.50,
  "actual_profit": 2.35,
  "fees_paid": 0.15,
  "slippage": 0.25,
  "status": "completed",
  "started_at": "2024-01-01T12:00:00Z",
  "completed_at": "2024-01-01T12:00:45Z",
  "execution_time_ms": 45000
}
```

#### GET /api/v1/signals

**Description:** Get arbitrage signals.

**Query Parameters:**
- `start_time` (optional): Start timestamp
- `end_time` (optional): End timestamp
- `symbol` (optional): Filter by symbol
- `executed` (optional): Filter by execution status
- `limit` (optional): Maximum number of results

**Response:**
```json
{
  "signals": [
    {
      "id": 456,
      "symbol": "BTCUSDT",
      "buy_exchange": "bybit",
      "sell_exchange": "binance",
      "buy_price": 43249.00,
      "sell_price": 43251.00,
      "profit": 2.00,
      "profit_percent": 0.0046,
      "confidence": 0.85,
      "executed": true,
      "timestamp": 1640995200.123
    }
  ],
  "total_count": 1
}
```

### Account Data

#### GET /api/v1/balances

**Description:** Get current account balances across all exchanges.

**Response:**
```json
{
  "timestamp": 1640995200.123,
  "balances": {
    "binance": {
      "USDT": {
        "free": 9850.25,
        "locked": 149.75,
        "total": 10000.00
      },
      "BTC": {
        "free": 0.15,
        "locked": 0.05,
        "total": 0.20
      }
    },
    "bybit": {
      "USDT": {
        "free": 4925.50,
        "locked": 74.50,
        "total": 5000.00
      }
    }
  },
  "total_value_usd": 23645.75
}
```

#### GET /api/v1/performance

**Description:** Get trading performance metrics.

**Query Parameters:**
- `period` (optional): Time period (day, week, month, year)
- `start_date` (optional): Custom start date
- `end_date` (optional): Custom end date

**Response:**
```json
{
  "period": "month",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "metrics": {
    "total_trades": 342,
    "successful_trades": 318,
    "win_rate": 92.98,
    "total_profit": 1247.85,
    "total_fees": 89.32,
    "net_profit": 1158.53,
    "avg_profit_per_trade": 3.65,
    "max_profit": 45.67,
    "max_loss": -12.34,
    "avg_execution_time_seconds": 42.5,
    "sharpe_ratio": 2.14,
    "max_drawdown_percent": 2.8,
    "profit_factor": 4.2
  },
  "daily_breakdown": [
    {
      "date": "2024-01-01",
      "trades": 15,
      "profit": 52.34,
      "win_rate": 93.33
    }
  ]
}
```

## WebSocket API

### Real-time Data Streams

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8080/api/v1/ws');

// Authentication (if required)
ws.send(JSON.stringify({
    type: 'auth',
    token: 'your-jwt-token'
}));
```

**Subscribe to Price Updates:**
```javascript
// Subscribe to all price updates
ws.send(JSON.stringify({
    type: 'subscribe',
    channel: 'prices',
    symbols: ['BTCUSDT', 'ETHUSDT']  // Optional filter
}));

// Receive price updates
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'price_update') {
        console.log('Price update:', data.data);
    }
};
```

**Subscribe to Trading Signals:**
```javascript
// Subscribe to arbitrage signals
ws.send(JSON.stringify({
    type: 'subscribe',
    channel: 'signals'
}));

// Receive signal updates
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'signal') {
        console.log('New arbitrage signal:', data.data);
    }
};
```

**Subscribe to Trade Updates:**
```javascript
// Subscribe to trade execution updates
ws.send(JSON.stringify({
    type: 'subscribe',
    channel: 'trades'
}));

// Receive trade updates
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'trade_update') {
        console.log('Trade update:', data.data);
    }
};
```

## Advanced Features

### Batch Operations

#### POST /api/v1/batch/trades

**Description:** Execute multiple trading operations in a single request.

**Request Body:**
```json
{
  "operations": [
    {
      "type": "execute_signal",
      "signal_id": 123,
      "quantity": 0.1
    },
    {
      "type": "cancel_trade",
      "trade_id": 456
    }
  ]
}
```

**Response:**
```json
{
  "results": [
    {
      "operation": 1,
      "success": true,
      "trade_id": 789
    },
    {
      "operation": 2,
      "success": false,
      "error": "Trade not found"
    }
  ]
}
```

### Custom Analytics

#### POST /api/v1/analytics/query

**Description:** Execute custom analytics queries.

**Request Body:**
```json
{
  "query_type": "symbol_performance",
  "parameters": {
    "symbols": ["BTCUSDT", "ETHUSDT"],
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "metrics": ["profit", "win_rate", "volume"]
  }
}
```

**Response:**
```json
{
  "query_type": "symbol_performance",
  "results": {
    "BTCUSDT": {
      "profit": 567.89,
      "win_rate": 94.2,
      "volume": 125.67
    },
    "ETHUSDT": {
      "profit": 234.56,
      "win_rate": 91.8,
      "volume": 89.23
    }
  },
  "execution_time_ms": 125
}
```

### Risk Management

#### POST /api/v1/risk/emergency-stop

**Description:** Emergency stop all trading activities.

**Request Body:**
```json
{
  "reason": "Market volatility spike",
  "force": false  // Force close all positions
}
```

**Response:**
```json
{
  "success": true,
  "message": "Emergency stop activated",
  "trades_cancelled": 3,
  "positions_closed": 2,
  "timestamp": "2024-01-01T15:30:00Z"
}
```

#### GET /api/v1/risk/limits

**Description:** Get current risk management limits and usage.

**Response:**
```json
{
  "limits": {
    "max_drawdown_percent": 5.0,
    "current_drawdown_percent": 2.3,
    "max_concurrent_trades": 5,
    "current_active_trades": 2,
    "daily_loss_limit": 1000.0,
    "current_daily_loss": 125.50
  },
  "status": "normal",  // "normal", "warning", "critical"
  "warnings": []
}
```

## Error Handling

### Standard Error Response

```json
{
  "error": {
    "code": "INVALID_SYMBOL",
    "message": "Symbol 'INVALID' is not supported",
    "details": {
      "valid_symbols": ["BTCUSDT", "ETHUSDT"],
      "provided_symbol": "INVALID"
    },
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|------------|-------------|
| `INVALID_SYMBOL` | 400 | Invalid trading symbol |
| `EXCHANGE_NOT_AVAILABLE` | 503 | Exchange connection unavailable |
| `INSUFFICIENT_BALANCE` | 400 | Insufficient account balance |
| `RATE_LIMIT_EXCEEDED` | 429 | API rate limit exceeded |
| `UNAUTHORIZED` | 401 | Invalid or missing authentication |
| `TRADING_DISABLED` | 403 | Trading is currently disabled |
| `INTERNAL_ERROR` | 500 | Internal server error |

## Rate Limiting

### Default Limits

| Endpoint Type | Requests per Minute | Burst Limit |
|---------------|-------------------|-------------|
| Read Operations | 1000 | 50 |
| Write Operations | 100 | 10 |
| WebSocket Connections | 10 | 3 |

### Rate Limit Headers

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 987
X-RateLimit-Reset: 1640995260
X-RateLimit-Type: requests
```

## SDK Examples

### Python SDK

```python
import requests
from datetime import datetime, timedelta

class ArbotClient:
    def __init__(self, base_url="http://localhost:8080", api_key=None):
        self.base_url = base_url
        self.headers = {}
        if api_key:
            self.headers['X-API-Key'] = api_key
    
    def get_status(self):
        response = requests.get(f"{self.base_url}/api/v1/status", headers=self.headers)
        return response.json()
    
    def get_current_prices(self, symbol=None):
        params = {'symbol': symbol} if symbol else {}
        response = requests.get(
            f"{self.base_url}/api/v1/prices/current", 
            params=params, 
            headers=self.headers
        )
        return response.json()
    
    def get_trades(self, start_date=None, end_date=None, symbol=None, limit=100):
        params = {'limit': limit}
        if start_date:
            params['start_date'] = start_date.strftime('%Y-%m-%d')
        if end_date:
            params['end_date'] = end_date.strftime('%Y-%m-%d')
        if symbol:
            params['symbol'] = symbol
        
        response = requests.get(
            f"{self.base_url}/api/v1/trades", 
            params=params, 
            headers=self.headers
        )
        return response.json()
    
    def start_trading(self, mode="live"):
        response = requests.post(
            f"{self.base_url}/api/v1/trading/start",
            json={'mode': mode},
            headers=self.headers
        )
        return response.json()
    
    def stop_trading(self):
        response = requests.post(
            f"{self.base_url}/api/v1/trading/stop",
            headers=self.headers
        )
        return response.json()

# Usage example
client = ArbotClient(api_key="your-api-key")

# Get system status
status = client.get_status()
print(f"ArBot status: {status['status']}")

# Get recent trades
recent_trades = client.get_trades(
    start_date=datetime.now() - timedelta(days=1),
    limit=50
)
print(f"Found {len(recent_trades['trades'])} recent trades")

# Start trading
result = client.start_trading(mode="simulation")
print(f"Trading started: {result['success']}")
```

### JavaScript SDK

```javascript
class ArbotClient {
    constructor(baseUrl = 'http://localhost:8080', apiKey = null) {
        this.baseUrl = baseUrl;
        this.headers = {
            'Content-Type': 'application/json'
        };
        if (apiKey) {
            this.headers['X-API-Key'] = apiKey;
        }
    }

    async request(method, endpoint, data = null) {
        const config = {
            method,
            headers: this.headers
        };

        if (data) {
            config.body = JSON.stringify(data);
        }

        const response = await fetch(`${this.baseUrl}${endpoint}`, config);
        return await response.json();
    }

    async getStatus() {
        return await this.request('GET', '/api/v1/status');
    }

    async getCurrentPrices(symbol = null) {
        const query = symbol ? `?symbol=${symbol}` : '';
        return await this.request('GET', `/api/v1/prices/current${query}`);
    }

    async getTrades(options = {}) {
        const params = new URLSearchParams();
        Object.entries(options).forEach(([key, value]) => {
            if (value !== null && value !== undefined) {
                params.append(key, value);
            }
        });
        
        const query = params.toString() ? `?${params.toString()}` : '';
        return await this.request('GET', `/api/v1/trades${query}`);
    }

    async startTrading(mode = 'live') {
        return await this.request('POST', '/api/v1/trading/start', { mode });
    }

    async stopTrading() {
        return await this.request('POST', '/api/v1/trading/stop');
    }
}

// Usage example
const client = new ArbotClient('http://localhost:8080', 'your-api-key');

// Get system status
client.getStatus().then(status => {
    console.log(`ArBot status: ${status.status}`);
});

// Get current prices
client.getCurrentPrices('BTCUSDT').then(prices => {
    console.log('Current BTC prices:', prices);
});

// WebSocket connection
const ws = new WebSocket('ws://localhost:8080/api/v1/ws');
ws.onopen = () => {
    ws.send(JSON.stringify({
        type: 'subscribe',
        channel: 'signals'
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'signal') {
        console.log('New arbitrage signal:', data.data);
    }
};
```

!!! tip "API Best Practices"
    Always implement proper error handling and respect rate limits. Use WebSocket connections for real-time data instead of polling REST endpoints frequently.

!!! warning "Security"
    Never expose API keys in client-side code. Use environment variables for API keys and enable authentication in production environments.

!!! note "Performance"
    Use batch operations when possible and implement connection pooling for high-frequency API usage. Monitor your API usage with the provided rate limit headers.