"""
Ensemble Wrapper for Variance Reduction
Generates diverse parameter variants and requires agreement for entry signals.
Uses existing HybridAdaptiveStrategy as base.

Target: Improve VBL Sharpe 1.16 → 1.42, SUNPHARMA Sharpe 1.84 → 2.10
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from strategies.hybrid_adaptive import HybridAdaptiveStrategy
from utils.indicators import calculate_rsi, calculate_volatility


def generate_ensemble_params(base_params: Dict, n_variants: int = 5) -> List[Dict]:
    """
    Generate diverse parameter variants around base parameters.
    
    Diversity criteria:
    - RSI entry: ±5 points from base
    - RSI exit: ±8 points from base
    - Volatility: ±0.002 from base
    - Max hold: ±2 bars from base
    """
    np.random.seed(42)  # Reproducibility
    variants = [base_params.copy()]  # Always include base
    
    for i in range(n_variants - 1):
        variant = base_params.copy()
        
        # Perturb RSI thresholds
        rsi_entry_base = base_params.get('rsi_entry', 30)
        rsi_exit_base = base_params.get('rsi_exit', 70)
        variant['rsi_entry'] = max(15, min(45, rsi_entry_base + np.random.randint(-5, 6)))
        variant['rsi_exit'] = max(55, min(98, rsi_exit_base + np.random.randint(-8, 9)))
        
        # Perturb volatility filter
        vol_base = base_params.get('vol_min_pct', 0.005)
        variant['vol_min_pct'] = max(0.001, vol_base + np.random.uniform(-0.002, 0.002))
        
        # Perturb max hold
        hold_base = base_params.get('max_hold_bars', 10)
        variant['max_hold_bars'] = max(3, min(15, hold_base + np.random.randint(-2, 3)))
        
        # Keep KER thresholds unchanged (regime detection should be stable)
        variants.append(variant)
    
    return variants


class EnsembleStrategy:
    """
    Ensemble wrapper that requires minimum agreement across variants.
    """
    
    def __init__(self, base_params: Dict, n_variants: int = 5, min_agreement: int = 3):
        self.base_params = base_params
        self.n_variants = n_variants
        self.min_agreement = min_agreement
        self.param_variants = generate_ensemble_params(base_params, n_variants)
        self.strategies = [HybridAdaptiveStrategy(p) for p in self.param_variants]
        self.max_return_cap = base_params.get('max_return_cap', 5.0)
    
    def generate_ensemble_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate signals requiring min_agreement across variants."""
        df = df.copy()
        
        # Collect signals from all variants
        signal_cols = []
        for idx, strategy in enumerate(self.strategies):
            signal_df = strategy.generate_signals(df)
            col_name = f'signal_{idx}'
            df[col_name] = signal_df['signal_long'].astype(int)
            signal_cols.append(col_name)
        
        # Count agreement
        df['signal_count'] = df[signal_cols].sum(axis=1)
        df['signal_strength'] = df['signal_count'] / len(self.strategies)
        
        # Require minimum agreement
        df['ensemble_signal'] = (df['signal_count'] >= self.min_agreement).astype(int)
        
        # Use median RSI exit from variants
        median_rsi_exit = int(np.median([p.get('rsi_exit', 70) for p in self.param_variants]))
        
        # Calculate RSI with base period
        rsi_period = self.base_params.get('rsi_period', 2)
        df['RSI'] = calculate_rsi(df['close'], rsi_period)
        
        # Clean up
        df.drop(columns=signal_cols, inplace=True)
        
        # Store for exit logic
        df['median_rsi_exit'] = median_rsi_exit
        
        return df
    
    def backtest(self, df: pd.DataFrame, initial_capital: float = 100000) -> Tuple[List[Dict], Dict]:
        """Backtest with ensemble signals."""
        df = self.generate_ensemble_signals(df)
        
        if 'datetime' not in df.columns and df.index.name == 'datetime':
            df = df.reset_index()
        
        trades = []
        capital = initial_capital
        
        in_position = False
        entry_price = 0
        entry_time = None
        entry_capital = 0
        entry_qty = 0
        entry_confidence = 0
        bars_held = 0
        
        fee_per_order = 24
        median_max_hold = int(np.median([p.get('max_hold_bars', 10) for p in self.param_variants]))
        allowed_hours = self.base_params.get('allowed_hours', [9, 10, 11, 12, 13])
        
        for i in range(50, len(df)):
            current_time = df['datetime'].iloc[i]
            current_hour = current_time.hour
            current_minute = current_time.minute
            current_close = df['close'].iloc[i]
            
            # === ENTRY: Require ensemble consensus ===
            if not in_position:
                if current_hour not in allowed_hours:
                    continue
                if current_hour >= 14 and current_minute >= 30:
                    continue
                
                if df['ensemble_signal'].iloc[i] == 1:
                    qty = int((capital - fee_per_order) * 0.95 / current_close)
                    
                    if qty > 0:
                        entry_price = current_close
                        entry_time = current_time
                        entry_capital = capital
                        entry_qty = qty
                        entry_confidence = df['signal_strength'].iloc[i]
                        capital -= fee_per_order
                        in_position = True
                        bars_held = 0
            
            # === EXIT: Use median parameters ===
            else:
                bars_held += 1
                
                current_return_pct = ((current_close - entry_price) / entry_price) * 100
                current_rsi = df['RSI'].iloc[i]
                median_rsi_exit = df['median_rsi_exit'].iloc[i]
                
                # Exit conditions
                outlier_exit = current_return_pct >= self.max_return_cap
                rsi_exit = current_rsi > median_rsi_exit
                time_exit = bars_held >= median_max_hold
                eod_exit = (current_hour >= 15 and current_minute >= 15)
                
                if rsi_exit or outlier_exit or time_exit or eod_exit:
                    exit_price = current_close
                    exit_time = current_time
                    
                    gross_pnl = entry_qty * (exit_price - entry_price)
                    net_pnl = gross_pnl - (2 * fee_per_order)
                    capital = entry_capital + gross_pnl - (2 * fee_per_order)
                    
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': exit_time,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'qty': entry_qty,
                        'pnl': net_pnl,
                        'capital': capital,
                        'bars_held': bars_held,
                        'return_pct': current_return_pct,
                        'confidence': entry_confidence,
                        'outlier_capped': outlier_exit,
                    })
                    
                    in_position = False
        
        metrics = self._calculate_metrics(trades, initial_capital, capital)
        return trades, metrics
    
    def _calculate_metrics(self, trades: List[Dict], initial_capital: float, final_capital: float) -> Dict:
        """Calculate metrics including Sharpe ratio."""
        if len(trades) == 0:
            return {
                'total_trades': 0,
                'total_return_pct': 0,
                'sharpe_ratio': -999,
                'win_rate': 0,
                'final_capital': final_capital,
            }
        
        trades_df = pd.DataFrame(trades)
        
        total_trades = len(trades_df)
        total_return_pct = (final_capital - initial_capital) / initial_capital * 100
        winning_trades = (trades_df['pnl'] > 0).sum()
        win_rate = (winning_trades / total_trades) * 100
        
        # Sharpe ratio
        returns = (trades_df['pnl'] / initial_capital) * 100
        
        if returns.std() > 0 and len(returns) > 1:
            trades_per_year = 1500 / (len(trades_df) / 250) if len(trades_df) > 0 else 1
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(min(trades_per_year, 252))
        else:
            sharpe_ratio = 0
        
        # Average confidence
        avg_confidence = trades_df['confidence'].mean()
        
        return {
            'total_trades': total_trades,
            'total_return_pct': total_return_pct,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'avg_confidence': avg_confidence,
            'final_capital': final_capital,
            'max_return': trades_df['return_pct'].max(),
            'min_return': trades_df['return_pct'].min(),
        }


