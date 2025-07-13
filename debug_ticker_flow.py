#!/usr/bin/env python3
"""Debug ticker flow to understand why only some symbols are stored"""

import asyncio
import time
from arbot.config import Config
from arbot.database import Database
from arbot.exchanges import BinanceExchange, BybitExchange

class DebugExchange(BinanceExchange):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ticker_count = {}
        self.last_ticker_time = {}
    
    async def _emit_ticker(self, ticker):
        """Override to debug ticker emissions"""
        # Count tickers per symbol
        if ticker.symbol not in self.ticker_count:
            self.ticker_count[ticker.symbol] = 0
        self.ticker_count[ticker.symbol] += 1
        
        # Track timing
        current_time = time.time()
        if ticker.symbol not in self.last_ticker_time:
            print(f"🎯 First ticker for {ticker.symbol}: {ticker.bid:.6f}/{ticker.ask:.6f}")
        else:
            interval = current_time - self.last_ticker_time[ticker.symbol]
            if interval > 5:  # Only log if more than 5 seconds
                print(f"📊 {ticker.symbol}: {ticker.bid:.6f}/{ticker.ask:.6f} (interval: {interval:.1f}s, count: {self.ticker_count[ticker.symbol]})")
        
        self.last_ticker_time[ticker.symbol] = current_time
        
        # Call parent method
        await super()._emit_ticker(ticker)

async def debug_ticker_flow():
    """Debug the ticker flow"""
    
    print("🔍 Debugging ticker flow...")
    
    # Load config
    config = Config()
    
    # Get dynamic symbols like GUI does
    from arbot.gui import ArBotGUI
    
    class MockTkinter:
        def after(self, *args): pass
        def title(self, *args): pass
        def geometry(self, *args): pass  
        def configure(self, *args): pass
        def columnconfigure(self, *args): pass
        def rowconfigure(self, *args): pass
        def protocol(self, *args): pass
    
    # Create mock GUI to get symbols
    import tkinter as tk
    original_tk = tk.Tk
    tk.Tk = MockTkinter
    
    try:
        # Initialize database
        database = Database(config)
        await database.initialize()
        
        gui = ArBotGUI(config, database)
        
        # Get symbols like GUI does
        await gui._get_dynamic_symbols()
        
        print(f"📋 Dynamic symbols found: {len(gui.dynamic_symbols)}")
        print(f"🎯 Top 10 symbols: {gui.dynamic_symbols[:10]}")
        
        # Test with debug exchange
        debug_exchange = DebugExchange(
            config.exchanges['binance'].api_key,
            config.exchanges['binance'].api_secret,
            testnet=config.exchanges['binance'].testnet
        )
        
        # Add ticker callback like GUI does
        ticker_count = 0
        async def test_callback(ticker):
            nonlocal ticker_count
            ticker_count += 1
            if ticker_count % 50 == 0:
                print(f"💾 Total tickers received: {ticker_count}")
        
        debug_exchange.on_ticker(test_callback)
        
        # Connect to first 10 symbols for testing
        test_symbols = gui.dynamic_symbols[:10]
        print(f"🔌 Connecting to WebSocket with symbols: {test_symbols}")
        
        await debug_exchange.connect_ws(test_symbols)
        
        print("⏳ Listening for tickers for 30 seconds...")
        await asyncio.sleep(30)
        
        print(f"\n📊 Ticker summary:")
        for symbol in test_symbols:
            count = debug_exchange.ticker_count.get(symbol, 0)
            print(f"  {symbol}: {count} tickers")
        
        await debug_exchange.disconnect_ws()
        
    finally:
        tk.Tk = original_tk

if __name__ == "__main__":
    asyncio.run(debug_ticker_flow())