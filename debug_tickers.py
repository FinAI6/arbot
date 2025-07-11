#!/usr/bin/env python3
"""
Debug script to test Bitget and OKX ticker API calls
"""
import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitget import BitgetExchange
from exchanges.okx import OKXExchange

async def test_bitget():
    print("🔍 Testing Bitget get_all_tickers...")
    exchange = BitgetExchange("", "", False)  # Empty credentials for public API
    try:
        tickers = await exchange.get_all_tickers()
        print(f"✅ Bitget returned {len(tickers) if tickers else 0} tickers")
        if tickers:
            print(f"📊 First ticker sample: {tickers[0]}")
            
            # Test volume calculation
            sample_ticker = tickers[0]
            print(f"🔍 Sample ticker fields: {list(sample_ticker.keys())}")
            quote_volume = sample_ticker.get('quoteVolume', 0)
            base_volume = sample_ticker.get('baseVolume', 0)
            last_price = sample_ticker.get('lastPrice', 0)
            print(f"📈 Sample volumes - quoteVolume: {quote_volume}, baseVolume: {base_volume}, lastPrice: {last_price}")
            
    except Exception as e:
        print(f"❌ Bitget error: {e}")
    finally:
        if exchange.session and not exchange.session.closed:
            await exchange.session.close()

async def test_okx():
    print("\n🔍 Testing OKX get_all_tickers...")
    exchange = OKXExchange("", "", False)  # Empty credentials for public API
    try:
        tickers = await exchange.get_all_tickers()
        print(f"✅ OKX returned {len(tickers) if tickers else 0} tickers")
        if tickers:
            print(f"📊 First ticker sample: {tickers[0]}")
            
            # Test volume calculation
            sample_ticker = tickers[0]
            print(f"🔍 Sample ticker fields: {list(sample_ticker.keys())}")
            vol_ccy_24h = sample_ticker.get('volCcy24h', 0)
            vol_24h = sample_ticker.get('vol24h', 0)
            last_price = sample_ticker.get('last', 0)
            print(f"📈 Sample volumes - volCcy24h: {vol_ccy_24h}, vol24h: {vol_24h}, last: {last_price}")
            
    except Exception as e:
        print(f"❌ OKX error: {e}")
    finally:
        if exchange.session and not exchange.session.closed:
            await exchange.session.close()

async def main():
    await test_bitget()
    await test_okx()

if __name__ == "__main__":
    asyncio.run(main())