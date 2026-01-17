
"""
Ornstein-Uhlenbeck Mean Reversion: Optimal Entry/Exit Calculation
Based on Bertram (2010) - "Optimal Mean Reversion Trading with Transaction Costs"
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from scipy.stats import norm
import sys
import os
import json

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../'))
sys.path.insert(0, project_root)

from src.strategies.hybrid_adaptive import HybridAdaptiveStrategy

class OUOptimalThresholds:
    """
    Calculate optimal RSI entry/exit thresholds using OU process theory
    """
    
    def __init__(self, transaction_cost_pct=0.0048):
        """
        Args:
            transaction_cost_pct: Round-trip transaction cost as fraction (0.48% = 48 basis points)
        """
        self.transaction_cost = transaction_cost_pct
    
    def estimate_ou_parameters(self, prices, window=60):
        """
        Estimate OU parameters from price series
        """
        # Use log prices for better stationarity
        log_prices = np.log(prices)
        
        # Estimate using discrete approximation
        # ΔY = κ(μ - Y_{t-1})Δt + σ√Δt * ε
        
        delta_y = log_prices.diff().dropna()
        y_lag = log_prices.shift(1).dropna()
        
        # Align series
        delta_y = delta_y.iloc[-len(y_lag):]
        
        # Linear regression: ΔY ~ a + b*Y_{t-1}
        from scipy.stats import linregress
        
        slope, intercept, _, _, _ = linregress(y_lag, delta_y)
        
        # Extract parameters
        # slope = -κΔt, intercept = κμΔt
        dt = 1.0  # 1-hour bars
        
        kappa = -slope / dt
        mu = intercept / (kappa * dt) if kappa != 0 else y_lag.mean()
        sigma = delta_y.std() / np.sqrt(dt)
        
        return kappa, mu, sigma
    
    def calculate_optimal_entry_threshold(self, kappa, mu, sigma, risk_free_rate=0.05):
        """
        Calculate optimal entry threshold (how far below mean to enter)
        """
        
        def negative_sharpe(c):
            """
            Objective function: Maximize Sharpe ratio
            """
            
            # Expected spread capture
            expected_return = c * sigma / np.sqrt(2 * kappa) - self.transaction_cost
            
            # Expected holding time
            holding_time = (1 / (2 * kappa)) * np.exp(c**2)
            
            # Variance of returns
            variance = (sigma**2 / (2 * kappa)) * np.exp(c**2)
            
            # Sharpe ratio (annualized)
            if variance > 0 and holding_time > 0:
                sharpe = (expected_return / np.sqrt(variance)) * np.sqrt(252 / holding_time)
            else:
                sharpe = 0
            
            return -sharpe  # Negative because we minimize
        
        # Find optimal c (search between 0.5 and 3.0 standard deviations)
        result = minimize_scalar(negative_sharpe, bounds=(0.5, 3.0), method='bounded')
        
        optimal_c = result.x
        
        # Convert to entry threshold (how many std devs below mean)
        entry_threshold_stds = optimal_c
        
        return entry_threshold_stds, -result.fun  # Return threshold and Sharpe
    
    def map_to_rsi_threshold(self, ou_threshold_stds, rsi_series):
        """
        Map OU threshold (in std deviations) to RSI value
        """
        
        # Map: μ - c*σ (OU) → RSI percentile
        # Assume RSI ~ Normal (approximate, not exact but close enough)
        
        percentile = norm.cdf(-ou_threshold_stds) * 100
        
        rsi_threshold = np.percentile(rsi_series.dropna(), percentile)
        
        return rsi_threshold
    
    def calculate_optimal_rsi_thresholds(self, df, rsi_column='RSI', price_column='close', window=60):
        """
        Calculate optimal RSI entry/exit thresholds for a given symbol
        """
        
        prices = df[price_column].iloc[-window:]
        rsi = df[rsi_column].iloc[-window:]
        
        # Estimate OU parameters from prices
        kappa, mu, sigma = self.estimate_ou_parameters(prices, window)
        
        print(f"  OU Parameters: κ={kappa:.4f}, μ={mu:.4f}, σ={sigma:.4f}")
        
        # Calculate optimal threshold
        entry_threshold_stds, expected_sharpe = self.calculate_optimal_entry_threshold(kappa, mu, sigma)
        
        print(f"  Optimal entry: {entry_threshold_stds:.2f} std devs below mean")
        print(f"  Expected Sharpe (OU theory): {expected_sharpe:.3f}")
        
        # Map to RSI values
        optimal_rsi_entry = self.map_to_rsi_threshold(entry_threshold_stds, rsi)
        
        # Exit threshold: symmetric (same distance above mean)
        # RSI is bounded , so use symmetry around 50
        optimal_rsi_exit = 100 - optimal_rsi_entry
        
        # Bound to reasonable ranges
        optimal_rsi_entry = max(15, min(optimal_rsi_entry, 35))
        optimal_rsi_exit = max(65, min(optimal_rsi_exit, 85))
        
        return {
            'rsi_entry': int(optimal_rsi_entry),
            'rsi_exit': int(optimal_rsi_exit),
            'ou_kappa': kappa,
            'ou_sigma': sigma,
            'expected_sharpe': expected_sharpe,
            'entry_stds': entry_threshold_stds
        }


# TESTING SCRIPT
def test_ou_optimal_thresholds():
    """Test OU-derived optimal thresholds on all symbols"""
    
    symbols = {
        'YESBANK': 'data/raw/NSE_YESBANK_EQ_1hour.csv',
        'RELIANCE': 'data/raw/NSE_RELIANCE_EQ_1hour.csv',
        'VBL': 'data/raw/NSE_VBL_EQ_1hour.csv',
        'SUNPHARMA': 'data/raw/NSE_SUNPHARMA_EQ_1hour.csv',
    }
    
    ou_calculator = OUOptimalThresholds(transaction_cost_pct=0.0048)
    
    results = {}
    
    for symbol, filepath in symbols.items():
        print("\n" + "="*70)
        print(f"OU OPTIMAL THRESHOLDS: {symbol}")
        print("="*70)
        
        full_path = os.path.join(project_root, filepath)
        if not os.path.exists(full_path):
             full_path = full_path.replace('data/raw/', 'data/')
        
        df = pd.read_csv(full_path)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        
        # Calculate RSI first
        def calculate_rsi(close, period=2):
            delta = close.diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(period).mean()
            avg_loss = loss.rolling(period).mean()
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.fillna(50)
        
        df['RSI'] = calculate_rsi(df['close'], period=2)
        
        # Get OU-optimal thresholds
        ou_thresholds = ou_calculator.calculate_optimal_rsi_thresholds(df, window=120)
        
        print(f"\n📊 OPTIMAL THRESHOLDS:")
        print(f"  RSI Entry: {ou_thresholds['rsi_entry']} (OU-derived)")
        print(f"  RSI Exit: {ou_thresholds['rsi_exit']} (OU-derived)")
        print(f"  Theoretical Sharpe: {ou_thresholds['expected_sharpe']:.3f}")
        
        # Test with baseline strategy using OU thresholds
        ou_params = {
            'ker_period': 10,
            'rsi_period': 2,
            'rsi_entry': ou_thresholds['rsi_entry'],
            'rsi_exit': ou_thresholds['rsi_exit'],
            'vol_min_pct': 0.005,
            'max_hold_bars': 10,
            'allowed_hours': [10, 11, 12, 13, 14],
            'max_return_cap': 5.0,
            'ker_threshold_meanrev': 0.30,
            'ker_threshold_trend': 0.50,
            'ema_fast': 8,
            'ema_slow': 21,
            'trend_pulse_mult': 0.4,
        }
        
        # Test OU-optimized params
        print(f"\n🧪 TESTING OU-OPTIMIZED PARAMS...")
        strategy = HybridAdaptiveStrategy(ou_params)
        trades, metrics = strategy.backtest(df)
        
        print(f"  Trades: {metrics['total_trades']}")
        print(f"  Sharpe: {metrics['sharpe_ratio']:.3f}")
        print(f"  Return: {metrics['total_return_pct']:.2f}%")
        print(f"  Win Rate: {metrics['win_rate']:.1f}%")
        
        # Compare to baseline (RSI 30/70)
        baseline_params = ou_params.copy()
        baseline_params['rsi_entry'] = 30
        baseline_params['rsi_exit'] = 70
        
        baseline_strategy = HybridAdaptiveStrategy(baseline_params)
        baseline_trades, baseline_metrics = baseline_strategy.backtest(df)
        
        print(f"\n📈 BASELINE (RSI 30/70):")
        print(f"  Sharpe: {baseline_metrics['sharpe_ratio']:.3f}")
        print(f"  Trades: {baseline_metrics['total_trades']}")
        
        improvement = metrics['sharpe_ratio'] - baseline_metrics['sharpe_ratio']
        print(f"\n{'✅' if improvement > 0 else '❌'} OU Improvement: {improvement:+.3f} Sharpe")
        
        results[symbol] = {
            'ou_thresholds': ou_thresholds,
            'ou_metrics': metrics,
            'baseline_metrics': baseline_metrics,
            'improvement': improvement,
            'params': ou_params
        }
    
    # Save results
    output_dir = os.path.join(project_root, 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    save_data = {}
    for symbol, result in results.items():
        save_data[symbol] = {
            'rsi_entry': result['ou_thresholds']['rsi_entry'],
            'rsi_exit': result['ou_thresholds']['rsi_exit'],
            'sharpe': result['ou_metrics']['sharpe_ratio'],
            'trades': result['ou_metrics']['total_trades'],
            'improvement': result['improvement'],
            'params': result['params']
        }
    
    with open(os.path.join(output_dir, 'phase2_ou_optimal.json'), 'w') as f:
        json.dump(save_data, f, indent=2)
    
    print("\n✅ Results saved to: output/phase2_ou_optimal.json")
    
    return results

if __name__ == "__main__":
    test_ou_optimal_thresholds()
