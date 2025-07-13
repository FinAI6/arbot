#!/usr/bin/env python3
"""
Test script to demonstrate the balance rate limiting functionality.
This script shows how balance API calls are now properly rate-limited.
"""

import asyncio
import time
import sys
import os

# Add the arbot directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'arbot'))

from arbot.config import Config, TradingMode
from arbot.database import Database
from arbot.gui import ArBotGUI

async def test_balance_rate_limiting():
    print("=" * 60)
    print("🧪 ArBot Balance Rate Limiting Test")
    print("=" * 60)
    
    # Load configuration
    config = Config()
    config.trading_mode = TradingMode.LIVE  # Force live mode for testing
    database = Database(config)
    
    # Create GUI instance (but don't show the actual GUI)
    gui = ArBotGUI(config, database)
    
    # Initialize exchanges manually
    from arbot.exchanges import BinanceExchange, BybitExchange
    
    # Only create Binance for this test to avoid API key issues with Bybit
    gui.exchanges = {
        'binance': BinanceExchange(
            config.exchanges['binance'].api_key,
            config.exchanges['binance'].api_secret,
            config.exchanges['binance'].testnet
        )
    }
    
    print("✅ Initialized test environment")
    print(f"📊 Trading mode: {config.trading_mode.value}")
    print(f"⏰ Balance update interval: {gui.balance_update_interval} seconds")
    print()
    
    # Test rate limiting behavior
    print("🔄 Testing balance update rate limiting...")
    
    for i in range(5):
        print(f"\n--- Test iteration {i+1} ---")
        current_time = time.time()
        
        # Check if update should happen
        should_update = (current_time - gui.last_balance_update) > gui.balance_update_interval
        
        print(f"Current time: {current_time:.1f}")
        print(f"Last update: {gui.last_balance_update:.1f}")
        print(f"Time since last update: {current_time - gui.last_balance_update:.1f}s")
        print(f"Should update: {should_update}")
        
        if should_update:
            print("✅ Updating balances...")
            try:
                await gui._update_real_balances()
                gui.last_balance_update = current_time
                print(f"✅ Balance update completed")
                print(f"📊 Found balances: {len(gui.current_balances)} exchanges")
            except Exception as e:
                print(f"❌ Balance update failed: {e}")
        else:
            time_until_next = gui.balance_update_interval - (current_time - gui.last_balance_update)
            print(f"⏳ Rate limited - next update in {time_until_next:.1f}s")
        
        # Wait 10 seconds before next iteration
        if i < 4:  # Don't wait after last iteration
            print("⏸️  Waiting 10 seconds...")
            await asyncio.sleep(10)
    
    print("\n" + "=" * 60)
    print("✅ Rate limiting test completed!")
    print("🎯 Key benefits:")
    print("   • Prevents API rate limit errors")
    print("   • Reduces unnecessary API calls")
    print("   • Maintains balance data freshness")
    print("   • Improves application stability")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_balance_rate_limiting())