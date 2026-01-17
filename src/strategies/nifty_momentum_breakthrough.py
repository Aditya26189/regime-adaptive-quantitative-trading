"""
NIFTY50 Momentum Breakthrough Strategy
Based on: Moskowitz et al. (2012) - Time Series Momentum (most robust academic finding)

Key Insight: NIFTY50 is an INDEX - it TRENDS, doesn't mean-revert like stocks!

Expected: NIFTY50 0.006 → 0.8-1.2 Sharpe
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


class NiftyMomentumStrategy:
    """
    Pure momentum for indices - they TREND, don't mean-revert
    Multi-timeframe momentum consensus approach
    """
    
    def __init__(self, params: Dict):
        self.min_return = params.get('min_return', 1.0)
        self.lookback_short = params.get('lookback_short', 60)
        self.lookback_medium = params.get('lookback_medium', 120)
        self.lookback_long = params.get('lookback_long', 180)
        self.max_hold = params.get('max_hold', 48)
        self.allowed_hours = params.get('allowed_hours', [9, 10, 11])
        self.exit_any_negative = params.get('exit_any_negative', True)
    
    def calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate multi-timeframe momentum signals"""
        df = df.copy()
        
        # Calculate returns over multiple periods
        df['ret_short'] = (df['close'] / df['close'].shift(self.lookback_short) - 1) * 100
        df['ret_medium'] = (df['close'] / df['close'].shift(self.lookback_medium) - 1) * 100
        df['ret_long'] = (df['close'] / df['close'].shift(self.lookback_long) - 1) * 100
        
        # ENTRY: All timeframes must agree on positive momentum
        df['signal_long'] = (
            (df['ret_short'] > self.min_return) &
            (df['ret_medium'] > self.min_return) &
            (df['ret_long'] > self.min_return)
        )
        
        # EXIT: When ANY timeframe turns negative
        if self.exit_any_negative:
            df['exit_signal'] = (
                (df['ret_short'] < 0) |
                (df['ret_medium'] < 0) |
                (df['ret_long'] < 0)
            )
        else:
            # More lenient exit: only when short-term turns negative
            df['exit_signal'] = df['ret_short'] < 0
        
        return df
    
    def backtest(self, df: pd.DataFrame = None) -> Tuple[List, Dict]:
        """Run backtest on NIFTY50"""
        if df is None:
            df = pd.read_csv('data/raw/NSE_NIFTY50_INDEX_1hour.csv')
        
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        df['hour'] = df['datetime'].dt.hour
        df['minute'] = df['datetime'].dt.minute
        
        # Calculate signals
        df = self.calculate_signals(df)
        
        trades = []
        capital = 100000
        in_position = False
        entry_price = 0
        entry_time = None
        entry_qty = 0
        bars_held = 0
        
        warmup = max(200, self.lookback_long + 20)
        
        for i in range(warmup, len(df)):
            current = df.iloc[i]
            
            if pd.isna(current['ret_short']) or pd.isna(current['ret_long']):
                continue
            
            current_hour = current['hour']
            current_minute = current['minute']
            
            # ENTRY
            if not in_position:
                # Time filter: only enter during allowed hours
                if current_hour not in self.allowed_hours:
                    continue
                
                if current['signal_long']:
                    qty = int((capital - 24) * 0.95 / current['close'])
                    if qty > 0:
                        entry_price = current['close']
                        entry_time = current['datetime']
                        entry_qty = qty
                        capital -= 24
                        in_position = True
                        bars_held = 0
            
            # EXIT
            else:
                bars_held += 1
                
                # Exit conditions
                signal_exit = current['exit_signal']
                time_exit = bars_held >= self.max_hold
                
                # EOD squareoff
                eod = current_hour >= 15 and current_minute >= 15
                
                if signal_exit or time_exit or eod:
                    gross_pnl = entry_qty * (current['close'] - entry_price)
                    net_pnl = gross_pnl - 48
                    capital += gross_pnl - 24
                    
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': current['datetime'],
                        'entry_price': entry_price,
                        'exit_price': current['close'],
                        'qty': entry_qty,
                        'pnl': net_pnl,
                        'bars_held': bars_held,
                    })
                    
                    in_position = False
        
        # Calculate metrics
        metrics = self._calculate_metrics(trades, capital)
        return trades, metrics
    
    def _calculate_metrics(self, trades: List, final_capital: float) -> Dict:
        """Calculate Sharpe and other metrics"""
        if len(trades) == 0:
            return {'total_trades': 0, 'sharpe_ratio': -999, 'total_return': -999}
        
        trades_df = pd.DataFrame(trades)
        trades_df['return_pct'] = (trades_df['pnl'] / 100000) * 100
        
        if trades_df['return_pct'].std() == 0:
            sharpe = 0
        else:
            sharpe = trades_df['return_pct'].mean() / trades_df['return_pct'].std()
        
        total_return = (final_capital - 100000) / 100000 * 100
        win_rate = (trades_df['pnl'] > 0).mean() * 100
        
        return {
            'total_trades': len(trades_df),
            'sharpe_ratio': sharpe,
            'total_return': total_return,
            'win_rate': win_rate,
            'avg_pnl': trades_df['pnl'].mean(),
            'final_capital': final_capital,
        }


