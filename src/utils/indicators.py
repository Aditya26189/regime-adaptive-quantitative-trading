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

def calculate_dynamic_rsi_bands(
    rsi_series: pd.Series,
    window: int = 20,
    num_std: float = 2.0,
    lower_clip: tuple = (15, 45),
    upper_clip: tuple = (60, 95)
) -> tuple:
    """
    Calculate volatility-adaptive RSI bands.
    
    Args:
        rsi_series: RSI values (2-100 range)
        window: Lookback period for mean/std calculation
        num_std: Standard deviation multiplier
        lower_clip: (min, max) bounds for lower band
        upper_clip: (min, max) bounds for upper band
    
    Returns:
        (lower_band, upper_band) as pd.Series
    """
    # Rolling statistics
    rsi_mean = rsi_series.rolling(window=window, min_periods=window).mean()
    rsi_std = rsi_series.rolling(window=window, min_periods=window).std()
    
    # Calculate bands
    lower_band = rsi_mean - (num_std * rsi_std)
    upper_band = rsi_mean + (num_std * rsi_std)
    
    # Clip to valid RSI range
    lower_band = lower_band.clip(lower=lower_clip[0], upper=lower_clip[1])
    upper_band = upper_band.clip(lower=upper_clip[0], upper=upper_clip[1])
    
    # Fill NaN with static defaults during warmup
    lower_band = lower_band.fillna(30)
    upper_band = upper_band.fillna(70)
    
    return lower_band, upper_band
