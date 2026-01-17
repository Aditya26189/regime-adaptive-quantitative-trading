
"""
Ensemble Strategy: Combine multiple strategy signals with voting/weighting
"""

import pandas as pd
import numpy as np
from typing import Dict, List
import os
import json
import sys

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../'))
sys.path.insert(0, project_root)

class EnsembleStrategy:
    """
    Combine multiple strategies:
    1. Trend-following
    2. Mean-reversion
    3. Volatility-adaptive
    
    Entry: Vote (2/3 agree) or weighted combination
    Exit: Any strategy triggers
    """
    
    def __init__(self, params):
        self.params = params
        self.min_agreement = params.get('min_agreement', 2)  # Out of 3
    
    def generate_signals(self, df):
        """Generate signals from 3 sub-strategies and combine"""
        df = df.copy()
        
        # Calculate indicators
        df['RSI'] = self.calculate_rsi(df['close'], period=2)
        df['ema_fast'] = df['close'].ewm(span=8, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=21, adjust=False).mean()
        
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(14).std() * 100
        
        # Strategy 1: Mean Reversion
        df['signal_meanrev'] = (df['RSI'].shift(1) < 30) & (df['volatility'] > 0.005)
        
        # Strategy 2: Trend Following
        df['trend_up'] = df['ema_fast'] > df['ema_slow']
        df['momentum'] = (df['close'] > df['ema_fast'] * 1.003)
        df['signal_trend'] = df['trend_up'] & df['momentum']
        
        # Strategy 3: Volatility Breakout
        vol_sma = df['volatility'].rolling(20).mean()
        df['vol_breakout'] = df['volatility'] > (vol_sma * 1.5)
        # Using rolling max efficiently
        rolling_max = df['close'].rolling(10).max().shift(1)
        price_breakout = df['close'] > rolling_max
        df['signal_volbreakout'] = df['vol_breakout'] & price_breakout
        
        # Combine signals (voting)
        df['vote_count'] = (
            df['signal_meanrev'].astype(int) +
            df['signal_trend'].astype(int) +
            df['signal_volbreakout'].astype(int)
        )
        
        df['signal_long'] = df['vote_count'] >= self.min_agreement
        
        # Time filter
        df['hour'] = pd.to_datetime(df['datetime']).dt.hour
        allowed_hours = self.params.get('allowed_hours', [10, 11, 12, 13, 14])
        df['signal_long'] = df['signal_long'] & df['hour'].isin(allowed_hours)
        
        # Track which strategies agreed
        def get_strategies(row):
            strategies = []
            if row['signal_meanrev']: strategies.append('meanrev')
            if row['signal_trend']: strategies.append('trend')
            if row['signal_volbreakout']: strategies.append('volbreak')
            return strategies
            
        df['agreeing_strategies'] = df.apply(get_strategies, axis=1)
        
        return df
    
    def backtest(self, df, initial_capital=100000):
        """Backtest ensemble strategy"""
        df = self.generate_signals(df)
        
        trades = []
        capital = initial_capital
        in_position = False
        
        entry_price = 0
        entry_time = None
        entry_qty = 0
        bars_held = 0
        entry_strategies = []
        
        fee_per_order = 24
        max_hold = self.params.get('max_hold_bars', 10)
        max_return_cap = 5.0
        
        for i in range(50, len(df)):
            current_time = df['datetime'].iloc[i]
            current_hour = pd.to_datetime(current_time).hour
            current_minute = pd.to_datetime(current_time).minute
            current_close = df['close'].iloc[i]
            current_rsi = df['RSI'].iloc[i]
            
            # ENTRY
            if not in_position:
                if df['signal_long'].iloc[i]:
                    entry_qty = int((capital - fee_per_order) * 0.95 / current_close)
                    
                    if entry_qty > 0:
                        entry_price = current_close
                        entry_time = current_time
                        capital -= fee_per_order
                        in_position = True
                        bars_held = 0
                        entry_strategies = df['agreeing_strategies'].iloc[i]
            
            # EXIT (any strategy exit trigger)
            else:
                bars_held += 1
                current_return_pct = ((current_close - entry_price) / entry_price) * 100
                
                # Exit triggers from different strategies
                meanrev_exit = current_rsi > 70
                trend_exit = current_close < df['ema_fast'].iloc[i]
                time_exit = bars_held >= max_hold
                outlier_exit = current_return_pct >= max_return_cap
                eod_exit = (current_hour >= 15 and current_minute >= 15)
                
                if meanrev_exit or trend_exit or time_exit or outlier_exit or eod_exit:
                    exit_price = current_close
                    gross_pnl = entry_qty * (exit_price - entry_price)
                    net_pnl = gross_pnl - (2 * fee_per_order)
                    capital += (entry_qty * exit_price) - fee_per_order
                    
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'qty': entry_qty,
                        'pnl': net_pnl,
                        'capital': capital,
                        'bars_held': bars_held,
                        'return_pct': current_return_pct,
                        'entry_strategies': ','.join(entry_strategies),
                        'vote_count': len(entry_strategies),
                    })
                    
                    in_position = False
        
        metrics = self.calculate_metrics(trades, initial_capital, capital)
        return trades, metrics
    
    def calculate_rsi(self, close, period=2):
        """Calculate RSI"""
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)
    
    def calculate_metrics(self, trades, initial_capital, final_capital):
        """Calculate metrics"""
        if len(trades) == 0:
            return {
                'total_trades': 0,
                'sharpe_ratio': 0,
                'total_return_pct': 0,
                'win_rate': 0,
                'max_drawdown_pct': 0,
                'final_capital': final_capital
            }
        
        trades_df = pd.DataFrame(trades)
        
        total_trades = len(trades_df)
        total_return_pct = (final_capital - initial_capital) / initial_capital * 100
        
        wins = (trades_df['pnl'] > 0).sum()
        win_rate = (wins / total_trades) * 100
        
        returns = (trades_df['pnl'] / initial_capital) * 100
        if returns.std() > 0:
            trades_per_year = 1500 / (len(trades_df) / 250) if len(trades_df) > 0 else 1
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(min(trades_per_year, 252))
        else:
            sharpe_ratio = 0
        
        capital_curve = trades_df['capital'].values
        running_max = np.maximum.accumulate(capital_curve)
        drawdown = (capital_curve - running_max) / running_max * 100
        max_drawdown_pct = drawdown.min()
        
        return {
            'total_trades': total_trades,
            'sharpe_ratio': sharpe_ratio,
            'total_return_pct': total_return_pct,
            'win_rate': win_rate,
            'max_drawdown_pct': max_drawdown_pct,
            'final_capital': final_capital,
            'avg_trade_pnl': trades_df['pnl'].mean(),
        }


