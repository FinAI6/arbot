#!/usr/bin/env python3
"""Test fixed symbol list without problematic symbols"""

# Test the problematic symbols filtering logic
def test_symbol_filtering():
    print("🧪 Testing symbol filtering logic...")
    
    # Original problematic symbols
    base_symbols = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", 
        "IOTAUSDT", "ONTUSDT", "IOSTUSDT", "FOOTBALLUSUSDT", 
        "VOXELUSDT", "NMRUSDT", "ORNUSDT", "CTSIUSDT",
        "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT", "MATICUSDT"
    ]
    
    # Known problematic symbols for Bybit
    problematic_symbols = {
        "IOTAUSDT", "ONTUSDT", "IOSTUSDT", "FOOTBALLUSUSDT", 
        "VOXELUSDT", "NMRUSDT", "ORNUSDT", "CTSIUSDT",
    }
    
    # Filter function
    def _is_symbol_enabled(symbol: str) -> bool:
        """Check if symbol uses enabled quote currency"""
        enabled_quote_currencies = ["USDT"]
        for quote_currency in enabled_quote_currencies:
            if symbol.endswith(quote_currency):
                return True
        return False
    
    # Filter out problematic symbols
    filtered_symbols = []
    removed_symbols = []
    
    for symbol in base_symbols:
        if symbol in problematic_symbols:
            removed_symbols.append(symbol)
            print(f"❌ Removed problematic symbol: {symbol}")
        elif not _is_symbol_enabled(symbol):
            removed_symbols.append(symbol)
            print(f"❌ Removed symbol (quote currency): {symbol}")
        else:
            filtered_symbols.append(symbol)
            print(f"✅ Kept symbol: {symbol}")
    
    print(f"\n📊 Results:")
    print(f"  Original symbols: {len(base_symbols)}")
    print(f"  Removed symbols: {len(removed_symbols)}")
    print(f"  Final symbols: {len(filtered_symbols)}")
    print(f"  Removed: {removed_symbols}")
    print(f"  Final: {filtered_symbols}")
    
    # Test specific problematic symbols are removed
    for problematic in ["IOTAUSDT", "ONTUSDT", "IOSTUSDT"]:
        if problematic not in filtered_symbols:
            print(f"✅ {problematic} successfully removed")
        else:
            print(f"❌ {problematic} still present!")

if __name__ == "__main__":
    test_symbol_filtering()