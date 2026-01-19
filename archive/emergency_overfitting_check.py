"""
EMERGENCY OVERFITTING CHECK
Critical test: Train/Test split validation
"""

import pandas as pd
import numpy as np
import sys
import os
import json

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from src.strategies.hybrid_adaptive import HybridAdaptiveStrategy
from src.strategies.hybrid_adaptive_v2 import HybridAdaptiveStrategyV2
from src.strategies.regime_switching_strategy import RegimeSwitchingStrategy
from src.strategies.nifty_trend_ladder import NIFTYTrendLadderStrategy

def train_test_split_validation():
    """
    Critical test: Split data into Train (70%) and Test (30%)
    If Sharpe drops >30% on test set = OVERFITTED
    """
    
    # ACTUAL PARAMS FROM PHASE 3
    symbol_configs = {
        'SUNPHARMA': {
            'filepath': 'data/raw/NSE_SUNPHARMA_EQ_1hour.csv',
            'strategy': HybridAdaptiveStrategyV2,
            'params': {
                "ker_period": 15,
                "rsi_period": 4,
                "vol_lookback": 14,
                "max_return_cap": 5.0,
                "ker_threshold_meanrev": 0.38224215306531234,
                "ker_threshold_trend": 0.6094140658792518,
                "rsi_entry": 41,  # Boosted (38+3)
                "rsi_exit": 52,
                "vol_min_pct": 0.004,  # Boosted (0.005-0.001)
                "ema_fast": 8,
                "ema_slow": 21,
                "trend_pulse_mult": 0.45596263377414287,
                "allowed_hours": [9, 10, 11],
                "max_hold_bars": 6,
                "use_dynamic_sizing": False,
                "use_multi_timeframe": False,
                "use_profit_ladder": True,
                "ladder_rsi_1": 65,
                "ladder_rsi_2": 73,
                "ladder_frac_1": 0.35,
                "use_adaptive_hold": True,
                "use_dynamic_rsi": False
            }
        },
        'RELIANCE': {
            'filepath': 'data/raw/NSE_RELIANCE_EQ_1hour.csv',
            'strategy': HybridAdaptiveStrategyV2,
            'params': {
                "strategy_type": "HYBRID",
                "ker_period": 10,
                "ker_threshold_meanrev": 0.28,
                "ker_threshold_trend": 0.5,
                "rsi_period": 2,
                "rsi_entry_range": 29,
                "rsi_exit_range": 90,
                "vol_min_pct": 0.008,
                "ema_fast": 5,
                "ema_slow": 21,
                "allowed_hours": [9, 10, 11, 12],
                "max_hold_bars": 8,
                "use_dynamic_sizing": False,
                "use_multi_timeframe": True,
                "daily_ema_period": 50,
                "require_daily_bias": False,
                "use_profit_ladder": False,
                "use_adaptive_hold": True,
                "use_dynamic_rsi": False
            }
        },
        'VBL': {
            'filepath': 'data/raw/NSE_VBL_EQ_1hour.csv',
            'strategy': RegimeSwitchingStrategy,
            'params': {
                'rsi_period': 2,
                'allowed_hours': [10, 11, 12, 13, 14, 15]
            }
        },
        'YESBANK': {
            'filepath': 'data/raw/NSE_YESBANK_EQ_1hour.csv',
            'strategy': HybridAdaptiveStrategy,
            'params': {
                "ker_period": 10,
                "rsi_period": 2,
                "vol_lookback": 20,
                "max_return_cap": 5.0,
                "ker_threshold_meanrev": 0.26980488595343255,
                "ker_threshold_trend": 0.47911308589265544,
                "rsi_entry": 27,  # Boosted (23+4)
                "rsi_exit": 88,
                "vol_min_pct": 0.0045,  # Boosted (0.0055-0.001)
                "ema_fast": 5,
                "ema_slow": 21,
                "trend_pulse_mult": 0.4097573487563908,
                "allowed_hours": [9, 10, 11, 12, 13],
                "max_hold_bars": 2,
                "_strategy": "SINGLE"
            }
        },
        'NIFTY50': {
            'filepath': 'data/raw/NSE_NIFTY50_INDEX_1hour.csv',
            'strategy': NIFTYTrendLadderStrategy,
            'params': {
                'ema_fast': 8,
                'ema_slow': 21,
                'momentum_threshold': 0.002,
                'vol_min_pct': 0.003,
                'max_hold_bars': 6,
                'stop_loss_pct': 2.0,
                'allowed_hours': [10, 11, 12, 13, 14, 15]
            }
        }
    }
    
    print("\n" + "="*70)
    print("EMERGENCY OVERFITTING CHECK: TRAIN/TEST SPLIT")
    print("="*70)
    print("Testing ACTUAL Phase 3 parameters")
    print("="*70)
    
    results = {}
    
    for symbol, config in symbol_configs.items():
        print(f"\n📊 Testing {symbol}...")
        
        filepath = config['filepath']
        if not os.path.exists(filepath):
            filepath = filepath.replace('data/raw/', 'data/')
        
        df = pd.read_csv(filepath)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        
        # Split: First 70% (train) vs Last 30% (test)
        split_idx = int(len(df) * 0.70)
        
        train_df = df.iloc[:split_idx].reset_index(drop=True)
        test_df = df.iloc[split_idx:].reset_index(drop=True)
        
        print(f"  Train: {train_df['datetime'].iloc[0].date()} to {train_df['datetime'].iloc[-1].date()} ({len(train_df)} bars)")
        print(f"  Test:  {test_df['datetime'].iloc[0].date()} to {test_df['datetime'].iloc[-1].date()} ({len(test_df)} bars)")
        
        # Backtest on TRAIN
        strategy_train = config['strategy'](config['params'])
        
        if symbol == 'NIFTY50':
            trades_train, metrics_train = strategy_train.backtest_with_ladder_exits(train_df)
        else:
            trades_train, metrics_train = strategy_train.backtest(train_df)
        
        # Backtest on TEST (out-of-sample)
        strategy_test = config['strategy'](config['params'])
        
        if symbol == 'NIFTY50':
            trades_test, metrics_test = strategy_test.backtest_with_ladder_exits(test_df)
        else:
            trades_test, metrics_test = strategy_test.backtest(test_df)
        
        train_sharpe = metrics_train['sharpe_ratio']
        test_sharpe = metrics_test['sharpe_ratio']
        degradation = train_sharpe - test_sharpe
        degradation_pct = (degradation / train_sharpe * 100) if train_sharpe != 0 else 0
        
        print(f"\n  📈 TRAIN Sharpe: {train_sharpe:.3f} (Trades: {metrics_train['total_trades']})")
        print(f"  📉 TEST Sharpe:  {test_sharpe:.3f} (Trades: {metrics_test['total_trades']})")
        print(f"  🔻 Degradation:  {degradation:+.3f} ({degradation_pct:+.1f}%)")
        
        # Evaluate
        if test_sharpe < 0 and train_sharpe > 2.0:
            status = "🚨 SEVERE OVERFITTING"
        elif abs(degradation_pct) > 50:
            status = "🚨 SEVERE OVERFITTING"
        elif abs(degradation_pct) > 30:
            status = "⚠️  OVERFITTED"
        elif abs(degradation_pct) > 15:
            status = "⚠️  MODERATE CONCERN"
        else:
            status = "✅ STABLE"
        
        print(f"  {status}")
        
        results[symbol] = {
            'train_sharpe': train_sharpe,
            'test_sharpe': test_sharpe,
            'train_trades': metrics_train['total_trades'],
            'test_trades': metrics_test['total_trades'],
            'degradation': degradation,
            'degradation_pct': degradation_pct,
            'status': status
        }
    
    # Portfolio analysis
    print("\n" + "="*70)
    print("PORTFOLIO OVERFITTING ASSESSMENT")
    print("="*70)
    
    avg_train = np.mean([r['train_sharpe'] for r in results.values()])
    avg_test = np.mean([r['test_sharpe'] for r in results.values()])
    portfolio_degradation = avg_train - avg_test
    portfolio_deg_pct = (portfolio_degradation / avg_train * 100) if avg_train != 0 else 0
    
    print(f"Portfolio Train Sharpe: {avg_train:.3f}")
    print(f"Portfolio Test Sharpe:  {avg_test:.3f}")
    print(f"Portfolio Degradation:  {portfolio_degradation:+.3f} ({portfolio_deg_pct:+.1f}%)")
    
    if abs(portfolio_deg_pct) > 40:
        print("\n🚨 CRITICAL: Portfolio is SEVERELY OVERFITTED")
        print("   Your 2.559 Sharpe will likely collapse in real trading")
        print("   RECOMMENDATION: DO NOT SUBMIT - Fix overfitting first")
        verdict = "DO_NOT_SUBMIT"
    elif abs(portfolio_deg_pct) > 25:
        print("\n⚠️  WARNING: Significant overfitting detected")
        print(f"   Expected real-world Sharpe: ~{avg_test:.2f}")
        print("   RECOMMENDATION: Submit but with realistic expectations")
        verdict = "SUBMIT_WITH_CAUTION"
    else:
        print("\n✅ ACCEPTABLE: Parameters appear stable")
        print(f"   Expected real-world Sharpe: ~{avg_test:.2f}")
        print("   RECOMMENDATION: Safe to submit")
        verdict = "SAFE_TO_SUBMIT"
    
    # Save results
    with open('output/OVERFITTING_CHECK.json', 'w') as f:
        json.dump({
            'symbol_results': results,
            'portfolio_train': avg_train,
            'portfolio_test': avg_test,
            'portfolio_degradation_pct': portfolio_deg_pct,
            'verdict': verdict
        }, f, indent=2)
    
    print("\n✅ Results saved: output/OVERFITTING_CHECK.json")
    
    return results, avg_test, verdict

if __name__ == "__main__":
    results, realistic_sharpe, verdict = train_test_split_validation()
    
    print("\n" + "="*70)
    print("REALISTIC SUBMISSION SHARPE ESTIMATE")
    print("="*70)
    print(f"Claimed Sharpe (Full Data): 2.559")
    print(f"Realistic Sharpe (OOS Test): {realistic_sharpe:.3f}")
    
    if realistic_sharpe >= 1.8:
        print("✅ Still competitive - SUBMIT")
    elif realistic_sharpe >= 1.5:
        print("⚠️  Moderate - Consider submitting as backup")
    else:
        print("🚨 Weak - Need to fix overfitting")
    
    print(f"\nFinal Verdict: {verdict}")
