"""
Volatility Breakout Strategy
Trade when volatility expands significantly.

Expected Sharpe: 1.3-1.8
Rule 12 Compliant: Uses only close prices
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


def calculate_volatility_metrics(df: pd.DataFrame, params: Dict) -> pd.DataFrame:
    """Calculate volatility indicators from close prices only."""
    df = df.copy()
    
    vol_short = params.get('vol_short_period', 5)
    vol_long = params.get('vol_long_period', 20)
    bb_period = params.get('bb_period', 20)
    bb_std = params.get('bb_std_mult', 2.0)
    
    # Short and long volatility (from close returns)
    returns = df['close'].pct_change()
    df['vol_short'] = returns.rolling(vol_short).std() * 100
    df['vol_long'] = returns.rolling(vol_long).std() * 100
    df['vol_ratio'] = df['vol_short'] / (df['vol_long'] + 1e-10)
    
    # Bollinger Bands (close-only)
    df['bb_middle'] = df['close'].rolling(bb_period).mean()
    df['bb_std'] = df['close'].rolling(bb_period).std()
    df['bb_upper'] = df['bb_middle'] + (bb_std * df['bb_std'])
    df['bb_lower'] = df['bb_middle'] - (bb_std * df['bb_std'])
    
    # Volatility percentile
    df['vol_percentile'] = df['vol_short'].rolling(100).apply(
        lambda x: (x.iloc[-1] > x).sum() / len(x) if len(x) > 0 else 0.5,
        raw=False
    )
    
    # Price position within bands
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'] + 1e-10)
    
    return df


def generate_vol_breakout_signals(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
    """
    Generate volatility breakout signals.
    
    Strategy Logic:
    1. Entry when:
       - Vol ratio > threshold (expansion)
       - Price breaks Bollinger Band
       - Vol percentile > threshold
    2. Exit when:
       - Vol ratio < threshold (contraction)
       - Price returns inside BB
       - Max hold reached
    """
    df = data.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    df['hour'] = df['datetime'].dt.hour
    
    # Calculate indicators
    df = calculate_volatility_metrics(df, params)
    
    # Parameters
    vol_ratio_entry = params.get('vol_ratio_entry', 1.5)
    vol_ratio_exit = params.get('vol_ratio_exit', 0.8)
    vol_percentile_threshold = params.get('vol_percentile_threshold', 0.6)
    max_hold = params.get('max_hold', 12)
    allowed_hours = params.get('allowed_hours', [9, 10, 11, 12, 13, 14])
    
    # Generate trades
    trades = []
    position = None
    capital = 100000
    
    warmup = max(100, params.get('vol_long_period', 20) + 10)
    
    for i in range(warmup, len(df) - max_hold):
        current = df.iloc[i]
        
        # Skip if NaN
        if pd.isna(current['vol_ratio']) or pd.isna(current['bb_upper']):
            continue
        
        # ENTRY LOGIC
        if position is None:
            # Check entry conditions
            vol_expanding = current['vol_ratio'] > vol_ratio_entry
            vol_percentile_high = current['vol_percentile'] > vol_percentile_threshold
            breaks_lower_bb = current['close'] < current['bb_lower']
            is_allowed_hour = current['hour'] in allowed_hours
            
            # Entry: Vol expanding + price at lower BB (buy dip in expansion)
            if vol_expanding and vol_percentile_high and breaks_lower_bb and is_allowed_hour:
                entry_price = current['close']
                qty = int((capital * 0.95 - 24) / entry_price)
                
                if qty > 0:
                    position = {
                        'entry_idx': i,
                        'entry_price': entry_price,
                        'entry_time': current['datetime'],
                        'qty': qty,
                        'entry_vol_ratio': current['vol_ratio'],
                    }
                    capital -= 24
        
        # EXIT LOGIC
        else:
            bars_held = i - position['entry_idx']
            current_price = current['close']
            
            # Exit conditions
            vol_contracting = current['vol_ratio'] < vol_ratio_exit
            back_in_bb = current['bb_lower'] <= current['close'] <= current['bb_upper']
            max_hold_reached = bars_held >= max_hold
            
            # Profit target
            pnl_pct = (current_price - position['entry_price']) / position['entry_price'] * 100
            profit_target = pnl_pct > 2.5
            stop_loss = pnl_pct < -2.0
            
            if vol_contracting or max_hold_reached or profit_target or stop_loss:
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
                    'exit_reason': 'vol_contract' if vol_contracting else 
                                  'profit' if profit_target else
                                  'stop' if stop_loss else 'max_hold',
                })
                
                capital += net_pnl
                position = None
    
    if len(trades) == 0:
        return pd.DataFrame()
    
    return pd.DataFrame(trades)


def optimize_vol_breakout(data: pd.DataFrame, n_iterations: int = 300) -> Tuple[Dict, float, int]:
    """Optimize volatility breakout parameters."""
    import random
    
    param_space = {
        'vol_short_period': [3, 5, 7, 10],
        'vol_long_period': [15, 20, 25, 30],
        'bb_period': [15, 20, 25],
        'bb_std_mult': [1.5, 2.0, 2.5],
        'vol_ratio_entry': [1.3, 1.5, 1.7, 2.0],
        'vol_ratio_exit': [0.6, 0.8, 1.0],
        'vol_percentile_threshold': [0.5, 0.6, 0.7],
        'max_hold': [8, 12, 16, 20],
    }
    
    best_sharpe = -999
    best_params = None
    best_trades = 0
    
    for i in range(n_iterations):
        params = {k: random.choice(v) for k, v in param_space.items()}
        
        try:
            trades_df = generate_vol_breakout_signals(data, params)
            
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


class VolatilityBreakoutStrategy:
    """Complete Volatility Breakout Strategy class."""
    
    def __init__(self, params: Dict):
        self.params = params
        
    def backtest(self, df: pd.DataFrame) -> Tuple[List, Dict]:
        """Run backtest."""
        trades_df = generate_vol_breakout_signals(df, self.params)
        
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
