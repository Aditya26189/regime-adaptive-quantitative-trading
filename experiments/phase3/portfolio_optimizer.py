
"""
Portfolio-level optimization: Allocate capital optimally across 5 symbols
Based on Markowitz Mean-Variance framework
"""

import pandas as pd
import numpy as np
from scipy.optimize import minimize
import json
import sys
import os

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../'))
sys.path.insert(0, project_root)

class PortfolioOptimizer:
    """
    Optimize capital allocation across 5 symbols to maximize portfolio Sharpe
    
    Constraints:
    - Each symbol must trade (min 120 trades)
    - Total capital = 100,000
    - No leverage (sum of allocations = 1.0)
    """
    
    def __init__(self, symbol_strategies, initial_capital=10000000):
        """
        Args:
            symbol_strategies: Dict of {symbol: (strategy_class, params)}
            initial_capital: Starting capital
        """
        self.symbol_strategies = symbol_strategies
        self.initial_capital = initial_capital
        self.symbols = list(symbol_strategies.keys())
        
    def backtest_symbol(self, symbol, strategy_class, params, allocated_capital):
        """Backtest single symbol with allocated capital"""
        
        # Load data
        filepath_map = {
            'NIFTY50': 'data/raw/NSE_NIFTY50_INDEX_1hour.csv',
            'RELIANCE': 'data/raw/NSE_RELIANCE_EQ_1hour.csv',
            'VBL': 'data/raw/NSE_VBL_EQ_1hour.csv',
            'YESBANK': 'data/raw/NSE_YESBANK_EQ_1hour.csv',
            'SUNPHARMA': 'data/raw/NSE_SUNPHARMA_EQ_1hour.csv',
        }
        
        full_path = os.path.join(project_root, filepath_map[symbol])
        if not os.path.exists(full_path):
             full_path = full_path.replace('data/raw/', 'data/')
        
        df = pd.read_csv(full_path)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        
        # Backtest with allocated capital
        strategy = strategy_class(params)
        
        if symbol == 'NIFTY50' and hasattr(strategy, 'backtest_with_ladder_exits'):
             trades, metrics = strategy.backtest_with_ladder_exits(df, initial_capital=allocated_capital)
        else:
             trades, metrics = strategy.backtest(df, initial_capital=allocated_capital)
        
        return trades, metrics
    
    def calculate_portfolio_metrics(self, allocations):
        """
        Calculate portfolio Sharpe for given capital allocations
        
        Args:
            allocations: Array of 5 values summing to 1.0
        
        Returns:
            portfolio_sharpe: Average Sharpe across symbols
            symbol_metrics: Individual symbol metrics
        """
        
        symbol_metrics = {}
        
        for i, symbol in enumerate(self.symbols):
            allocated_capital = self.initial_capital * allocations[i]
            
            if allocated_capital < 1000:  # Skip if too little capital
                symbol_metrics[symbol] = {
                    'sharpe_ratio': 0,
                    'total_trades': 0,
                    'total_return_pct': 0
                }
                continue
            
            strategy_class, params = self.symbol_strategies[symbol]
            
            try:
                trades, metrics = self.backtest_symbol(
                    symbol, strategy_class, params, allocated_capital
                )
                symbol_metrics[symbol] = metrics
                
            except Exception as e:
                # print(f"  Error backtesting {symbol}: {e}")
                symbol_metrics[symbol] = {
                    'sharpe_ratio': 0,
                    'total_trades': 0,
                    'total_return_pct': 0
                }
        
        # Calculate portfolio Sharpe (average of symbols)
        sharpes = [m['sharpe_ratio'] for m in symbol_metrics.values()]
        portfolio_sharpe = np.mean(sharpes)
        
        # Check trade count constraint
        trade_counts = [m['total_trades'] for m in symbol_metrics.values()]
        min_trades = min(trade_counts) if trade_counts else 0
        
        # Penalize if any symbol < 120 trades
        if min_trades < 120:
            portfolio_sharpe -= (120 - min_trades) * 0.1  # Heavy penalty
        
        return portfolio_sharpe, symbol_metrics
    
    def optimize_allocations(self, initial_guess=None):
        """
        Find optimal capital allocation to maximize portfolio Sharpe
        
        Uses scipy.optimize to search allocation space
        """
        
        if initial_guess is None:
            # Equal allocation as starting point
            initial_guess = np.array([0.20, 0.20, 0.20, 0.20, 0.20])
        
        # Objective function (minimize negative Sharpe)
        def objective(allocations):
            portfolio_sharpe, _ = self.calculate_portfolio_metrics(allocations)
            return -portfolio_sharpe  # Negative because we minimize
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1.0},  # Sum to 1.0
        ]
        
        # Bounds (each allocation between 10% and 40%)
        bounds = [(0.10, 0.40) for _ in range(5)]
        
        print("\n" + "="*70)
        print("PORTFOLIO ALLOCATION OPTIMIZATION")
        print("="*70)
        print(f"Initial allocation: {initial_guess}")
        
        # Optimize
        result = minimize(
            objective,
            initial_guess,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 50, 'disp': True}
        )
        
        optimal_allocations = result.x
        optimal_sharpe = -result.fun
        
        print(f"\n✅ OPTIMAL ALLOCATION:")
        for symbol, alloc in zip(self.symbols, optimal_allocations):
            print(f"  {symbol:12} | {alloc*100:5.1f}% | ₹{alloc*self.initial_capital:,.0f}")
        
        print(f"\nOptimal Portfolio Sharpe: {optimal_sharpe:.3f}")
        
        # Get final metrics with optimal allocation
        _, final_metrics = self.calculate_portfolio_metrics(optimal_allocations)
        
        return optimal_allocations, optimal_sharpe, final_metrics


