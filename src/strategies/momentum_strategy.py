"""
Time Series Momentum Strategy
Multi-period momentum with consensus requirement.

Academic Foundation: Moskowitz, Ooi, Pedersen (2012)
Expected Sharpe: 1.2-1.6
Rule 12 Compliant: Uses only close prices
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


def calculate_momentum_indicators(df: pd.DataFrame, params: Dict) -> pd.DataFrame:
    """Calculate multi-period momentum indicators."""
    df = df.copy()
    
    lookback_short = params.get('lookback_short', 60)
    lookback_medium = params.get('lookback_medium', 120)
    lookback_long = params.get('lookback_long', 180)
    
    # Calculate returns over multiple periods
    lookbacks = [lookback_short, lookback_medium, lookback_long]
    
    for lb in lookbacks:
        df[f'momentum_{lb}h'] = (df['close'] / df['close'].shift(lb) - 1) * 100
        df[f'momentum_{lb}h_sign'] = np.sign(df[f'momentum_{lb}h'])
    
    # Count agreement (how many periods agree on direction)
    df['momentum_agree'] = (
        df[f'momentum_{lookback_short}h_sign'] + 
        df[f'momentum_{lookback_medium}h_sign'] + 
        df[f'momentum_{lookback_long}h_sign']
    )
    
    # Average momentum strength
    df['momentum_strength'] = (
        df[f'momentum_{lookback_short}h'].abs() + 
        df[f'momentum_{lookback_medium}h'].abs() + 
        df[f'momentum_{lookback_long}h'].abs()
    ) / 3
    
    # Average momentum (signed)
    df['momentum_avg'] = (
        df[f'momentum_{lookback_short}h'] + 
        df[f'momentum_{lookback_medium}h'] + 
        df[f'momentum_{lookback_long}h']
    ) / 3
    
    return df


def generate_momentum_signals(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
    """
    Generate time series momentum signals.
    
    Strategy Logic:
    1. Calculate returns over multiple lookback periods
    2. Enter when all periods agree on direction
    3. Position size proportional to momentum strength
    4. Exit when momentum reverses or weakens
    """
    df = data.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    df['hour'] = df['datetime'].dt.hour
    
    # Calculate momentum
    df = calculate_momentum_indicators(df, params)
    
    # Parameters
    min_agreement = params.get('min_agreement', 3)
    min_strength = params.get('min_strength_pct', 2.0)
    max_hold = params.get('max_hold', 24)
    allowed_hours = params.get('allowed_hours', [9, 10, 11, 12, 13, 14])
    
    # Generate trades
    trades = []
    position = None
    capital = 100000
    
    lookback_max = max(params.get('lookback_long', 180), 200)
    
    for i in range(lookback_max, len(df) - max_hold):
        current = df.iloc[i]
        
        if pd.isna(current['momentum_agree']):
            continue
        
        # ENTRY LOGIC
        if position is None:
            # All periods agree on positive momentum
            strong_positive = (current['momentum_agree'] >= min_agreement and 
                              current['momentum_strength'] >= min_strength)
            is_allowed_hour = current['hour'] in allowed_hours
            
            if strong_positive and is_allowed_hour:
                entry_price = current['close']
                qty = int((capital * 0.95 - 24) / entry_price)
                
                if qty > 0:
                    position = {
                        'entry_idx': i,
                        'entry_price': entry_price,
                        'entry_time': current['datetime'],
                        'qty': qty,
                        'entry_momentum': current['momentum_avg'],
                    }
                    capital -= 24
        
        # EXIT LOGIC
        else:
            bars_held = i - position['entry_idx']
            current_price = current['close']
            
            # Exit conditions
            momentum_reversed = current['momentum_agree'] < 0
            momentum_weakened = current['momentum_avg'] < position['entry_momentum'] * 0.3
            max_hold_reached = bars_held >= max_hold
            
            # Profit/Loss limits
            pnl_pct = (current_price - position['entry_price']) / position['entry_price'] * 100
            profit_target = pnl_pct > 3.0
            stop_loss = pnl_pct < -2.0
            
            if momentum_reversed or momentum_weakened or max_hold_reached or profit_target or stop_loss:
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
                    'exit_reason': 'reversed' if momentum_reversed else
                                  'weakened' if momentum_weakened else
                                  'profit' if profit_target else
                                  'stop' if stop_loss else 'max_hold',
                })
                
                capital += net_pnl
                position = None
    
    if len(trades) == 0:
        return pd.DataFrame()
    
    return pd.DataFrame(trades)


def optimize_momentum(data: pd.DataFrame, n_iterations: int = 300) -> Tuple[Dict, float, int]:
    """Optimize momentum strategy parameters."""
    import random
    
    param_space = {
        'lookback_short': [40, 50, 60, 80],
        'lookback_medium': [100, 120, 140],
        'lookback_long': [160, 180, 200],
        'min_agreement': [2, 3],
        'min_strength_pct': [1.0, 1.5, 2.0, 2.5],
        'max_hold': [12, 18, 24, 36],
    }
    
    best_sharpe = -999
    best_params = None
    best_trades = 0
    
    for i in range(n_iterations):
        params = {k: random.choice(v) for k, v in param_space.items()}
        
        try:
            trades_df = generate_momentum_signals(data, params)
            
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


class TimeSeriesMomentumStrategy:
    """Complete Time Series Momentum Strategy class."""
    
    def __init__(self, params: Dict):
        self.params = params
        
    def backtest(self, df: pd.DataFrame) -> Tuple[List, Dict]:
        """Run backtest."""
        trades_df = generate_momentum_signals(df, self.params)
        
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
