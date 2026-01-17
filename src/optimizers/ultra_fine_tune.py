"""
Ultra Fine-Tuning Optimizer
Takes the best params and does local perturbation search to squeeze more Sharpe.
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from src.strategies.nifty_trend_strategy import generate_nifty_trend_signals, calculate_sharpe_ratio
from src.strategies.hybrid_adaptive import HybridAdaptiveStrategy

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)


def fine_tune_nifty(base_params: dict, data: pd.DataFrame, n_iter: int = 500) -> tuple:
    """Fine-tune NIFTY trend params with local perturbation."""
    print(f"\n{'='*60}")
    print("NIFTY50 FINE-TUNING (Local Perturbation)")
    print(f"{'='*60}")
    print(f"Base Sharpe: {base_params.get('base_sharpe', 'N/A')}")
    
    best_sharpe = -999
    best_params = None
    best_trades = None
    valid_count = 0
    
    # Perturbation ranges (±20% of base or discrete steps)
    for i in range(n_iter):
        # Perturb each parameter
        params = {
            'ema_fast': max(3, base_params['ema_fast'] + np.random.randint(-2, 3)),
            'ema_slow': max(15, base_params['ema_slow'] + np.random.randint(-5, 6)),
            'momentum_period': max(3, base_params['momentum_period'] + np.random.randint(-2, 3)),
            'momentum_threshold': max(0.05, base_params['momentum_threshold'] + np.random.uniform(-0.1, 0.1)),
            'ema_diff_threshold': max(0.01, base_params['ema_diff_threshold'] + np.random.uniform(-0.05, 0.05)),
            'vol_min': max(0.0, base_params['vol_min'] + np.random.uniform(-0.05, 0.05)),
            'allowed_hours': base_params['allowed_hours'],  # Keep same
            'max_hold': max(3, base_params['max_hold'] + np.random.randint(-3, 4)),
            'vol_period': 14,
        }
        
        # Ensure fast < slow
        if params['ema_fast'] >= params['ema_slow']:
            continue
        
        try:
            trades_df = generate_nifty_trend_signals(data, params)
            
            if len(trades_df) < 120:
                continue
            
            total_return = trades_df['pnl'].sum() / 100000 * 100
            trades_df['return_pct'] = trades_df['pnl'] / 100000 * 100
            
            if trades_df['return_pct'].std() == 0:
                continue
            
            sharpe = trades_df['return_pct'].mean() / trades_df['return_pct'].std()
            valid_count += 1
            
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_params = params.copy()
                best_trades = trades_df.copy()
                print(f"  [{i+1}/{n_iter}] NEW BEST: Sharpe={sharpe:.4f}, Return={total_return:+.2f}%, Trades={len(trades_df)}")
        
        except Exception:
            continue
        
        if (i + 1) % 100 == 0:
            print(f"  [{i+1}/{n_iter}] Valid={valid_count}, Best={best_sharpe:.4f}")
    
    return best_params, best_trades, best_sharpe


def fine_tune_yesbank(base_params: dict, data: pd.DataFrame, n_iter: int = 500) -> tuple:
    """Fine-tune YESBANK hybrid params."""
    print(f"\n{'='*60}")
    print("YESBANK FINE-TUNING")
    print(f"{'='*60}")
    
    best_sharpe = -999
    best_params = None
    best_trades = None
    valid_count = 0
    
    for i in range(n_iter):
        # Perturb params
        params = base_params.copy()
        params['rsi_oversold'] = max(10, params.get('rsi_oversold', 30) + np.random.randint(-5, 6))
        params['rsi_overbought'] = min(90, params.get('rsi_overbought', 70) + np.random.randint(-5, 6))
        params['ker_threshold'] = max(0.1, min(0.9, params.get('ker_threshold', 0.5) + np.random.uniform(-0.1, 0.1)))
        params['vol_min'] = max(0.001, params.get('vol_min', 0.005) + np.random.uniform(-0.002, 0.002))
        params['max_hold'] = max(3, params.get('max_hold', 8) + np.random.randint(-2, 3))
        
        try:
            strategy = HybridAdaptiveStrategy(params)
            trades, metrics = strategy.backtest(data)
            
            if metrics['total_trades'] < 120:
                continue
            
            sharpe = metrics['sharpe_ratio']
            valid_count += 1
            
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_params = params.copy()
                best_trades = trades
                print(f"  [{i+1}/{n_iter}] NEW BEST: Sharpe={sharpe:.4f}, Return={metrics['total_return_pct']:+.2f}%")
        
        except Exception:
            continue
        
        if (i + 1) % 100 == 0:
            print(f"  [{i+1}/{n_iter}] Valid={valid_count}, Best={best_sharpe:.4f}")
    
    return best_params, best_trades, best_sharpe


if __name__ == '__main__':
    print("="*70)
    print("ULTRA FINE-TUNING OPTIMIZER")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}")
    
    # === NIFTY50 Fine-Tuning ===
    with open('output/nifty_trend_optimized_params.json', 'r') as f:
        nifty_data = json.load(f)
    
    base_nifty = nifty_data['NIFTY50_TREND']
    base_nifty['base_sharpe'] = nifty_data['metrics']['sharpe']
    
    nifty_df = pd.read_csv('data/raw/NSE_NIFTY50_INDEX_1hour.csv')
    
    new_nifty_params, new_nifty_trades, new_nifty_sharpe = fine_tune_nifty(
        base_nifty, nifty_df, n_iter=800
    )
    
    if new_nifty_sharpe > base_nifty['base_sharpe']:
        print(f"\n✅ NIFTY50 IMPROVED: {base_nifty['base_sharpe']:.4f} -> {new_nifty_sharpe:.4f}")
        # Save improved params
        nifty_data['NIFTY50_TREND'] = new_nifty_params
        nifty_data['metrics']['sharpe'] = new_nifty_sharpe
        nifty_data['metrics']['return'] = new_nifty_trades['pnl'].sum() / 100000 * 100
        nifty_data['metrics']['trades'] = len(new_nifty_trades)
        with open('output/nifty_trend_optimized_params.json', 'w') as f:
            json.dump(nifty_data, f, indent=2, cls=NpEncoder)
    else:
        print(f"\n⚠️ NIFTY50: No improvement found. Keeping {base_nifty['base_sharpe']:.4f}")
    
    # === YESBANK Fine-Tuning ===
    with open('output/sharpe_optimized_params.json', 'r') as f:
        sharpe_params = json.load(f)
    
    base_yesbank = sharpe_params.get('YESBANK', {}).get('params', {})
    
    if base_yesbank:
        yesbank_df = pd.read_csv('data/raw/NSE_YESBANK_EQ_1hour.csv')
        
        new_yesbank_params, _, new_yesbank_sharpe = fine_tune_yesbank(
            base_yesbank, yesbank_df, n_iter=500
        )
        
        if new_yesbank_params and new_yesbank_sharpe > sharpe_params['YESBANK']['metrics']['sharpe_ratio']:
            print(f"\n✅ YESBANK IMPROVED: {sharpe_params['YESBANK']['metrics']['sharpe_ratio']:.4f} -> {new_yesbank_sharpe:.4f}")
            sharpe_params['YESBANK']['params'] = new_yesbank_params
            sharpe_params['YESBANK']['metrics']['sharpe_ratio'] = new_yesbank_sharpe
            with open('output/sharpe_optimized_params.json', 'w') as f:
                json.dump(sharpe_params, f, indent=2, cls=NpEncoder)
        else:
            print(f"\n⚠️ YESBANK: No improvement found.")
    
    print(f"\n{'='*70}")
    print("FINE-TUNING COMPLETE")
    print(f"{'='*70}")
    print(f"Finished: {datetime.now().strftime('%H:%M:%S')}")
