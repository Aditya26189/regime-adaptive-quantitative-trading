"""
RSI(2) Strategy Testing & Validation Suite
===========================================
Quant Games Hackathon - IIT Kharagpur

This file contains comprehensive tests to validate:
1. Helper function correctness (RSI, Volatility)
2. Signal generation on real data
3. Trade count requirements
4. Output format compliance
"""

import pandas as pd
import numpy as np
import sys
import os

# Import strategy functions
from strategy1_rsi2_meanrev import (
    calculate_rsi, 
    calculate_close_range_volatility,
    calculate_ema,
    generate_signals,
    Config,
    BacktestEngine
)


def test_rsi_calculation():
    """
    TEST 1: Validate RSI(2) calculation
    """
    print("=" * 60)
    print("TEST 1: RSI(2) Calculation Validation")
    print("=" * 60)
    
    # Test data: Simple uptrend
    test_prices = pd.Series([
        100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 
        108, 110, 112, 111, 113, 115, 114, 116, 118, 117
    ])
    
    # Calculate RSI(2)
    rsi2 = calculate_rsi(test_prices, period=2)
    
    print(f"Test data: {len(test_prices)} price points")
    print(f"RSI values (last 5): {rsi2.tail(5).values}")
    print(f"RSI range: {rsi2.min():.1f} - {rsi2.max():.1f}")
    print(f"Expected range: 0.0 - 100.0")
    
    # Validation checks
    check1 = 0 <= rsi2.dropna().min() <= 100
    check2 = 0 <= rsi2.dropna().max() <= 100
    check3 = len(rsi2) == len(test_prices)
    
    if check1 and check2 and check3:
        print("✓ PASS - RSI values within valid range")
        return True
    else:
        print("✗ FAIL - RSI values out of range or length mismatch")
        return False


def test_volatility_calculation():
    """
    TEST 2: Validate Close-Range Volatility calculation
    """
    print("\n" + "=" * 60)
    print("TEST 2: Volatility Calculation Validation")
    print("=" * 60)
    
    # Test data
    test_prices = pd.Series([
        100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 
        108, 110, 112, 111, 113, 115, 114, 116, 118, 117
    ])
    
    # Calculate volatility
    vol = calculate_close_range_volatility(test_prices, period=14)
    
    print(f"Test data: {len(test_prices)} price points")
    print(f"Volatility values (last 5): {vol.tail(5).values}")
    print(f"Volatility range: {vol.dropna().min():.4f} - {vol.dropna().max():.4f}")
    print(f"Expected: 0.001 - 0.200 (0.1% - 20%)")
    
    # Calculate expected: (max-min)/current for last point
    # For period 14, using last 14 values: [107, 109, 108, 110, 112, 111, 113, 115, 114, 116, 118, 117]
    # That's actually only 12 values after index 8
    
    # Validation checks
    check1 = vol.dropna().min() >= 0
    check2 = vol.dropna().max() <= 1.0  # Should never be > 100%
    check3 = len(vol) == len(test_prices)
    
    if check1 and check2 and check3:
        print("✓ PASS - Volatility values within valid range")
        return True
    else:
        print("✗ FAIL - Volatility values out of range")
        return False


