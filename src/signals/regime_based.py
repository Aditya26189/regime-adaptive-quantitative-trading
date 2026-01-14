"""
Regime-based signal filters.

This module provides functions to classify market regimes and
filter trading signals based on market conditions.

The core idea is to only trade in favorable market regimes,
avoiding volatile or uncertain conditions.
"""

from typing import List, Optional
import pandas as pd
import numpy as np


def volatility_regime(
    data: pd.DataFrame,
    window: int = 100,
    calm_percentile: float = 25.0,
    volatile_percentile: float = 75.0,
    volatility_col: str = 'volatility'
) -> List[str]:
    """
    Classify market volatility state.
    
    Classifies each time point into one of three regimes:
    - CALM: Volatility below 25th percentile (low vol, may be ranging)
    - NORMAL: Volatility between 25th and 75th percentile (ideal for trading)
    - VOLATILE: Volatility above 75th percentile (high vol, risky)
    
    Args:
        data: DataFrame with volatility data or returns for calculation
        window: Window for calculating rolling volatility percentiles
        calm_percentile: Percentile threshold below which is CALM
        volatile_percentile: Percentile threshold above which is VOLATILE
        volatility_col: Column name for volatility (optional)
        
    Returns:
        List of regime labels ('CALM', 'NORMAL', 'VOLATILE'), same length as data
    """
    regimes: List[str] = []
    
    # Get or calculate volatility
    if volatility_col in data.columns:
        volatility = data[volatility_col]
    elif 'returns' in data.columns:
        volatility = data['returns'].rolling(window=20).std()
    elif 'mid' in data.columns:
        returns = np.log(data['mid'] / data['mid'].shift(1))
        volatility = returns.rolling(window=20).std()
    elif 'close' in data.columns:
        returns = np.log(data['close'] / data['close'].shift(1))
        volatility = returns.rolling(window=20).std()
    else:
        # Default to NORMAL if can't calculate
        return ['NORMAL'] * len(data)
    
    # Calculate rolling percentiles
    for i in range(len(data)):
        if i < window:
            regimes.append('NORMAL')  # Default during warmup
            continue
        
        current_vol = volatility.iloc[i]
        
        if np.isnan(current_vol):
            regimes.append('NORMAL')
            continue
        
        # Get historical volatility for percentile calculation
        historical_vol = volatility.iloc[max(0, i - window):i + 1].dropna()
        
        if len(historical_vol) < 2:
            regimes.append('NORMAL')
            continue
        
        p_calm = np.percentile(historical_vol, calm_percentile)
        p_volatile = np.percentile(historical_vol, volatile_percentile)
        
        if current_vol < p_calm:
            regimes.append('CALM')
        elif current_vol > p_volatile:
            regimes.append('VOLATILE')
        else:
            regimes.append('NORMAL')
    
    return regimes


def should_trade_regime(regime: str) -> bool:
    """
    Determine if trading should occur in the given regime.
    
    By default, only trade in NORMAL regime.
    CALM regime may have too little movement for profit.
    VOLATILE regime has too much risk.
    
    Args:
        regime: Current regime ('CALM', 'NORMAL', 'VOLATILE')
        
    Returns:
        True if trading is allowed, False otherwise
    """
    return regime == 'NORMAL'


def should_trade_regime_conservative(regime: str) -> bool:
    """
    Conservative regime filter - only trade in CALM and NORMAL.
    
    Args:
        regime: Current regime ('CALM', 'NORMAL', 'VOLATILE')
        
    Returns:
        True if trading is allowed, False otherwise
    """
    return regime in ('CALM', 'NORMAL')


def should_trade_regime_aggressive(regime: str) -> bool:
    """
    Aggressive regime filter - trade in all regimes.
    
    Use with caution as this allows trading in volatile conditions.
    
    Args:
        regime: Current regime
        
    Returns:
        Always True
    """
    return True


