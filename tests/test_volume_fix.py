#!/usr/bin/env python3
"""
Test volume calculation fix for Bitget and OKX
"""
import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitget import BitgetExchange
from exchanges.okx import OKXExchange

async def test_volume_calculation():
    print("🔍 Testing volume calculation for filtering...")
    
    # Test Bitget
    print("\n📊 Testing Bitget volume calculation:")
    bitget = BitgetExchange("", "", False)
    try:
        tickers = await bitget.get_all_tickers()
        if tickers:
            sample = tickers[0]
            print(f"Sample ticker: {sample['symbol']}")
            
            # Test volume calculation logic from main.py
            volume_usdt = float(sample.get('quoteVol', 0))
            if volume_usdt == 0:
                volume = float(sample.get('baseVol', 0))
                price = float(sample.get('close', 0)) or float(sample.get('lastPrice', 0))
                volume_usdt = volume * price
            
            print(f"quoteVol: {sample.get('quoteVol', 0)}")
            print(f"baseVol: {sample.get('baseVol', 0)}")
            print(f"close: {sample.get('close', 0)}")
            print(f"Calculated volume_usdt: ${volume_usdt:,.0f}")
            
            # Test filtering with 1M USDT threshold
            min_volume = 1000000
            qualifying_count = 0
            for ticker in tickers[:100]:  # Test first 100
                volume_usdt = float(ticker.get('quoteVol', 0))
                if volume_usdt == 0:
                    volume = float(ticker.get('baseVol', 0))
                    price = float(ticker.get('close', 0))
                    volume_usdt = volume * price
                
                if volume_usdt >= min_volume:
                    qualifying_count += 1
            
            print(f"✅ Bitget: {qualifying_count}/100 symbols meet ${min_volume:,} volume threshold")
            
    except Exception as e:
        print(f"❌ Bitget error: {e}")
    finally:
        if bitget.session and not bitget.session.closed:
            await bitget.session.close()
    
    # Test OKX
    print("\n📊 Testing OKX volume calculation:")
    okx = OKXExchange("", "", False)
    try:
        tickers = await okx.get_all_tickers()
        if tickers:
            sample = tickers[0]
            print(f"Sample ticker: {sample['instId']}")
            
            # Test volume calculation logic from main.py
            volume_usdt = float(sample.get('volCcy24h', 0))
            
            print(f"volCcy24h: {sample.get('volCcy24h', 0)}")
            print(f"vol24h: {sample.get('vol24h', 0)}")
            print(f"last: {sample.get('last', 0)}")
            print(f"Calculated volume_usdt: ${volume_usdt:,.0f}")
            
            # Test filtering with 1M USDT threshold
            min_volume = 1000000
            qualifying_count = 0
            for ticker in tickers[:100]:  # Test first 100
                volume_usdt = float(ticker.get('volCcy24h', 0))
                if volume_usdt >= min_volume:
                    qualifying_count += 1
            
            print(f"✅ OKX: {qualifying_count}/100 symbols meet ${min_volume:,} volume threshold")
            
    except Exception as e:
        print(f"❌ OKX error: {e}")
    finally:
        if okx.session and not okx.session.closed:
            await okx.session.close()

if __name__ == "__main__":
    asyncio.run(test_volume_calculation())