def test_signal_generation_nifty():
    """
    TEST 3: Signal Generation on NIFTY50 data
    """
    print("\n" + "=" * 60)
    print("TEST 3: Signal Generation on NIFTY50")
    print("=" * 60)
    
    # Load real data
    data_file = "fyers_data/NSE_NIFTY50_INDEX_1hour.csv"
    if not os.path.exists(data_file):
        print(f"✗ FAIL - Data file not found: {data_file}")
        return False
    
    df = pd.read_csv(data_file)
    print(f"Data loaded: {len(df)} rows")
    print(f"Date range: {df['datetime'].iloc[0]} to {df['datetime'].iloc[-1]}")
    
    # Generate signals
    df_signals = generate_signals(df.copy(), None)
    
    # Count signals
    signal_counts = df_signals['signal'].value_counts()
    buy_count = signal_counts.get(1, 0)
    sell_count = signal_counts.get(-1, 0)
    hold_count = signal_counts.get(0, 0)
    
    print(f"\nSignal distribution:")
    print(f"  HOLD (0):  {hold_count} bars")
    print(f"  BUY (1):   {buy_count} signals")
    print(f"  SELL (-1): {sell_count} signals")
    
    # Check trade count
    print(f"\n" + "-" * 40)
    print(f"Total potential trades: {buy_count}")
    print(f"Expected range: 150-220 trades")
    print(f"Minimum required: 120 trades")
    
    # Validation
    if buy_count >= 150 and buy_count <= 250:
        print("✓ PASS - Trade count within expected range")
        status = "PASS"
    elif buy_count >= 120:
        print("⚠ WARNING - Trade count acceptable but low")
        status = "WARN"
    else:
        print("✗ FAIL - Below minimum (likely RSI period = 14 instead of 2)")
        status = "FAIL"
    
    # Check for NaN signals
    nan_count = df_signals['signal'].isna().sum()
    print(f"\nNaN signals: {nan_count}")
    if nan_count > 0:
        print("✗ FAIL - Has NaN signal values")
        return False
    else:
        print("✓ PASS - No NaN signals")
    
    # Check signal values
    unique_signals = set(df_signals['signal'].unique())
    valid_signals = unique_signals.issubset({-1, 0, 1})
    print(f"\nSignal values: {sorted(unique_signals)}")
    if valid_signals:
        print("✓ PASS - Signal values are valid")
    else:
        print("✗ FAIL - Invalid signal values found")
        return False
    
    return status != "FAIL"


def test_full_backtest():
    """
    TEST 4: Full Backtest Execution
    """
    print("\n" + "=" * 60)
    print("TEST 4: Full Backtest Execution")
    print("=" * 60)
    
    # Load data
    data_file = "fyers_data/NSE_NIFTY50_INDEX_1hour.csv"
    df = pd.read_csv(data_file)
    
    # Generate signals
    df_signals = generate_signals(df.copy(), None)
    
    # Run backtest
    engine = BacktestEngine(Config)
    trades_df = engine.run(df_signals)
    metrics = engine.get_metrics()
    
    print(f"\nBacktest Results:")
    print(f"  Total Trades:    {metrics.get('total_trades', 0)}")
    print(f"  Win Rate:        {metrics.get('win_rate', 0)}%")
    print(f"  Total Return:    {metrics.get('total_return', 0)}%")
    print(f"  Final Capital:   ₹{metrics.get('final_capital', 0):,.2f}")
    print(f"  Sharpe Ratio:    {metrics.get('sharpe_ratio', 0)}")
    print(f"  Max Drawdown:    {metrics.get('max_drawdown', 0)}%")
    
    # Validation checks
    checks_passed = True
    
    # Check 1: Minimum trades
    if metrics.get('total_trades', 0) >= 120:
        print("\n✓ Trade count meets minimum requirement")
    else:
        print("\n✗ Trade count below minimum requirement")
        checks_passed = False
    
    # Check 2: Win rate sanity
    win_rate = metrics.get('win_rate', 0)
    if 40 <= win_rate <= 65:
        print("✓ Win rate within expected range (40-65%)")
    elif win_rate > 65:
        print("⚠ WARNING: Win rate suspiciously high - check for look-ahead bias")
    else:
        print("⚠ WARNING: Win rate below expected")
    
    # Check 3: Return sanity
    total_return = metrics.get('total_return', 0)
    if -50 < total_return < 100:
        print("✓ Return within reasonable range")
    elif total_return > 100:
        print("⚠ WARNING: Return suspiciously high - check for look-ahead bias")
    else:
        print("⚠ WARNING: Return below expected")
    
    return checks_passed


