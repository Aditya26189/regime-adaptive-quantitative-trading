"""
VALIDATE PNL ACCOUNTING
Verify that Submission 5 files use Simple Additive PnL (no compounding bugs)
"""

import pandas as pd
import os
import sys

def validate_pnl_accounting():
    submission_dir = 'submission_new'
    print(f"Checking {submission_dir} for PnL consistency...")
    
    files = [f for f in os.listdir(submission_dir) if f.startswith('STRATEGY5') and f.endswith('.csv')]
    
    overall_status = True
    
    for f in files:
        path = os.path.join(submission_dir, f)
        df = pd.read_csv(path)
        
        # 1. Check PnL Formula
        # Calculated PnL
        calc_pnl = (df['exit_trade_price'] - df['entry_trade_price']) * df['qty'] - df['fees']
        
        # 2. Check Capital Path
        initial_capital = 2000000.0
        running_capital = initial_capital + calc_pnl.cumsum()
        
        # 3. Validation
        if 'cumulative_capital_after_trade' in df.columns:
            # Check deviation
            diff = (df['cumulative_capital_after_trade'] - running_capital).abs().max()
            
            non_finite = calc_pnl.isin([float('inf'), float('-inf'), float('nan')]).any()
            
            if non_finite:
                print(f"❌ {f:40} : CONTAINS INFINITE/NAN VALUES 🚨")
                overall_status = False
            elif diff > 1.0: # Allow small float rounding
                print(f"❌ {f:40} : Capital Mismatch (Diff: {diff:.2f})")
                overall_status = False
            else:
                final_util = (running_capital.iloc[-1] / initial_capital - 1) * 100
                print(f"✅ {f:40} : Valid Additive PnL. Return: {final_util:.2f}%")
        else:
            print(f"⚠️ {f:40} : Missing 'cumulative_capital_after_trade' column")
            
    if overall_status:
        print("\n✅ PNL ACCOUNTING VALIDATED: NO OVERFLOWS DETECTED")
    else:
        print("\n❌ PNL ACCOUNTING FAILED")

if __name__ == "__main__":
    validate_pnl_accounting()
