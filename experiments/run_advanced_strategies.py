"""
Advanced Strategies Comparison Runner
Tests all 3 strategies on all symbols and generates comparison report.
"""

import pandas as pd
import numpy as np
import json
import sys
from datetime import datetime
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.strategies.pairs_trading_strategy import PairsTradingStrategy, optimize_pairs_trading
from src.strategies.volume_momentum_strategy import VolumeWeightedMomentumStrategy, optimize_volume_momentum
from src.strategies.volatility_regime_strategy import VolatilityRegimeSwitchingStrategy, optimize_volatility_regime

BASELINE_SHARPES = {
    'VBL': 1.574,
    'RELIANCE': 1.683,
    'SUNPHARMA': 3.132,
    'YESBANK': 1.036,
    'NIFTY50': 0.006,
}

SYMBOLS = ['RELIANCE', 'VBL', 'SUNPHARMA', 'YESBANK']

def run_optimization():
    """Run full optimization for all 3 strategies."""
    
    print("="*80)
    print("ADVANCED STRATEGIES OPTIMIZATION")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Target: Sharpe > 2.0")
    print("="*80)
    
    all_results = []
    
    # 1. PAIRS TRADING
    print("\n" + "="*80)
    print("STRATEGY 1: PAIRS TRADING (Stock vs NIFTY50)")
    print("="*80)
    
    for symbol in SYMBOLS:
        print(f"\n[{symbol}] Optimizing (300 iterations)...")
        best_params, best_sharpe, best_trades = optimize_pairs_trading(symbol, 300)
        
        if best_params:
            improvement = best_sharpe - BASELINE_SHARPES.get(symbol, 0)
            print(f"  Sharpe: {best_sharpe:.3f} (Δ{improvement:+.3f})")
            print(f"  Trades: {best_trades}")
            
            all_results.append({
                'strategy': 'PairsTrading',
                'symbol': symbol,
                'sharpe': best_sharpe,
                'trades': best_trades,
                'params': best_params,
                'improvement': improvement,
            })
        else:
            print(f"  No valid params found (< 120 trades)")
            all_results.append({
                'strategy': 'PairsTrading',
                'symbol': symbol,
                'sharpe': -999,
                'trades': 0,
            })
    
    # 2. VOLUME MOMENTUM
    print("\n" + "="*80)
    print("STRATEGY 2: VOLUME-WEIGHTED MOMENTUM")
    print("="*80)
    
    for symbol in SYMBOLS:
        print(f"\n[{symbol}] Optimizing (300 iterations)...")
        best_params, best_sharpe, best_trades = optimize_volume_momentum(symbol, 300)
        
        if best_params:
            improvement = best_sharpe - BASELINE_SHARPES.get(symbol, 0)
            print(f"  Sharpe: {best_sharpe:.3f} (Δ{improvement:+.3f})")
            print(f"  Trades: {best_trades}")
            
            all_results.append({
                'strategy': 'VolumeMomentum',
                'symbol': symbol,
                'sharpe': best_sharpe,
                'trades': best_trades,
                'params': best_params,
                'improvement': improvement,
            })
        else:
            print(f"  No valid params found")
            all_results.append({
                'strategy': 'VolumeMomentum',
                'symbol': symbol,
                'sharpe': -999,
                'trades': 0,
            })
    
    # 3. VOLATILITY REGIME
    print("\n" + "="*80)
    print("STRATEGY 3: VOLATILITY REGIME SWITCHING")
    print("="*80)
    
    for symbol in SYMBOLS:
        print(f"\n[{symbol}] Optimizing (300 iterations)...")
        best_params, best_sharpe, best_trades = optimize_volatility_regime(symbol, 300)
        
        if best_params:
            improvement = best_sharpe - BASELINE_SHARPES.get(symbol, 0)
            print(f"  Sharpe: {best_sharpe:.3f} (Δ{improvement:+.3f})")
            print(f"  Trades: {best_trades}")
            
            all_results.append({
                'strategy': 'VolRegime',
                'symbol': symbol,
                'sharpe': best_sharpe,
                'trades': best_trades,
                'params': best_params,
                'improvement': improvement,
            })
        else:
            print(f"  No valid params found")
            all_results.append({
                'strategy': 'VolRegime',
                'symbol': symbol,
                'sharpe': -999,
                'trades': 0,
            })
    
    return all_results


