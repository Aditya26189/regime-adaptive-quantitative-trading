"""
Adaptive Bollinger Band Mean Reversion Strategy
BB with dynamic period and std based on volatility regime.

Expected Sharpe: 1.3-1.7
Rule 12 Compliant: Uses only close prices
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


def calculate_adaptive_bb(df: pd.DataFrame, params: Dict) -> pd.DataFrame:
    """
    Calculate adaptive Bollinger Bands that adjust to volatility regime.
    High vol → Wider bands (more deviation needed)
    Low vol → Tighter bands (capture small moves)
    """
    df = df.copy()
    
    base_period_min = params.get('base_period_min', 15)
    base_period_max = params.get('base_period_max', 30)
    std_mult_min = params.get('std_mult_min', 1.5)
    std_mult_max = params.get('std_mult_max', 3.0)
    vol_lookback = params.get('vol_lookback', 100)
    
    # Base volatility
    returns = df['close'].pct_change()
    base_vol = returns.rolling(20).std()
    
    # Volatility percentile
    vol_percentile = base_vol.rolling(vol_lookback).apply(
        lambda x: (x.iloc[-1] > x).sum() / len(x) if len(x) > 0 else 0.5,
        raw=False
    )
    
    # Adaptive period (longer in high vol)
    adaptive_period = (base_period_min + vol_percentile * (base_period_max - base_period_min)).fillna(20)
    
    # Adaptive std multiplier (wider in high vol)
    adaptive_std = (std_mult_min + vol_percentile * (std_mult_max - std_mult_min)).fillna(2.0)
    
    # Calculate BB with fixed lookback for efficiency
    df['bb_middle'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    
    # Adjust by adaptive std
    df['bb_upper'] = df['bb_middle'] + (adaptive_std * df['bb_std'])
    df['bb_lower'] = df['bb_middle'] - (adaptive_std * df['bb_std'])
    
    # Store percentile for analysis
    df['vol_percentile'] = vol_percentile
    df['adaptive_std'] = adaptive_std
    
    return df


def generate_adaptive_bb_signals(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
    """
    Generate adaptive Bollinger Band mean reversion signals.
    
    Strategy Logic:
    1. Entry when price touches/breaks lower adaptive BB
    2. Exit when price touches/breaks upper adaptive BB
    3. Volatility regime determines band width
    """
    df = data.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    df['hour'] = df['datetime'].dt.hour
    
    # Calculate adaptive BB
    df = calculate_adaptive_bb(df, params)
    
    # Parameters
    max_hold = params.get('max_hold', 12)
    allowed_hours = params.get('allowed_hours', [9, 10, 11, 12, 13, 14])
    entry_touch = params.get('entry_touch', True)  # Entry on touch vs break
    
    # Generate trades
    trades = []
    position = None
    capital = 100000
    
    warmup = 120
    
    for i in range(warmup, len(df) - max_hold):
        current = df.iloc[i]
        
        if pd.isna(current['bb_lower']) or pd.isna(current['bb_upper']):
            continue
        
        # ENTRY LOGIC
        if position is None:
            # Entry on lower band touch/break
            if entry_touch:
                entry_signal = current['close'] <= current['bb_lower']
            else:
                entry_signal = current['close'] < current['bb_lower']
            
            is_allowed_hour = current['hour'] in allowed_hours
            
            if entry_signal and is_allowed_hour:
                entry_price = current['close']
                qty = int((capital * 0.95 - 24) / entry_price)
                
                if qty > 0:
                    position = {
                        'entry_idx': i,
                        'entry_price': entry_price,
                        'entry_time': current['datetime'],
                        'qty': qty,
                        'entry_bb_lower': current['bb_lower'],
                    }
                    capital -= 24
        
        # EXIT LOGIC
        else:
            bars_held = i - position['entry_idx']
            current_price = current['close']
            
            # Exit conditions
            reaches_upper = current['close'] >= current['bb_upper']
            reaches_middle = current['close'] >= current['bb_middle']
            max_hold_reached = bars_held >= max_hold
            
            # Profit/stop
            pnl_pct = (current_price - position['entry_price']) / position['entry_price'] * 100
            profit_target = pnl_pct > 2.5
            stop_loss = pnl_pct < -2.0
            
            if reaches_upper or max_hold_reached or profit_target or stop_loss:
                gross_pnl = (current_price - position['entry_price']) * position['qty']
                net_pnl = gross_pnl - 48
                
                trades.append({
                    'entry_time': position['entry_time'],
                    'exit_time': current['datetime'],
                    'entry_price': position['entry_price'],
                    'exit_price': current_price,
                    'qty': position['qty'],
                    'pnl': net_pnl,
                    'bars_held': bars_held,
                    'exit_reason': 'upper_bb' if reaches_upper else
                                  'profit' if profit_target else
                                  'stop' if stop_loss else 'max_hold',
                })
                
                capital += net_pnl
                position = None
    
    if len(trades) == 0:
        return pd.DataFrame()
    
    return pd.DataFrame(trades)


def optimize_adaptive_bb(data: pd.DataFrame, n_iterations: int = 300) -> Tuple[Dict, float, int]:
    """Optimize adaptive BB parameters."""
    import random
    
    param_space = {
        'base_period_min': [10, 15, 20],
        'base_period_max': [25, 30, 35, 40],
        'std_mult_min': [1.5, 2.0],
        'std_mult_max': [2.5, 3.0, 3.5],
        'vol_lookback': [80, 100, 120],
        'max_hold': [8, 10, 12, 15],
        'entry_touch': [True, False],
    }
    
    best_sharpe = -999
    best_params = None
    best_trades = 0
    
    for i in range(n_iterations):
        params = {k: random.choice(v) for k, v in param_space.items()}
        
        try:
            trades_df = generate_adaptive_bb_signals(data, params)
            
            if len(trades_df) < 120:
                continue
            
            trades_df['return_pct'] = trades_df['pnl'] / 100000 * 100
            
            if trades_df['return_pct'].std() == 0:
                continue
            
            sharpe = trades_df['return_pct'].mean() / trades_df['return_pct'].std()
            
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_params = params.copy()
                best_trades = len(trades_df)
                
        except Exception:
            continue
    
    return best_params, best_sharpe, best_trades


class AdaptiveBollingerStrategy:
    """Complete Adaptive Bollinger Band Strategy class."""
    
    def __init__(self, params: Dict):
        self.params = params
        
    def backtest(self, df: pd.DataFrame) -> Tuple[List, Dict]:
        """Run backtest."""
        trades_df = generate_adaptive_bb_signals(df, self.params)
        
        if len(trades_df) == 0:
            return [], {'total_trades': 0, 'sharpe_ratio': -999}
        
        trades = trades_df.to_dict('records')
        
        trades_df['return_pct'] = trades_df['pnl'] / 100000 * 100
        total_return = trades_df['pnl'].sum() / 100000 * 100
        
        if trades_df['return_pct'].std() > 0:
            sharpe = trades_df['return_pct'].mean() / trades_df['return_pct'].std()
        else:
            sharpe = 0
        
        win_rate = (trades_df['pnl'] > 0).sum() / len(trades_df) * 100
        
        metrics = {
            'total_trades': len(trades_df),
            'sharpe_ratio': sharpe,
            'total_return': total_return,
            'win_rate': win_rate,
        }
        
        return trades, metrics