# TESTING SCRIPT
def test_ensemble_strategy():
    """Test ensemble strategy on VBL"""
    
    print("\n" + "="*70)
    print("ENSEMBLE STRATEGY TEST: VBL")
    print("="*70)
    
    filepath = 'data/raw/NSE_VBL_EQ_1hour.csv'
    full_path = os.path.join(project_root, filepath)
    if not os.path.exists(full_path):
         full_path = full_path.replace('data/raw/', 'data/')
            
    df = pd.read_csv(full_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    # Test different voting thresholds
    voting_configs = [
        {'min_agreement': 1, 'max_hold_bars': 10, 'allowed_hours': [10, 11, 12, 13, 14]},  # Any 1/3
        {'min_agreement': 2, 'max_hold_bars': 10, 'allowed_hours': [10, 11, 12, 13, 14]},  # 2/3 majority
        {'min_agreement': 3, 'max_hold_bars': 10, 'allowed_hours': [10, 11, 12, 13, 14]},  # All 3 unanimous
    ]
    
    results = []
    
    for config in voting_configs:
        print(f"\n🗳️  Testing: {config['min_agreement']}/3 agreement required")
        
        strategy = EnsembleStrategy(config)
        trades, metrics = strategy.backtest(df)
        
        print(f"  Trades: {metrics['total_trades']}")
        print(f"  Sharpe: {metrics['sharpe_ratio']:.3f}")
        print(f"  Return: {metrics['total_return_pct']:.2f}%")
        print(f"  Win Rate: {metrics['win_rate']:.1f}%")
        
        results.append({
            'config': config,
            'metrics': metrics
        })
    
    # Find best
    valid = [r for r in results if r['metrics']['total_trades'] >= 120]
    
    if valid:
        best = max(valid, key=lambda x: x['metrics']['sharpe_ratio'])
        
        print(f"\n✅ BEST ENSEMBLE CONFIG:")
        print(f"  Agreement: {best['config']['min_agreement']}/3")
        print(f"  Sharpe: {best['metrics']['sharpe_ratio']:.3f}")
        print(f"  Trades: {best['metrics']['total_trades']}")
        
        # Save
        output_dir = os.path.join(project_root, 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        with open(os.path.join(output_dir, 'phase2_ensemble.json'), 'w') as f:
            json.dump({
                'sharpe': best['metrics']['sharpe_ratio'],
                'trades': best['metrics']['total_trades'],
                'config': best['config'],
                'return_pct': best['metrics']['total_return_pct']
            }, f, indent=2)
        
        print("\n✅ Results saved to: output/phase2_ensemble.json")
        
        return best
    else:
        print("\n❌ NO VALID ENSEMBLE CONFIGS")
        return None

if __name__ == "__main__":
    ensemble_result = test_ensemble_strategy()
