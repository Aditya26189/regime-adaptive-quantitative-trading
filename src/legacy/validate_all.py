"""Quick validation script to check all symbols meet 120 trade minimum."""
import pandas as pd
import sys
sys.path.insert(0, '.')
from strategy1_rsi2_meanrev import generate_signals, Config, BacktestEngine

symbols = [
    ("NIFTY50", "fyers_data/NSE_NIFTY50_INDEX_1hour.csv"),
    ("RELIANCE", "fyers_data/NSE_RELIANCE_EQ_1hour.csv"),
    ("VBL", "fyers_data/NSE_VBL_EQ_1hour.csv"),
    ("YESBANK", "fyers_data/NSE_YESBANK_EQ_1hour.csv"),
    ("SUNPHARMA", "fyers_data/NSE_SUNPHARMA_EQ_1hour.csv"),
]

print("="*60)
print("TRADE COUNT VALIDATION - ALL SYMBOLS")
print("="*60)

all_pass = True
for name, file in symbols:
    df = pd.read_csv(file)
    df_s = generate_signals(df.copy(), None)
    buy_count = (df_s['signal'] == 1).sum()
    status = "PASS" if buy_count >= 120 else "FAIL"
    if buy_count < 120:
        all_pass = False
    print(f"{status}: {name:12} - {buy_count:3} trades")

print("="*60)
if all_pass:
    print("ALL SYMBOLS MEET 120 TRADE MINIMUM - READY FOR SUBMISSION")
else:
    print("SOME SYMBOLS BELOW MINIMUM - NEEDS ADJUSTMENT")
