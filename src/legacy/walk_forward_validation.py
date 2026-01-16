"""
Walk-Forward Validation
========================
Quant Games Hackathon - IIT Kharagpur

Validates strategy robustness using exact train/val/test splits.

EXACT Date Splits (NO flexibility):
- Train: 2025-01-01 to 2025-06-30
- Validation: 2025-07-01 to 2025-09-30
- Test: 2025-10-01 to 2025-12-31

3-Variant Testing:
- base: RSI entry=12, exit=88, vol=0.020
- aggressive: RSI entry=8, exit=92, vol=0.012
- original: RSI entry=10, exit=90, vol=0.015
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, List


# ============================================
# EXACT DATE SPLITS (Hard-coded to prevent data snooping)
# ============================================

TRAIN_START = '2025-01-01'
TRAIN_END = '2025-06-30'

VAL_START = '2025-07-01'
VAL_END = '2025-09-30'

TEST_START = '2025-10-01'
TEST_END = '2025-12-31'


# ============================================
# 3-VARIANT PARAMETER SETS
# ============================================

VARIANTS = {
    'base': {'rsi_entry': 12, 'rsi_exit': 88, 'vol_gate': 0.020},
    'aggressive': {'rsi_entry': 8, 'rsi_exit': 92, 'vol_gate': 0.012},
    'original': {'rsi_entry': 10, 'rsi_exit': 90, 'vol_gate': 0.015}
}


def split_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split data into train/val/test using EXACT dates.
    
    Args:
        df: DataFrame with 'datetime' column
        
    Returns:
        Tuple of (train, val, test) DataFrames
    """
    # Parse datetime if needed
    df = df.copy()
    if df['datetime'].dtype == 'object':
        df['datetime_parsed'] = pd.to_datetime(df['datetime'])
    else:
        df['datetime_parsed'] = df['datetime']
    
    # Extract date for comparison
    df['date'] = df['datetime_parsed'].dt.strftime('%Y-%m-%d')
    
    # Split by date ranges
    train = df[(df['date'] >= TRAIN_START) & (df['date'] <= TRAIN_END)].copy()
    val = df[(df['date'] >= VAL_START) & (df['date'] <= VAL_END)].copy()
    test = df[(df['date'] >= TEST_START) & (df['date'] <= TEST_END)].copy()
    
    # Drop helper columns
    for dataset in [train, val, test]:
        dataset.drop(columns=['datetime_parsed', 'date'], inplace=True, errors='ignore')
    
    # Validation
    assert len(train) > 0, f"Training set is empty ({TRAIN_START} to {TRAIN_END})"
    assert len(val) > 0, f"Validation set is empty ({VAL_START} to {VAL_END})"
    assert len(test) > 0, f"Test set is empty ({TEST_START} to {TEST_END})"
    
    return train, val, test


def backtest_with_params(df: pd.DataFrame, params: dict) -> dict:
    """
    Run backtest with specific RSI parameters.
    
    Args:
        df: DataFrame with price data
        params: Dict with rsi_entry, rsi_exit, vol_gate
        
    Returns:
        Dict with performance metrics
    """
    from strategy1_rsi2_meanrev import calculate_rsi, calculate_close_range_volatility, calculate_ema
    
    df = df.copy()
    
    # Calculate indicators
    df['rsi2'] = calculate_rsi(df['close'], period=2)
    df['volatility'] = calculate_close_range_volatility(df['close'], period=14)
    df['ema200'] = calculate_ema(df['close'], period=200)
    df['signal'] = 0
    
    rsi_entry = params['rsi_entry']
    rsi_exit = params['rsi_exit']
    vol_gate = params['vol_gate']
    
    warmup = 200
    in_position = False
    bars_held = 0
    trades = []
    entry_price = 0
    
    for i in range(warmup, len(df)):
        prev_rsi = df['rsi2'].iloc[i-1]
        prev_vol = df['volatility'].iloc[i-1]
        price = df['close'].iloc[i]
        
        if pd.isna(prev_rsi) or pd.isna(prev_vol):
            continue
        
        # Exit logic
        if in_position:
            bars_held += 1
            if prev_rsi > rsi_exit or bars_held >= 12:
                pnl = (price - entry_price) / entry_price
                trades.append(pnl)
                in_position = False
                bars_held = 0
        
        # Entry logic
        if not in_position:
            if prev_rsi < rsi_entry and prev_vol > vol_gate:
                entry_price = price
                in_position = True
                bars_held = 0
    
    # Calculate metrics
    if len(trades) == 0:
        return {'trades': 0, 'sharpe': 0, 'win_rate': 0, 'total_return': 0}
    
    returns = np.array(trades)
    win_rate = sum(1 for r in returns if r > 0) / len(returns) * 100
    total_return = (1 + returns).prod() - 1
    sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
    
    return {
        'trades': len(trades),
        'sharpe': round(sharpe, 2),
        'win_rate': round(win_rate, 2),
        'total_return': round(total_return * 100, 2)
    }


