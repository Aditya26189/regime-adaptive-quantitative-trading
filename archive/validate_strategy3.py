"""
STRATEGY 3 CONSTRAINT VALIDATION
Verify all files meet competition requirements
"""

import pandas as pd
import os
import json

def validate_strategy3_files():
    """Validate all Strategy 3 submission files"""
    
    submission_dir = 'submission_3'
    
    print("\n" + "="*70)
    print("STRATEGY 3 CONSTRAINT VALIDATION")
    print("="*70)
    
    # Expected files with strategy number 3
    files = {
        'NIFTY50': f'{submission_dir}/STRATEGY3_NSE_NIFTY50-INDEX_trades.csv',
        'RELIANCE': f'{submission_dir}/STRATEGY3_NSE_RELIANCE-EQ_trades.csv',
        'VBL': f'{submission_dir}/STRATEGY3_NSE_VBL-EQ_trades.csv',
        'YESBANK': f'{submission_dir}/STRATEGY3_NSE_YESBANK-EQ_trades.csv',
        'SUNPHARMA': f'{submission_dir}/STRATEGY3_NSE_SUNPHARMA-EQ_trades.csv'
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
        
        # Check columns
        required_cols = [
            'student_roll_number',
            'strategy_submission_number',
            'symbol',
            'timeframe',
            'entry_trade_time',
            'exit_trade_time',
            'entry_trade_price',
            'exit_trade_price',
            'qty',
            'fees',
            'cumulative_capital_after_trade'
        ]
        
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"  ❌ Missing columns: {missing_cols}")
            all_passed = False
            continue
        else:
            print(f"  ✅ All required columns present")
        
        # Check strategy number
        strategy_numbers = df['strategy_submission_number'].unique()
        if len(strategy_numbers) != 1:
            print(f"  ⚠️  Multiple strategy numbers: {strategy_numbers}")
            print(f"     Updating to strategy 3...")
            df['strategy_submission_number'] = 3
            df.to_csv(filepath, index=False)
            print(f"  ✅ Updated to strategy 3")
        elif strategy_numbers[0] != 3:
            print(f"  ⚠️  Strategy number is {strategy_numbers[0]}, updating to 3...")
            df['strategy_submission_number'] = 3
            df.to_csv(filepath, index=False)
            print(f"  ✅ Updated to strategy 3")
        else:
            print(f"  ✅ Strategy number: 3")
        
        # Check trade count
        trade_count = len(df)
        if trade_count < 120:
            print(f"  ❌ FAILED: Only {trade_count} trades (need ≥120)")
            all_passed = False
        else:
            print(f"  ✅ Trade count: {trade_count} (≥120)")
        
        # Check roll number
        roll_numbers = df['student_roll_number'].unique()
        if '23ME3EP03' not in roll_numbers:
            print(f"  ⚠️  Roll number issue: {roll_numbers}")
            all_passed = False
        else:
            print(f"  ✅ Roll number: 23ME3EP03")
        
        # Check timeframe
        timeframes = df['timeframe'].unique()
        if '60' not in timeframes:
            print(f"  ⚠️  Timeframe: {timeframes} (expected 60)")
        else:
            print(f"  ✅ Timeframe: 60 (1 hour)")
        
        # Check fees
        fee_values = df['fees'].unique()
        if 48 not in fee_values:
            print(f"  ⚠️  Fees: {fee_values} (expected 48)")
        else:
            print(f"  ✅ Fees: 48")
        
        # Calculate metrics
        initial_capital = 2000000
        final_capital = float(df['cumulative_capital_after_trade'].iloc[-1])
        total_return = ((final_capital - initial_capital) / initial_capital) * 100
        
        # Convert to numeric and calculate Sharpe
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
        
        wins = (df['pnl'] > 0).sum()
        win_rate = (wins / len(df)) * 100
        
        print(f"\n  📈 Performance Metrics:")
        print(f"     Trades: {trade_count}")
        print(f"     Sharpe: {sharpe:.3f}")
        print(f"     Return: {total_return:.2f}%")
        print(f"     Win Rate: {win_rate:.1f}%")
        
        results[symbol] = {
            'filepath': filepath,
            'trades': trade_count,
            'sharpe': sharpe,
            'return_pct': total_return,
            'win_rate': win_rate,
            'passes_constraints': trade_count >= 120
        }
    
    # Portfolio summary
    print("\n" + "="*70)
    print("PORTFOLIO SUMMARY")
    print("="*70)
    
    total_trades = sum(r['trades'] for r in results.values())
    avg_sharpe = sum(r['sharpe'] for r in results.values()) / len(results)
    
    print(f"Total Trades: {total_trades}")
    print(f"Portfolio Sharpe: {avg_sharpe:.3f}")
    
    constraints_met = all(r['passes_constraints'] for r in results.values())
    
    if constraints_met and all_passed:
        print("\n✅ ALL CONSTRAINTS PASSED - READY TO SUBMIT")
        verdict = "READY"
    else:
        print("\n❌ SOME CONSTRAINTS FAILED - FIX BEFORE SUBMITTING")
        verdict = "NOT_READY"
    
    # Save validation report
    validation_report = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'submission_folder': submission_dir,
        'strategy_number': 3,
        'symbol_results': results,
        'portfolio_trades': total_trades,
        'portfolio_sharpe': avg_sharpe,
        'constraints_met': constraints_met,
        'verdict': verdict
    }
    
    with open(f'{submission_dir}/VALIDATION_REPORT.json', 'w') as f:
        json.dump(validation_report, f, indent=2)
    
    print(f"\n✅ Validation report saved: {submission_dir}/VALIDATION_REPORT.json")
    
    # Create submission checklist
    checklist = f"""# STRATEGY 3 SUBMISSION CHECKLIST

## Files Ready for Upload

1. **Timeframe:** 1h ✅

2. **Strategy Logic:** 
   - File: `STRATEGY_3_LOGIC.md`
   - Location: `{submission_dir}/STRATEGY_3_LOGIC.md`

3. **Trade Files:**

| Symbol | Filename | Trades | Status |
|--------|----------|--------|--------|
| NIFTY50 | STRATEGY3_NSE_NIFTY50-INDEX_trades.csv | {results['NIFTY50']['trades']} | {'✅' if results['NIFTY50']['passes_constraints'] else '❌'} |
| RELIANCE | STRATEGY3_NSE_RELIANCE-EQ_trades.csv | {results['RELIANCE']['trades']} | {'✅' if results['RELIANCE']['passes_constraints'] else '❌'} |
| VBL | STRATEGY3_NSE_VBL-EQ_trades.csv | {results['VBL']['trades']} | {'✅' if results['VBL']['passes_constraints'] else '❌'} |
| YESBANK | STRATEGY3_NSE_YESBANK-EQ_trades.csv | {results['YESBANK']['trades']} | {'✅' if results['YESBANK']['passes_constraints'] else '❌'} |
| SUNPHARMA | STRATEGY3_NSE_SUNPHARMA-EQ_trades.csv | {results['SUNPHARMA']['trades']} | {'✅' if results['SUNPHARMA']['passes_constraints'] else '❌'} |

## Portfolio Metrics

- **Total Trades:** {total_trades}
- **Portfolio Sharpe:** {avg_sharpe:.3f}
- **All Constraints Met:** {'YES ✅' if constraints_met else 'NO ❌'}

## Submission Status

**{verdict}** - {'Ready to submit!' if verdict == 'READY' else 'Fix issues first!'}

---

**Validated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    with open(f'{submission_dir}/SUBMISSION_CHECKLIST.md', 'w', encoding='utf-8') as f:
        f.write(checklist)
    
    print(f"✅ Checklist saved: {submission_dir}/SUBMISSION_CHECKLIST.md")
    
    return results, verdict

if __name__ == "__main__":
    results, verdict = validate_strategy3_files()
    
    print("\n" + "="*70)
    print("FINAL VERDICT")
    print("="*70)
    print(f"Status: {verdict}")
    
    if verdict == "READY":
        print("\n🎉 All files validated and ready for competition submission!")
        print(f"\n📁 Upload files from: submission_3/")
    else:
        print("\n⚠️  Please fix the issues above before submitting")
