#!/usr/bin/env python3
"""
Debug the _update_from_dict method in config.py
"""
import sys
import os
import json

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config, ExchangeConfig

def debug_update_from_dict():
    print("🔍 _update_from_dict 메서드 디버깅...")
    
    # Load merged config data manually
    with open('config.json', 'r') as f:
        main_config = json.load(f)
    
    with open('config.local.json', 'r') as f:
        local_config = json.load(f)
    
    def deep_merge_dict(base, overlay):
        result = base.copy()
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge_dict(result[key], value)
            else:
                result[key] = value
        return result
    
    merged_config = deep_merge_dict(main_config, local_config)
    
    print("📄 병합된 설정에서 exchanges 부분:")
    exchanges_data = merged_config.get('exchanges', {})
    for name, exchange_data in exchanges_data.items():
        print(f"  {name}: {exchange_data}")
    
    # Test the ExchangeConfig creation logic
    print("\n🔧 ExchangeConfig 생성 테스트:")
    exchanges = {}
    
    for name, exchange_data in exchanges_data.items():
        # Get existing config or create default
        existing = exchanges.get(name, ExchangeConfig(name=name, api_key='', api_secret=''))
        
        print(f"\n{name}:")
        print(f"  기존: enabled={existing.enabled}, arbitrage_enabled={existing.arbitrage_enabled}")
        print(f"  데이터: {exchange_data}")
        
        # Update only the fields that are provided in the new config
        new_config = ExchangeConfig(
            name=name,
            api_key=exchange_data.get('api_key', existing.api_key),
            api_secret=exchange_data.get('api_secret', existing.api_secret),
            testnet=exchange_data.get('testnet', existing.testnet),
            enabled=exchange_data.get('enabled', existing.enabled),
            arbitrage_enabled=exchange_data.get('arbitrage_enabled', existing.arbitrage_enabled),
            region=exchange_data.get('region', existing.region),
            premium_baseline=exchange_data.get('premium_baseline', existing.premium_baseline)
        )
        
        exchanges[name] = new_config
        print(f"  결과: enabled={new_config.enabled}, arbitrage_enabled={new_config.arbitrage_enabled}")

if __name__ == "__main__":
    debug_update_from_dict()