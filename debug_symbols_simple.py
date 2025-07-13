#!/usr/bin/env python3
"""Simple debug script to check symbol coverage"""

import asyncio
import time
from arbot.config import Config
from arbot.exchanges import BinanceExchange, BybitExchange

async def debug_symbols():
    """Debug what symbols are being monitored"""
    
    print("🔍 Debugging symbol coverage...")
    
    # Load config
    config = Config()
    
    # Check which symbols should be monitored
    print(f"📋 Config symbols: {len(config.arbitrage.symbols)}")
    print(f"🎯 First 10: {config.arbitrage.symbols[:10]}")
    print(f"📊 Max symbols: {config.arbitrage.max_symbols}")
    
    # Get volume data like GUI does
    print(f"\n🔌 Testing exchange connections...")
    
    # Test Binance
    if config.exchanges['binance'].enabled:
        binance = BinanceExchange(
            config.exchanges['binance'].api_key,
            config.exchanges['binance'].api_secret,
            testnet=config.exchanges['binance'].testnet
        )
        
        print(f"📊 Getting volume data from Binance...")
        try:
            # Simulate get_common_symbols_with_volume logic
            symbols_with_volume = []
            
            # Test a few symbols for volume
            test_symbols = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'SOLUSDT', 'ADAUSDT']
            for symbol in test_symbols:
                try:
                    # Get 24h ticker stats
                    response = await binance._make_request('GET', '/api/v3/ticker/24hr', {'symbol': symbol})
                    volume = float(response['quoteVolume'])
                    symbols_with_volume.append((symbol, volume))
                    print(f"  {symbol}: ${volume:,.0f} volume")
                except Exception as e:
                    print(f"  {symbol}: Error - {e}")
            
            print(f"✅ Found {len(symbols_with_volume)} symbols with volume data")
            
        except Exception as e:
            print(f"❌ Error getting volume data: {e}")
    
    # Test ticker callback registration
    print(f"\n🎯 Testing ticker callback...")
    
    ticker_received = {}
    
    async def ticker_callback(ticker):
        if ticker.symbol not in ticker_received:
            ticker_received[ticker.symbol] = 0
        ticker_received[ticker.symbol] += 1
        
        if len(ticker_received) <= 5:  # Only print first few
            print(f"📈 Received ticker: {ticker.symbol} {ticker.bid:.6f}/{ticker.ask:.6f}")
    
    # Register callback and connect
    if config.exchanges['bybit'].enabled:
        bybit = BybitExchange(
            config.exchanges['bybit'].api_key,
            config.exchanges['bybit'].api_secret,
            testnet=config.exchanges['bybit'].testnet
        )
        
        bybit.on_ticker(ticker_callback)
        
        # Test with a few symbols
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT']
        print(f"🔌 Connecting Bybit WebSocket to: {test_symbols}")
        
        try:
            await bybit.connect_ws(test_symbols)
            
            print(f"⏳ Listening for 20 seconds...")
            await asyncio.sleep(20)
            
            print(f"\n📊 Ticker summary:")
            for symbol in test_symbols:
                count = ticker_received.get(symbol, 0)
                print(f"  {symbol}: {count} tickers received")
            
            await bybit.disconnect_ws()
            
        except Exception as e:
            print(f"❌ WebSocket error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_symbols())