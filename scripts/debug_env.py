#!/usr/bin/env python3
"""
Debug environment loading
"""
import os

exchanges = ['binance', 'bybit', 'okx', 'bitget']

print("🔍 환경변수 확인:")
for exchange_name in exchanges:
    api_key = os.getenv(f"{exchange_name.upper()}_API_KEY")
    api_secret = os.getenv(f"{exchange_name.upper()}_API_SECRET")
    testnet = os.getenv(f"{exchange_name.upper()}_TESTNET", "false").lower() == "true"
    
    print(f"{exchange_name}: api_key={bool(api_key)}, api_secret={bool(api_secret)}, testnet={testnet}")
    
    if api_key and api_secret:
        print(f"  ⚠️ {exchange_name} API 키가 환경변수에 설정되어 있어 enabled=True로 덮어써집니다!")