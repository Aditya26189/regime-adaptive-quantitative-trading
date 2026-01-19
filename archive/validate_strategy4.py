"""
STRATEGY 4 CONSTRAINT VALIDATION
Verify all files meet competition requirements for Submission 4
"""

import pandas as pd
import os
import json

def validate_strategy4_files():
    """Validate all Strategy 4 submission files"""
    
    submission_dir = 'submission_4'
    target_strategy_num = 4
    
    print("\n" + "="*70)
    print(f"STRATEGY {target_strategy_num} CONSTRAINT VALIDATION")
    print("="*70)
    
    # Expected files with strategy number 4
    files = {
        'NIFTY50': f'{submission_dir}/STRATEGY4_NSE_NIFTY50-INDEX_trades.csv',
        'RELIANCE': f'{submission_dir}/STRATEGY4_NSE_RELIANCE-EQ_trades.csv',
        'VBL': f'{submission_dir}/STRATEGY4_NSE_VBL-EQ_trades.csv',
        'YESBANK': f'{submission_dir}/STRATEGY4_NSE_YESBANK-EQ_trades.csv',
        'SUNPHARMA': f'{submission_dir}/STRATEGY4_NSE_SUNPHARMA-EQ_trades.csv'
    }
    
    results = {}
    all_passed = True
    
    for symbol, filepath in files.items():
        print(f"\n📊 Validating {symbol}...")
        
        if not os.path.exists(filepath):
            print(f"  ❌ File not found: {filepath}")
            all_passed = False
            continue
        
        # Read CSV
        df = pd.read_csv(filepath)
        
        # Check strategy number and update if needed
        strategy_numbers = df['strategy_submission_number'].unique()
        if len(strategy_numbers) != 1 or strategy_numbers[0] != target_strategy_num:
            print(f"  ⚠️  Strategy number is {strategy_numbers}, updating to {target_strategy_num}...")
            df['strategy_submission_number'] = target_strategy_num
            df.to_csv(filepath, index=False)
            print(f"  ✅ Updated to strategy {target_strategy_num}")
        else:
            print(f"  ✅ Strategy number: {target_strategy_num}")
            
        # Check trade count
        trade_count = len(df)
        if trade_count < 120:
            print(f"  ❌ FAILED: Only {trade_count} trades (need ≥120)")
            all_passed = False
        else:
            print(f"  ✅ Trade count: {trade_count} (≥120)")
            
        # Check other constraints
        if '23ME3EP03' not in df['student_roll_number'].unique():
             print("  ❌ Wrong Roll Number")
             all_passed = False
        
        # Calculate metrics (Institutional Capital Sizing)
        initial_capital = 2000000
        
        # Convert to numeric
        df['entry_trade_price'] = pd.to_numeric(df['entry_trade_price'], errors='coerce')
        df['exit_trade_price'] = pd.to_numeric(df['exit_trade_price'], errors='coerce')
        df['qty'] = pd.to_numeric(df['qty'], errors='coerce')
        df['fees'] = pd.to_numeric(df['fees'], errors='coerce')
        
        df['pnl'] = (df['exit_trade_price'] - df['entry_trade_price']) * df['qty'] - df['fees']
        returns = (df['pnl'] / initial_capital) * 100
        
        if returns.std() > 0:
            sharpe = (returns.mean() / returns.std()) * (252 ** 0.5)
        else:
            sharpe = 0
            
        print(f"  📈 Sharpe: {sharpe:.3f}")
        
        results[symbol] = {
            'sharpe': sharpe,
            'trades': trade_count,
            'passes': trade_count >= 120
        }

    # Portfolio Stats
    avg_sharpe = sum(r['sharpe'] for r in results.values()) / len(results)
    total_trades = sum(r['trades'] for r in results.values())
    
    print("\n" + "="*70)
    print(f"PORTFOLIO SHARPE: {avg_sharpe:.3f}")
    print(f"TOTAL TRADES: {total_trades}")
    print("="*70)
    
    if all_passed:
        print("\n✅ READY FOR SUBMISSION 4")
        
        # Generate Checklist
        checklist = f"""# STRATEGY 4 SUBMISSION CHECKLIST (High Sharpe Edition)

## Submission 4 Details
- **Portfolio Sharpe:** {avg_sharpe:.3f} ✅
- **Total Trades:** {total_trades}
- **Strategy Number:** 4

## Files
| Symbol | Filename | Trades | Sharpe |
|--------|----------|--------|--------|
| NIFTY50 | STRATEGY4_NSE_NIFTY50-INDEX_trades.csv | {results['NIFTY50']['trades']} | {results['NIFTY50']['sharpe']:.3f} |
| RELIANCE | STRATEGY4_NSE_RELIANCE-EQ_trades.csv | {results['RELIANCE']['trades']} | {results['RELIANCE']['sharpe']:.3f} |
| VBL | STRATEGY4_NSE_VBL-EQ_trades.csv | {results['VBL']['trades']} | {results['VBL']['sharpe']:.3f} |
| YESBANK | STRATEGY4_NSE_YESBANK-EQ_trades.csv | {results['YESBANK']['trades']} | {results['YESBANK']['sharpe']:.3f} |
| SUNPHARMA | STRATEGY4_NSE_SUNPHARMA-EQ_trades.csv | {results['SUNPHARMA']['trades']} | {results['SUNPHARMA']['sharpe']:.3f} |

**Generated:** {pd.Timestamp.now()}
"""
        with open(f'{submission_dir}/SUBMISSION_CHECKLIST.md', 'w', encoding='utf-8') as f:
            f.write(checklist)
            
    else:
        print("\n❌ ISSUES FOUND")

if __name__ == "__main__":
    validate_strategy4_files()
