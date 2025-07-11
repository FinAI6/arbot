#!/usr/bin/env python3
"""
Trace config loading step by step
"""
import sys
import os
import json

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config, ExchangeConfig

# Patch _update_from_dict to add debug prints
original_update_from_dict = Config._update_from_dict

def debug_update_from_dict(self, config_data):
    print(f"\n🔧 _update_from_dict 호출됨")
    print(f"입력 데이터: {config_data}")
    print(f"현재 exchanges: {[(name, f'enabled={config.enabled}') for name, config in self.exchanges.items()]}")
    
    result = original_update_from_dict(self, config_data)
    
    print(f"결과 exchanges: {[(name, f'enabled={config.enabled}') for name, config in self.exchanges.items()]}")
    return result

Config._update_from_dict = debug_update_from_dict

def trace_config():
    print("🔍 Config 로딩 과정 추적...")
    config = Config('config.json')
    
    print(f"\n✅ 최종 결과:")
    for name, exchange_config in config.exchanges.items():
        print(f"  {name}: enabled={exchange_config.enabled}, arbitrage_enabled={exchange_config.arbitrage_enabled}")

if __name__ == "__main__":
    trace_config()