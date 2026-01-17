"""
Comprehensive Strategy Comparison Runner
Tests all 6 new strategies on all 5 symbols and compares results.
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

# Import all strategies
from src.strategies.stat_arb_strategy import optimize_stat_arb, StatisticalArbitrageStrategy, calculate_correlation
from src.strategies.vol_breakout_strategy import optimize_vol_breakout, VolatilityBreakoutStrategy
from src.strategies.momentum_strategy import optimize_momentum, TimeSeriesMomentumStrategy
from src.strategies.enhanced_regime_strategy import optimize_enhanced_regime, EnhancedRegimeSwitchingStrategy
from src.strategies.adaptive_bb_strategy import optimize_adaptive_bb, AdaptiveBollingerStrategy
from src.strategies.seasonality_strategy import optimize_seasonality, SeasonalityStrategy

# Data paths
DATA_PATHS = {
    'NIFTY50': 'data/raw/NSE_NIFTY50_INDEX_1hour.csv',
    'RELIANCE': 'data/raw/NSE_RELIANCE_EQ_1hour.csv',
    'VBL': 'data/raw/NSE_VBL_EQ_1hour.csv',
    'YESBANK': 'data/raw/NSE_YESBANK_EQ_1hour.csv',
    'SUNPHARMA': 'data/raw/NSE_SUNPHARMA_EQ_1hour.csv',
}

BASELINE_SHARPES = {
    'VBL': 1.574,
    'RELIANCE': 1.683,
    'SUNPHARMA': 3.132,
    'YESBANK': 1.036,
    'NIFTY50': 0.006,
}


def load_data():
    """Load all symbol data."""
    data = {}
    for symbol, path in DATA_PATHS.items():
        df = pd.read_csv(path)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        data[symbol] = df
    return data


def test_stat_arb(data):
    """Test Statistical Arbitrage on pairs."""
    print("\n" + "="*70)
    print("STRATEGY 1: STATISTICAL ARBITRAGE (PAIRS TRADING)")
    print("="*70)
    
    # Test pairs
    pairs = [
        ('VBL', 'RELIANCE'),
        ('SUNPHARMA', 'RELIANCE'),
        ('VBL', 'SUNPHARMA'),
        ('YESBANK', 'RELIANCE'),
    ]
    
    results = []
    
    for asset1, asset2 in pairs:
        print(f"\n[{asset1}-{asset2}]")
        
        # Calculate correlation
        corr = calculate_correlation(data[asset1], data[asset2])
        print(f"  Correlation: {corr:.3f}")
        
        # Optimize
        best_params, best_sharpe, best_trades = optimize_stat_arb(
            data[asset1], data[asset2], n_iterations=200
        )
        
        if best_params:
            print(f"  Best Sharpe: {best_sharpe:.3f}")
            print(f"  Best Trades: {best_trades}")
            
            results.append({
                'pair': f"{asset1}-{asset2}",
                'correlation': corr,
                'sharpe': best_sharpe,
                'trades': best_trades,
                'params': best_params,
            })
        else:
            print(f"  No valid params found (< 120 trades)")
    
    return results


def test_single_asset_strategies(data, n_iterations=200):
    """Test single-asset strategies on all symbols."""
    
    strategies = [
        ('VolBreakout', optimize_vol_breakout),
        ('Momentum', optimize_momentum),
        ('EnhancedRegime', optimize_enhanced_regime),
        ('AdaptiveBB', optimize_adaptive_bb),
        ('Seasonality', optimize_seasonality),
    ]
    
    all_results = {}
    
    for strategy_name, optimize_fn in strategies:
        print(f"\n{'='*70}")
        print(f"STRATEGY: {strategy_name.upper()}")
        print("="*70)
        
        strategy_results = {}
        
        for symbol in ['VBL', 'RELIANCE', 'SUNPHARMA', 'YESBANK', 'NIFTY50']:
            print(f"\n[{symbol}]")
            
            df = data[symbol]
            
            best_params, best_sharpe, best_trades = optimize_fn(df, n_iterations)
            
            if best_params:
                improvement = best_sharpe - BASELINE_SHARPES[symbol]
                print(f"  Sharpe: {best_sharpe:.3f} (Δ{improvement:+.3f})")
                print(f"  Trades: {best_trades}")
                
                strategy_results[symbol] = {
                    'sharpe': best_sharpe,
                    'trades': best_trades,
                    'params': best_params,
                    'improvement': improvement,
                }
            else:
                print(f"  No valid params found")
                strategy_results[symbol] = {
                    'sharpe': -999,
                    'trades': 0,
                    'params': None,
                }
        
        # Calculate average Sharpe
        valid_sharpes = [r['sharpe'] for r in strategy_results.values() if r['sharpe'] > -100]
        avg_sharpe = sum(valid_sharpes) / len(valid_sharpes) if valid_sharpes else -999
        
        all_results[strategy_name] = {
            'symbols': strategy_results,
            'avg_sharpe': avg_sharpe,
        }
        
        print(f"\n  Average Sharpe: {avg_sharpe:.3f}")
    
    return all_results


def generate_comparison_report(stat_arb_results, strategy_results):
    """Generate comparison report."""
    
    print("\n" + "="*70)
    print("STRATEGY COMPARISON REPORT")
    print("="*70)
    
    # Header
    print(f"\n{'Strategy':<20} {'Avg Sharpe':>12} {'Min Trades':>12} {'Status':<15}")
    print("-"*60)
    
    comparisons = []
    
    # Add baseline
    baseline_avg = sum(BASELINE_SHARPES.values()) / 5
    print(f"{'BASELINE':<20} {baseline_avg:>12.3f} {120:>12} {'Current Best':<15}")
    comparisons.append({
        'strategy': 'BASELINE',
        'avg_sharpe': baseline_avg,
        'min_trades': 120,
    })
    
    # Add single-asset strategies
    for strategy_name, results in strategy_results.items():
        min_trades = min(r['trades'] for r in results['symbols'].values())
        
        if results['avg_sharpe'] > -100:
            status = "✅ Valid" if min_trades >= 120 else "⚠️ Low trades"
            print(f"{strategy_name:<20} {results['avg_sharpe']:>12.3f} {min_trades:>12} {status:<15}")
            
            comparisons.append({
                'strategy': strategy_name,
                'avg_sharpe': results['avg_sharpe'],
                'min_trades': min_trades,
            })
    
    # Add StatArb (best pair)
    if stat_arb_results:
        best_pair = max(stat_arb_results, key=lambda x: x['sharpe'])
        print(f"{'StatArb ('+best_pair['pair']+')':<20} {best_pair['sharpe']:>12.3f} {best_pair['trades']:>12} {'✅ Valid' if best_pair['trades'] >= 120 else '⚠️ Low trades':<15}")
    
    # Rank strategies
    print("\n" + "="*70)
    print("RANKING (by Avg Sharpe)")
    print("="*70)
    
    sorted_strategies = sorted(comparisons, key=lambda x: x['avg_sharpe'], reverse=True)
    
    for i, s in enumerate(sorted_strategies, 1):
        valid = "✅" if s['min_trades'] >= 120 else "❌"
        print(f"  #{i}: {s['strategy']:<20} Sharpe={s['avg_sharpe']:.3f} {valid}")
    
    # Top 3 recommendation
    print("\n" + "="*70)
    print("TOP 3 RECOMMENDATIONS")
    print("="*70)
    
    valid_strategies = [s for s in sorted_strategies if s['min_trades'] >= 120 and s['avg_sharpe'] > 0]
    
    for i, s in enumerate(valid_strategies[:3], 1):
        print(f"\n  Slot {i+2}: {s['strategy']}")
        print(f"    Avg Sharpe: {s['avg_sharpe']:.3f}")
        print(f"    Min Trades: {s['min_trades']}")
    
    return sorted_strategies


def save_results(stat_arb_results, strategy_results, sorted_strategies):
    """Save all results to JSON."""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    output = {
        'timestamp': timestamp,
        'baseline_avg_sharpe': sum(BASELINE_SHARPES.values()) / 5,
        'baseline_per_symbol': BASELINE_SHARPES,
        'stat_arb_results': stat_arb_results,
        'strategy_results': {k: {
            'avg_sharpe': v['avg_sharpe'],
            'symbols': {sk: {
                'sharpe': sv['sharpe'],
                'trades': sv['trades'],
            } for sk, sv in v['symbols'].items()}
        } for k, v in strategy_results.items()},
        'ranking': [{'strategy': s['strategy'], 'avg_sharpe': s['avg_sharpe'], 'min_trades': s['min_trades']} 
                   for s in sorted_strategies],
    }
    
    Path('experiments/results').mkdir(parents=True, exist_ok=True)
    filename = f'experiments/results/strategy_comparison_{timestamp}.json'
    
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"\n✅ Results saved to {filename}")
    
    return filename


def main():
    """Main execution."""
    
    print("="*70)
    print("COMPREHENSIVE STRATEGY COMPARISON")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Target: Sharpe > 1.8 (Current best: 1.486)")
    print("="*70)
    
    # Load data
    print("\nLoading data...")
    data = load_data()
    print(f"Loaded {len(data)} symbols")
    
    # Test Statistical Arbitrage
    stat_arb_results = test_stat_arb(data)
    
    # Test single-asset strategies
    strategy_results = test_single_asset_strategies(data, n_iterations=200)
    
    # Generate comparison
    sorted_strategies = generate_comparison_report(stat_arb_results, strategy_results)
    
    # Save results
    save_results(stat_arb_results, strategy_results, sorted_strategies)
    
    print("\n" + "="*70)
    print("COMPARISON COMPLETE")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    return stat_arb_results, strategy_results, sorted_strategies


if __name__ == '__main__':
    main()
