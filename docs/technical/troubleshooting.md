# Troubleshooting Guide

This comprehensive troubleshooting guide helps you diagnose and resolve common issues with ArBot. The guide is organized by problem category and includes detailed solutions, diagnostic steps, and prevention strategies.

## Quick Diagnostic Checklist

### System Health Check

```bash
# Check ArBot status
curl http://localhost:8080/api/v1/health

# Check log files
tail -f logs/arbot.log

# Check system resources
top -p $(pgrep -f arbot)

# Check network connectivity
ping api.binance.com
ping api.bybit.com
```

### Common Indicators

| Symptom | Likely Cause | Quick Fix |
|---------|--------------|----------|
| No arbitrage signals | Exchange disconnection | Check internet/API keys |
| High CPU usage | Too many symbols | Reduce max_symbols |
| Memory leaks | Database not closing connections | Restart ArBot |
| Execution failures | Insufficient balance | Check account balances |
| GUI not updating | WebSocket connection lost | Restart GUI |

## Connection Issues

### Exchange API Connection Problems

#### Symptom: "Exchange not connected" or "Connection timeout"

**Diagnostic Steps:**
```python
# Test exchange connectivity
import requests

# Test Binance API
try:
    response = requests.get('https://api.binance.com/api/v3/ping', timeout=5)
    print(f"Binance API: {response.status_code}")
except Exception as e:
    print(f"Binance API Error: {e}")

# Test Bybit API
try:
    response = requests.get('https://api.bybit.com/v3/public/time', timeout=5)
    print(f"Bybit API: {response.status_code}")
except Exception as e:
    print(f"Bybit API Error: {e}")
```

**Common Causes and Solutions:**

1. **Invalid API Keys**
   ```bash
   # Check API key format
   echo $BINANCE_API_KEY | wc -c  # Should be 64 characters
   echo $BINANCE_API_SECRET | wc -c  # Should be 64 characters
   
   # Test API key validity
   curl -H "X-MBX-APIKEY: $BINANCE_API_KEY" \
        "https://api.binance.com/api/v3/account"
   ```

2. **Network Connectivity**
   ```bash
   # Check DNS resolution
   nslookup api.binance.com
   nslookup api.bybit.com
   
   # Check firewall/proxy
   curl -v https://api.binance.com/api/v3/ping
   ```

3. **Rate Limiting**
   ```bash
   # Check for rate limit errors in logs
   grep -i "rate limit" logs/arbot.log
   grep -i "429" logs/arbot.log
   ```

**Solutions:**
```python
# config.py adjustments for connection issues
EXCHANGE_CONFIG = {
    "connection_timeout": 10,  # Increase timeout
    "retry_attempts": 5,       # More retry attempts
    "retry_delay": 2,          # Delay between retries
    "rate_limit_buffer": 0.1   # 10% buffer for rate limits
}
```

### WebSocket Connection Issues

#### Symptom: "WebSocket disconnected" or "No real-time data"

**Diagnostic Steps:**
```python
# Test WebSocket connection manually
import websocket
import json

def on_message(ws, message):
    print(f"Received: {message}")

def on_error(ws, error):
    print(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("WebSocket closed")

def on_open(ws):
    # Subscribe to ticker data
    subscribe_msg = {
        "method": "SUBSCRIBE",
        "params": ["btcusdt@ticker"],
        "id": 1
    }
    ws.send(json.dumps(subscribe_msg))

# Test Binance WebSocket
ws = websocket.WebSocketApp("wss://stream.binance.com:9443/ws/btcusdt@ticker",
                          on_message=on_message,
                          on_error=on_error,
                          on_close=on_close,
                          on_open=on_open)
ws.run_forever()
```

**Solutions:**
1. **Implement Reconnection Logic**
   ```python
   class RobustWebSocket:
       def __init__(self, url):
           self.url = url
           self.reconnect_attempts = 0
           self.max_reconnect_attempts = 10
       
       async def connect_with_retry(self):
           while self.reconnect_attempts < self.max_reconnect_attempts:
               try:
                   await self.connect()
                   self.reconnect_attempts = 0  # Reset on success
                   break
               except Exception as e:
                   self.reconnect_attempts += 1
                   wait_time = min(2 ** self.reconnect_attempts, 60)
                   await asyncio.sleep(wait_time)
   ```