def test_ensemble_vs_single(symbol: str, data_path: str, params: Dict):
    """Compare single strategy vs ensemble for a symbol."""
    print(f"\n{'='*70}")
    print(f"TESTING {symbol}: Single vs Ensemble")
    print(f"{'='*70}")
    
    # Load data
    df = pd.read_csv(data_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    # Single strategy
    single = HybridAdaptiveStrategy(params)
    single_trades, single_metrics = single.backtest(df)
    
    print(f"\n📊 SINGLE BEST STRATEGY:")
    print(f"   Sharpe: {single_metrics['sharpe_ratio']:.3f}")
    print(f"   Return: {single_metrics['total_return_pct']:.2f}%")
    print(f"   Trades: {single_metrics['total_trades']}")
    print(f"   Win Rate: {single_metrics['win_rate']:.1f}%")
    
    # Ensemble strategy
    ensemble = EnsembleStrategy(params, n_variants=5, min_agreement=3)
    ensemble_trades, ensemble_metrics = ensemble.backtest(df)
    
    print(f"\n🎯 ENSEMBLE STRATEGY (5 variants, min_agreement=3):")
    print(f"   Sharpe: {ensemble_metrics['sharpe_ratio']:.3f}")
    print(f"   Return: {ensemble_metrics['total_return_pct']:.2f}%")
    print(f"   Trades: {ensemble_metrics['total_trades']}")
    print(f"   Win Rate: {ensemble_metrics['win_rate']:.1f}%")
    print(f"   Avg Confidence: {ensemble_metrics['avg_confidence']:.2f}")
    
    # Comparison
    sharpe_improvement = ensemble_metrics['sharpe_ratio'] - single_metrics['sharpe_ratio']
    trade_diff = ensemble_metrics['total_trades'] - single_metrics['total_trades']
    
    print(f"\n{'='*70}")
    print(f"COMPARISON:")
    print(f"   Sharpe Change: {sharpe_improvement:+.3f}")
    print(f"   Trade Count Change: {trade_diff:+d}")
    
    if sharpe_improvement > 0.15 and ensemble_metrics['total_trades'] >= 120:
        print(f"   ✅ ENSEMBLE WINS - Use this for submission")
        use_ensemble = True
    elif ensemble_metrics['total_trades'] < 120:
        print(f"   ⚠️ ENSEMBLE TRADE COUNT TOO LOW - Try min_agreement=2")
        use_ensemble = False
    else:
        print(f"   ❌ KEEP SINGLE - Improvement not significant")
        use_ensemble = False
    
    print(f"{'='*70}")
    
    return {
        'symbol': symbol,
        'single_sharpe': single_metrics['sharpe_ratio'],
        'ensemble_sharpe': ensemble_metrics['sharpe_ratio'],
        'improvement': sharpe_improvement,
        'single_trades': single_metrics['total_trades'],
        'ensemble_trades': ensemble_metrics['total_trades'],
        'use_ensemble': use_ensemble,
    }


if __name__ == "__main__":
    import json
    
    # Load optimized params
    with open('output/sharpe_optimized_params.json', 'r') as f:
        all_params = json.load(f)
    
    results = []
    
    # Test VBL
    vbl_result = test_ensemble_vs_single(
        'VBL',
        'data/raw/NSE_VBL_EQ_1hour.csv',
        all_params['VBL']['params']
    )
    results.append(vbl_result)
    
    # Test SUNPHARMA
    sunpharma_result = test_ensemble_vs_single(
        'SUNPHARMA',
        'data/raw/NSE_SUNPHARMA_EQ_1hour.csv',
        all_params['SUNPHARMA']['params']
    )
    results.append(sunpharma_result)
    
    # Summary
    print(f"\n{'='*70}")
    print("ENSEMBLE TESTING SUMMARY")
    print(f"{'='*70}")
    for r in results:
        status = "✅ USE ENSEMBLE" if r['use_ensemble'] else "❌ USE SINGLE"
        print(f"{r['symbol']}: {r['single_sharpe']:.2f} → {r['ensemble_sharpe']:.2f} ({r['improvement']:+.2f}) | {status}")
