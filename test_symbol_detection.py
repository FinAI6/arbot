#!/usr/bin/env python3
"""
Test symbol detection with volume filtering for Bitget and OKX
"""
import asyncio
import sys
import os
import json

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitget import BitgetExchange
from exchanges.okx import OKXExchange
from config import Config

async def test_symbol_detection():
    print("🔍 Testing symbol detection with volume filtering...")
    
    # Load config
    config = Config('config.json')
    min_volume_usdt = config.arbitrage.min_volume_usdt
    print(f"💰 최소 볼륨 기준: ${min_volume_usdt:,.0f}")
    
    # Test Bitget if enabled
    if config.exchanges.bitget.enabled:
        print("\n📊 Testing Bitget symbol detection:")
        bitget = BitgetExchange("", "", False)
        try:
            tickers = await bitget.get_all_tickers()
            if tickers:
                symbols = set()
                volumes = {}
                
                for ticker in tickers:
                    symbol = ticker.get('symbol')
                    if not symbol:
                        continue
                    
                    # Extract volume using corrected field names
                    try:
                        volume_usdt = float(ticker.get('quoteVol', 0))
                        if volume_usdt == 0:
                            volume = float(ticker.get('baseVol', 0))
                            price = float(ticker.get('close', 0)) or float(ticker.get('lastPrice', 0))
                            volume_usdt = volume * price
                    except (ValueError, TypeError):
                        volume_usdt = 0
                    
                    if volume_usdt >= min_volume_usdt:
                        symbols.add(symbol)
                        volumes[symbol] = volume_usdt
                
                print(f"✅ Bitget: {len(symbols)}개 심볼 (볼륨 기준 충족)")
                
                # Show top 10 by volume
                top_symbols = sorted(volumes.items(), key=lambda x: x[1], reverse=True)[:10]
                for i, (symbol, volume) in enumerate(top_symbols, 1):
                    print(f"  {i:2}. {symbol}: ${volume:,.0f}")
                    
        except Exception as e:
            print(f"❌ Bitget 오류: {e}")
        finally:
            if bitget.session and not bitget.session.closed:
                await bitget.session.close()
    else:
        print("❌ Bitget이 비활성화되어 있습니다")
    
    # Test OKX if enabled
    if config.exchanges.okx.enabled:
        print("\n📊 Testing OKX symbol detection:")
        okx = OKXExchange("", "", False)
        try:
            tickers = await okx.get_all_tickers()
            if tickers:
                symbols = set()
                volumes = {}
                
                for ticker in tickers:
                    symbol = ticker.get('instId')  # OKX uses instId
                    if not symbol:
                        continue
                    
                    # Convert OKX format (BTC-USDT) to standard format (BTCUSDT)
                    if '-' in symbol:
                        symbol = symbol.replace('-', '')
                    
                    # Extract volume using OKX field names
                    try:
                        volume_usdt = float(ticker.get('volCcy24h', 0))
                    except (ValueError, TypeError):
                        volume_usdt = 0
                    
                    if volume_usdt >= min_volume_usdt:
                        symbols.add(symbol)
                        volumes[symbol] = volume_usdt
                
                print(f"✅ OKX: {len(symbols)}개 심볼 (볼륨 기준 충족)")
                
                # Show top 10 by volume
                top_symbols = sorted(volumes.items(), key=lambda x: x[1], reverse=True)[:10]
                for i, (symbol, volume) in enumerate(top_symbols, 1):
                    print(f"  {i:2}. {symbol}: ${volume:,.0f}")
                    
        except Exception as e:
            print(f"❌ OKX 오류: {e}")
        finally:
            if okx.session and not okx.session.closed:
                await okx.session.close()
    else:
        print("❌ OKX가 비활성화되어 있습니다")

if __name__ == "__main__":
    asyncio.run(test_symbol_detection())