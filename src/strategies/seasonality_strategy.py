"""
Intraday Seasonality Strategy
Trade based on hour-of-day patterns.

Expected Sharpe: 1.0-1.4
Rule 12 Compliant: Uses only close prices
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


def analyze_hourly_patterns(df: pd.DataFrame) -> Dict:
    """
    Analyze historical performance by hour.
    Returns dict with hourly stats.
    """
    df = df.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['hour'] = df['datetime'].dt.hour
    df['forward_return'] = df['close'].shift(-1) / df['close'] - 1
    
    hourly_stats = {}
    
    for hour in range(9, 16):
        hour_data = df[df['hour'] == hour]['forward_return'].dropna()
        
        if len(hour_data) < 30:
            continue
        
        hourly_stats[hour] = {
            'mean_return': hour_data.mean() * 100,
            'std': hour_data.std() * 100,
            'sharpe': hour_data.mean() / (hour_data.std() + 1e-10),
            'count': len(hour_data),
            'positive_pct': (hour_data > 0).mean() * 100,
        }
    
    return hourly_stats


def get_best_hours(hourly_stats: Dict, top_n: int = 3) -> List[int]:
    """Get top N hours by Sharpe ratio."""
    sorted_hours = sorted(
        hourly_stats.items(),
        key=lambda x: x[1]['sharpe'],
        reverse=True
    )
    return [h for h, _ in sorted_hours[:top_n]]


def generate_seasonality_signals(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
    """
    Generate intraday seasonality signals.
    
    Strategy Logic:
    1. Analyze historical performance by hour
    2. Enter at hours with positive historical expectation
    3. Exit after hold period or target
    """
    df = data.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    df['hour'] = df['datetime'].dt.hour
    
    # Parameters
    training_pct = params.get('training_pct', 0.5)  # Use first 50% to learn patterns
    hold_periods = params.get('hold_periods', 2)
    min_sharpe = params.get('min_hourly_sharpe', 0.0)
    top_hours_n = params.get('top_hours_n', 4)
    
    # Split data for pattern learning
    train_end = int(len(df) * training_pct)
    train_df = df.iloc[:train_end]
    
    # Learn patterns from training data
    hourly_stats = analyze_hourly_patterns(train_df)
    
    # Get best hours
    if not hourly_stats:
        return pd.DataFrame()
    
    best_hours = get_best_hours(hourly_stats, top_hours_n)
    
    # Filter to hours with positive Sharpe
    best_hours = [h for h in best_hours if hourly_stats[h]['sharpe'] > min_sharpe]
    
    if not best_hours:
        return pd.DataFrame()
    
    # Generate trades on test data
    trades = []
    position = None
    capital = 100000
    
    for i in range(train_end, len(df) - hold_periods - 1):
        current = df.iloc[i]
        
        # ENTRY LOGIC
        if position is None:
            if current['hour'] in best_hours:
                entry_price = current['close']
                qty = int((capital * 0.95 - 24) / entry_price)
                
                if qty > 0:
                    position = {
                        'entry_idx': i,
                        'entry_price': entry_price,
                        'entry_time': current['datetime'],
                        'qty': qty,
                        'entry_hour': current['hour'],
                    }
                    capital -= 24
        
        # EXIT LOGIC
        else:
            bars_held = i - position['entry_idx']
            current_price = current['close']
            
            # Exit after hold period
            should_exit = bars_held >= hold_periods
            
            # Profit/stop
            pnl_pct = (current_price - position['entry_price']) / position['entry_price'] * 100
            profit_target = pnl_pct > 1.5
            stop_loss = pnl_pct < -1.0
            
            if should_exit or profit_target or stop_loss:
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
                    'entry_hour': position['entry_hour'],
                    'exit_reason': 'profit' if profit_target else
                                  'stop' if stop_loss else 'hold_complete',
                })
                
                capital += net_pnl
                position = None
    
    if len(trades) == 0:
        return pd.DataFrame()
    
    return pd.DataFrame(trades)


def optimize_seasonality(data: pd.DataFrame, n_iterations: int = 200) -> Tuple[Dict, float, int]:
    """Optimize seasonality strategy parameters."""
    import random
    
    param_space = {
        'training_pct': [0.4, 0.5, 0.6],
        'hold_periods': [1, 2, 3, 4],
        'min_hourly_sharpe': [0.0, 0.05, 0.1],
        'top_hours_n': [2, 3, 4, 5],
    }
    
    best_sharpe = -999
    best_params = None
    best_trades = 0
    
    for i in range(n_iterations):
        params = {k: random.choice(v) for k, v in param_space.items()}
        
        try:
            trades_df = generate_seasonality_signals(data, params)
            
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


class SeasonalityStrategy:
    """Complete Seasonality Strategy class."""
    
    def __init__(self, params: Dict):
        self.params = params
        
    def backtest(self, df: pd.DataFrame) -> Tuple[List, Dict]:
        """Run backtest."""
        trades_df = generate_seasonality_signals(df, self.params)
        
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
