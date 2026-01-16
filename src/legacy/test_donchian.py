"""Test Donchian strategy on all symbols."""
import pandas as pd
import numpy as np
from strategy_donchian import generate_signals, Config, BacktestEngine

symbols = [
    ("NIFTY50", "NSE:NIFTY50-INDEX", "fyers_data/NSE_NIFTY50_INDEX_1day.csv"),
    ("RELIANCE", "NSE:RELIANCE-EQ", "fyers_data/NSE_RELIANCE_EQ_1day.csv"),
    ("VBL", "NSE:VBL-EQ", "fyers_data/NSE_VBL_EQ_1day.csv"),
    ("YESBANK", "NSE:YESBANK-EQ", "fyers_data/NSE_YESBANK_EQ_1day.csv"),
    ("SUNPHARMA", "NSE:SUNPHARMA-EQ", "fyers_data/NSE_SUNPHARMA_EQ_1day.csv"),
]

results = []

for name, symbol, file in symbols:
    df = pd.read_csv(file)
    df_signals = generate_signals(df.copy(), None)
    
    class SymbolConfig:
        STUDENT_ROLL_NUMBER = Config.STUDENT_ROLL_NUMBER
        STRATEGY_SUBMISSION_NUMBER = 2
        SYMBOL = symbol
        TIMEFRAME = "1D"
        INITIAL_CAPITAL = 100000
        FEE_PER_ORDER = 24
    
    engine = BacktestEngine(SymbolConfig)
    trades_df = engine.run(df_signals)
    metrics = engine.get_metrics()
    
    results.append({
        'symbol': name,
        'trades': metrics.get('total_trades', 0),
        'win_rate': metrics.get('win_rate', 0),
        'return': metrics.get('total_return', 0),
        'sharpe': metrics.get('sharpe_ratio', 0)
    })

# Write results
with open("donchian_results.txt", "w") as f:
    f.write("DONCHIAN BREAKOUT STRATEGY - DAILY TIMEFRAME\n")
    f.write("=" * 60 + "\n\n")
    f.write(f"{'Symbol':<12} {'Trades':>8} {'Win Rate':>10} {'Return':>10} {'Sharpe':>8}\n")
    f.write("-" * 60 + "\n")
    for r in results:
        f.write(f"{r['symbol']:<12} {r['trades']:>8} {r['win_rate']:>9.1f}% {r['return']:>9.2f}% {r['sharpe']:>8.2f}\n")
    f.write("-" * 60 + "\n")
    
    # Expected: 10-15 trades per symbol, min 80 for daily
    total_trades = sum(r['trades'] for r in results)
    f.write(f"\nTotal trades across 5 symbols: {total_trades}\n")
    f.write(f"Expected per symbol: 10-15 trades\n")
    f.write(f"Minimum required for daily: 80 per symbol\n")

print("Results written to donchian_results.txt")
