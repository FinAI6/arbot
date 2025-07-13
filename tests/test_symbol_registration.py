#!/usr/bin/env python3
"""Test symbol registration and WebSocket subscription"""

import asyncio
import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

async def test_symbol_registration():
    """Test if all symbols are properly registered for WebSocket"""
    
    print("🧪 Testing symbol registration...")
    
    # Mock the GUI initialization process
    from arbot.config import Config
    from arbot.exchanges import BybitExchange
    
    try:
        config = Config()
        print(f"📊 Config loaded successfully")
        print(f"📊 use_dynamic_symbols: {config.arbitrage.use_dynamic_symbols}")
        print(f"📊 max_symbols: {getattr(config.arbitrage, 'max_symbols', 200)}")
        print(f"📊 Default symbols count: {len(config.arbitrage.symbols)}")
        
        # Test symbol filtering logic
        enabled_quote_currencies = config.arbitrage.enabled_quote_currencies
        print(f"📊 Enabled quote currencies: {enabled_quote_currencies}")
        
        def _is_symbol_enabled(symbol: str) -> bool:
            """Check if symbol uses enabled quote currency"""
            for quote_currency in enabled_quote_currencies:
                if symbol.endswith(quote_currency):
                    return True
            return False
        
        # Test the predefined symbol list
        top_volume_symbols = [
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", 
            "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT", "MATICUSDT",
            "LTCUSDT", "UNIUSDT", "BCHUSDT", "FILUSDT", "ATOMUSDT",
            "ETCUSDT", "TRXUSDT", "VETUSDT", "XLMUSDT", "ICPUSDT",
            "FTMUSDT", "THETAUSDT", "HBARUSDT", "EOSUSDT", "AAVEUSDT",
            "MKRUSDT", "SUSHIUSDT", "COMPUSDT", "YFIUSDT", "SNXUSDT",
            "CRVUSDT", "1INCHUSDT", "ENJUSDT", "CHZUSDT", "MANAUSDT",
            "SANDUSDT", "GALAUSDT", "LRCUSDT", "BATUSDT", "ZRXUSDT",
            "STORJUSDT", "KNCUSDT", "RENUSDT", "BALUSDT", "BANDUSDT",
            "ANKRUSDT", "CELOUSDT", "CTKUSDT", "ORNUSDT", "NMRUSDT"
        ]
        
        # Filter symbols
        enabled_symbols = []
        for symbol in top_volume_symbols:
            if _is_symbol_enabled(symbol):
                enabled_symbols.append(symbol)
            else:
                print(f"⚠️  Symbol {symbol} disabled (quote currency not enabled)")
        
        max_symbols = getattr(config.arbitrage, 'max_symbols', 200)
        selected_symbols = enabled_symbols[:max_symbols]
        
        print(f"✅ Filtered symbols: {len(enabled_symbols)} enabled out of {len(top_volume_symbols)} total")
        print(f"✅ Selected symbols (top {max_symbols}): {len(selected_symbols)}")
        print(f"📊 First 20 symbols: {selected_symbols[:20]}")
        
        # Test Bybit exchange if enabled
        if config.exchanges['bybit'].enabled:
            print(f"\n🔌 Testing Bybit WebSocket with {len(selected_symbols)} symbols...")
            
            bybit = BybitExchange(
                config.exchanges['bybit'].api_key,
                config.exchanges['bybit'].api_secret,
                testnet=config.exchanges['bybit'].testnet
            )
            bybit.exchange_name = 'bybit'
            
            # Track received tickers
            ticker_count = 0
            symbols_received = set()
            
            async def ticker_callback(ticker):
                nonlocal ticker_count
                ticker_count += 1
                symbols_received.add(ticker.symbol)
                
                # Log first 10 tickers
                if ticker_count <= 10:
                    print(f"📈 Ticker {ticker_count}: {ticker.symbol} {ticker.bid:.6f}/{ticker.ask:.6f}")
            
            bybit.on_ticker(ticker_callback)
            
            # Connect WebSocket with all symbols
            test_symbols = selected_symbols[:50]  # Test with first 50 symbols
            print(f"🔌 Connecting to {len(test_symbols)} symbols...")
            
            try:
                await bybit.connect_ws(test_symbols)
                
                print(f"⏳ Listening for 15 seconds...")
                await asyncio.sleep(15)
                
                print(f"\n📊 WebSocket Results:")
                print(f"  Total tickers received: {ticker_count}")
                print(f"  Unique symbols received: {len(symbols_received)}")
                print(f"  Expected symbols: {len(test_symbols)}")
                print(f"  Coverage: {len(symbols_received)}/{len(test_symbols)} = {len(symbols_received)/len(test_symbols)*100:.1f}%")
                
                # Show which symbols were received
                received_list = sorted(list(symbols_received))
                print(f"  Symbols received: {received_list[:20]}{'...' if len(received_list) > 20 else ''}")
                
                # Show missing symbols
                missing_symbols = set(test_symbols) - symbols_received
                if missing_symbols:
                    missing_list = sorted(list(missing_symbols))
                    print(f"  Missing symbols: {missing_list[:10]}{'...' if len(missing_list) > 10 else ''}")
                
                await bybit.disconnect_ws()
                
                if len(symbols_received) >= len(test_symbols) * 0.8:  # 80% coverage
                    print("✅ WebSocket symbol registration working well!")
                else:
                    print("⚠️  Low symbol coverage - some symbols may not be available")
                
            except Exception as e:
                print(f"❌ WebSocket connection failed: {e}")
        
        else:
            print("⚠️  Bybit is disabled in config")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_symbol_registration())