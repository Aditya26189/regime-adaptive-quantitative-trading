# verify_costs.py
import pandas as pd
import glob

print("="*70)
print("TRANSACTION COST VERIFICATION")
print("="*70)

# Find the OPTIMAL submission
files = glob.glob("output/23ME3EP03_OPTIMAL_submission_*.csv")
if not files:
    print("❌ No OPTIMAL submission found!")
    exit(1)

df = pd.read_csv(files[0])
print(f"File: {files[0]}")
print(f"Total trades: {len(df)}\n")

# Check fee column
if (df['fees'] != 48).any():
    print("❌ ERROR: Some trades don't have ₹48 fees!")
    print(df[df['fees'] != 48][['symbol', 'fees']])
else:
    print("✅ All trades have ₹48 fees")

# Verify capital progression
print("\nCapital Progression Check:")
capital = 100000.0
errors = 0

for idx, row in df.iterrows():
    gross_pnl = (row['exit_trade_price'] - row['entry_trade_price']) * row['qty']
    net_pnl = gross_pnl - 48
    expected_capital = capital + net_pnl
    
    if abs(expected_capital - row['cumulative_capital_after_trade']) > 0.01:
        print(f"❌ Trade {idx}: Expected {expected_capital:.2f}, Got {row['cumulative_capital_after_trade']:.2f}")
        errors += 1
        if errors >= 5:
            print("... (showing first 5 errors)")
            break
    
    capital = row['cumulative_capital_after_trade']

if errors == 0:
    print("✅ Capital progression correct")
    print(f"Final capital: ₹{capital:,.2f}")
