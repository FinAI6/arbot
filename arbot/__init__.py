"""
arbot - Cryptocurrency Arbitrage Trading Bot

A high-performance Python-based trading system for automated arbitrage 
trading across multiple centralized crypto exchanges.
"""

__version__ = "1.0.0"
__author__ = "Euiyun Kim"
__email__ = "geniuskey@gmail.com"

from .config import config
from .main import main

__all__ = ["config", "main"]