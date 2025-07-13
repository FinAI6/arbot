#!/usr/bin/env python3
"""Test script for batch ticker storage functionality"""

import asyncio
import time
from datetime import datetime
from arbot.config import Config
from arbot.database import Database, TickerRecord

async def test_batch_storage():
    """Test the batch storage functionality"""
    
    # Load config
    config = Config()
    
    # Initialize database
    database = Database(config)
    await database.initialize()
    
    print(f"✅ Config loaded - ticker_storage_mode: {config.database.ticker_storage_mode}")
    print(f"✅ Batch size: {config.database.ticker_batch_size}")
    print(f"✅ Batch interval: {config.database.ticker_batch_interval_seconds}s")
    
    # Create test ticker records
    test_tickers = []
    for i in range(5):
        ticker = TickerRecord(
            exchange=f"test_exchange_{i % 2}",
            symbol=f"TEST{i}USDT",
            bid=100.0 + i,
            ask=100.1 + i,
            bid_size=1000.0,
            ask_size=1000.0,
            timestamp=time.time()
        )
        test_tickers.append(ticker)
    
    print(f"\n🧪 Testing batch insertion of {len(test_tickers)} records...")
    
    # Test batch insert
    start_time = time.time()
    result = await database.insert_tickers_batch(test_tickers)
    end_time = time.time()
    
    print(f"✅ Batch insert completed: {result} records in {end_time - start_time:.3f}s")
    
    # Test individual insert for comparison
    individual_ticker = TickerRecord(
        exchange="test_individual",
        symbol="INDIVIDUALUSDT",
        bid=200.0,
        ask=200.1,
        bid_size=1000.0,
        ask_size=1000.0,
        timestamp=time.time()
    )
    
    print(f"\n🧪 Testing individual insertion...")
    start_time = time.time()
    result = await database.insert_ticker(individual_ticker)
    end_time = time.time()
    
    print(f"✅ Individual insert completed: ID {result} in {end_time - start_time:.3f}s")
    
    print(f"\n✅ Batch storage test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_batch_storage())