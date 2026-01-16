import pandas as pd
import numpy as np

def calculate_rsi(close: pd.Series, period: int = 2) -> pd.Series:
    """RSI calculation using Wilder's smoothing"""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))

def calculate_volatility(close: pd.Series, period: int = 14) -> pd.Series:
    """Close-based volatility (Rule 12 compliant)"""
    rolling_max = close.rolling(window=period).max()
    rolling_min = close.rolling(window=period).min()
    return (rolling_max - rolling_min) / close