2. **Monitor Connection Health**
   ```python
   async def websocket_health_check():
       last_message_time = time.time()
       
       while True:
           if time.time() - last_message_time > 30:  # 30 seconds timeout
               logger.warning("WebSocket seems disconnected, reconnecting...")
               await reconnect_websocket()
           
           await asyncio.sleep(5)
   ```

## Trading Issues

### No Arbitrage Opportunities Found

#### Symptom: "No signals generated" or "Signal count: 0"

**Diagnostic Steps:**
```python
# Check current spreads manually
async def check_spreads_manually():
    binance_price = await get_binance_price("BTCUSDT")
    bybit_price = await get_bybit_price("BTCUSDT")
    
    spread = abs(binance_price['ask'] - bybit_price['bid'])
    spread_percent = spread / binance_price['ask'] * 100
    
    print(f"Binance: {binance_price}")
    print(f"Bybit: {bybit_price}")
    print(f"Spread: {spread} ({spread_percent:.4f}%)")
    
    # Check against configured thresholds
    min_threshold = config.arbitrage.min_profit_threshold
    print(f"Min threshold: {min_threshold * 100:.4f}%")
    print(f"Profitable: {spread_percent > min_threshold * 100}")
```

**Common Causes:**

1. **Thresholds Too High**
   ```json
   {
     "arbitrage": {
       "min_profit_threshold": 0.001,  // Lower from 0.005
       "slippage_tolerance": 0.001     // Reduce slippage assumption
     }
   }
   ```

2. **Market Conditions**
   ```python
   # Check market volatility
   def check_market_conditions():
       volatility = calculate_24h_volatility("BTCUSDT")
       volume = get_24h_volume("BTCUSDT")
       
       print(f"24h Volatility: {volatility:.2f}%")
       print(f"24h Volume: ${volume:,.2f}")
       
       if volatility < 1.0:
           print("Low volatility - fewer arbitrage opportunities")
       if volume < 1000000:
           print("Low volume - reduced liquidity")
   ```

3. **Symbol Selection Issues**
   ```python
   # Debug symbol selection
   def debug_symbol_selection():
       all_symbols = get_all_available_symbols()
       filtered_symbols = apply_filters(all_symbols)
       
       print(f"Total symbols available: {len(all_symbols)}")
       print(f"After filtering: {len(filtered_symbols)}")
       
       if len(filtered_symbols) == 0:
           print("No symbols pass filters - check quote currency settings")
   ```

### Order Execution Failures

#### Symptom: "Order failed" or "Insufficient balance"

**Diagnostic Steps:**
```python
# Check account balances
async def check_balances():
    exchanges = ['binance', 'bybit']
    
    for exchange in exchanges:
        try:
            balance = await get_exchange_balance(exchange)
            print(f"{exchange.title()} Balances:")
            for asset, amount in balance.items():
                if amount > 0:
                    print(f"  {asset}: {amount}")
        except Exception as e:
            print(f"Error getting {exchange} balance: {e}")

# Test order placement (small amount)
async def test_order_placement():
    try:
        test_order = await place_test_order(
            symbol="BTCUSDT",
            side="BUY",
            amount=0.001,  # Small test amount
            exchange="binance"
        )
        print(f"Test order successful: {test_order}")
    except Exception as e:
        print(f"Test order failed: {e}")
```

**Solutions:**

1. **Balance Management**
   ```python
   # Implement balance checks before trading
   def check_sufficient_balance(symbol, amount, exchange):
       base_asset = symbol.replace('USDT', '')  # e.g., BTC from BTCUSDT
       quote_asset = 'USDT'
       
       balances = get_exchange_balance(exchange)
       
       required_quote = amount  # USD amount
       available_quote = balances.get(quote_asset, 0)
       
       if available_quote < required_quote * 1.1:  # 10% buffer
           raise InsufficientBalanceError(f"Need {required_quote}, have {available_quote}")
   ```

