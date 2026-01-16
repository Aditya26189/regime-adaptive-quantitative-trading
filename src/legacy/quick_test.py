"""Quick test - output to file."""
import pandas as pd
from strategy1_rsi2_meanrev import generate_signals

symbols = [
    ("NIFTY50", "fyers_data/NSE_NIFTY50_INDEX_1hour.csv"),
    ("RELIANCE", "fyers_data/NSE_RELIANCE_EQ_1hour.csv"),
    ("VBL", "fyers_data/NSE_VBL_EQ_1hour.csv"),
    ("YESBANK", "fyers_data/NSE_YESBANK_EQ_1hour.csv"),
    ("SUNPHARMA", "fyers_data/NSE_SUNPHARMA_EQ_1hour.csv"),
]

results = []
for name, file in symbols:
    df = pd.read_csv(file)
    df_s = generate_signals(df.copy(), None)
    buy_count = (df_s['signal'] == 1).sum()
    status = "PASS" if buy_count >= 120 else "FAIL"
    results.append(f"{status}: {name:12} - {buy_count} trades")

with open("trade_counts.txt", "w") as f:
    f.write("TRADE COUNT AFTER FIXES\n")
    f.write("="*50 + "\n")
    for r in results:
        f.write(r + "\n")
    f.write("="*50 + "\n")

print("Results written to trade_counts.txt")
