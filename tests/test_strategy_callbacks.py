#!/usr/bin/env python3
"""Test strategy callbacks to verify WebSocket ticker flow"""

import asyncio
import time
from arbot.config import Config
from arbot.database import Database
from arbot.strategy import ArbitrageStrategy
from arbot.exchanges import BinanceExchange, BybitExchange

async def test_strategy_callbacks():
    """Test if strategy receives WebSocket tickers"""
    
    print("🧪 Testing strategy callbacks...")
    
    # Load config
    config = Config()
    
    # Initialize database
    database = Database(config)
    await database.initialize()
    
    # Create exchanges
    exchanges = {}
    
    if config.exchanges['bybit'].enabled:
        exchanges['bybit'] = BybitExchange(
            config.exchanges['bybit'].api_key,
            config.exchanges['bybit'].api_secret,
            testnet=config.exchanges['bybit'].testnet
        )
        exchanges['bybit'].exchange_name = 'bybit'
    
    print(f"📊 Created {len(exchanges)} exchanges")
    
    # Create strategy
    strategy = ArbitrageStrategy(config, database)
    
    # Mock active symbols 
    strategy.set_active_symbols(['BTCUSDT', 'ETHUSDT', 'XRPUSDT'])
    
    # Initialize strategy with exchanges
    await strategy.initialize(exchanges)
    
    # Start strategy
    await strategy.start()
    
    # Connect WebSocket
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT']
    print(f"🔌 Connecting to WebSocket with symbols: {test_symbols}")
    
    for exchange_name, exchange in exchanges.items():
        await exchange.connect_ws(test_symbols)
    
    print("⏳ Listening for strategy ticker callbacks for 20 seconds...")
    
    # Monitor strategy data
    start_time = time.time()
    last_log_time = start_time
    
    while time.time() - start_time < 20:
        await asyncio.sleep(1)
        
        current_time = time.time()
        if current_time - last_log_time >= 5:  # Log every 5 seconds
            # Check strategy exchange data
            total_symbols = 0
            for exchange_name, exchange_data in strategy.exchange_data.items():
                symbol_count = len(exchange_data)
                total_symbols += symbol_count
                if symbol_count > 0:
                    latest_symbols = list(exchange_data.keys())[:3]
                    print(f"📈 {exchange_name}: {symbol_count} symbols with data: {latest_symbols}")
            
            if total_symbols == 0:
                print("⚠️  Strategy has no ticker data yet")
            else:
                print(f"✅ Strategy has data for {total_symbols} symbols total")
                
            last_log_time = current_time
    
    # Disconnect
    for exchange in exchanges.values():
        await exchange.disconnect_ws()
    
    # Final summary
    print(f"\n📊 Final strategy data summary:")
    for exchange_name, exchange_data in strategy.exchange_data.items():
        print(f"  {exchange_name}: {len(exchange_data)} symbols")
        for symbol, data in list(exchange_data.items())[:5]:  # Show first 5
            print(f"    {symbol}: {data.ticker.bid:.6f}/{data.ticker.ask:.6f}")

if __name__ == "__main__":
    asyncio.run(test_strategy_callbacks())