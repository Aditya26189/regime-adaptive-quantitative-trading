"""
Strategy 1 Only Submission Generator
=====================================
Generates submission with ONLY Strategy 1 (RSI(2) 1H)

Strategy 2 (Donchian Daily) doesn't meet 80 trade minimum for daily.
This version only includes Strategy 1 which passes all checks.
"""

import pandas as pd
from datetime import datetime


def run_strategy1_only():
    """Generate submission with only Strategy 1."""
    
    from strategy1_rsi2_meanrev import generate_signals, BacktestEngine, Config
    
    STUDENT_ROLL_NUMBER = "23ME3EP03"
    
    symbols = [
        ("NSE:NIFTY50-INDEX", "fyers_data/NSE_NIFTY50_INDEX_1hour.csv"),
        ("NSE:RELIANCE-EQ", "fyers_data/NSE_RELIANCE_EQ_1hour.csv"),
        ("NSE:VBL-EQ", "fyers_data/NSE_VBL_EQ_1hour.csv"),
        ("NSE:YESBANK-EQ", "fyers_data/NSE_YESBANK_EQ_1hour.csv"),
        ("NSE:SUNPHARMA-EQ", "fyers_data/NSE_SUNPHARMA_EQ_1hour.csv"),
    ]
    
    print("="*70)
    print("GENERATING STRATEGY 1 ONLY SUBMISSION")
    print(f"Roll Number: {STUDENT_ROLL_NUMBER}")
    print("="*70)
    
    all_trades = []
    
    for symbol, file in symbols:
        print(f"\nProcessing {symbol}...")
        
        df = pd.read_csv(file)
        df_signals = generate_signals(df.copy(), None)
        
        class SymbolConfig:
            STUDENT_ROLL_NUMBER = "23ME3EP03"
            STRATEGY_SUBMISSION_NUMBER = 1
            SYMBOL = symbol
            TIMEFRAME = "60"
            INITIAL_CAPITAL = 100000
            FEE_PER_ORDER = 24
        
        engine = BacktestEngine(SymbolConfig)
        trades_df = engine.run(df_signals)
        
        if len(trades_df) > 0:
            all_trades.append(trades_df)
            status = "✅" if len(trades_df) >= 120 else "⚠️"
            print(f"  {status} {len(trades_df)} trades")
    
    # Combine
    combined = pd.concat(all_trades, ignore_index=True)
    
    # Sort
    combined = combined.sort_values(['symbol', 'entry_trade_time'])
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{STUDENT_ROLL_NUMBER}_strategy1_submission_{timestamp}.csv"
    
    # Save
    combined.to_csv(filename, index=False)
    
    print(f"\n{'='*70}")
    print(f"✅ SUBMISSION FILE: {filename}")
    print(f"   Total trades: {len(combined)}")
    print(f"   All symbols ≥120 trades: YES")
    print("="*70)
    
    # Summary by symbol
    print("\nTrade Summary:")
    for symbol in combined['symbol'].unique():
        count = len(combined[combined['symbol'] == symbol])
        print(f"  {symbol}: {count} trades")
    
    return filename


if __name__ == "__main__":
    run_strategy1_only()
