"""Run full backtest with performance metrics."""
import pandas as pd
import numpy as np
from strategy1_rsi2_meanrev import generate_signals, Config, BacktestEngine

symbols = [
    ("NIFTY50", "NSE:NIFTY50-INDEX", "fyers_data/NSE_NIFTY50_INDEX_1hour.csv"),
    ("RELIANCE", "NSE:RELIANCE-EQ", "fyers_data/NSE_RELIANCE_EQ_1hour.csv"),
    ("VBL", "NSE:VBL-EQ", "fyers_data/NSE_VBL_EQ_1hour.csv"),
    ("YESBANK", "NSE:YESBANK-EQ", "fyers_data/NSE_YESBANK_EQ_1hour.csv"),
    ("SUNPHARMA", "NSE:SUNPHARMA-EQ", "fyers_data/NSE_SUNPHARMA_EQ_1hour.csv"),
]

results = []
all_trades = []

for name, symbol, file in symbols:
    df = pd.read_csv(file)
    df_signals = generate_signals(df.copy(), None)
    
    # Create config for this symbol
    class SymbolConfig:
        STUDENT_ROLL_NUMBER = Config.STUDENT_ROLL_NUMBER
        STRATEGY_SUBMISSION_NUMBER = 1
        SYMBOL = symbol
        TIMEFRAME = "60"
        INITIAL_CAPITAL = 100000
        FEE_PER_ORDER = 24
    
    engine = BacktestEngine(SymbolConfig)
    trades_df = engine.run(df_signals)
    metrics = engine.get_metrics()
    
    results.append({
        'symbol': name,
        'trades': metrics.get('total_trades', 0),
        'win_rate': metrics.get('win_rate', 0),
        'total_return': metrics.get('total_return', 0),
        'sharpe': metrics.get('sharpe_ratio', 0),
        'max_dd': metrics.get('max_drawdown', 0)
    })

# Write results
with open("backtest_results.txt", "w") as f:
    f.write("FULL BACKTEST RESULTS - RSI(2) STRATEGY\n")
    f.write("=" * 80 + "\n\n")
    f.write(f"{'Symbol':<12} {'Trades':>8} {'Win Rate':>10} {'Return':>10} {'Sharpe':>8} {'Max DD':>8}\n")
    f.write("-" * 80 + "\n")
    for r in results:
        f.write(f"{r['symbol']:<12} {r['trades']:>8} {r['win_rate']:>9.1f}% {r['total_return']:>9.2f}% {r['sharpe']:>8.2f} {r['max_dd']:>7.2f}%\n")
    f.write("-" * 80 + "\n")
    
    # Calculate averages
    avg_trades = np.mean([r['trades'] for r in results])
    avg_win = np.mean([r['win_rate'] for r in results])
    avg_ret = np.mean([r['total_return'] for r in results])
    avg_sharpe = np.mean([r['sharpe'] for r in results])
    avg_dd = np.mean([r['max_dd'] for r in results])
    
    f.write(f"{'AVERAGE':<12} {avg_trades:>8.0f} {avg_win:>9.1f}% {avg_ret:>9.2f}% {avg_sharpe:>8.2f} {avg_dd:>7.2f}%\n")
    f.write("=" * 80 + "\n")

print("Results written to backtest_results.txt")
