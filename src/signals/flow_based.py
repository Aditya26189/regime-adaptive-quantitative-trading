"""
Flow-based signal generators.

This module provides signal generation functions based on order flow
data including order book imbalance (OBI) and microprice deviation.

These signals capture information about supply/demand imbalance
that may predict short-term price movements.
"""

from typing import List, Optional
import pandas as pd
import numpy as np


def obi_signal(
    data: pd.DataFrame,
    threshold: float = 0.3
) -> List[Optional[str]]:
    """
    Generate signals based on Order Book Imbalance (OBI).
    
    OBI = (bid_qty - ask_qty) / (bid_qty + ask_qty)
    
    Strategy logic:
    - BUY if OBI > threshold (strong buying pressure)
    - SELL if OBI < -threshold (strong selling pressure)
    - None otherwise
    
    Rationale: High OBI indicates more buyers than sellers at the
    best prices, suggesting upward price pressure.
    
    Args:
        data: DataFrame with 'obi' column or 'bid_qty'/'ask_qty' columns
        threshold: OBI threshold for signal generation (0 to 1)
        
    Returns:
        List of signals ('BUY', 'SELL', or None), same length as data
    """
    signals: List[Optional[str]] = []
    
    # Calculate OBI if not present
    if 'obi' in data.columns:
        obi = data['obi']
    elif 'bid_qty' in data.columns and 'ask_qty' in data.columns:
        total_qty = data['bid_qty'] + data['ask_qty']
        obi = np.where(
            total_qty > 0,
            (data['bid_qty'] - data['ask_qty']) / total_qty,
            0.0
        )
        obi = pd.Series(obi, index=data.index)
    else:
        # No OBI data available
        return [None] * len(data)
    
    for i, val in enumerate(obi):
        if np.isnan(val):
            signals.append(None)
        elif val > threshold:
            signals.append('BUY')
        elif val < -threshold:
            signals.append('SELL')
        else:
            signals.append(None)
    
    return signals


def microprice_deviation(
    data: pd.DataFrame,
    window: int = 20,
    threshold_std: float = 1.0
) -> List[Optional[str]]:
    """
    Generate signals based on microprice deviation from mid.
    
    Microprice is a quantity-weighted mid price that better reflects
    the true equilibrium price. When microprice deviates significantly
    from mid, it suggests directional pressure.
    
    Strategy logic:
    - BUY if microprice > mid + threshold (buying pressure, price likely to rise)
    - SELL if microprice < mid - threshold (selling pressure, price likely to fall)
    
    Args:
        data: DataFrame with 'microprice' and 'mid' columns, or the raw data
        window: Window for calculating threshold based on rolling std
        threshold_std: Number of standard deviations for threshold
        
    Returns:
        List of signals ('BUY', 'SELL', or None), same length as data
    """
    signals: List[Optional[str]] = []
    
    # Calculate microprice if not present
    if 'microprice' not in data.columns:
        required = ['bid', 'ask', 'bid_qty', 'ask_qty']
        if not all(c in data.columns for c in required):
            return [None] * len(data)
        
        total_qty = data['bid_qty'] + data['ask_qty']
        microprice = np.where(
            total_qty > 0,
            (data['bid'] * data['ask_qty'] + data['ask'] * data['bid_qty']) / total_qty,
            (data['bid'] + data['ask']) / 2
        )
        microprice = pd.Series(microprice, index=data.index)
    else:
        microprice = data['microprice']
    
    # Calculate mid if not present
    if 'mid' not in data.columns:
        if 'bid' in data.columns and 'ask' in data.columns:
            mid = (data['bid'] + data['ask']) / 2
        else:
            return [None] * len(data)
    else:
        mid = data['mid']
    
    # Calculate deviation
    deviation = microprice - mid
    
    # Calculate rolling threshold based on deviation std
    rolling_std = deviation.rolling(window=window).std()
    threshold = threshold_std * rolling_std
    
    for i in range(len(data)):
        if i < window or np.isnan(deviation.iloc[i]) or np.isnan(threshold.iloc[i]):
            signals.append(None)
            continue
        
        if deviation.iloc[i] > threshold.iloc[i]:
            signals.append('BUY')
        elif deviation.iloc[i] < -threshold.iloc[i]:
            signals.append('SELL')
        else:
            signals.append(None)
    
    return signals


def trade_flow_signal(
    data: pd.DataFrame,
    window: int = 10,
    threshold: float = 0.6
) -> List[Optional[str]]:
    """
    Generate signals based on cumulative trade flow.
    
    Tracks the cumulative signed volume over a window.
    Positive flow = more buy trades, negative = more sell trades.
    
    Args:
        data: DataFrame with 'side' and 'quantity' or 'signed_qty' columns
        window: Rolling window for cumulative flow
        threshold: Threshold as fraction of window capacity
        
    Returns:
        List of signals ('BUY', 'SELL', or None), same length as data
    """
    signals: List[Optional[str]] = []
    
    # Get signed quantity
    if 'signed_qty' in data.columns:
        signed_qty = data['signed_qty']
    elif 'side' in data.columns and 'quantity' in data.columns:
        signed_qty = data['quantity'] * np.where(
            data['side'].str.upper() == 'BUY', 1, -1
        )
    else:
        return [None] * len(data)
    
    # Calculate rolling sum of signed quantity
    flow = signed_qty.rolling(window=window).sum()
    
    # Dynamic threshold based on rolling abs volume
    abs_volume = abs(signed_qty).rolling(window=window).mean() * window
    
    for i in range(len(data)):
        if i < window or np.isnan(flow.iloc[i]) or abs_volume.iloc[i] == 0:
            signals.append(None)
            continue
        
        normalized_flow = flow.iloc[i] / abs_volume.iloc[i]
        
        if normalized_flow > threshold:
            signals.append('BUY')
        elif normalized_flow < -threshold:
            signals.append('SELL')
        else:
            signals.append(None)
    
    return signals


def obi_momentum_signal(
    data: pd.DataFrame,
    window: int = 5,
    threshold: float = 0.1
) -> List[Optional[str]]:
    """
    Generate signals based on OBI momentum (change in OBI).
    
    Captures shifts in order book imbalance that may precede price moves.
    
    Strategy logic:
    - BUY if OBI is rapidly increasing (threshold exceeded)
    - SELL if OBI is rapidly decreasing (negative threshold exceeded)
    
    Args:
        data: DataFrame with 'obi' column or bid/ask quantity data
        window: Window for calculating OBI change
        threshold: Threshold for OBI change to generate signal
        
    Returns:
        List of signals ('BUY', 'SELL', or None), same length as data
    """
    signals: List[Optional[str]] = []
    
    # Calculate OBI if not present
    if 'obi' in data.columns:
        obi = data['obi']
    elif 'bid_qty' in data.columns and 'ask_qty' in data.columns:
        total_qty = data['bid_qty'] + data['ask_qty']
        obi = np.where(
            total_qty > 0,
            (data['bid_qty'] - data['ask_qty']) / total_qty,
            0.0
        )
        obi = pd.Series(obi, index=data.index)
    else:
        return [None] * len(data)
    
    # Calculate OBI momentum (change over window)
    obi_change = obi - obi.shift(window)
    
    for i in range(len(data)):
        if i < window or np.isnan(obi_change.iloc[i]):
            signals.append(None)
            continue
        
        if obi_change.iloc[i] > threshold:
            signals.append('BUY')
        elif obi_change.iloc[i] < -threshold:
            signals.append('SELL')
        else:
            signals.append(None)
    
    return signals
