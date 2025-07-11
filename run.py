#!/usr/bin/env python3
"""
ArBot - Entry point script for running from project root
"""

import asyncio

if __name__ == "__main__":
    from arbot.main import main
    asyncio.run(main())