# quick_check.py - FIXED
import pandas as pd

submission = pd.read_csv("output/23ME3EP03_advanced_submission_20260117_080808.csv")

print("="*70)
print("CURRENT TRADE COUNTS IN SUBMISSION")
print("="*70)

# Correct symbol codes in CSV
symbol_map = {
    'NIFTY50': 'NSE:NIFTY50-INDEX',
    'VBL': 'NSE:VBL-EQ',
    'RELIANCE': 'NSE:RELIANCE-EQ',
    'SUNPHARMA': 'NSE:SUNPHARMA-EQ',
    'YESBANK': 'NSE:YESBANK-EQ'
}

for name, code in symbol_map.items():
    count = len(submission[submission['symbol'] == code])
    margin = count - 120
    
    if margin < 10:
        status = "🔴 DANGER"
    elif margin < 20:
        status = "⚠️  WARNING"
    else:
        status = "✅ SAFE"
    
    print(f"{name:12} {count:3} trades  |  Margin: +{margin:2}  |  {status}")

print("="*70)
print(f"TOTAL TRADES: {len(submission)}")
