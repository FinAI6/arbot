"""
Technical indicators module - Alternative to ta-lib using pandas-ta
"""

import pandas as pd
import numpy as np
from typing import Union, Optional


def sma(data: Union[pd.Series, np.ndarray], period: int = 20) -> pd.Series:
    """Simple Moving Average"""
    if isinstance(data, np.ndarray):
        data = pd.Series(data)
    return data.rolling(window=period).mean()


def ema(data: Union[pd.Series, np.ndarray], period: int = 20) -> pd.Series:
    """Exponential Moving Average"""
    if isinstance(data, np.ndarray):
        data = pd.Series(data)
    return data.ewm(span=period).mean()


def rsi(data: Union[pd.Series, np.ndarray], period: int = 14) -> pd.Series:
    """Relative Strength Index"""
    if isinstance(data, np.ndarray):
        data = pd.Series(data)
    
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi_values = 100 - (100 / (1 + rs))
    return rsi_values


def macd(data: Union[pd.Series, np.ndarray], 
         fast_period: int = 12, 
         slow_period: int = 26, 
         signal_period: int = 9) -> dict:
    """MACD indicator"""
    if isinstance(data, np.ndarray):
        data = pd.Series(data)
    
    ema_fast = ema(data, fast_period)
    ema_slow = ema(data, slow_period)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal_period)
    histogram = macd_line - signal_line
    
    return {
        'macd': macd_line,
        'signal': signal_line,
        'histogram': histogram
    }


def bollinger_bands(data: Union[pd.Series, np.ndarray], 
                   period: int = 20, 
                   std_dev: float = 2.0) -> dict:
    """Bollinger Bands"""
    if isinstance(data, np.ndarray):
        data = pd.Series(data)
    
    middle_band = sma(data, period)
    std = data.rolling(window=period).std()
    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)
    
    return {
        'upper': upper_band,
        'middle': middle_band,
        'lower': lower_band
    }


def stochastic_oscillator(high: Union[pd.Series, np.ndarray],
                         low: Union[pd.Series, np.ndarray],
                         close: Union[pd.Series, np.ndarray],
                         k_period: int = 14,
                         d_period: int = 3) -> dict:
    """Stochastic Oscillator"""
    if isinstance(high, np.ndarray):
        high = pd.Series(high)
    if isinstance(low, np.ndarray):
        low = pd.Series(low)
    if isinstance(close, np.ndarray):
        close = pd.Series(close)
    
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    
    k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
    d_percent = k_percent.rolling(window=d_period).mean()
    
    return {
        'k': k_percent,
        'd': d_percent
    }


def atr(high: Union[pd.Series, np.ndarray],
        low: Union[pd.Series, np.ndarray],
        close: Union[pd.Series, np.ndarray],
        period: int = 14) -> pd.Series:
    """Average True Range"""
    if isinstance(high, np.ndarray):
        high = pd.Series(high)
    if isinstance(low, np.ndarray):
        low = pd.Series(low)
    if isinstance(close, np.ndarray):
        close = pd.Series(close)
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return true_range.rolling(window=period).mean()


def volume_sma(volume: Union[pd.Series, np.ndarray], period: int = 20) -> pd.Series:
    """Volume Simple Moving Average"""
    if isinstance(volume, np.ndarray):
        volume = pd.Series(volume)
    return volume.rolling(window=period).mean()


def price_change_percent(data: Union[pd.Series, np.ndarray], periods: int = 1) -> pd.Series:
    """Price change percentage"""
    if isinstance(data, np.ndarray):
        data = pd.Series(data)
    return data.pct_change(periods=periods) * 100


def volatility(data: Union[pd.Series, np.ndarray], period: int = 20) -> pd.Series:
    """Price volatility (standard deviation of returns)"""
    if isinstance(data, np.ndarray):
        data = pd.Series(data)
    returns = data.pct_change()
    return returns.rolling(window=period).std() * np.sqrt(period)