def generate_comparison_report(all_results):
    """Generate comprehensive comparison report."""
    
    print("\n" + "="*80)
    print("STRATEGY COMPARISON REPORT")
    print("="*80)
    
    df = pd.DataFrame(all_results)
    
    # Filter valid results
    valid = df[df['sharpe'] > -100]
    
    # 1. Strategy Rankings
    print("\n1. STRATEGY RANKINGS (by Sharpe)")
    print("-"*60)
    
    if len(valid) > 0:
        for _, row in valid.nlargest(10, 'sharpe').iterrows():
            status = "✅" if row['trades'] >= 120 else "⚠️"
            print(f"  {row['strategy']:20} {row['symbol']:12} Sharpe={row['sharpe']:>6.3f} Trades={row['trades']:3} {status}")
    
    # 2. Best per Symbol
    print("\n2. BEST STRATEGY PER SYMBOL")
    print("-"*60)
    
    best_per_symbol = {}
    for symbol in SYMBOLS:
        symbol_results = valid[valid['symbol'] == symbol]
        if len(symbol_results) > 0:
            best = symbol_results.nlargest(1, 'sharpe').iloc[0]
            best_per_symbol[symbol] = best
            vs_baseline = best['sharpe'] - BASELINE_SHARPES.get(symbol, 0)
            print(f"  {symbol:12} → {best['strategy']:20} Sharpe={best['sharpe']:.3f} (vs baseline: {vs_baseline:+.3f})")
    
    # 3. Average Sharpe by Strategy
    print("\n3. AVERAGE SHARPE BY STRATEGY")
    print("-"*60)
    
    for strategy in ['PairsTrading', 'VolumeMomentum', 'VolRegime']:
        strat_results = valid[valid['strategy'] == strategy]
        if len(strat_results) > 0:
            avg_sharpe = strat_results['sharpe'].mean()
            valid_count = len(strat_results[strat_results['trades'] >= 120])
            print(f"  {strategy:20} Avg Sharpe={avg_sharpe:.3f} Valid Symbols={valid_count}/4")
    
    # 4. Comparison with Baseline
    print("\n4. COMPARISON WITH BASELINE (1.486)")
    print("-"*60)
    
    baseline_avg = sum(BASELINE_SHARPES.values()) / 5  # 1.486
    
    for strategy in ['PairsTrading', 'VolumeMomentum', 'VolRegime']:
        strat_results = valid[(valid['strategy'] == strategy) & (valid['trades'] >= 120)]
        if len(strat_results) > 0:
            portfolio_sharpe = strat_results['sharpe'].mean()
            diff = portfolio_sharpe - baseline_avg
            status = "✅ BETTER" if diff > 0 else "❌ WORSE"
            print(f"  {strategy:20} Sharpe={portfolio_sharpe:.3f} (Δ{diff:+.3f}) {status}")
    
    print(f"\n  BASELINE:             Sharpe=1.486")
    
    return valid, best_per_symbol


def save_results(all_results, best_per_symbol):
    """Save results to JSON and generate documentation."""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save JSON
    output = {
        'timestamp': timestamp,
        'baseline_sharpe': 1.486,
        'results': all_results,
        'best_per_symbol': {k: {
            'strategy': v['strategy'],
            'sharpe': v['sharpe'],
            'trades': v['trades'],
        } for k, v in best_per_symbol.items()} if best_per_symbol else {},
    }
    
    Path('experiments/results').mkdir(parents=True, exist_ok=True)
    filepath = f'experiments/results/advanced_strategies_{timestamp}.json'
    
    with open(filepath, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"\n✅ Results saved to {filepath}")
    
    return filepath


def main():
    """Main execution."""
    
    # Run optimization
    all_results = run_optimization()
    
    # Generate comparison
    valid_df, best_per_symbol = generate_comparison_report(all_results)
    
    # Save results
    save_results(all_results, best_per_symbol)
    
    print("\n" + "="*80)
    print("OPTIMIZATION COMPLETE")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    return all_results


if __name__ == '__main__':
    main()
