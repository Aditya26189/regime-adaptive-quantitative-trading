import pandas as pd
import numpy as np
import sys
import os

# CONFIGURATION
# Using the absolute path or relative path from project root
SUBMISSION_FILE = "output/23ME3EP03_optimized_submission_20260116_215309.csv" 
Z_SCORE_THRESHOLD = 3.0  # Statistical outlier limit
ABSOLUTE_RETURN_CAP = 5.0 # Flag any trade > 15% return (Suspicious for 1H)

def audit_outliers(file_path):
    print(f"🛡️  AUDITING FOR OUTLIERS: {file_path}")
    print("="*60)
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        # Try to find the latest submission if the specific one is missing
        import glob
        files = glob.glob("output/*_optimized_submission_*.csv")
        if files:
            file_path = max(files, key=os.path.getctime)
            print(f"⚠️  Falling back to latest found: {file_path}")
        else:
            return

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return

    # 1. Calculate Per-Trade Returns
    # Net PnL = (Exit - Entry) * Qty - Fees
    # Return % = (Exit - Entry) / Entry * 100
    df['return_pct'] = ((df['exit_trade_price'] - df['entry_trade_price']) / df['entry_trade_price']) * 100
    
    symbols = df['symbol'].unique()
    clean_bill_of_health = True

    for sym in symbols:
        sym_data = df[df['symbol'] == sym].copy()
        
        # Calculate Stats
        mean_ret = sym_data['return_pct'].mean()
        std_dev = sym_data['return_pct'].std()
        
        # Calculate Z-Scores
        if std_dev > 0:
            sym_data['z_score'] = (sym_data['return_pct'] - mean_ret) / std_dev
        else:
            sym_data['z_score'] = 0
        
        # Find Outliers
        statistical_outliers = sym_data[sym_data['z_score'].abs() > Z_SCORE_THRESHOLD]
        absolute_outliers = sym_data[sym_data['return_pct'].abs() > ABSOLUTE_RETURN_CAP]
        
        print(f"\n📊 {sym}:")
        print(f"   Avg Return: {mean_ret:.2f}% | Std Dev: {std_dev:.2f}%")
        print(f"   Max Return: {sym_data['return_pct'].max():.2f}% | Min Return: {sym_data['return_pct'].min():.2f}%")
        
        # REPORTING
        if not statistical_outliers.empty:
            print(f"   ⚠️  WARNING: Found {len(statistical_outliers)} Statistical Outliers (Z > {Z_SCORE_THRESHOLD})")
            # Show top 3 worst offenders
            for idx, row in statistical_outliers.head(3).iterrows():
                print(f"      - Trade at {row['entry_trade_time']}: {row['return_pct']:.2f}% (Z={row['z_score']:.1f})")
            clean_bill_of_health = False
            
        if not absolute_outliers.empty:
            print(f"   🚨 CRITICAL: Found {len(absolute_outliers)} Extreme Trades (> {ABSOLUTE_RETURN_CAP}%)")
            clean_bill_of_health = False

    print("\n" + "="*60)
    if clean_bill_of_health:
        print("✅ PASSED: No extreme outliers detected. Submission is safe.")
    else:
        print("❌ FAILED: Potential anomalies found. Review specific trades.")
        print("   Rule 64: 'Avoid extreme outliers (e.g. +5% when others are 1%)'")

if __name__ == "__main__":
    audit_outliers(SUBMISSION_FILE)
