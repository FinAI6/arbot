#!/usr/bin/env python3
"""
Test script to demonstrate the balance display functionality in ArBot GUI.
This script will run the GUI for a short time to showcase the balance feature.
"""

import asyncio
import sys
import os

# Add the arbot directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'arbot'))

from arbot.main import main

if __name__ == "__main__":
    # Override command line args to force UI mode
    sys.argv = ["test_balance_display.py", "--mode", "ui"]
    
    print("=" * 60)
    print("🎯 ArBot Balance Display Test")
    print("=" * 60)
    print("✅ Starting ArBot in UI mode to demonstrate balance display")
    print("📊 The GUI will show:")
    print("   • Arbitrage Spreads (left panel)")
    print("   • Arbitrage Opportunities (right top)")
    print("   • Recent Trades (right middle)")
    print("   • 🆕 Account Balances (right bottom) ← NEW FEATURE!")
    print("=" * 60)
    print("🔍 Look for the 'Account Balances' section showing:")
    print("   • Exchange name (BINANCE, BYBIT)")
    print("   • Asset symbols (USDT, BTC, ETH)")
    print("   • Free, Locked, Total amounts")
    print("   • Estimated USD values")
    print("   • Color coding for different asset types")
    print("=" * 60)
    
    # Run the main application
    asyncio.run(main())