def test_output_format():
    """
    TEST 5: Output Format Validation
    """
    print("\n" + "=" * 60)
    print("TEST 5: Output Format Validation")
    print("=" * 60)
    
    # Load data and generate trades
    data_file = "fyers_data/NSE_NIFTY50_INDEX_1hour.csv"
    df = pd.read_csv(data_file)
    df_signals = generate_signals(df.copy(), None)
    
    engine = BacktestEngine(Config)
    trades_df = engine.run(df_signals)
    
    # Expected columns (as per competition rules)
    expected_cols = [
        'student_roll_number', 'strategy_submission_number', 
        'symbol', 'timeframe', 'entry_trade_time', 'exit_trade_time',
        'entry_trade_price', 'exit_trade_price', 'qty', 'fees',
        'cumulative_capital_after_trade'
    ]
    
    print(f"Expected columns: {len(expected_cols)}")
    print(f"Actual columns:   {len(trades_df.columns)}")
    print(f"Columns: {list(trades_df.columns)}")
    
    # Check column match
    if list(trades_df.columns) == expected_cols:
        print("✓ PASS - Columns match exactly")
    else:
        print("✗ FAIL - Column mismatch")
        print(f"Expected: {expected_cols}")
        print(f"Got: {list(trades_df.columns)}")
        return False
    
    # Check fees
    if len(trades_df) > 0:
        fees_correct = (trades_df['fees'] == 48).all()
        print(f"\nFees check (all ₹48): {'✓ PASS' if fees_correct else '✗ FAIL'}")
        
        # Check timeframe
        tf_correct = (trades_df['timeframe'] == Config.TIMEFRAME).all()
        print(f"Timeframe check: {'✓ PASS' if tf_correct else '✗ FAIL'}")
        
        return fees_correct and tf_correct
    
    return True


def test_all_symbols():
    """
    TEST 6: Run on all required symbols
    """
    print("\n" + "=" * 60)
    print("TEST 6: All Required Symbols")
    print("=" * 60)
    
    symbols = [
        ("NSE:NIFTY50-INDEX", "fyers_data/NSE_NIFTY50_INDEX_1hour.csv"),
        ("NSE:RELIANCE-EQ", "fyers_data/NSE_RELIANCE_EQ_1hour.csv"),
        ("NSE:VBL-EQ", "fyers_data/NSE_VBL_EQ_1hour.csv"),
        ("NSE:YESBANK-EQ", "fyers_data/NSE_YESBANK_EQ_1hour.csv"),
        ("NSE:SUNPHARMA-EQ", "fyers_data/NSE_SUNPHARMA_EQ_1hour.csv"),
    ]
    
    all_passed = True
    results = []
    
    for symbol, data_file in symbols:
        if not os.path.exists(data_file):
            print(f"  {symbol}: ✗ Data file not found")
            all_passed = False
            continue
        
        df = pd.read_csv(data_file)
        df_signals = generate_signals(df.copy(), None)
        
        buy_count = (df_signals['signal'] == 1).sum()
        
        status = "✓" if buy_count >= 120 else "✗"
        results.append((symbol, buy_count, status))
        
        if buy_count < 120:
            all_passed = False
    
    print("\nResults by symbol:")
    print("-" * 50)
    for symbol, count, status in results:
        print(f"  {status} {symbol}: {count} trades")
    
    print("-" * 50)
    if all_passed:
        print("✓ All symbols meet minimum 120 trades requirement")
    else:
        print("✗ Some symbols below minimum requirement")
    
    return all_passed


def run_all_tests():
    """Run all validation tests."""
    print("\n" + "=" * 70)
    print("RSI(2) MEAN REVERSION STRATEGY - VALIDATION SUITE")
    print("=" * 70)
    
    results = {
        "RSI Calculation": test_rsi_calculation(),
        "Volatility Calculation": test_volatility_calculation(),
        "Signal Generation": test_signal_generation_nifty(),
        "Full Backtest": test_full_backtest(),
        "Output Format": test_output_format(),
        "All Symbols": test_all_symbols(),
    }
    
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("-" * 70)
    if all_passed:
        print("✓ ALL TESTS PASSED - Strategy ready for submission!")
    else:
        print("✗ SOME TESTS FAILED - Review and fix issues before submission")
    print("=" * 70)
    
    return all_passed


if __name__ == "__main__":
    run_all_tests()
