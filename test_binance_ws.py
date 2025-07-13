#!/usr/bin/env python3
"""Test if Binance WebSocket still works despite REST API ban"""

import asyncio
import time
from arbot.config import Config
from arbot.exchanges import BinanceExchange

async def test_binance_ws():
    """Test Binance WebSocket connectivity"""
    
    print("🧪 Testing Binance WebSocket...")
    
    # Load config
    config = Config()
    
    if not config.exchanges['binance'].enabled:
        print("❌ Binance is disabled in config")
        return
    
    # Create Binance exchange
    binance = BinanceExchange(
        config.exchanges['binance'].api_key,
        config.exchanges['binance'].api_secret,
        testnet=config.exchanges['binance'].testnet
    )
    binance.exchange_name = 'binance'
    
    # Track received tickers
    ticker_count = 0
    symbols_received = set()
    
    async def ticker_callback(ticker):
        nonlocal ticker_count
        ticker_count += 1
        symbols_received.add(ticker.symbol)
        
        if ticker_count <= 5:  # Log first few
            print(f"📈 Binance ticker: {ticker.symbol} {ticker.bid:.6f}/{ticker.ask:.6f}")
    
    binance.on_ticker(ticker_callback)
    
    # Test with a few symbols
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT']
    print(f"🔌 Attempting Binance WebSocket connection to: {test_symbols}")
    
    try:
        await binance.connect_ws(test_symbols)
        
        print(f"⏳ Listening for 15 seconds...")
        await asyncio.sleep(15)
        
        print(f"\n📊 Binance WebSocket Results:")
        print(f"  Total tickers received: {ticker_count}")
        print(f"  Unique symbols: {len(symbols_received)}")
        print(f"  Symbols received: {list(symbols_received)}")
        
        if ticker_count > 0:
            print("✅ Binance WebSocket is working despite REST API ban!")
        else:
            print("❌ Binance WebSocket is also not working")
        
        await binance.disconnect_ws()
        
    except Exception as e:
        print(f"❌ Binance WebSocket connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_binance_ws())