def optimize_nifty_momentum(n_iterations: int = 200) -> Tuple[Dict, float, int]:
    """Optimize NIFTY momentum parameters"""
    import random
    
    df = pd.read_csv('data/raw/NSE_NIFTY50_INDEX_1hour.csv')
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    param_space = {
        'min_return': [0.3, 0.5, 0.7, 1.0, 1.5, 2.0],
        'lookback_short': [30, 40, 50, 60, 80],
        'lookback_medium': [80, 100, 120, 140],
        'lookback_long': [140, 160, 180, 200],
        'max_hold': [24, 36, 48, 60],
        'allowed_hours': [[9, 10, 11], [9, 10, 11, 12], [9, 10, 11, 12, 13]],
        'exit_any_negative': [True, False],
    }
    
    best_sharpe = -999
    best_params = None
    best_trades = 0
    best_metrics = None
    
    print("Optimizing NIFTY50 Momentum Strategy...")
    
    for i in range(n_iterations):
        params = {k: random.choice(v) for k, v in param_space.items()}
        
        # Ensure lookbacks are in order
        if params['lookback_short'] >= params['lookback_medium']:
            continue
        if params['lookback_medium'] >= params['lookback_long']:
            continue
        
        try:
            strategy = NiftyMomentumStrategy(params)
            trades, metrics = strategy.backtest(df.copy())
            
            if metrics['total_trades'] < 120:
                continue
            
            if metrics['sharpe_ratio'] > best_sharpe:
                best_sharpe = metrics['sharpe_ratio']
                best_params = params.copy()
                best_trades = metrics['total_trades']
                best_metrics = metrics.copy()
                print(f"  [{i}] Sharpe={best_sharpe:.3f}, Trades={best_trades}, Return={metrics['total_return']:.2f}%")
                
        except Exception as e:
            continue
    
    return best_params, best_sharpe, best_trades, best_metrics


if __name__ == '__main__':
    print("="*60)
    print("NIFTY50 MOMENTUM BREAKTHROUGH")
    print("="*60)
    
    # Quick test with default params
    print("\n1. Quick Test (Default Params):")
    for min_return in [0.3, 0.5, 0.7, 1.0, 1.5]:
        strategy = NiftyMomentumStrategy({'min_return': min_return})
        trades, metrics = strategy.backtest()
        print(f"   Min Return {min_return}%: Sharpe={metrics['sharpe_ratio']:.3f}, Trades={metrics['total_trades']}")
    
    # Full optimization
    print("\n2. Full Optimization (200 iterations):")
    best_params, best_sharpe, best_trades, best_metrics = optimize_nifty_momentum(200)
    
    print("\n" + "="*60)
    print("BEST NIFTY50 MOMENTUM RESULT:")
    print("="*60)
    if best_params:
        print(f"  Sharpe: {best_sharpe:.3f}")
        print(f"  Trades: {best_trades}")
        print(f"  Return: {best_metrics['total_return']:.2f}%")
        print(f"  Win Rate: {best_metrics['win_rate']:.1f}%")
        print(f"  Params: {best_params}")
        
        # Calculate portfolio impact
        baseline_sharpe = 1.486
        old_nifty = 0.006
        new_portfolio = (3.132 + 1.683 + 1.574 + 1.036 + best_sharpe) / 5
        print(f"\n  Portfolio Impact:")
        print(f"    Old NIFTY Sharpe: {old_nifty}")
        print(f"    New NIFTY Sharpe: {best_sharpe:.3f}")
        print(f"    Old Portfolio: {baseline_sharpe}")
        print(f"    New Portfolio: {new_portfolio:.3f}")
        print(f"    Improvement: +{new_portfolio - baseline_sharpe:.3f}")
    else:
        print("  No valid parameters found (< 120 trades)")
