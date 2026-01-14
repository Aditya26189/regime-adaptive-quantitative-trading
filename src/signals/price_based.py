"""
Price-based signal generators.

This module provides signal generation functions based on price movements
including z-score mean reversion, momentum crossovers, and simple mean reversion.

All signals are generated without lookahead bias.
"""

from typing import List, Optional, Union
import pandas as pd
import numpy as np


def z_score_signal(
    data: pd.DataFrame,
    window: int = 20,
    entry_z: float = 2.0,
    exit_z: float = 0.5,
    price_col: str = 'mid'
) -> List[Optional[str]]:
    """
    Generate signals based on z-score mean reversion.
    
    Strategy logic:
    - BUY if z < -entry_z (price abnormally low, expect reversion up)
    - SELL if z > +entry_z (price abnormally high, expect reversion down)
    - CLOSE if |z| < exit_z (price returned to mean)
    - None otherwise
    
    Args:
        data: DataFrame with price data
        window: Lookback window for rolling mean/std calculation
        entry_z: Z-score threshold for entry (absolute value)
        exit_z: Z-score threshold for exit (absolute value)
        price_col: Column name for price data
        
    Returns:
        List of signals ('BUY', 'SELL', 'CLOSE', or None), same length as data
    """
    signals: List[Optional[str]] = []
    
    # Get price column
    if price_col not in data.columns:
        if 'close' in data.columns:
            price_col = 'close'
        elif 'price' in data.columns:
            price_col = 'price'
        elif 'bid' in data.columns and 'ask' in data.columns:
            prices = (data['bid'] + data['ask']) / 2
        else:
            # Return all None if no valid price column
            return [None] * len(data)
    
    if price_col in data.columns:
        prices = data[price_col]
    
    # Calculate rolling mean and std
    rolling_mean = prices.rolling(window=window).mean()
    rolling_std = prices.rolling(window=window).std()
    
    # Calculate z-score
    z_scores = np.where(
        rolling_std > 0,
        (prices - rolling_mean) / rolling_std,
        0.0
    )
    
    # Track position state for proper signal generation
    current_position = 0  # 1 = long, -1 = short, 0 = flat
    
    for i, z in enumerate(z_scores):
        if np.isnan(z) or i < window:
            # Not enough data for z-score
            signals.append(None)
            continue
        
        signal = None
        
        if current_position == 0:
            # No position, look for entry
            if z < -entry_z:
                signal = 'BUY'
                current_position = 1
            elif z > entry_z:
                signal = 'SELL'
                current_position = -1
        elif current_position == 1:
            # Long position, look for exit or flip
            if abs(z) < exit_z:
                signal = 'CLOSE'
                current_position = 0
            elif z > entry_z:
                # Flip to short
                signal = 'SELL'
                current_position = -1
        elif current_position == -1:
            # Short position, look for exit or flip
            if abs(z) < exit_z:
                signal = 'CLOSE'
                current_position = 0
            elif z < -entry_z:
                # Flip to long
                signal = 'BUY'
                current_position = 1
        
        signals.append(signal)
    
    return signals


def momentum_signal(
    data: pd.DataFrame,
    fast_ma: int = 5,
    slow_ma: int = 20,
    price_col: str = 'mid'
) -> List[Optional[str]]:
    """
    Generate signals based on moving average crossover momentum.
    
    Strategy logic:
    - BUY when fast MA crosses above slow MA (bullish momentum)
    - SELL when fast MA crosses below slow MA (bearish momentum)
    
    Args:
        data: DataFrame with price data
        fast_ma: Window for fast moving average
        slow_ma: Window for slow moving average
        price_col: Column name for price data
        
    Returns:
        List of signals ('BUY', 'SELL', or None), same length as data
    """
    signals: List[Optional[str]] = []
    
    # Get price column
    if price_col not in data.columns:
        if 'close' in data.columns:
            price_col = 'close'
        elif 'price' in data.columns:
            price_col = 'price'
        elif 'bid' in data.columns and 'ask' in data.columns:
            prices = (data['bid'] + data['ask']) / 2
        else:
            return [None] * len(data)
    
    if price_col in data.columns:
        prices = data[price_col]
    
    # Calculate moving averages
    fast = prices.rolling(window=fast_ma).mean()
    slow = prices.rolling(window=slow_ma).mean()
    
    # Track previous crossover state
    prev_fast_above = None
    
    for i in range(len(data)):
        if i < slow_ma or np.isnan(fast.iloc[i]) or np.isnan(slow.iloc[i]):
            signals.append(None)
            continue
        
        current_fast_above = fast.iloc[i] > slow.iloc[i]
        
        signal = None
        
        if prev_fast_above is not None:
            if current_fast_above and not prev_fast_above:
                # Fast crossed above slow -> bullish
                signal = 'BUY'
            elif not current_fast_above and prev_fast_above:
                # Fast crossed below slow -> bearish
                signal = 'SELL'
        
        prev_fast_above = current_fast_above
        signals.append(signal)
    
    return signals


