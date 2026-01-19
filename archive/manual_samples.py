# manual_samples.py
import pandas as pd
import glob

print("="*70)
print("MANUAL VERIFICATION SAMPLES")
print("="*70)

files = glob.glob("output/23ME3EP03_OPTIMAL_submission_*.csv")
if not files:
    print("❌ No OPTIMAL submission found!")
    exit(1)

df = pd.read_csv(files[0])
samples = df.sample(3, random_state=42)

print("\nGo to FYERS and verify these trades:\n")

for idx, trade in samples.iterrows():
    print(f"Trade #{idx + 1}:")
    print(f"  Symbol: {trade['symbol']}")
    print(f"  Entry: {trade['entry_trade_time']} @ ₹{trade['entry_trade_price']:.2f}")
    print(f"  Exit:  {trade['exit_trade_time']} @ ₹{trade['exit_trade_price']:.2f}")
    print(f"  Qty:   {trade['qty']}")
    print(f"  P&L:   ₹{(trade['exit_trade_price'] - trade['entry_trade_price']) * trade['qty'] - 48:.2f}")
    print(f"  [ ] Verified on chart\n")
