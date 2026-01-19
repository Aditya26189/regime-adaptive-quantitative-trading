# outlier_check.py
import pandas as pd
import glob

print("="*70)
print("OUTLIER CHECK (±5% Cap)")
print("="*70)

files = glob.glob("output/23ME3EP03_OPTIMAL_submission_*.csv")
if not files:
    print("❌ No OPTIMAL submission found!")
    exit(1)

df = pd.read_csv(files[0])
df['return_pct'] = ((df['exit_trade_price'] - df['entry_trade_price']) / 
                     df['entry_trade_price'] * 100)

max_return = df['return_pct'].max()
min_return = df['return_pct'].min()

print(f"Return Range:")
print(f"  Max: {max_return:.2f}%")
print(f"  Min: {min_return:.2f}%")

# Check for outliers
outliers_high = df[df['return_pct'] > 5.0]
outliers_low = df[df['return_pct'] < -5.0]

if len(outliers_high) > 0:
    print(f"\n⚠️  {len(outliers_high)} trades exceed +5%:")
    print(outliers_high[['symbol', 'entry_trade_price', 'exit_trade_price', 'return_pct']].head())

if len(outliers_low) > 0:
    print(f"\n⚠️  {len(outliers_low)} trades below -5%:")
    print(outliers_low[['symbol', 'entry_trade_price', 'exit_trade_price', 'return_pct']].head())

if max_return <= 5.0 and min_return >= -5.0:
    print("\n✅ PASS: All returns within ±5% cap")
else:
    print("\n❌ FAIL: Outliers detected - check capping logic")
