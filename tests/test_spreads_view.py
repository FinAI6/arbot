#!/usr/bin/env python3
"""Test spreads view update with single exchange"""

import time
from arbot.gui import MovingAverageManager

def test_single_exchange_spreads():
    """Test the spreads view logic with single exchange data"""
    
    print("🧪 Testing single exchange spreads view logic...")
    
    # Mock current_prices data (simulating Bybit only)
    current_prices = {
        'bybit': {
            'BTCUSDT': {
                'bid': 117800.0,
                'ask': 117820.0,
                'timestamp': time.time()
            },
            'ETHUSDT': {
                'bid': 2950.0,
                'ask': 2952.0,
                'timestamp': time.time()
            },
            'XRPUSDT': {
                'bid': 2.785,
                'ask': 2.787,
                'timestamp': time.time()
            }
        }
    }
    
    # Test the spreads calculation logic
    arbitrage_rows = []
    moving_average_manager = MovingAverageManager(30)
    
    # Simulate the single exchange logic
    exchange_names = list(current_prices.keys())
    total_symbols = sum(len(symbols) for symbols in current_prices.values())
    
    print(f"📊 Exchange names: {exchange_names}")
    print(f"📊 Total symbols: {total_symbols}")
    print(f"📊 Single exchange condition: {len(exchange_names) == 1}")
    
    if len(current_prices) >= 1 and total_symbols > 0:
        print("✅ Passed initial condition check")
        
        # Skip multi-exchange logic for this test...
        
        # Single exchange logic
        if len(exchange_names) == 1:
            exchange_name = exchange_names[0]
            exchange_data = current_prices[exchange_name]
            
            print(f"📊 Processing single exchange: {exchange_name}")
            print(f"📊 Symbols: {list(exchange_data.keys())}")
            
            for symbol, price_data in exchange_data.items():
                bid = price_data.get('bid', 0)
                ask = price_data.get('ask', 0)
                
                if bid > 0 and ask > 0:
                    # Calculate bid-ask spread
                    spread_abs = ask - bid
                    spread_pct = (spread_abs / bid) * 100 if bid > 0 else 0
                    mid_price = (bid + ask) / 2
                    
                    # Update moving average
                    moving_average_manager.update_price(f"{symbol}_{exchange_name}", mid_price)
                    
                    # Get moving average and trend
                    ma = moving_average_manager.get_moving_average(f"{symbol}_{exchange_name}")
                    trend = moving_average_manager.get_price_trend(f"{symbol}_{exchange_name}")
                    
                    row_data = {
                        'symbol': symbol,
                        'higher_exchange': exchange_name.upper(),
                        'price': mid_price,
                        'price_diff': spread_abs,
                        'spread_pct': spread_pct,
                        'actual_arbitrage_pct': spread_pct,
                        'ma1': ma,
                        'ma2': ma,
                        'trend1': trend,
                        'trend2': trend,
                        'exchange1': exchange_name,
                        'exchange2': exchange_name + '_bid_ask'
                    }
                    
                    arbitrage_rows.append(row_data)
                    
                    print(f"📈 {symbol}: {bid:.6f}/{ask:.6f} = {spread_pct:.4f}% spread")
    
    print(f"\n✅ Generated {len(arbitrage_rows)} arbitrage rows")
    
    if arbitrage_rows:
        print("📊 Sample rows:")
        for row in arbitrage_rows[:3]:
            print(f"  {row['symbol']}: {row['higher_exchange']} @ {row['price']:.6f} ({row['spread_pct']:.4f}%)")
        
        print("✅ Single exchange spreads view would be populated!")
    else:
        print("❌ No arbitrage rows generated")

if __name__ == "__main__":
    test_single_exchange_spreads()