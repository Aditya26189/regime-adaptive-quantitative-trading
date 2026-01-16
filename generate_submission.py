"""
Submission Generator
=====================
Quant Games Hackathon - IIT Kharagpur

Generates competition-compliant CSV submission file.

Output Format:
- student_roll_number
- strategy_submission_number
- symbol
- timeframe
- entry_trade_time
- exit_trade_time
- entry_trade_price
- exit_trade_price
- qty
- fees
- cumulative_capital_after_trade
"""

import pandas as pd
import numpy as np
from datetime import datetime
from compliance_checker import run_death_check


# ============================================
# CONFIGURATION
# ============================================

class SubmissionConfig:
    """Configuration for submission generation."""
    STUDENT_ROLL_NUMBER = "23ME3EP03"  # REPLACE WITH YOUR ROLL NUMBER
    
    SYMBOLS_1H = [
        ("NSE:NIFTY50-INDEX", "fyers_data/NSE_NIFTY50_INDEX_1hour.csv"),
        ("NSE:RELIANCE-EQ", "fyers_data/NSE_RELIANCE_EQ_1hour.csv"),
        ("NSE:VBL-EQ", "fyers_data/NSE_VBL_EQ_1hour.csv"),
        ("NSE:YESBANK-EQ", "fyers_data/NSE_YESBANK_EQ_1hour.csv"),
        ("NSE:SUNPHARMA-EQ", "fyers_data/NSE_SUNPHARMA_EQ_1hour.csv"),
    ]
    
    SYMBOLS_1D = [
        ("NSE:NIFTY50-INDEX", "fyers_data/NSE_NIFTY50_INDEX_1day.csv"),
        ("NSE:RELIANCE-EQ", "fyers_data/NSE_RELIANCE_EQ_1day.csv"),
        ("NSE:VBL-EQ", "fyers_data/NSE_VBL_EQ_1day.csv"),
        ("NSE:YESBANK-EQ", "fyers_data/NSE_YESBANK_EQ_1day.csv"),
        ("NSE:SUNPHARMA-EQ", "fyers_data/NSE_SUNPHARMA_EQ_1day.csv"),
    ]


def run_strategy1_all_symbols(config: SubmissionConfig) -> pd.DataFrame:
    """
    Run RSI(2) strategy on all 1H symbols.
    
    Returns:
        DataFrame with all trades
    """
    from strategy1_rsi2_meanrev import generate_signals, BacktestEngine, Config
    
    all_trades = []
    
    for symbol, file in config.SYMBOLS_1H:
        print(f"  Running RSI(2) on {symbol}...")
        
        # Load data
        df = pd.read_csv(file)
        
        # Generate signals
        df_signals = generate_signals(df.copy(), None)
        
        # Create config for this symbol
        class SymbolConfig:
            STUDENT_ROLL_NUMBER = config.STUDENT_ROLL_NUMBER
            STRATEGY_SUBMISSION_NUMBER = 1
            SYMBOL = symbol
            TIMEFRAME = "60"
            INITIAL_CAPITAL = 100000
            FEE_PER_ORDER = 24
        
        # Run backtest
        engine = BacktestEngine(SymbolConfig)
        trades_df = engine.run(df_signals)
        
        if len(trades_df) > 0:
            all_trades.append(trades_df)
            print(f"    → {len(trades_df)} trades")
        else:
            print(f"    → 0 trades")
    
    if all_trades:
        return pd.concat(all_trades, ignore_index=True)
    return pd.DataFrame()


