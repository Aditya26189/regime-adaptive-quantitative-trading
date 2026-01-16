"""
Multi-Objective Sharpe Ratio Optimizer
Random search with composite scoring for all 5 symbols
"""

import pandas as pd
import numpy as np
import json
import random
from typing import Dict, List, Tuple
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from strategies.hybrid_adaptive import HybridAdaptiveStrategy
from utils.indicators import calculate_rsi, calculate_volatility

class SharpeOptimizer:
    """
    Multi-objective optimization focused on Sharpe ratio.
    Tests random parameter combinations and ranks by composite score.
    """
    
    SYMBOLS = ['NIFTY50', 'RELIANCE', 'VBL', 'YESBANK', 'SUNPHARMA']
    
    DATA_PATHS = {
        'NIFTY50': ('data/raw/NSE_NIFTY50_INDEX_1hour.csv', 'NSE:NIFTY50-INDEX'),
        'RELIANCE': ('data/raw/NSE_RELIANCE_EQ_1hour.csv', 'NSE:RELIANCE-EQ'),
        'VBL': ('data/raw/NSE_VBL_EQ_1hour.csv', 'NSE:VBL-EQ'),
        'YESBANK': ('data/raw/NSE_YESBANK_EQ_1hour.csv', 'NSE:YESBANK-EQ'),
        'SUNPHARMA': ('data/raw/NSE_SUNPHARMA_EQ_1hour.csv', 'NSE:SUNPHARMA-EQ'),
    }
    
    # Metric weights for composite scoring
    WEIGHTS = {
        'sharpe_ratio': 0.50,
        'total_return': 0.20,
        'max_drawdown': 0.15,
        'win_rate': 0.10,
        'trade_count': 0.05,
    }
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.file_path, self.symbol_code = self.DATA_PATHS[symbol]
        self.df = self._load_data()
        self.results = []
        
    def _load_data(self) -> pd.DataFrame:
        """Load and prepare data"""
        df = pd.read_csv(self.file_path)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        return df
    
    def _generate_params(self) -> Dict:
        """Generate random parameters based on symbol characteristics"""
        
        # Base parameters (vary for all symbols)
        params = {
            'ker_period': random.choice([8, 10, 12, 15]),
            'rsi_period': random.choice([2, 3]),
            'vol_lookback': random.choice([10, 14, 20]),
            'max_return_cap': 5.0,  # Always cap at 5%
        }
        
        # Symbol-specific tuning
        if self.symbol == 'NIFTY50':
            # NIFTY trends - favor trend-following
            params.update({
                'ker_threshold_meanrev': random.uniform(0.15, 0.25),
                'ker_threshold_trend': random.uniform(0.28, 0.42),
                'rsi_entry': random.randint(28, 38),
                'rsi_exit': random.randint(55, 72),
                'vol_min_pct': random.uniform(0.004, 0.010),
                'ema_fast': random.choice([5, 8, 10]),
                'ema_slow': random.choice([18, 21, 26]),
                'trend_pulse_mult': random.uniform(0.25, 0.50),
                'allowed_hours': random.choice([
                    [9, 10, 11, 12, 13],
                    [9, 10, 11, 12, 13, 14],
                    [10, 11, 12, 13],
                ]),
                'max_hold_bars': random.choice([3, 5, 8, 10]),
            })
        
        elif self.symbol == 'VBL':
            # VBL: High volatility mean reversion
            params.update({
                'ker_threshold_meanrev': random.uniform(0.25, 0.40),
                'ker_threshold_trend': random.uniform(0.55, 0.70),
                'rsi_entry': random.randint(35, 45),
                'rsi_exit': random.randint(88, 98),
                'vol_min_pct': random.uniform(0.008, 0.016),
                'ema_fast': random.choice([5, 8]),
                'ema_slow': random.choice([15, 21]),
                'trend_pulse_mult': random.uniform(0.3, 0.5),
                'allowed_hours': random.choice([
                    [9, 10],
                    [9, 10, 11],
                ]),
                'max_hold_bars': random.choice([8, 10, 12, 15]),
            })
        
        elif self.symbol == 'SUNPHARMA':
            # SUNPHARMA: Conservative mean reversion
            params.update({
                'ker_threshold_meanrev': random.uniform(0.28, 0.40),
                'ker_threshold_trend': random.uniform(0.50, 0.65),
                'rsi_entry': random.randint(38, 48),
                'rsi_exit': random.randint(52, 68),
                'vol_min_pct': random.uniform(0.002, 0.006),
                'ema_fast': random.choice([5, 8]),
                'ema_slow': random.choice([15, 21]),
                'trend_pulse_mult': random.uniform(0.3, 0.5),
                'allowed_hours': random.choice([
                    [9, 10, 11],
                    [10, 11],
                    [10, 11, 12],
                ]),
                'max_hold_bars': random.choice([6, 8, 10]),
            })
        
        elif self.symbol == 'YESBANK':
            # YESBANK: Mixed with outlier control
            params.update({
                'ker_threshold_meanrev': random.uniform(0.18, 0.28),
                'ker_threshold_trend': random.uniform(0.45, 0.60),
                'rsi_entry': random.randint(18, 28),
                'rsi_exit': random.randint(72, 88),
                'vol_min_pct': random.uniform(0.003, 0.007),
                'ema_fast': random.choice([5, 8]),
                'ema_slow': random.choice([15, 21]),
                'trend_pulse_mult': random.uniform(0.35, 0.55),
                'allowed_hours': random.choice([
                    [9, 10, 11, 13],
                    [9, 10, 11, 12, 13],
                    [9, 11, 13],
                ]),
                'max_hold_bars': random.choice([1, 2, 3, 4]),
            })
        
        elif self.symbol == 'RELIANCE':
            # RELIANCE: Hybrid focus
            params.update({
                'ker_threshold_meanrev': random.uniform(0.22, 0.35),
                'ker_threshold_trend': random.uniform(0.42, 0.58),
                'rsi_entry': random.randint(25, 35),
                'rsi_exit': random.randint(78, 92),
                'vol_min_pct': random.uniform(0.003, 0.007),
                'ema_fast': random.choice([5, 8]),
                'ema_slow': random.choice([15, 21]),
                'trend_pulse_mult': random.uniform(0.3, 0.5),
                'allowed_hours': random.choice([
                    [9, 10],
                    [9, 10, 11],
                    [9, 10, 11, 12],
                ]),
                'max_hold_bars': random.choice([4, 6, 8]),
            })
        
        return params
    
    def _evaluate(self, params: Dict) -> Dict:
        """Evaluate parameter set"""
        strategy = HybridAdaptiveStrategy(params)
        
        try:
            trades, metrics = strategy.backtest(self.df)
        except Exception as e:
            print(f"  Error: {e}")
            return None
        
        # Calculate composite score
        score = self._composite_score(metrics)
        
        return {
            'params': params,
            'metrics': metrics,
            'score': score,
        }
    
    def _composite_score(self, metrics: Dict) -> float:
        """Calculate weighted composite score"""
        # Normalize scores
        sharpe_score = min(max(metrics['sharpe_ratio'] / 3.0, -1), 1)
        return_score = min(max(metrics['total_return_pct'] / 20.0, -1), 1)
        drawdown_score = 1 - min(abs(metrics['max_drawdown_pct']) / 10.0, 1)
        win_rate_score = metrics['win_rate'] / 100.0
        
        # Trade count penalty
        if metrics['total_trades'] >= 120:
            trade_score = 1.0
        else:
            trade_score = metrics['total_trades'] / 120
        
        score = (
            self.WEIGHTS['sharpe_ratio'] * sharpe_score +
            self.WEIGHTS['total_return'] * return_score +
            self.WEIGHTS['max_drawdown'] * drawdown_score +
            self.WEIGHTS['win_rate'] * win_rate_score +
            self.WEIGHTS['trade_count'] * trade_score
        )
        
        return score
    
    def optimize(self, n_iterations: int = 300) -> Dict:
        """Run optimization"""
        print(f"\n{'='*70}")
        print(f"OPTIMIZING {self.symbol} ({n_iterations} iterations)")
        print(f"{'='*70}")
        
        random.seed(42 + hash(self.symbol) % 1000)
        
        results = []
        best_score = -999
        best_result = None
        
        for i in range(n_iterations):
            params = self._generate_params()
            result = self._evaluate(params)
            
            if result is None:
                continue
            
            results.append(result)
            
            # Track best
            if result['metrics']['total_trades'] >= 120 and result['score'] > best_score:
                best_score = result['score']
                best_result = result
                print(f"  [{i+1}] New best: Sharpe={result['metrics']['sharpe_ratio']:.2f}, "
                      f"Return={result['metrics']['total_return_pct']:.2f}%, "
                      f"Trades={result['metrics']['total_trades']}")
            
            if (i + 1) % 50 == 0:
                print(f"  Progress: {i+1}/{n_iterations}")
        
        # Final results
        valid_results = [r for r in results if r['metrics']['total_trades'] >= 120]
        
        print(f"\n{'='*70}")
        print(f"OPTIMIZATION COMPLETE: {self.symbol}")
        print(f"{'='*70}")
        print(f"Total tested: {len(results)}")
        print(f"Valid (≥120 trades): {len(valid_results)}")
        
        if best_result:
            m = best_result['metrics']
            print(f"\n🏆 BEST RESULT:")
            print(f"   Trades: {m['total_trades']} (MeanRev: {m['meanrev_trades']}, Trend: {m['trend_trades']})")
            print(f"   Return: {m['total_return_pct']:.2f}%")
            print(f"   Sharpe: {m['sharpe_ratio']:.3f}")
            print(f"   Win Rate: {m['win_rate']:.1f}%")
            print(f"   Max Drawdown: {m['max_drawdown_pct']:.2f}%")
            print(f"   Max Trade Return: {m['max_return']:.2f}%")
        
        return best_result


