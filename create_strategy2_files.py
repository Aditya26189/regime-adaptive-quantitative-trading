# create_strategy2_files.py
"""
Create Strategy #2 submission files from the 1.573 Sharpe advanced submission
"""
import pandas as pd

print("="*70)
print("CREATING STRATEGY #2 FILES (1.573 Sharpe)")
print("="*70)

# Load the high Sharpe file
df = pd.read_csv('output/23ME3EP03_advanced_submission_20260117_080808.csv')

# Change strategy number to 2
df['strategy_submission_number'] = 2

# Save combined file
combined_file = 'output/23ME3EP03_STRATEGY2_submission.csv'
df.to_csv(combined_file, index=False)
print(f"\n✅ Combined: {combined_file}")

# Split by symbol
symbols_map = {
    'NSE:NIFTY50-INDEX': 'NIFTY50',
    'NSE:VBL-EQ': 'VBL',
    'NSE:RELIANCE-EQ': 'RELIANCE',
    'NSE:SUNPHARMA-EQ': 'SUNPHARMA',
    'NSE:YESBANK-EQ': 'YESBANK'
}

print("\nIndividual Symbol Files:")
for symbol_code, symbol_name in symbols_map.items():
    symbol_df = df[df['symbol'] == symbol_code].copy()
    symbol_df = symbol_df.sort_values('entry_trade_time').reset_index(drop=True)
    
    filename = f"output/STRATEGY2_{symbol_code.replace(':', '_')}_trades.csv"
    symbol_df.to_csv(filename, index=False)
    
    margin = len(symbol_df) - 120
    icon = "✅" if margin >= 10 else "⚠️" if margin >= 5 else "🔴"
    print(f"✅ {symbol_name:12} {len(symbol_df):3} trades (+{margin:2}) {icon} → {filename}")

print("\n" + "="*70)
print("STRATEGY #2 FILES CREATED")
print("Portfolio Sharpe: 1.573")
print("⚠️  WARNING: SUNPHARMA has exactly 120 trades (DQ risk)")
print("="*70)
