"""
MAIN OPTIMIZATION EXECUTION SCRIPT

Single command to run complete Optuna optimization for all symbols.

Usage:
    python scripts/run_full_optimization.py

Expected results:
- Portfolio Sharpe: 1.30-1.45 (vs 1.01 current)
- Rank: TOP 1-5 (vs TOP 8-12 current)
- Runtime: 60-90 minutes (parallel)

Copilot Instructions:
- Just run this script and wait
- Results saved automatically
- Progress bars show status
- Can resume if interrupted (Optuna stores state in DB)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.optimization.parallel_optimizer import ParallelSymbolOptimizer
import argparse
from datetime import datetime
import json


def main():
    """
    Main optimization workflow.
    """
    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Run Optuna optimization for all trading symbols'
    )
    parser.add_argument(
        '--trials',
        type=int,
        default=200,
        help='Number of trials per symbol (default: 200)'
    )
    parser.add_argument(
        '--jobs',
        type=int,
        default=-1,
        help='Number of parallel jobs, -1 for all cores (default: -1)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=None,
        help='Timeout per symbol in seconds (default: None)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='optimization_results',
        help='Output directory (default: optimization_results)'
    )
    parser.add_argument(
        '--quick-test',
        action='store_true',
        help='Quick test mode (10 trials per symbol, ~5 minutes)'
    )
    
    args = parser.parse_args()
    
    # Quick test mode
    if args.quick_test:
        print("\n" + "!"*60)
        print("QUICK TEST MODE - 10 trials per symbol")
        print("This is for testing the pipeline, not final optimization")
        print("!"*60 + "\n")
        args.trials = 10
    
    print("\n" + "="*60)
    print("OPTUNA OPTIMIZATION - FIRST PLACE PROTOCOL")
    print("="*60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Configuration:")
    print(f"  - Trials per symbol: {args.trials}")
    print(f"  - Parallel jobs: {args.jobs if args.jobs > 0 else 'ALL CORES'}")
    print(f"  - Timeout: {args.timeout if args.timeout else 'None'}")
    print(f"  - Output: {args.output}/")
    print("="*60 + "\n")
    
    # Create optimizer
    optimizer = ParallelSymbolOptimizer(
        n_trials=args.trials,
        n_jobs=args.jobs,
        timeout=args.timeout,
        output_dir=args.output
    )
    
    # Run optimization
    try:
        results = optimizer.optimize_all()
    except KeyboardInterrupt:
        print("\n\nOptimization interrupted by user.")
        print("Progress has been saved. You can resume by running this script again.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: Optimization failed - {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Generate visualizations
    print("\nGenerating visualization plots...")
    try:
        optimizer.generate_visualization()
    except Exception as e:
        print(f"Warning: Visualization failed - {e}")
    
    # Final summary
    print("\n" + "="*60)
    print("OPTIMIZATION WORKFLOW COMPLETE")
    print("="*60)
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nResults saved to: {args.output}/")
    print(f"  - optimization_results.json (full results)")
    print(f"  - best_params_per_symbol.json (parameters only)")
    print(f"  - optuna_studies.db (Optuna database)")
    print(f"  - plots/ (visualization HTML files)")
    
    # Next steps
    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)
    print("1. Review results in optimization_results.json")
    print("2. Check plots in plots/ directory")
    print("3. Run: python scripts/validate_results.py")
    print("4. Run: python scripts/generate_final_submission.py")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
