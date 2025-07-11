#!/usr/bin/env python3
"""
Debug config loading process
"""
import json
import os

def debug_config_loading():
    print("🔍 설정 파일 디버깅...")
    
    # Load main config
    with open('config.json', 'r') as f:
        main_config = json.load(f)
    
    print("📄 Main config exchanges:")
    for name, config in main_config.get('exchanges', {}).items():
        print(f"  {name}: enabled={config.get('enabled')}, arbitrage_enabled={config.get('arbitrage_enabled')}")
    
    # Load local config
    with open('config.local.json', 'r') as f:
        local_config = json.load(f)
    
    print("\n📄 Local config exchanges:")
    for name, config in local_config.get('exchanges', {}).items():
        print(f"  {name}: enabled={config.get('enabled')}, arbitrage_enabled={config.get('arbitrage_enabled')}")
    
    # Simulate merge
    def deep_merge_dict(base, overlay):
        result = base.copy()
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge_dict(result[key], value)
            else:
                result[key] = value
        return result
    
    merged_config = deep_merge_dict(main_config, local_config)
    
    print("\n🔄 Merged config exchanges:")
    for name, config in merged_config.get('exchanges', {}).items():
        print(f"  {name}: enabled={config.get('enabled')}, arbitrage_enabled={config.get('arbitrage_enabled')}")

if __name__ == "__main__":
    debug_config_loading()