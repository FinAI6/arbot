#!/usr/bin/env python3
"""
Test config loading to see which exchanges are enabled/arbitrage_enabled
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config

def test_config():
    print("🔍 설정 테스트...")
    config = Config('config.json')
    
    print("\n📊 모든 거래소 설정:")
    for name, exchange_config in config.exchanges.items():
        print(f"  {name}: enabled={exchange_config.enabled}, arbitrage_enabled={exchange_config.arbitrage_enabled}")
    
    print(f"\n✅ 활성화된 거래소: {config.get_enabled_exchanges()}")
    print(f"⚡ 차익거래 거래소: {config.get_arbitrage_exchanges()}")

if __name__ == "__main__":
    test_config()