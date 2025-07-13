#!/usr/bin/env python3
"""Check what symbols are actually stored in the database"""

import asyncio
import aiosqlite
from datetime import datetime, timedelta

async def check_db_symbols():
    """Check symbols stored in database"""
    
    async with aiosqlite.connect("arbot.db") as db:
        # Get unique symbols in last hour
        one_hour_ago = (datetime.now() - timedelta(hours=1)).timestamp()
        
        cursor = await db.execute('''
            SELECT DISTINCT symbol, exchange, COUNT(*) as count 
            FROM tickers 
            WHERE timestamp > ? 
            GROUP BY symbol, exchange 
            ORDER BY count DESC
        ''', (one_hour_ago,))
        
        results = await cursor.fetchall()
        
        print(f"📊 Symbols stored in database (last hour):")
        print(f"Found {len(results)} unique symbol-exchange combinations")
        
        for symbol, exchange, count in results[:30]:  # Show top 30
            print(f"  {exchange:<10} {symbol:<15} {count:>4} records")
        
        if len(results) > 30:
            print(f"  ... and {len(results) - 30} more combinations")
        
        # Get total count
        cursor = await db.execute('''
            SELECT COUNT(*) FROM tickers WHERE timestamp > ?
        ''', (one_hour_ago,))
        
        total = await cursor.fetchone()
        print(f"\n📈 Total ticker records in last hour: {total[0]}")
        
        # Get recent batch info
        cursor = await db.execute('''
            SELECT symbol, exchange, timestamp 
            FROM tickers 
            WHERE timestamp > ? 
            ORDER BY timestamp DESC 
            LIMIT 10
        ''', (one_hour_ago,))
        
        recent = await cursor.fetchall()
        print(f"\n🕒 Most recent 10 ticker records:")
        for symbol, exchange, timestamp in recent:
            dt = datetime.fromtimestamp(timestamp)
            print(f"  {dt.strftime('%H:%M:%S')} {exchange:<10} {symbol}")

if __name__ == "__main__":
    asyncio.run(check_db_symbols())