def run_strategy2_all_symbols(config: SubmissionConfig) -> pd.DataFrame:
    """
    Run Donchian/Momentum strategy on all 1D symbols.
    
    Returns:
        DataFrame with all trades
    """
    from strategy_donchian import generate_signals, BacktestEngine, Config
    
    all_trades = []
    
    for symbol, file in config.SYMBOLS_1D:
        print(f"  Running Momentum on {symbol}...")
        
        # Load data
        df = pd.read_csv(file)
        
        # Generate signals
        df_signals = generate_signals(df.copy(), None)
        
        # Create config for this symbol
        class SymbolConfig:
            STUDENT_ROLL_NUMBER = config.STUDENT_ROLL_NUMBER
            STRATEGY_SUBMISSION_NUMBER = 2
            SYMBOL = symbol
            TIMEFRAME = "1D"
            INITIAL_CAPITAL = 100000
            FEE_PER_ORDER = 24
        
        # Run backtest
        engine = BacktestEngine(SymbolConfig)
        trades_df = engine.run(df_signals)
        
        if len(trades_df) > 0:
            all_trades.append(trades_df)
            print(f"    → {len(trades_df)} trades")
        else:
            print(f"    → 0 trades")
    
    if all_trades:
        return pd.concat(all_trades, ignore_index=True)
    return pd.DataFrame()


def generate_submission_csv(trades_df: pd.DataFrame, config: SubmissionConfig) -> str:
    """
    Generate competition-compliant CSV.
    
    Args:
        trades_df: DataFrame with all trades
        config: Submission configuration
        
    Returns:
        Filename of generated CSV
    """
    # Ensure correct column order
    required_cols = [
        'student_roll_number',
        'strategy_submission_number',
        'symbol',
        'timeframe',
        'entry_trade_time',
        'exit_trade_time',
        'entry_trade_price',
        'exit_trade_price',
        'qty',
        'fees',
        'cumulative_capital_after_trade'
    ]
    
    output_df = trades_df[required_cols].copy()
    
    # Symbol format validation
    for symbol in output_df['symbol'].unique():
        if 'NIFTY50' in symbol:
            assert symbol == 'NSE:NIFTY50-INDEX', f"Wrong index format: {symbol}"
        else:
            assert symbol.endswith('-EQ'), f"Missing -EQ suffix: {symbol}"
            assert symbol.startswith('NSE:'), f"Missing NSE: prefix: {symbol}"
    
    # Sort by strategy, then symbol, then entry time
    output_df = output_df.sort_values(['strategy_submission_number', 'symbol', 'entry_trade_time'])
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{config.STUDENT_ROLL_NUMBER}_combined_submission_{timestamp}.csv"
    
    # Save
    output_df.to_csv(filename, index=False)
    
    return filename


# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == "__main__":
    print("=" * 70)
    print("GENERATING SUBMISSION FILE")
    print("=" * 70)
    
    config = SubmissionConfig()
    
    print(f"\nStudent Roll Number: {config.STUDENT_ROLL_NUMBER}")
    if config.STUDENT_ROLL_NUMBER == "23ME3EP03":
        print("⚠️  WARNING: Please update STUDENT_ROLL_NUMBER in SubmissionConfig")
    
    # Strategy 1: RSI(2) on 1H
    print("\n1. Running Strategy 1 (RSI(2) Mean Reversion - 1H):")
    print("-" * 50)
    strategy1_trades = run_strategy1_all_symbols(config)
    print(f"\n   Total Strategy 1 trades: {len(strategy1_trades)}")
    
    # Strategy 2: Momentum on 1D
    print("\n2. Running Strategy 2 (Momentum - 1D):")
    print("-" * 50)
    strategy2_trades = run_strategy2_all_symbols(config)
    print(f"\n   Total Strategy 2 trades: {len(strategy2_trades)}")
    
    # Combine all trades
    print("\n3. Combining trades...")
    all_trades = pd.concat([strategy1_trades, strategy2_trades], ignore_index=True)
    print(f"   Total combined trades: {len(all_trades)}")
    
    # Generate submission
    print("\n4. Generating submission CSV...")
    filename = generate_submission_csv(all_trades, config)
    print(f"   ✅ Saved: {filename}")
    
    # Run compliance check
    print("\n5. Running compliance check...")
    passed = run_death_check(all_trades)
    
    print("\n" + "=" * 70)
    if passed:
        print(f"✅ SUBMISSION READY: {filename}")
    else:
        print("❌ COMPLIANCE ISSUES - Review and fix before submission")
    print("=" * 70)
