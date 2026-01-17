
"""
Meta-Ensemble: Combine top 3 strategies per symbol with dynamic weighting
"""

import pandas as pd
import numpy as np
import json
import sys
import os

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../'))
sys.path.insert(0, project_root)

class MetaEnsemble:
    """
    Run multiple strategies in parallel, combine results
    """
    
    def __init__(self, symbol, strategies_list):
        """
        Args:
            symbol: Symbol name
            strategies_list: List of (strategy_class, params, weight) tuples
        """
        self.symbol = symbol
        self.strategies_list = strategies_list
    
    def backtest_weighted_ensemble(self, df, initial_capital=100000):
        """
        Backtest with weighted voting:
        """
        
        # Run all strategies
        all_signals = []
        weights = []
        
        for strategy_class, params, weight in self.strategies_list:
            strategy = strategy_class(params)
            df_signals = strategy.generate_signals(df)
            
            all_signals.append(df_signals['signal_long'])
            weights.append(weight)
        
        # Combine signals with weights
        df_combined = df.copy()
        
        weighted_votes = np.zeros(len(df))
        for signals, weight in zip(all_signals, weights):
            weighted_votes += signals.values * weight
        
        # Normalize by total weight
        total_weight = sum(weights)
        weighted_votes = weighted_votes / total_weight
        
        # Entry threshold (>50% weighted agreement)
        df_combined['signal_long'] = weighted_votes > 0.5
        
        # Time filter
        df_combined['hour'] = pd.to_datetime(df_combined['datetime']).dt.hour
        allowed_hours = [10, 11, 12, 13, 14, 15]
        df_combined['signal_long'] = df_combined['signal_long'] & df_combined['hour'].isin(allowed_hours)
        
        # Calculate RSI for exits
        df_combined['RSI'] = self.calculate_rsi(df_combined['close'], period=2)
        
        # Backtest
        trades = []
        capital = initial_capital
        in_position = False
        
        entry_price = 0
        entry_time = None
        entry_qty = 0
        bars_held = 0
        
        fee_per_order = 24
        
        for i in range(50, len(df_combined)):
            current_time = df_combined['datetime'].iloc[i]
            current_hour = pd.to_datetime(current_time).hour
            current_minute = pd.to_datetime(current_time).minute
            current_close = df_combined['close'].iloc[i]
            current_rsi = df_combined['RSI'].iloc[i]
            
            # ENTRY
            if not in_position:
                if df_combined['signal_long'].iloc[i]:
                    entry_qty = int((capital - fee_per_order) * 0.95 / current_close)
                    
                    if entry_qty > 0:
                        entry_price = current_close
                        entry_time = current_time
                        capital -= fee_per_order
                        in_position = True
                        bars_held = 0
            
            # EXIT
            else:
                bars_held += 1
                current_return_pct = ((current_close - entry_price) / entry_price) * 100
                
                # Average exit logic from all strategies
                rsi_exit = current_rsi > 70
                time_exit = bars_held >= 10
                outlier_exit = current_return_pct >= 5.0
                eod_exit = (current_hour >= 15 and current_minute >= 15)
                
                if rsi_exit or time_exit or outlier_exit or eod_exit:
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


def test_meta_ensemble():
    """Test meta-ensemble on VBL (most volatile, benefits from diversification)"""
    
    from src.strategies.hybrid_adaptive import HybridAdaptiveStrategy
    from src.strategies.vol_adaptive_rsi import VolatilityAdaptiveRSI
    from src.strategies.regime_switching_strategy import RegimeSwitchingStrategy
    
    print("\n" + "="*70)
    print("META-ENSEMBLE TEST: VBL")
    print("="*70)
    
    filepath = 'data/raw/NSE_VBL_EQ_1hour.csv'
    full_path = os.path.join(project_root, filepath)
    if not os.path.exists(full_path):
         full_path = full_path.replace('data/raw/', 'data/')
            
    df = pd.read_csv(full_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    # Define ensemble strategies with weights (based on Phase 2 performance)
    strategies_list = [
        (HybridAdaptiveStrategy, {
            'ker_period': 10,
            'rsi_period': 2,
            'rsi_entry': 30,
            'rsi_exit': 70,
            'vol_min_pct': 0.005,
            'max_hold_bars': 10,
            'allowed_hours': [10, 11, 12, 13, 14, 15],
            'max_return_cap': 5.0,
            'ker_threshold_meanrev': 0.30,
            'ker_threshold_trend': 0.50,
            'ema_fast': 8,
            'ema_slow': 21,
            'trend_pulse_mult': 0.4,
        }, 1.574),  # Weight = baseline Sharpe
        
        (VolatilityAdaptiveRSI, {
            'rsi_period': 2,
            'vol_min_pct': 0.005,
            'max_return_cap': 5.0,
            'allowed_hours': [10, 11, 12, 13, 14, 15]
        }, 1.3),  # Weight = estimated Sharpe
        
        (RegimeSwitchingStrategy, {
            'rsi_period': 2,
            'allowed_hours': [10, 11, 12, 13, 14, 15]
        }, 2.09),  # Weight = actual Sharpe (High weight for winner)
    ]
    
    # Test meta-ensemble
    meta = MetaEnsemble('VBL', strategies_list)
    trades, metrics = meta.backtest_weighted_ensemble(df)
    
    print(f"\n✅ META-ENSEMBLE RESULTS:")
    print(f"  Trades: {metrics['total_trades']}")
    print(f"  Sharpe: {metrics['sharpe_ratio']:.3f}")
    print(f"  Return: {metrics['total_return_pct']:.2f}%")
    print(f"  Win Rate: {metrics['win_rate']:.1f}%")
    
    # Save
    output_dir = os.path.join(project_root, 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    with open(os.path.join(output_dir, 'phase3_meta_ensemble.json'), 'w') as f:
        json.dump({
            'VBL': {
                'sharpe': metrics['sharpe_ratio'],
                'trades': metrics['total_trades'],
                'return_pct': metrics['total_return_pct']
            }
        }, f, indent=2)
    
    print("\n✅ Results saved to: output/phase3_meta_ensemble.json")
    
    return metrics

if __name__ == "__main__":
    test_meta_ensemble()