2. **Order Size Optimization**
   ```python
   # Adjust order sizes based on available liquidity
   def calculate_optimal_order_size(symbol, target_amount):
       orderbook = get_orderbook(symbol)
       
       # Check available liquidity in top 5 levels
       available_liquidity = sum(
           level['quantity'] for level in orderbook['bids'][:5]
       )
       
       # Use maximum 10% of available liquidity
       max_safe_size = available_liquidity * 0.1
       
       return min(target_amount, max_safe_size)
   ```

## Performance Issues

### High CPU Usage

#### Symptom: CPU usage consistently above 80%

**Diagnostic Steps:**
```bash
# Profile CPU usage
python -m cProfile -s cumulative main.py > cpu_profile.txt

# Check for CPU-intensive operations
grep -E "(calculate|process|analyze)" cpu_profile.txt | head -20

# Monitor real-time CPU usage
top -p $(pgrep -f arbot) -d 1
```

**Common Causes and Solutions:**

1. **Too Many Symbols**
   ```json
   {
     "arbitrage": {
       "max_symbols": 100,  // Reduce from 200+
       "symbol_update_interval": 3600  // Reduce update frequency
     }
   }
   ```

2. **Inefficient Data Processing**
   ```python
   # Optimize price data processing
   import numpy as np
   
   # Use vectorized operations instead of loops
   def calculate_spreads_vectorized(prices_df):
       spreads = np.abs(prices_df['ask'] - prices_df['bid'])
       spread_percentages = spreads / prices_df['ask'] * 100
       return spread_percentages
   
   # Cache frequently accessed data
   from functools import lru_cache
   
   @lru_cache(maxsize=1000)
   def get_symbol_info(symbol):
       return fetch_symbol_info(symbol)
   ```

3. **Database Inefficiency**
   ```sql
   -- Add missing indexes
   CREATE INDEX IF NOT EXISTS idx_tickers_symbol_timestamp 
   ON tickers(symbol, timestamp);
   
   CREATE INDEX IF NOT EXISTS idx_signals_timestamp 
   ON arbitrage_signals(timestamp);
   
   -- Optimize queries
   PRAGMA journal_mode=WAL;
   PRAGMA cache_size=10000;
   PRAGMA temp_store=memory;
   ```

### Memory Leaks

#### Symptom: Memory usage continuously increasing

**Diagnostic Steps:**
```python
# Monitor memory usage
import psutil
import gc

def monitor_memory():
    process = psutil.Process()
    memory_info = process.memory_info()
    
    print(f"RSS: {memory_info.rss / 1024 / 1024:.2f} MB")
    print(f"VMS: {memory_info.vms / 1024 / 1024:.2f} MB")
    
    # Check Python object counts
    print(f"Objects in memory: {len(gc.get_objects())}")
    
    # Force garbage collection
    collected = gc.collect()
    print(f"Garbage collected: {collected} objects")

# Use memory profiler
# pip install memory_profiler
# python -m memory_profiler main.py
```

**Solutions:**

1. **Implement Data Cleanup**
   ```python
   # Regular cleanup of old data
   class DataCleanup:
       def __init__(self):
           self.last_cleanup = time.time()
           self.cleanup_interval = 3600  # 1 hour
       
       async def periodic_cleanup(self):
           if time.time() - self.last_cleanup > self.cleanup_interval:
               await self.cleanup_old_price_data()
               await self.cleanup_old_signals()
               gc.collect()  # Force garbage collection
               self.last_cleanup = time.time()
       
       async def cleanup_old_price_data(self):
           cutoff_time = time.time() - 3600  # Keep 1 hour of data
           # Remove old price data from memory
           for symbol in self.price_cache:
               self.price_cache[symbol] = [
                   price for price in self.price_cache[symbol]
                   if price['timestamp'] > cutoff_time
               ]
   ```

2. **Use Weak References**
   ```python
   import weakref
   
   class ExchangeManager:
       def __init__(self):
           self._exchanges = weakref.WeakValueDictionary()
       
       def get_exchange(self, name):
           if name not in self._exchanges:
               self._exchanges[name] = create_exchange(name)
           return self._exchanges[name]
   ```

