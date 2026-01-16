"""Check data sizes for all symbols and timeframes."""
import pandas as pd
import os

timeframes = ['1day', '1hour']
symbols = [
    'NSE_NIFTY50_INDEX',
    'NSE_RELIANCE_EQ', 
    'NSE_VBL_EQ',
    'NSE_YESBANK_EQ',
    'NSE_SUNPHARMA_EQ'
]

print("DATA SIZE ANALYSIS")
print("=" * 60)

for tf in timeframes:
    print(f"\n{tf.upper()} TIMEFRAME:")
    print("-" * 40)
    for sym in symbols:
        file = f"fyers_data/{sym}_{tf}.csv"
        if os.path.exists(file):
            df = pd.read_csv(file)
            start = df['datetime'].iloc[0][:10] if len(df) > 0 else 'N/A'
            end = df['datetime'].iloc[-1][:10] if len(df) > 0 else 'N/A'
            print(f"  {sym:20} - {len(df):4} bars ({start} to {end})")
        else:
            print(f"  {sym:20} - FILE NOT FOUND")
