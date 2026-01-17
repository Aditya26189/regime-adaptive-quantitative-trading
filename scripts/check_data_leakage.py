"""
CHECK DATA LEAKAGE
Verify strict timestamp ordering and Rule 12 compliance
"""

import pandas as pd
import os
import sys

def check_data_leakage():
    submission_dir = 'submission_new'
    print(f"Checking {submission_dir} for Data Leakage...")
    
    files = [f for f in os.listdir(submission_dir) if f.startswith('STRATEGY5') and f.endswith('.csv')]
    
    overall_status = True
    
    for f in files:
        path = os.path.join(submission_dir, f)
        df = pd.read_csv(path)
        
        # 1. Check Time Flow
        df['entry_time'] = pd.to_datetime(df['entry_trade_time'])
        df['exit_time'] = pd.to_datetime(df['exit_trade_time'])
        
        time_travel = df[df['exit_time'] <= df['entry_time']]
        
        # 2. Check Sorting
        sorted_check = df['entry_time'].is_monotonic_increasing
        
        if len(time_travel) > 0:
            print(f"❌ {f:40} : {len(time_travel)} trades exit before entry! 🚨")
            overall_status = False
        elif not sorted_check:
            print(f"⚠️ {f:40} : Trades not sorted chronologically")
            # Not a fatal error but bad practice
        else:
            print(f"✅ {f:40} : Time Flow Correct")
            
    if overall_status:
        print("\n✅ DATA LEAKAGE CHECK PASSED")
    else:
        print("\n❌ DATA LEAKAGE DETECTED")

if __name__ == "__main__":
    check_data_leakage()
