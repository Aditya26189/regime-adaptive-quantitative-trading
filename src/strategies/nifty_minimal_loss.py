"""
NIFTY50 Minimal Loss Strategy - Trade Count Focused

GOAL: Generate 120+ trades with minimal losses (Sharpe close to 0)
INSIGHT: NIFTY is hard to profit from. Accept near-zero Sharpe, just avoid big losses.

Strategy: Ultra-simple mean reversion with very tight stops
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


def generate_nifty_minimal_loss_signals(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
    """
    Generate signals for NIFTY50 with focus on trade count and minimal losses.
    
    Strategy: Buy oversold, sell quickly with tight stops
    """
    df = data.copy()
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Extract time features
    df['hour'] = df['timestamp'].dt.hour
    df['minute'] = df['timestamp'].dt.minute
    
    # Calculate RSI
    df['rsi'] = calculate_rsi(df['close'], period=2)
    
    # Parameters
    rsi_entry = params.get('rsi_entry', 25)
    rsi_exit = params.get('rsi_exit', 70)
    max_hold = params.get('max_hold', 8)
    stop_loss_pct = params.get('stop_loss_pct', 0.8)  # Very tight stop
    profit_target_pct = params.get('profit_target_pct', 1.2)  # Quick profit
    allowed_hours = params.get('allowed_hours', [9, 10, 11, 12, 13, 14])
    
    # Generate trades
    trades = []
    position = None
    capital = 100000
    
    for i in range(len(df) - max_hold):
        current = df.iloc[i]
        
        # ENTRY
        if position is None:
            if (current['rsi'] < rsi_entry and 
                current['hour'] in allowed_hours and
                not pd.isna(current['rsi'])):
                
                entry_price = current['close']
                qty = int((capital * 0.90 - 24) / entry_price)
                
                if qty > 0:
                    position = {
                        'entry_idx': i,
                        'entry_price': entry_price,
                        'entry_time': current['timestamp'],
                        'qty': qty,
                    }
                    capital -= 24
        
        # EXIT
        else:
            bars_held = i - position['entry_idx']
            current_price = current['close']
            pnl_pct = (current_price - position['entry_price']) / position['entry_price'] * 100
            
            # Exit conditions
            is_overbought = current['rsi'] > rsi_exit
            max_hold_reached = bars_held >= max_hold
            hit_stop = pnl_pct < -stop_loss_pct
            hit_target = pnl_pct > profit_target_pct
            is_eod = (current['hour'] >= 15 and current['minute'] >= 15)
            
            if (is_overbought or max_hold_reached or hit_stop or hit_target or is_eod):
                gross_pnl = (current_price - position['entry_price']) * position['qty']
                net_pnl = gross_pnl - 48
                
                trades.append({
                    'entry_time': position['entry_time'],
                    'exit_time': current['timestamp'],
                    'entry_price': position['entry_price'],
                    'exit_price': current_price,
                    'qty': position['qty'],
                    'pnl': net_pnl,
                    'bars_held': bars_held,
                })
                
                capital += net_pnl
                position = None
    
    if len(trades) == 0:
        return pd.DataFrame()
    
    return pd.DataFrame(trades)