## Database Issues

### Database Corruption

#### Symptom: "Database is locked" or "Corrupt database"

**Diagnostic Steps:**
```bash
# Check database integrity
sqlite3 data/arbot.db "PRAGMA integrity_check;"

# Check for locks
lsof data/arbot.db

# Check database size
ls -lh data/arbot.db
```

**Solutions:**

1. **Backup and Repair**
   ```bash
   # Create backup
   cp data/arbot.db data/arbot_backup.db
   
   # Attempt repair
   sqlite3 data/arbot.db ".dump" | sqlite3 data/arbot_repaired.db
   
   # Replace if repair successful
   mv data/arbot.db data/arbot_corrupted.db
   mv data/arbot_repaired.db data/arbot.db
   ```

2. **Prevent Future Corruption**
   ```python
   # Use WAL mode and proper connection handling
   import sqlite3
   
   def get_db_connection():
       conn = sqlite3.connect('data/arbot.db', timeout=30)
       conn.execute('PRAGMA journal_mode=WAL')
       conn.execute('PRAGMA synchronous=NORMAL')
       conn.execute('PRAGMA busy_timeout=30000')
       return conn
   
   # Always use context managers
   async def safe_db_operation(query, params=None):
       async with aiosqlite.connect('data/arbot.db') as conn:
           try:
               cursor = await conn.execute(query, params or [])
               await conn.commit()
               return await cursor.fetchall()
           except Exception as e:
               await conn.rollback()
               raise e
   ```

### Slow Database Queries

#### Symptom: High database response times

**Diagnostic Steps:**
```sql
-- Enable query timing
.timer ON

-- Test common queries
EXPLAIN QUERY PLAN 
SELECT * FROM tickers 
WHERE symbol = 'BTCUSDT' AND timestamp > 1640995200;

-- Check table statistics
SELECT name, COUNT(*) FROM sqlite_master sm 
JOIN pragma_table_info(sm.name) pti 
GROUP BY name;
```

**Solutions:**

1. **Add Missing Indexes**
   ```sql
   -- Analyze query patterns and add indexes
   CREATE INDEX idx_tickers_symbol_time ON tickers(symbol, timestamp);
   CREATE INDEX idx_signals_profit ON arbitrage_signals(profit_percent);
   CREATE INDEX idx_trades_status_time ON trades(status, started_at);
   
   -- Update statistics
   ANALYZE;
   ```

2. **Optimize Queries**
   ```python
   # Use efficient query patterns
   def get_recent_spreads_optimized(symbol, hours=1):
       cutoff_time = time.time() - (hours * 3600)
       
       # Use prepared statements and appropriate indexes
       query = """
       SELECT bid, ask, timestamp, exchange
       FROM tickers 
       WHERE symbol = ? AND timestamp > ?
       ORDER BY timestamp DESC
       LIMIT 1000
       """
       
       return execute_query(query, (symbol, cutoff_time))
   ```

## GUI Issues

### GUI Not Responding

#### Symptom: GUI freezes or doesn't update

**Diagnostic Steps:**
```python
# Check GUI thread status
import threading

def debug_gui_threads():
    threads = threading.enumerate()
    for thread in threads:
        print(f"Thread: {thread.name}, Alive: {thread.is_alive()}")
    
    # Check if GUI thread is blocked
    if not any(t.name == 'MainThread' and t.is_alive() for t in threads):
        print("GUI thread appears to be blocked")
```

**Solutions:**

1. **Separate GUI from Trading Logic**
   ```python
   # Use proper threading for GUI
   import tkinter as tk
   from threading import Thread
   import queue
   
   class TradingGUI:
       def __init__(self):
           self.root = tk.Tk()
           self.update_queue = queue.Queue()
           self.setup_periodic_update()
       
       def setup_periodic_update(self):
           def update_gui():
               try:
                   while True:
                       update_data = self.update_queue.get_nowait()
                       self.apply_update(update_data)
               except queue.Empty:
                   pass
               finally:
                   self.root.after(100, update_gui)  # Update every 100ms
           
           update_gui()
       
       def update_from_trading_thread(self, data):
           self.update_queue.put(data)
   ```

