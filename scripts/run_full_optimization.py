"""
MAIN OPTIMIZATION EXECUTION SCRIPT

Single command to run complete Optuna optimization for all symbols.
"""

import sys
from pathlib import Path
import argparse

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.optimization.parallel_optimizer import run_parallel_optimization

def main():
    parser = argparse.ArgumentParser(description="Run Optuna Parallel Optimization")
    parser.add_argument('--trials', type=int, default=200, help='Number of trials per symbol')
    parser.add_argument('--symbols', nargs='+', help='List of symbols to optimize (default: all)')
    parser.add_argument('--quick-test', action='store_true', help='Run short test (10 trials)')
    
    args = parser.parse_args()
    
    trials = 10 if args.quick_test else args.trials
    
    print(f"🚀 Initializing Optuna Optimization...")
    run_parallel_optimization(symbols=args.symbols, n_trials=trials)
    print("\n✅ Run 'python scripts/generate_final_submission.py' to generate artifacts.")

if __name__ == "__main__":
    main()
