#!/usr/bin/env python3
"""Test GUI batch ticker storage workflow"""

import asyncio
import time
from datetime import datetime
from arbot.config import Config
from arbot.database import Database, TickerRecord

class MockTicker:
    def __init__(self, symbol, bid, ask):
        self.symbol = symbol
        self.bid = bid
        self.ask = ask
        self.bid_size = 1000.0
        self.ask_size = 1000.0
        self.timestamp = time.time()

class MockGUI:
    def __init__(self, config, database):
        self.config = config
        self.database = database
        
        # Initialize ticker storage like GUI
        self.last_ticker_storage = {}
        self.ticker_buffer = []
        self.last_batch_storage = time.time()
    
    async def _add_to_ticker_batch(self, ticker, exchange_name):
        """Add ticker to batch buffer for bulk storage"""
        try:
            # Create a unique key for this exchange-symbol combination
            storage_key = f"{exchange_name}_{ticker.symbol}"
            current_time = time.time()
            
            # Check if enough time has passed since last storage for this ticker
            last_storage_time = self.last_ticker_storage.get(storage_key, 0)
            time_since_last_storage = current_time - last_storage_time
            
            if time_since_last_storage >= self.config.database.ticker_storage_interval_seconds:
                ticker_record = TickerRecord(
                    exchange=exchange_name,
                    symbol=ticker.symbol,
                    bid=ticker.bid,
                    ask=ticker.ask,
                    bid_size=ticker.bid_size,
                    ask_size=ticker.ask_size,
                    timestamp=ticker.timestamp
                )
                
                # Add to buffer
                self.ticker_buffer.append(ticker_record)
                self.last_ticker_storage[storage_key] = current_time
                
                print(f"📦 Added {exchange_name} {ticker.symbol} to batch (buffer size: {len(self.ticker_buffer)})")
                
                # Check if buffer is full or enough time has passed for batch storage
                time_since_batch = current_time - self.last_batch_storage
                
                if (len(self.ticker_buffer) >= self.config.database.ticker_batch_size or 
                    time_since_batch >= self.config.database.ticker_batch_interval_seconds):
                    await self._flush_ticker_batch()
                    
        except Exception as e:
            print(f"❌ Error adding ticker to batch: {e}")
    
    async def _flush_ticker_batch(self):
        """Flush ticker buffer to database"""
        if not self.ticker_buffer:
            return
            
        try:
            count = len(self.ticker_buffer)
            await self.database.insert_tickers_batch(self.ticker_buffer)
            
            # Log without milliseconds
            now = datetime.now()
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
            print(f"💾 {timestamp} - Stored {count} ticker records in batch")
            
            # Clear buffer and update timing
            self.ticker_buffer.clear()
            self.last_batch_storage = time.time()
            
        except Exception as e:
            print(f"❌ Error flushing ticker batch: {e}")
    
    async def _on_ticker_for_storage(self, ticker, exchange_name):
        """Store ticker data in database if enabled and within storage interval"""
        try:
            if not self.config.database.store_ticker_data:
                return
            
            # Check storage mode
            if self.config.database.ticker_storage_mode == "batch":
                await self._add_to_ticker_batch(ticker, exchange_name)
            else:
                print(f"ℹ️  Individual mode not implemented in test")
                
        except Exception as e:
            print(f"❌ Error storing ticker data: {e}")

async def test_gui_batch_workflow():
    """Test the GUI batch workflow"""
    
    # Load config
    config = Config()
    
    # Initialize database
    database = Database(config)
    await database.initialize()
    
    # Create mock GUI
    mock_gui = MockGUI(config, database)
    
    print(f"🧪 Testing GUI batch workflow")
    print(f"📋 Batch size: {config.database.ticker_batch_size}")
    print(f"⏱️  Batch interval: {config.database.ticker_batch_interval_seconds}s")
    print(f"⏱️  Ticker interval: {config.database.ticker_storage_interval_seconds}s")
    
    # Test 1: Add tickers rapidly (should trigger batch size limit)
    print(f"\n🎯 Test 1: Adding {config.database.ticker_batch_size + 5} tickers rapidly...")
    
    for i in range(config.database.ticker_batch_size + 5):
        ticker = MockTicker(f"TEST{i}USDT", 100.0 + i, 100.1 + i)
        await mock_gui._on_ticker_for_storage(ticker, f"exchange_{i % 3}")
        
        # Add small delay to avoid rate limiting
        if i % 10 == 0:
            await asyncio.sleep(0.1)
    
    # Test 2: Add a few more tickers and wait for time-based flush
    print(f"\n🎯 Test 2: Adding a few tickers and waiting for time-based flush...")
    
    for i in range(5):
        ticker = MockTicker(f"TIME{i}USDT", 200.0 + i, 200.1 + i)
        await mock_gui._on_ticker_for_storage(ticker, "time_exchange")
        await asyncio.sleep(1)  # Add delay to allow time interval
    
    print(f"⏳ Waiting {config.database.ticker_batch_interval_seconds}s for time-based flush...")
    await asyncio.sleep(config.database.ticker_batch_interval_seconds + 1)
    
    # Test 3: Force flush any remaining
    print(f"\n🎯 Test 3: Final flush...")
    if mock_gui.ticker_buffer:
        await mock_gui._flush_ticker_batch()
    
    print(f"\n✅ GUI batch workflow test completed!")

if __name__ == "__main__":
    asyncio.run(test_gui_batch_workflow())