def mean_reversion_signal(
    data: pd.DataFrame,
    window: int = 20,
    threshold: float = 2.0,
    price_col: str = 'mid'
) -> List[Optional[str]]:
    """
    Generate signals based on simple mean reversion.
    
    Strategy logic:
    - BUY if price < (rolling_mean - threshold * rolling_std)
    - SELL if price > (rolling_mean + threshold * rolling_std)
    
    Simpler than z_score_signal as it doesn't track position state.
    
    Args:
        data: DataFrame with price data
        window: Lookback window for calculations
        threshold: Number of standard deviations for entry
        price_col: Column name for price data
        
    Returns:
        List of signals ('BUY', 'SELL', or None), same length as data
    """
    signals: List[Optional[str]] = []
    
    # Get price column
    if price_col not in data.columns:
        if 'close' in data.columns:
            price_col = 'close'
        elif 'price' in data.columns:
            price_col = 'price'
        elif 'bid' in data.columns and 'ask' in data.columns:
            prices = (data['bid'] + data['ask']) / 2
        else:
            return [None] * len(data)
    
    if price_col in data.columns:
        prices = data[price_col]
    
    # Calculate rolling statistics
    rolling_mean = prices.rolling(window=window).mean()
    rolling_std = prices.rolling(window=window).std()
    
    lower_band = rolling_mean - threshold * rolling_std
    upper_band = rolling_mean + threshold * rolling_std
    
    for i in range(len(data)):
        if i < window or np.isnan(rolling_mean.iloc[i]):
            signals.append(None)
            continue
        
        price = prices.iloc[i]
        
        if price < lower_band.iloc[i]:
            signals.append('BUY')
        elif price > upper_band.iloc[i]:
            signals.append('SELL')
        else:
            signals.append(None)
    
    return signals


def bollinger_band_signal(
    data: pd.DataFrame,
    window: int = 20,
    num_std: float = 2.0,
    price_col: str = 'mid'
) -> List[Optional[str]]:
    """
    Generate signals based on Bollinger Bands.
    
    Strategy logic:
    - BUY when price touches lower band and starts rising
    - SELL when price touches upper band and starts falling
    
    Args:
        data: DataFrame with price data
        window: Lookback window for calculations
        num_std: Number of standard deviations for bands
        price_col: Column name for price data
        
    Returns:
        List of signals ('BUY', 'SELL', or None), same length as data
    """
    signals: List[Optional[str]] = []
    
    # Get price column
    if price_col not in data.columns:
        if 'close' in data.columns:
            price_col = 'close'
        elif 'price' in data.columns:
            price_col = 'price'
        elif 'bid' in data.columns and 'ask' in data.columns:
            prices = (data['bid'] + data['ask']) / 2
        else:
            return [None] * len(data)
    
    if price_col in data.columns:
        prices = data[price_col]
    
    # Calculate Bollinger Bands
    rolling_mean = prices.rolling(window=window).mean()
    rolling_std = prices.rolling(window=window).std()
    
    upper_band = rolling_mean + num_std * rolling_std
    lower_band = rolling_mean - num_std * rolling_std
    
    for i in range(len(data)):
        if i < window + 1 or np.isnan(rolling_mean.iloc[i]):
            signals.append(None)
            continue
        
        price = prices.iloc[i]
        prev_price = prices.iloc[i - 1]
        
        # Buy when touching lower band and rising
        if prev_price <= lower_band.iloc[i - 1] and price > prev_price:
            signals.append('BUY')
        # Sell when touching upper band and falling
        elif prev_price >= upper_band.iloc[i - 1] and price < prev_price:
            signals.append('SELL')
        else:
            signals.append(None)
    
    return signals