def run_portfolio_optimization():
    """Run portfolio-level capital allocation optimization"""
    
    # Import best strategies from Phase 2
    from src.strategies.hybrid_adaptive import HybridAdaptiveStrategy
    from src.strategies.hybrid_adaptive_v2 import HybridAdaptiveStrategyV2
    from src.strategies.nifty_trend_ladder import NIFTYTrendLadderStrategy
    from src.strategies.vol_adaptive_rsi import VolatilityAdaptiveRSI
    from src.strategies.regime_switching_strategy import RegimeSwitchingStrategy
    
    # Define exact params matched to generate_final_submission_files.py (Phase 2 winning logic)
    
    # NIFTY50
    nifty_params = {
        'ema_fast': 8, 'ema_slow': 21, 'momentum_threshold': 0.002,
        'vol_min_pct': 0.003, 'max_hold_bars': 6, 'stop_loss_pct': 2.0,
        'allowed_hours': [10, 11, 12, 13, 14, 15]
    }
    
    # VBL (Regime Switching)
    vbl_params = {
        'rsi_period': 2,
        'allowed_hours': [10, 11, 12, 13, 14, 15]
    }
    
    # RELIANCE (Advanced V2)
    # Copied from advanced_optimization_results.json
    reliance_params = {
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

    # SUNPHARMA (Advanced V2 Boosted)
    # Base from advanced_optimization_results.json
    sun_params = {
        "ker_period": 15,
        "rsi_period": 4,
        "vol_lookback": 14,
        "max_return_cap": 5.0,
        "ker_threshold_meanrev": 0.38224215306531234,
        "ker_threshold_trend": 0.6094140658792518,
        "rsi_entry": 38,
        "rsi_exit": 52,
        "vol_min_pct": 0.005,
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
    # Boosting logic: rsi_entry + 3, vol_min - 0.001
    sun_params['rsi_entry'] = sun_params.get('rsi_entry', 30) + 3
    sun_params['vol_min_pct'] = max(0.003, sun_params.get('vol_min_pct', 0.005) - 0.001)

    # YESBANK (Baseline Boosted)
    # Base from baseline_metrics.json
    yes_params = {
        "ker_period": 10,
        "rsi_period": 2,
        "vol_lookback": 20,
        "max_return_cap": 5.0,
        "ker_threshold_meanrev": 0.26980488595343255,
        "ker_threshold_trend": 0.47911308589265544,
        "rsi_entry": 23,
        "rsi_exit": 88,
        "vol_min_pct": 0.0054985912613041196,
        "ema_fast": 5,
        "ema_slow": 21,
        "trend_pulse_mult": 0.4097573487563908,
        "allowed_hours": [9, 10, 11, 12, 13],
        "max_hold_bars": 2,
        "_strategy": "SINGLE"
    }
    # Boosting logic: rsi_entry + 4, vol_min - 0.001
    yes_params['rsi_entry'] = yes_params.get('rsi_entry', 30) + 4
    yes_params['vol_min_pct'] = max(0.003, yes_params.get('vol_min_pct', 0.005) - 0.001)

    # Map symbols to their best strategies
    symbol_strategies = {
        'NIFTY50': (NIFTYTrendLadderStrategy, nifty_params),
        'YESBANK': (HybridAdaptiveStrategy, yes_params),
        'RELIANCE': (HybridAdaptiveStrategyV2, reliance_params),
        'VBL': (RegimeSwitchingStrategy, vbl_params),
        'SUNPHARMA': (HybridAdaptiveStrategyV2, sun_params),
    }
    
    # Run optimization
    optimizer = PortfolioOptimizer(symbol_strategies, initial_capital=10000000)
    
    optimal_allocations, optimal_sharpe, final_metrics = optimizer.optimize_allocations()
    
    # Save results
    output_dir = os.path.join(project_root, 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    save_data = {
        'portfolio_sharpe': optimal_sharpe,
        'allocations': {
            symbol: float(alloc) 
            for symbol, alloc in zip(optimizer.symbols, optimal_allocations)
        },
        'symbol_metrics': {
            symbol: {
                'sharpe': metrics['sharpe_ratio'],
                'trades': metrics['total_trades'],
                'return_pct': metrics['total_return_pct']
            }
            for symbol, metrics in final_metrics.items()
        }
    }
    
    with open(os.path.join(output_dir, 'phase3_portfolio_optimization.json'), 'w') as f:
        json.dump(save_data, f, indent=2)
    
    print("\n✅ Results saved to: output/phase3_portfolio_optimization.json")
    
    return optimal_allocations, optimal_sharpe, final_metrics

if __name__ == "__main__":
    run_portfolio_optimization()
