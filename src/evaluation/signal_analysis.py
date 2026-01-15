#!/usr/bin/env python
"""
Signal Information Coefficient (IC) Analysis Tool.

Measures predictive power of each signal using Spearman correlation
with forward returns. Critical for quick signal selection.

Usage:
    python -m src.evaluation.signal_analysis --data data/raw/test.csv
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def compute_signal_ic(
    signal_values: np.ndarray,
    forward_returns: np.ndarray,
    horizon: int = 1
) -> float:
    """
    Compute Information Coefficient (IC).
    
    IC = Spearman correlation between signal and forward returns.
    
    Args:
        signal_values: Array of signal strengths (numeric)
        forward_returns: Array of returns shifted by horizon
        horizon: Forward return horizon (informational only)
        
    Returns:
        IC (float between -1 and +1), or 0 if insufficient data
        
    Interpretation:
        IC > 0.10: Strong predictive signal
        IC > 0.05: Useful signal
        IC > 0.03: Marginal signal
        IC < 0.03: Weak signal (consider dropping)
    """
    # Convert to numpy arrays
    signal = np.asarray(signal_values)
    returns = np.asarray(forward_returns)
    
    # Create valid mask (non-NaN in both)
    valid_mask = ~(np.isnan(signal) | np.isnan(returns) | 
                   np.isinf(signal) | np.isinf(returns))
    
    if valid_mask.sum() < 30:  # Need minimum samples
        return 0.0
    
    signal_valid = signal[valid_mask]
    returns_valid = returns[valid_mask]
    
    # Compute Spearman correlation
    try:
        ic, _ = spearmanr(signal_valid, returns_valid)
        return float(ic) if np.isfinite(ic) else 0.0
    except Exception:
        return 0.0


def compute_ic_by_regime(
    signal_values: np.ndarray,
    forward_returns: np.ndarray,
    regimes: np.ndarray
) -> Dict[str, float]:
    """
    Compute IC separately for each market regime.
    
    Args:
        signal_values: Array of signal strengths
        forward_returns: Array of forward returns
        regimes: Array of regime labels ('CALM', 'NORMAL', 'VOLATILE')
        
    Returns:
        {'CALM': float, 'NORMAL': float, 'VOLATILE': float}
    """
    results = {}
    
    for regime in ['CALM', 'NORMAL', 'VOLATILE']:
        mask = regimes == regime
        
        if mask.sum() < 30:
            results[regime] = np.nan
        else:
            results[regime] = compute_signal_ic(
                signal_values[mask],
                forward_returns[mask]
            )
    
    return results


def classify_regime(df: pd.DataFrame, window: int = 100) -> np.ndarray:
    """
    Classify market regime based on volatility.
    
    Args:
        df: DataFrame with price data
        window: Rolling window for volatility calculation
        
    Returns:
        Array of 'CALM', 'NORMAL', or 'VOLATILE' labels
    """
    # Get price column
    if 'mid' in df.columns:
        price = df['mid']
    elif 'close' in df.columns:
        price = df['close']
    else:
        # Create default
        return np.array(['NORMAL'] * len(df))
    
    # Calculate rolling volatility
    returns = price.pct_change()
    vol = returns.rolling(window=window, min_periods=20).std()
    
    # Calculate percentiles
    vol_25 = vol.quantile(0.25)
    vol_75 = vol.quantile(0.75)
    
    # Classify
    regimes = np.where(
        vol < vol_25, 'CALM',
        np.where(vol > vol_75, 'VOLATILE', 'NORMAL')
    )
    
    # Handle NaN at start
    regimes[:window] = 'NORMAL'
    
    return regimes


def compute_z_score_signal(df: pd.DataFrame, window: int = 20) -> np.ndarray:
    """Compute z-score signal."""
    if 'mid' in df.columns:
        price = df['mid']
    elif 'close' in df.columns:
        price = df['close']
    else:
        return np.zeros(len(df))
    
    rolling_mean = price.rolling(window=window, min_periods=5).mean()
    rolling_std = price.rolling(window=window, min_periods=5).std()
    
    z_score = (price - rolling_mean) / rolling_std
    z_score = z_score.fillna(0)
    
    # Negate: negative z-score = bullish (mean reversion)
    return -z_score.values


def compute_obi_signal(df: pd.DataFrame) -> np.ndarray:
    """Compute Order Book Imbalance signal."""
    # Find volume columns
    bid_vol = None
    ask_vol = None
    
    for col in ['bid_qty', 'bid_vol', 'bid_vol_1']:
        if col in df.columns:
            bid_vol = df[col]
            break
    
    for col in ['ask_qty', 'ask_vol', 'ask_vol_1']:
        if col in df.columns:
            ask_vol = df[col]
            break
    
    if bid_vol is None or ask_vol is None:
        return np.zeros(len(df))
    
    total = bid_vol + ask_vol
    obi = np.where(total > 0, (bid_vol - ask_vol) / total, 0)
    
    return obi


def compute_microprice_signal(df: pd.DataFrame) -> np.ndarray:
    """Compute microprice deviation signal."""
    if not all(col in df.columns for col in ['bid', 'ask']):
        return np.zeros(len(df))
    
    mid = (df['bid'] + df['ask']) / 2
    
    # Find volume columns
    bid_vol = None
    ask_vol = None
    
    for col in ['bid_qty', 'bid_vol', 'bid_vol_1']:
        if col in df.columns:
            bid_vol = df[col]
            break
    
    for col in ['ask_qty', 'ask_vol', 'ask_vol_1']:
        if col in df.columns:
            ask_vol = df[col]
            break
    
    if bid_vol is None or ask_vol is None:
        return np.zeros(len(df))
    
    total = bid_vol + ask_vol
    microprice = np.where(
        total > 0,
        (df['bid'] * ask_vol + df['ask'] * bid_vol) / total,
        mid
    )
    
    # Deviation from mid
    deviation = microprice - mid
    
    return deviation


def compute_momentum_signal(df: pd.DataFrame, lookback: int = 5) -> np.ndarray:
    """Compute momentum signal (short-term price change)."""
    if 'mid' in df.columns:
        price = df['mid']
    elif 'close' in df.columns:
        price = df['close']
    else:
        return np.zeros(len(df))
    
    momentum = price.pct_change(lookback).fillna(0)
    
    return momentum.values


def compute_spread_signal(df: pd.DataFrame) -> np.ndarray:
    """Compute spread signal (wider spread = less liquidity)."""
    if not all(col in df.columns for col in ['bid', 'ask']):
        return np.zeros(len(df))
    
    spread = df['ask'] - df['bid']
    mid = (df['bid'] + df['ask']) / 2
    
    # Relative spread
    rel_spread = np.where(mid > 0, spread / mid, 0)
    
    # Negate: wider spread = bearish
    return -rel_spread


def analyze_all_signals(
    df: pd.DataFrame,
    horizon: int = 1
) -> Dict[str, Dict[str, Any]]:
    """
    Analyze IC for all available signals.
    
    Args:
        df: DataFrame with market data and features
        horizon: Forward return horizon (default: 1 tick)
        
    Returns:
        Dict with IC metrics for each signal
    """
    results = {}
    
    # Calculate forward returns
    if 'mid' in df.columns:
        price = df['mid']
    elif 'close' in df.columns:
        price = df['close']
    else:
        print("Warning: No price column found")
        return {}
    
    forward_returns = price.pct_change().shift(-horizon).values
    
    # Classify regimes
    regimes = classify_regime(df)
    
    # Define signals to analyze
    signals = {
        'z_score': compute_z_score_signal(df),
        'obi': compute_obi_signal(df),
        'microprice': compute_microprice_signal(df),
        'momentum': compute_momentum_signal(df),
        'spread': compute_spread_signal(df)
    }
    
    # Analyze each signal
    for signal_name, signal_values in signals.items():
        # Overall IC
        ic = compute_signal_ic(signal_values, forward_returns)
        
        # Regime-specific IC
        regime_ic = compute_ic_by_regime(signal_values, forward_returns, regimes)
        
        # Determine recommendation
        if pd.isna(ic) or ic == 0:
            recommendation = '❓ INSUFFICIENT_DATA'
        elif abs(ic) > 0.10:
            recommendation = '✅ USE (strong)'
        elif abs(ic) > 0.05:
            recommendation = '⚠️  USE (moderate)'
        elif abs(ic) > 0.03:
            recommendation = '⚠️  MARGINAL'
        else:
            recommendation = '❌ SKIP (weak)'
        
        results[signal_name] = {
            'ic': ic,
            'CALM': regime_ic.get('CALM', np.nan),
            'NORMAL': regime_ic.get('NORMAL', np.nan),
            'VOLATILE': regime_ic.get('VOLATILE', np.nan),
            'recommendation': recommendation
        }
    
    return results


def print_signal_report(results: Dict[str, Dict[str, Any]]) -> None:
    """
    Pretty-print IC analysis table.
    
    Args:
        results: Output from analyze_all_signals()
    """
    print("\n" + "=" * 80)
    print(f"{'SIGNAL INFORMATION COEFFICIENT (IC) ANALYSIS':^80}")
    print("=" * 80)
    
    if not results:
        print("\n⚠️  No signals analyzed. Check data format.")
        return
    
    # Header
    print(f"\n{'Signal':<12} {'IC':>8} {'IC_Calm':>10} {'IC_Normal':>10} {'IC_Volatile':>12} {'Recommendation':<20}")
    print("-" * 80)
    
    # Sort by absolute IC
    sorted_signals = sorted(
        results.items(),
        key=lambda x: abs(x[1]['ic']) if not pd.isna(x[1]['ic']) else -1,
        reverse=True
    )
    
    for signal_name, metrics in sorted_signals:
        ic = metrics['ic']
        calm = metrics['CALM']
        normal = metrics['NORMAL']
        volatile = metrics['VOLATILE']
        rec = metrics['recommendation']
        
        ic_str = f"{ic:+.4f}" if not pd.isna(ic) else "N/A"
        calm_str = f"{calm:+.4f}" if not pd.isna(calm) else "N/A"
        normal_str = f"{normal:+.4f}" if not pd.isna(normal) else "N/A"
        volatile_str = f"{volatile:+.4f}" if not pd.isna(volatile) else "N/A"
        
        print(f"{signal_name:<12} {ic_str:>8} {calm_str:>10} {normal_str:>10} {volatile_str:>12} {rec:<20}")
    
    print("=" * 80)
    
    # Legend
    print("\nIC INTERPRETATION:")
    print("  |IC| > 0.10  →  Strong predictive power")
    print("  |IC| > 0.05  →  Useful signal")
    print("  |IC| > 0.03  →  Marginal signal")
    print("  |IC| < 0.03  →  Weak signal (consider dropping)")
    print("\nNote: Positive IC = signal predicts positive returns")
    print("      Negative IC = signal predicts negative returns (inverse)")


def get_top_signals(
    results: Dict[str, Dict[str, Any]],
    n: int = 3,
    min_ic: float = 0.03
) -> List[str]:
    """
    Get top N signals by IC.
    
    Args:
        results: Output from analyze_all_signals()
        n: Number of top signals to return
        min_ic: Minimum absolute IC threshold
        
    Returns:
        List of signal names
    """
    # Filter by minimum IC
    valid_signals = [
        (name, abs(metrics['ic']))
        for name, metrics in results.items()
        if not pd.isna(metrics['ic']) and abs(metrics['ic']) >= min_ic
    ]
    
    # Sort by IC
    valid_signals.sort(key=lambda x: x[1], reverse=True)
    
    return [name for name, _ in valid_signals[:n]]


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Analyze signal Information Coefficients'
    )
    
    parser.add_argument(
        '--data', '-d',
        type=str,
        required=True,
        help='Path to market data CSV'
    )
    
    parser.add_argument(
        '--horizon',
        type=int,
        default=1,
        help='Forward return horizon (default: 1)'
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Add path for imports
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    from src.data.loader import DataLoader
    from src.data.features import FeatureEngine
    
    print("\n" + "=" * 80)
    print("SIGNAL IC ANALYSIS")
    print("=" * 80)
    
    # Load data
    print(f"\nLoading data from {args.data}...")
    loader = DataLoader(verbose=False)
    df = loader.load_csv(args.data)
    df = loader.add_mid_price(df)
    
    engine = FeatureEngine(verbose=False)
    df = engine.add_all(df)
    df = engine.fill_missing(df)
    
    print(f"  ✓ Loaded {len(df)} rows")
    
    # Analyze
    results = analyze_all_signals(df, horizon=args.horizon)
    
    # Print report
    print_signal_report(results)
    
    # Print top signals
    top = get_top_signals(results)
    if top:
        print(f"\n🎯 TOP SIGNALS: {', '.join(top)}")


if __name__ == '__main__':
    main()