def optimize_all_symbols(n_iterations: int = 300) -> Dict:
    """Optimize all 5 symbols"""
    print("="*70)
    print("SHARPE RATIO OPTIMIZATION - ALL SYMBOLS")
    print("="*70)
    
    all_results = {}
    
    for symbol in SharpeOptimizer.SYMBOLS:
        optimizer = SharpeOptimizer(symbol)
        result = optimizer.optimize(n_iterations)
        
        if result:
            all_results[symbol] = result
    
    # Portfolio summary
    print("\n" + "="*70)
    print("PORTFOLIO SUMMARY")
    print("="*70)
    
    total_sharpe = 0
    total_return = 0
    count = 0
    
    for symbol, result in all_results.items():
        m = result['metrics']
        print(f"\n{symbol}:")
        print(f"  Trades: {m['total_trades']}")
        print(f"  Return: {m['total_return_pct']:.2f}%")
        print(f"  Sharpe: {m['sharpe_ratio']:.3f}")
        
        total_sharpe += m['sharpe_ratio']
        total_return += m['total_return_pct']
        count += 1
    
    avg_sharpe = total_sharpe / count if count > 0 else 0
    avg_return = total_return / count if count > 0 else 0
    
    print(f"\n{'='*70}")
    print(f"PORTFOLIO AVERAGE")
    print(f"{'='*70}")
    print(f"Average Sharpe: {avg_sharpe:.3f}")
    print(f"Average Return: {avg_return:.2f}%")
    
    # Estimate rank
    if avg_sharpe > 1.3:
        rank = "Top 3-5"
    elif avg_sharpe > 1.15:
        rank = "Top 5-8"
    elif avg_sharpe > 1.0:
        rank = "Top 8-12"
    elif avg_sharpe > 0.8:
        rank = "Top 12-18"
    else:
        rank = "Below Top 18"
    
    print(f"Estimated Rank: {rank} / 100")
    
    # Save results
    save_results = {}
    for symbol, result in all_results.items():
        save_results[symbol] = {
            'params': result['params'],
            'metrics': {
                'total_trades': result['metrics']['total_trades'],
                'total_return_pct': result['metrics']['total_return_pct'],
                'sharpe_ratio': result['metrics']['sharpe_ratio'],
                'win_rate': result['metrics']['win_rate'],
                'max_drawdown_pct': result['metrics']['max_drawdown_pct'],
            }
        }
    
    os.makedirs('output', exist_ok=True)
    with open('output/sharpe_optimized_params.json', 'w') as f:
        json.dump(save_results, f, indent=2, default=str)
    
    print(f"\n✅ Results saved to: output/sharpe_optimized_params.json")
    
    return all_results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Single symbol mode
        symbol = sys.argv[1]
        n_iter = int(sys.argv[2]) if len(sys.argv) > 2 else 300
        
        optimizer = SharpeOptimizer(symbol)
        result = optimizer.optimize(n_iter)
    else:
        # All symbols mode
        optimize_all_symbols(300)
