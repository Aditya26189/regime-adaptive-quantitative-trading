
"""
Multi-Regime Strategy: Detect volatility regime and switch parameters dynamically
Based on 2024 RegimeFolio research
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import os
import json
import sys

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../'))
sys.path.insert(0, project_root)

class RegimeSwitchingStrategy:
    """
    Detect volatility regime (LOW/MED/HIGH) and adapt strategy parameters
    """
    
    def __init__(self, base_params):
        self.base_params = base_params
        
        # Define regime-specific parameter adjustments
        self.regime_params = {
            'HIGH_VOL': {
                'rsi_entry': 20,      # More extreme (avoid noise)
                'rsi_exit': 80,
                'max_hold_bars': 6,   # Exit faster
                'vol_min_pct': 0.008, # Higher filter
                'position_size': 0.70, # Reduce size (higher risk)
            },
            'MEDIUM_VOL': {
                'rsi_entry': 28,
                'rsi_exit': 72,
                'max_hold_bars': 10,
                'vol_min_pct': 0.005,
                'position_size': 0.90,
            },
            'LOW_VOL': {
                'rsi_entry': 35,      # Tighter (fewer reversions)
                'rsi_exit': 65,
                'max_hold_bars': 14,  # Can hold longer
                'vol_min_pct': 0.003, # Lower filter
                'position_size': 0.95, # Full size (lower risk)
            }
        }
    
    def detect_regime(self, df, window=60):
        """
        Classify current regime based on volatility percentile
        
        Returns df with 'regime' column: HIGH_VOL, MEDIUM_VOL, LOW_VOL
        """
        df = df.copy()
        
        # Calculate rolling volatility
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(14).std() * 100
        
        # Calculate volatility percentile over rolling window
        def calculate_vol_percentile(vol_series, current_vol):
            if len(vol_series) < 2 or pd.isna(current_vol):
                return 50
            from scipy.stats import percentileofscore
            return percentileofscore(vol_series, current_vol)
        
        # Optimize: Avoid loop if possible, or use simple ranking
        # Rolling rank is faster
        df['vol_percentile'] = df['volatility'].rolling(window).rank(pct=True) * 100
        df['vol_percentile'] = df['vol_percentile'].fillna(50)
        
        # Classify regime
        def classify_regime(percentile):
            if pd.isna(percentile):
                return 'MEDIUM_VOL'
            elif percentile >= 66:
                return 'HIGH_VOL'
            elif percentile >= 33:
                return 'MEDIUM_VOL'
            else:
                return 'LOW_VOL'
        
        df['regime'] = df['vol_percentile'].apply(classify_regime)
        
        return df
    
    def generate_signals(self, df):
        """Generate signals with regime-specific parameters"""
        df = self.detect_regime(df, window=60)
        
        # Calculate RSI
        rsi_period = self.base_params.get('rsi_period', 2)
        df['RSI'] = self.calculate_rsi(df['close'], period=rsi_period)
        
        # Get regime-specific thresholds
        df['rsi_entry_threshold'] = df['regime'].map({
            'HIGH_VOL': self.regime_params['HIGH_VOL']['rsi_entry'],
            'MEDIUM_VOL': self.regime_params['MEDIUM_VOL']['rsi_entry'],
            'LOW_VOL': self.regime_params['LOW_VOL']['rsi_entry'],
        })
        
        df['rsi_exit_threshold'] = df['regime'].map({
            'HIGH_VOL': self.regime_params['HIGH_VOL']['rsi_exit'],
            'MEDIUM_VOL': self.regime_params['MEDIUM_VOL']['rsi_exit'],
            'LOW_VOL': self.regime_params['LOW_VOL']['rsi_exit'],
        })
        
        df['max_hold_regime'] = df['regime'].map({
            'HIGH_VOL': self.regime_params['HIGH_VOL']['max_hold_bars'],
            'MEDIUM_VOL': self.regime_params['MEDIUM_VOL']['max_hold_bars'],
            'LOW_VOL': self.regime_params['LOW_VOL']['max_hold_bars'],
        })
        
        df['position_size_regime'] = df['regime'].map({
            'HIGH_VOL': self.regime_params['HIGH_VOL']['position_size'],
            'MEDIUM_VOL': self.regime_params['MEDIUM_VOL']['position_size'],
            'LOW_VOL': self.regime_params['LOW_VOL']['position_size'],
        })
        
        # Entry signal
        df['signal_long'] = (
            (df['RSI'].shift(1) < df['rsi_entry_threshold'].shift(1)) &
            (df['volatility'] > 0.003)
        )
        
        # Time filter
        df['hour'] = pd.to_datetime(df['datetime']).dt.hour
        allowed_hours = self.base_params.get('allowed_hours', [10, 11, 12, 13, 14])
        df['signal_long'] = df['signal_long'] & df['hour'].isin(allowed_hours)
        
        return df
    
    def backtest(self, df, initial_capital=100000):
        """Backtest with regime-adaptive exits"""
        df = self.generate_signals(df)
        
        trades = []
        capital = initial_capital
        in_position = False
        
        entry_price = 0
        entry_time = None
        entry_qty = 0
        bars_held = 0
        entry_max_hold = 10
        entry_rsi_exit = 70
        
        fee_per_order = 24
        max_return_cap = 5.0
        
        for i in range(50, len(df)):
            current_time = df['datetime'].iloc[i]
            current_hour = pd.to_datetime(current_time).hour
            current_minute = pd.to_datetime(current_time).minute
            current_close = df['close'].iloc[i]
            current_rsi = df['RSI'].iloc[i]
            
            # ENTRY with regime-based position sizing
            if not in_position:
                if df['signal_long'].iloc[i]:
                    position_fraction = df['position_size_regime'].iloc[i]
                    entry_qty = int((capital - fee_per_order) * position_fraction / current_close)
                    
                    if entry_qty > 0:
                        entry_price = current_close
                        entry_time = current_time
                        capital -= fee_per_order
                        in_position = True
                        bars_held = 0
                        
                        # Lock in regime parameters at entry
                        entry_max_hold = int(df['max_hold_regime'].iloc[i])
                        entry_rsi_exit = df['rsi_exit_threshold'].iloc[i]
            
            # EXIT with regime-adaptive thresholds
            else:
                bars_held += 1
                current_return_pct = ((current_close - entry_price) / entry_price) * 100
                
                rsi_target = current_rsi > entry_rsi_exit
                time_exit = bars_held >= entry_max_hold
                outlier_cap = current_return_pct >= max_return_cap
                eod_exit = (current_hour >= 15 and current_minute >= 15)
                
                if rsi_target or time_exit or outlier_cap or eod_exit:
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
                        'entry_regime': df['regime'].iloc[i-bars_held],
                    })
                    
                    in_position = False
        
        metrics = self.calculate_metrics(trades, initial_capital, capital)
        
        # Add regime breakdown
        if len(trades) > 0:
            trades_df = pd.DataFrame(trades)
            regime_stats = trades_df.groupby('entry_regime').agg({
                'pnl': ['count', 'mean', 'sum'],
                'return_pct': 'mean'
            })
            metrics['regime_breakdown'] = regime_stats.to_dict()
        
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
def test_regime_switching():
    """Test regime-switching on all mean-reverting symbols"""
    
    symbols = {
        'YESBANK': 'data/raw/NSE_YESBANK_EQ_1hour.csv',
        'RELIANCE': 'data/raw/NSE_RELIANCE_EQ_1hour.csv',
        'VBL': 'data/raw/NSE_VBL_EQ_1hour.csv',
    }
    
    results = {}
    
    for symbol, filepath in symbols.items():
        print("\n" + "="*70)
        print(f"REGIME SWITCHING TEST: {symbol}")
        print("="*70)
        
        full_path = os.path.join(project_root, filepath)
        if not os.path.exists(full_path):
             full_path = full_path.replace('data/raw/', 'data/')
        
        df = pd.read_csv(full_path)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        
        base_params = {
            'rsi_period': 2,
            'allowed_hours': [10, 11, 12, 13, 14]
        }
        
        # Test regime-switching
        strategy = RegimeSwitchingStrategy(base_params)
        trades, metrics = strategy.backtest(df)
        
        print(f"\n✅ REGIME-SWITCHING RESULTS:")
        print(f"  Trades: {metrics['total_trades']}")
        print(f"  Sharpe: {metrics['sharpe_ratio']:.3f}")
        print(f"  Return: {metrics['total_return_pct']:.2f}%")
        print(f"  Win Rate: {metrics['win_rate']:.1f}%")
        
        if 'regime_breakdown' in metrics:
            print(f"\n📊 REGIME BREAKDOWN:")
            for regime, stats in metrics['regime_breakdown'].items():
                print(f"  {regime}: {stats}")
        
        results[symbol] = {
            'sharpe': metrics['sharpe_ratio'],
            'trades': metrics['total_trades'],
            'return_pct': metrics['total_return_pct'],
            'metrics': metrics
        }
    
    # Save results
    output_dir = os.path.join(project_root, 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    save_data = {}
    for symbol, result in results.items():
        save_data[symbol] = {
            'sharpe': result['sharpe'],
            'trades': result['trades'],
            'return_pct': result['return_pct']
        }
    
    with open(os.path.join(output_dir, 'phase2_regime_switching.json'), 'w') as f:
        json.dump(save_data, f, indent=2)
    
    print("\n✅ Results saved to: output/phase2_regime_switching.json")
    
    return results

if __name__ == "__main__":
    test_regime_switching()