2. **Async GUI Updates**
   ```python
   # Use asyncio for GUI updates
   import asyncio
   import tkinter as tk
   
   class AsyncGUI:
       def __init__(self):
           self.root = tk.Tk()
           self.loop = asyncio.new_event_loop()
       
       async def update_prices_display(self):
           while True:
               try:
                   prices = await self.get_latest_prices()
                   self.root.after(0, self.update_price_labels, prices)
                   await asyncio.sleep(1)
               except Exception as e:
                   logger.error(f"GUI update error: {e}")
                   await asyncio.sleep(5)
   ```

### Display Issues

#### Symptom: Incorrect data display or formatting issues

**Solutions:**

1. **Data Validation**
   ```python
   def safe_display_number(value, decimal_places=2):
       try:
           if value is None or value == "":
               return "N/A"
           
           num_value = float(value)
           if math.isnan(num_value) or math.isinf(num_value):
               return "Invalid"
           
           return f"{num_value:.{decimal_places}f}"
       except (ValueError, TypeError):
           return "Error"
   
   def safe_display_percentage(value):
       try:
           return f"{float(value) * 100:.2f}%"
       except (ValueError, TypeError):
           return "N/A"
   ```

2. **Proper Error Handling in Display**
   ```python
   def update_display_safe(self, data):
       try:
           # Update each component with error handling
           self.update_prices(data.get('prices', {}))
           self.update_balances(data.get('balances', {}))
           self.update_trades(data.get('trades', []))
       except Exception as e:
           logger.error(f"Display update error: {e}")
           # Show error in status bar instead of crashing
           self.status_label.config(text=f"Display error: {str(e)[:50]}")
   ```

## Prevention Strategies

### Monitoring and Alerting

```python
# Implement comprehensive monitoring
class SystemMonitor:
    def __init__(self):
        self.alerts = []
        self.thresholds = {
            'cpu_percent': 80,
            'memory_percent': 85,
            'disk_percent': 90,
            'error_rate': 5  # errors per minute
        }
    
    async def monitor_system_health(self):
        while True:
            try:
                # Check system resources
                cpu_percent = psutil.cpu_percent()
                memory_percent = psutil.virtual_memory().percent
                disk_percent = psutil.disk_usage('/').percent
                
                # Check error rates
                error_count = self.count_recent_errors()
                
                # Generate alerts
                if cpu_percent > self.thresholds['cpu_percent']:
                    await self.send_alert(f"High CPU usage: {cpu_percent}%")
                
                if memory_percent > self.thresholds['memory_percent']:
                    await self.send_alert(f"High memory usage: {memory_percent}%")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
```

### Regular Maintenance

```python
# Automated maintenance tasks
class MaintenanceScheduler:
    def __init__(self):
        self.tasks = {
            'database_cleanup': {'interval': 3600, 'last_run': 0},
            'log_rotation': {'interval': 86400, 'last_run': 0},
            'backup_creation': {'interval': 86400, 'last_run': 0},
            'performance_analysis': {'interval': 3600, 'last_run': 0}
        }
    
    async def run_maintenance_tasks(self):
        current_time = time.time()
        
        for task_name, task_info in self.tasks.items():
            if current_time - task_info['last_run'] > task_info['interval']:
                try:
                    await self.execute_maintenance_task(task_name)
                    task_info['last_run'] = current_time
                except Exception as e:
                    logger.error(f"Maintenance task {task_name} failed: {e}")
```

!!! tip "Proactive Monitoring"
    Set up automated monitoring and alerting to catch issues before they become critical. Monitor key metrics like CPU usage, memory consumption, database size, and error rates.

!!! warning "Backup Regularly"
    Always maintain recent backups of your database and configuration files. Test backup restoration procedures regularly to ensure they work when needed.

!!! note "Log Analysis"
    Regularly review log files for patterns that might indicate developing issues. Use log aggregation tools for better analysis of large log volumes.