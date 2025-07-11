#!/usr/bin/env python3
"""
Trace full config loading with _load_from_env
"""
import sys
import os
import json

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config, ExchangeConfig

# Patch both methods
original_update_from_dict = Config._update_from_dict
original_load_from_env = Config._load_from_env

def debug_update_from_dict(self, config_data):
    print(f"\n🔧 _update_from_dict 호출됨")
    print(f"결과 exchanges: {[(name, f'enabled={config.enabled}') for name, config in self.exchanges.items()]}")
    
    result = original_update_from_dict(self, config_data)
    
    print(f"_update_from_dict 후: {[(name, f'enabled={config.enabled}') for name, config in self.exchanges.items()]}")
    return result

def debug_load_from_env(self):
    print(f"\n🌍 _load_from_env 호출됨")
    print(f"_load_from_env 전: {[(name, f'enabled={config.enabled}') for name, config in self.exchanges.items()]}")
    
    result = original_load_from_env(self)
    
    print(f"_load_from_env 후: {[(name, f'enabled={config.enabled}') for name, config in self.exchanges.items()]}")
    return result

Config._update_from_dict = debug_update_from_dict
Config._load_from_env = debug_load_from_env

def trace_config():
    print("🔍 전체 Config 로딩 과정 추적...")
    config = Config('config.json')
    
    print(f"\n✅ 최종 결과:")
    for name, exchange_config in config.exchanges.items():
        print(f"  {name}: enabled={exchange_config.enabled}, arbitrage_enabled={exchange_config.arbitrage_enabled}")

if __name__ == "__main__":
    trace_config()