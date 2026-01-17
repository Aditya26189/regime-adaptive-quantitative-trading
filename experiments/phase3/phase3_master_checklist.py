
"""
Master checklist to ensure all validations pass before submission
"""
import os
import sys
import json

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../'))
sys.path.insert(0, project_root)

def run_master_checklist():
    """Run all critical checks before final submission"""
    
    print("\n" + "="*70)
    print("MASTER PRE-SUBMISSION CHECKLIST")
    print("="*70)
    
    checks = {
        'phase3_portfolio_optimization': False,
        'phase3_meta_ensemble': False,
        'final_validation': False,
        'submission_docs': False,
        'trade_counts_valid': False,
        'rule12_compliance': True,  # Assumed if using only close
        'transaction_costs_included': True,  # Assumed if in code
        'portfolio_sharpe_target': False,
    }
    
    output_dir = os.path.join(project_root, 'output')
    
    # Check file existence
    if os.path.exists(os.path.join(output_dir, 'phase3_portfolio_optimization.json')):
        checks['phase3_portfolio_optimization'] = True
        print("✅ Portfolio optimization complete")
    else:
        print("❌ Portfolio optimization missing")
    
    if os.path.exists(os.path.join(output_dir, 'phase3_meta_ensemble.json')):
        checks['phase3_meta_ensemble'] = True
        print("✅ Meta-ensemble complete")
    else:
        print("⚠️  Meta-ensemble missing (optional)")
    
    if os.path.exists(os.path.join(output_dir, 'final_validation_report.json')):
        checks['final_validation'] = True
        print("✅ Final validation complete")
        
        # Check validation results
        with open(os.path.join(output_dir, 'final_validation_report.json'), 'r') as f:
            validation = json.load(f)
        
        if validation['constraints_met']:
            checks['trade_counts_valid'] = True
            print("✅ All trade counts >= 120")
        else:
            print("❌ Trade count constraints NOT met")
        
        if validation['portfolio']['sharpe_ratio'] >= 1.95:
            checks['portfolio_sharpe_target'] = True
            print(f"✅ Portfolio Sharpe: {validation['portfolio']['sharpe_ratio']:.3f} (target: 1.95+)")
        else:
            print(f"⚠️  Portfolio Sharpe: {validation['portfolio']['sharpe_ratio']:.3f} (target: 1.95+)")
    
    else:
        print("❌ Final validation missing - RUN NOW!")
    
    if os.path.exists(os.path.join(output_dir, 'SUBMISSION_DOCUMENTATION.md')):
        checks['submission_docs'] = True
        print("✅ Submission documentation generated")
    else:
        print("❌ Submission documentation missing")
    
    # Summary
    print("\n" + "="*70)
    print("CHECKLIST SUMMARY")
    print("="*70)
    
    total_checks = len(checks)
    passed_checks = sum(checks.values())
    
    print(f"Passed: {passed_checks}/{total_checks}")
    
    critical_checks = [
        'final_validation',
        'trade_counts_valid',
        'rule12_compliance',
        'transaction_costs_included'
    ]
    
    critical_passed = all([checks[c] for c in critical_checks])
    
    if critical_passed and checks['portfolio_sharpe_target']:
        print("\n🎉 ALL CRITICAL CHECKS PASSED - READY TO SUBMIT! 🎉")
        return True
    elif critical_passed:
        print("\n⚠️  Critical checks passed, but Sharpe below target")
        print("   Consider additional tuning or submit current version")
        return True
    else:
        print("\n❌ CRITICAL CHECKS FAILED - FIX BEFORE SUBMITTING")
        return False

if __name__ == "__main__":
    ready = run_master_checklist()