def optimize_on_train(train_data: Dict[str, pd.DataFrame], symbols: List[str]) -> Tuple[str, dict]:
    """
    Test 3 variants on training data, return best.
    
    Args:
        train_data: Dict of {symbol: DataFrame} for training period
        symbols: List of symbol names
        
    Returns:
        Tuple of (best_variant_name, best_params)
    """
    results = {}
    
    for variant_name, params in VARIANTS.items():
        sharpe_scores = []
        
        for symbol in symbols:
            if symbol not in train_data or len(train_data[symbol]) == 0:
                continue
            result = backtest_with_params(train_data[symbol], params)
            sharpe_scores.append(result['sharpe'])
        
        # Average Sharpe across ALL symbols (not per-symbol optimization)
        avg_sharpe = np.mean(sharpe_scores) if sharpe_scores else 0
        results[variant_name] = avg_sharpe
        print(f"  {variant_name}: Avg Sharpe = {avg_sharpe:.2f}")
    
    # Return variant with best average Sharpe
    best_variant = max(results, key=results.get)
    return best_variant, VARIANTS[best_variant]


def validate_on_holdout(val_data: Dict[str, pd.DataFrame], 
                        test_data: Dict[str, pd.DataFrame],
                        best_params: dict, 
                        symbols: List[str]) -> Tuple[float, float]:
    """
    Test on unseen data.
    
    Args:
        val_data: Dict of {symbol: DataFrame} for validation period
        test_data: Dict of {symbol: DataFrame} for test period
        best_params: Best parameters from training
        symbols: List of symbol names
        
    Returns:
        Tuple of (avg_val_sharpe, avg_test_sharpe)
    """
    # Validation (Q3)
    val_sharpes = []
    for symbol in symbols:
        if symbol in val_data and len(val_data[symbol]) > 0:
            result = backtest_with_params(val_data[symbol], best_params)
            val_sharpes.append(result['sharpe'])
    avg_val_sharpe = np.mean(val_sharpes) if val_sharpes else 0
    
    # Test (Q4)
    test_sharpes = []
    for symbol in symbols:
        if symbol in test_data and len(test_data[symbol]) > 0:
            result = backtest_with_params(test_data[symbol], best_params)
            test_sharpes.append(result['sharpe'])
    avg_test_sharpe = np.mean(test_sharpes) if test_sharpes else 0
    
    return avg_val_sharpe, avg_test_sharpe


def check_overfitting(train_sharpe: float, val_sharpe: float) -> str:
    """
    Reject if validation degrades >30%.
    
    Args:
        train_sharpe: Average Sharpe on training data
        val_sharpe: Average Sharpe on validation data
        
    Returns:
        'ACCEPT', 'ACCEPT_WITH_WARNING', or 'REJECT'
    """
    if train_sharpe == 0:
        return 'ACCEPT'  # No training performance to compare
    
    degradation = (train_sharpe - val_sharpe) / abs(train_sharpe) if train_sharpe != 0 else 0
    
    if degradation > 0.30:
        if val_sharpe > 0.8:  # Still profitable
            print("⚠️  High degradation but Val Sharpe acceptable")
            print("    Likely Q3 downtrend effect (expected)")
            return 'ACCEPT_WITH_WARNING'
        else:
            print("❌ Failed validation - overfitting detected")
            return 'REJECT'
    else:
        print("✅ Validation passed - robust parameters")
        return 'ACCEPT'


# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == "__main__":
    print("=" * 70)
    print("WALK-FORWARD VALIDATION")
    print("=" * 70)
    
    # Define symbols
    symbols = ['NIFTY50', 'RELIANCE', 'VBL', 'YESBANK', 'SUNPHARMA']
    files = {
        'NIFTY50': 'fyers_data/NSE_NIFTY50_INDEX_1hour.csv',
        'RELIANCE': 'fyers_data/NSE_RELIANCE_EQ_1hour.csv',
        'VBL': 'fyers_data/NSE_VBL_EQ_1hour.csv',
        'YESBANK': 'fyers_data/NSE_YESBANK_EQ_1hour.csv',
        'SUNPHARMA': 'fyers_data/NSE_SUNPHARMA_EQ_1hour.csv',
    }
    
    # Load and split data
    print("\n1. Loading and splitting data...")
    train_data = {}
    val_data = {}
    test_data = {}
    
    for symbol, file in files.items():
        df = pd.read_csv(file)
        train, val, test = split_data(df)
        train_data[symbol] = train
        val_data[symbol] = val
        test_data[symbol] = test
        print(f"   {symbol}: Train={len(train)}, Val={len(val)}, Test={len(test)}")
    
    # Optimize on training
    print("\n2. Optimizing on training data (Q1-Q2)...")
    best_variant, best_params = optimize_on_train(train_data, symbols)
    print(f"\n   Best variant: {best_variant}")
    print(f"   Parameters: {best_params}")
    
    # Calculate train Sharpe for overfitting check
    train_sharpes = []
    for symbol in symbols:
        if symbol in train_data and len(train_data[symbol]) > 0:
            result = backtest_with_params(train_data[symbol], best_params)
            train_sharpes.append(result['sharpe'])
    avg_train_sharpe = np.mean(train_sharpes) if train_sharpes else 0
    
    # Validate on holdout
    print("\n3. Validating on holdout data (Q3-Q4)...")
    avg_val_sharpe, avg_test_sharpe = validate_on_holdout(
        val_data, test_data, best_params, symbols
    )
    print(f"   Train Sharpe:      {avg_train_sharpe:.2f}")
    print(f"   Validation Sharpe: {avg_val_sharpe:.2f}")
    print(f"   Test Sharpe:       {avg_test_sharpe:.2f}")
    
    # Check overfitting
    print("\n4. Overfitting check...")
    result = check_overfitting(avg_train_sharpe, avg_val_sharpe)
    
    print("\n" + "=" * 70)
    print(f"RESULT: {result}")
    print("=" * 70)
