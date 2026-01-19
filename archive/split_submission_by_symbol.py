# split_submission_by_symbol.py
"""
Split the OPTIMAL submission into separate CSV files per symbol
for individual upload requirements
"""
import pandas as pd
import glob

print("="*70)
print("SPLITTING SUBMISSION BY SYMBOL")
print("="*70)

# Find OPTIMAL submission
files = glob.glob("output/23ME3EP03_OPTIMAL_submission_*.csv")
if not files:
    print("❌ No OPTIMAL submission found!")
    exit(1)

df = pd.read_csv(files[0])
print(f"Source: {files[0]}")
print(f"Total trades: {len(df)}\n")

# Symbol mapping
symbols = {
    'NSE:NIFTY50-INDEX': 'NIFTY50',
    'NSE:VBL-EQ': 'VBL',
    'NSE:RELIANCE-EQ': 'RELIANCE',
    'NSE:SUNPHARMA-EQ': 'SUNPHARMA',
    'NSE:YESBANK-EQ': 'YESBANK'
}

# Split and save
for symbol_code, symbol_name in symbols.items():
    symbol_df = df[df['symbol'] == symbol_code].copy()
    
    # Sort by entry time
    symbol_df = symbol_df.sort_values('entry_trade_time').reset_index(drop=True)
    
    # Save
    filename = f"output/23ME3EP03_{symbol_code.replace(':', '_')}_trades.csv"
    symbol_df.to_csv(filename, index=False)
    
    print(f"✅ {symbol_name:12} {len(symbol_df):3} trades → {filename}")

print("\n" + "="*70)
print("SPLIT COMPLETE - Ready for individual upload")
print("="*70)
