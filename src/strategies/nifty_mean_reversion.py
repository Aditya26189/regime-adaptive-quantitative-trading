"""
NIFTY50 Mean Reversion Strategy - Adapted from Stock Strategies

INSIGHT: Trend-following failed (-0.08 Sharpe), trying mean reversion instead.
Stock strategies using RSI(2) mean reversion achieved 1.5-3.3 Sharpe.

Uses ONLY Close prices (Rule 12 compliant):
- RSI(2) for oversold/overbought detection
- Kaufman Efficiency Ratio (KER) for regime filtering
- Volatility for position sizing
"""

import pandas as pd
import numpy as np
from typing import Dict
import warnings
warnings.filterwarnings('ignore')


def calculate_rsi(series: pd.Series, period: int = 2) -> pd.Series:
    """Calculate RSI indicator."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_ker(series: pd.Series, period: int = 10) -> pd.Series:
    """Calculate Kaufman Efficiency Ratio."""
    change = abs(series.diff(period))
    volatility = series.diff().abs().rolling(period).sum()
    ker = change / volatility
    return ker.fillna(0)


def calculate_volatility(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate rolling volatility."""
    returns = series.pct_change()
    return returns.rolling(period).std() * 100


def generate_nifty_mean_reversion_signals(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
    """
    Generate mean reversion signals for NIFTY50.
    
    Strategy Logic:
    1. ENTRY: Long when:
       - RSI(2) < oversold_threshold (e.g., 10-30)
       - KER < ker_threshold (choppy market, good for mean reversion)
       - Volatility > vol_min (sufficient movement)
       - Time filter (trading hours)
    
    2. EXIT: Close when:
       - RSI(2) > overbought_threshold (e.g., 70-90)
       - Max hold period reached
       - End of day
    
    Args:
        data: DataFrame with 'datetime', 'close' columns
        params: Dictionary with strategy parameters
        
    Returns:
        DataFrame with trades
    """
    df = data.copy()
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Extract time features
    df['hour'] = df['timestamp'].dt.hour
    df['minute'] = df['timestamp'].dt.minute
    
    # Calculate indicators (ALL using Close only)
    rsi_period = params.get('rsi_period', 2)
    ker_period = params.get('ker_period', 10)
    vol_period = params.get('vol_period', 14)
    
    df['rsi'] = calculate_rsi(df['close'], rsi_period)
    df['ker'] = calculate_ker(df['close'], ker_period)
    df['volatility'] = calculate_volatility(df['close'], vol_period)
    
    # Thresholds
    rsi_entry = params.get('rsi_entry', 20)
    rsi_exit = params.get('rsi_exit', 70)
    ker_max = params.get('ker_max', 0.3)
    vol_min = params.get('vol_min', 0.005)
    allowed_hours = params.get('allowed_hours', [9, 10, 11, 12, 13, 14])
    max_hold = params.get('max_hold', 10)
    position_size = params.get('position_size', 0.95)
    
    # Generate trades
    trades = []
    position = None
    capital = 100000
    
    for i in range(len(df) - max_hold):
        current = df.iloc[i]
        
        # ENTRY LOGIC
        if position is None:
            # Mean reversion entry conditions
            is_oversold = current['rsi'] < rsi_entry
            is_choppy = current['ker'] < ker_max
            has_volatility = current['volatility'] > vol_min
            is_allowed_time = current['hour'] in allowed_hours
            
            if (is_oversold and is_choppy and has_volatility and is_allowed_time):
                # Calculate quantity
                entry_price = current['close']
                qty = int((capital * position_size - 24) / entry_price)
                
                if qty > 0:
                    position = {
                        'entry_idx': i,
                        'entry_price': entry_price,
                        'entry_time': current['timestamp'],
                        'qty': qty,
                        'entry_rsi': current['rsi'],
                    }
                    capital -= 24  # Entry fee
        
        # EXIT LOGIC
        else:
            bars_held = i - position['entry_idx']
            current_price = current['close']
            
            # Exit conditions
            is_overbought = current['rsi'] > rsi_exit
            max_hold_reached = bars_held >= max_hold
            
            # Profit target and stop loss
            pnl_pct = (current_price - position['entry_price']) / position['entry_price'] * 100
            profit_target = pnl_pct > 2.0  # Take profit at +2%
            stop_loss = pnl_pct < -1.5  # Stop loss at -1.5%
            
            # End of day
            is_eod = (current['hour'] >= 15 and current['minute'] >= 15)
            
            should_exit = (is_overbought or max_hold_reached or 
                          profit_target or stop_loss or is_eod)
            
            if should_exit:
                # Calculate P&L
                gross_pnl = (current_price - position['entry_price']) * position['qty']
                net_pnl = gross_pnl - 48  # Entry (24) + Exit (24)
                
                # Record trade
                trades.append({
                    'entry_time': position['entry_time'],
                    'exit_time': current['timestamp'],
                    'entry_price': position['entry_price'],
                    'exit_price': current_price,
                    'qty': position['qty'],
                    'pnl': net_pnl,
                    'bars_held': bars_held,
                    'exit_reason': ('overbought' if is_overbought else
                                   'max_hold' if max_hold_reached else
                                   'profit_target' if profit_target else
                                   'stop_loss' if stop_loss else 'eod'),
                })
                
                capital += net_pnl
                position = None
    
    # Convert to DataFrame
    if len(trades) == 0:
        return pd.DataFrame()
    
    trades_df = pd.DataFrame(trades)
    return trades_df
