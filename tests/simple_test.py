#!/usr/bin/env python3
"""
Simple test to verify both exchanges return symbols that meet volume criteria
"""
import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitget import BitgetExchange
from exchanges.okx import OKXExchange

async def test_both_exchanges():
    min_volume_usdt = 1000000  # 1M USDT
    print(f"🔍 Testing both exchanges with ${min_volume_usdt:,} minimum volume...")
    
    # Test Bitget
    print("\n📊 Bitget:")
    bitget = BitgetExchange("", "", False)
    try:
        tickers = await bitget.get_all_tickers()
        bitget_symbols = set()
        
        for ticker in tickers:
            symbol = ticker.get('symbol')
            if not symbol:
                continue
            
            # Use corrected field names for Bitget
            try:
                volume_usdt = float(ticker.get('quoteVol', 0))
                if volume_usdt == 0:
                    volume = float(ticker.get('baseVol', 0))
                    price = float(ticker.get('close', 0))
                    volume_usdt = volume * price
            except (ValueError, TypeError):
                volume_usdt = 0
            
            if volume_usdt >= min_volume_usdt:
                bitget_symbols.add(symbol)
        
        print(f"✅ Bitget: {len(bitget_symbols)}개 심볼 (볼륨 기준 충족)")
        
    except Exception as e:
        print(f"❌ Bitget 오류: {e}")
    finally:
        if bitget.session and not bitget.session.closed:
            await bitget.session.close()
    
    # Test OKX
    print("\n📊 OKX:")
    okx = OKXExchange("", "", False)
    try:
        tickers = await okx.get_all_tickers()
        okx_symbols = set()
        
        for ticker in tickers:
            symbol = ticker.get('instId')  # OKX uses instId
            if not symbol:
                continue
            
            # Convert OKX format (BTC-USDT) to standard format (BTCUSDT)
            if '-' in symbol:
                symbol = symbol.replace('-', '')
            
            # Use OKX field names
            try:
                volume_usdt = float(ticker.get('volCcy24h', 0))
            except (ValueError, TypeError):
                volume_usdt = 0
            
            if volume_usdt >= min_volume_usdt:
                okx_symbols.add(symbol)
        
        print(f"✅ OKX: {len(okx_symbols)}개 심볼 (볼륨 기준 충족)")
        
    except Exception as e:
        print(f"❌ OKX 오류: {e}")
    finally:
        if okx.session and not okx.session.closed:
            await okx.session.close()
    
    # Show common symbols if both worked
    if 'bitget_symbols' in locals() and 'okx_symbols' in locals():
        common = bitget_symbols & okx_symbols
        print(f"\n🎯 공통 심볼: {len(common)}개")
        if common:
            sorted_common = sorted(list(common))[:10]
            print(f"상위 10개: {', '.join(sorted_common)}")

if __name__ == "__main__":
    asyncio.run(test_both_exchanges())