def trend_regime(
    data: pd.DataFrame,
    window: int = 50,
    threshold: float = 0.02,
    price_col: str = 'mid'
) -> List[str]:
    """
    Classify market trend regime.
    
    Classifies each time point into:
    - UPTREND: Price significantly above moving average
    - DOWNTREND: Price significantly below moving average
    - SIDEWAYS: Price near moving average
    
    Args:
        data: DataFrame with price data
        window: Window for moving average
        threshold: Deviation threshold (as decimal)
        price_col: Column name for price data
        
    Returns:
        List of regime labels ('UPTREND', 'DOWNTREND', 'SIDEWAYS')
    """
    regimes: List[str] = []
    
    # Get price column
    if price_col not in data.columns:
        if 'close' in data.columns:
            price_col = 'close'
        elif 'price' in data.columns:
            price_col = 'price'
        elif 'bid' in data.columns and 'ask' in data.columns:
            prices = (data['bid'] + data['ask']) / 2
        else:
            return ['SIDEWAYS'] * len(data)
    
    if price_col in data.columns:
        prices = data[price_col]
    
    ma = prices.rolling(window=window).mean()
    
    for i in range(len(data)):
        if i < window or np.isnan(ma.iloc[i]):
            regimes.append('SIDEWAYS')
            continue
        
        deviation = (prices.iloc[i] - ma.iloc[i]) / ma.iloc[i]
        
        if deviation > threshold:
            regimes.append('UPTREND')
        elif deviation < -threshold:
            regimes.append('DOWNTREND')
        else:
            regimes.append('SIDEWAYS')
    
    return regimes


def spread_regime(
    data: pd.DataFrame,
    window: int = 100,
    wide_percentile: float = 75.0
) -> List[str]:
    """
    Classify market by bid-ask spread width.
    
    Wide spreads can indicate:
    - Low liquidity (risky to trade)
    - High uncertainty
    - Upcoming announcements
    
    Args:
        data: DataFrame with 'spread' or 'bid'/'ask' columns
        window: Window for percentile calculation
        wide_percentile: Percentile threshold for wide spread
        
    Returns:
        List of regime labels ('NARROW', 'NORMAL', 'WIDE')
    """
    regimes: List[str] = []
    
    # Get or calculate spread
    if 'spread' in data.columns:
        spread = data['spread']
    elif 'bid' in data.columns and 'ask' in data.columns:
        spread = data['ask'] - data['bid']
    else:
        return ['NORMAL'] * len(data)
    
    for i in range(len(data)):
        if i < window:
            regimes.append('NORMAL')
            continue
        
        current_spread = spread.iloc[i]
        
        if np.isnan(current_spread):
            regimes.append('NORMAL')
            continue
        
        historical_spread = spread.iloc[max(0, i - window):i + 1].dropna()
        
        if len(historical_spread) < 2:
            regimes.append('NORMAL')
            continue
        
        p_wide = np.percentile(historical_spread, wide_percentile)
        p_narrow = np.percentile(historical_spread, 100 - wide_percentile)
        
        if current_spread > p_wide:
            regimes.append('WIDE')
        elif current_spread < p_narrow:
            regimes.append('NARROW')
        else:
            regimes.append('NORMAL')
    
    return regimes


def combined_regime_filter(
    volatility_regime: str,
    trend_regime: Optional[str] = None,
    spread_regime: Optional[str] = None
) -> bool:
    """
    Combined filter using multiple regime indicators.
    
    Args:
        volatility_regime: Volatility regime ('CALM', 'NORMAL', 'VOLATILE')
        trend_regime: Optional trend regime ('UPTREND', 'DOWNTREND', 'SIDEWAYS')
        spread_regime: Optional spread regime ('NARROW', 'NORMAL', 'WIDE')
        
    Returns:
        True if all conditions are favorable for trading
    """
    # Must not be in volatile regime
    if volatility_regime == 'VOLATILE':
        return False
    
    # Avoid wide spreads if spread regime provided
    if spread_regime is not None and spread_regime == 'WIDE':
        return False
    
    return True
