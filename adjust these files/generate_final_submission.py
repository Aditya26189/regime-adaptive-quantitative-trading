"""
FINAL SUBMISSION GENERATOR (OPTUNA-OPTIMIZED)

Generates competition submission CSV using Optuna-optimized parameters.

Usage:
    python scripts/generate_final_submission.py

Output:
    output/23ME3EP03_optuna_submission_YYYYMMDD_HHMMSS.csv

Copilot Instructions:
- Loads best parameters from Optuna optimization
- Generates trades for all 5 symbols
- Creates competition-compliant CSV
- Runs final compliance checks
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import json
from datetime import datetime
import numpy as np


def generate_optuna_submission():
    """
    Generate final submission using Optuna-optimized parameters.
    """
    print("\n" + "="*60)
    print("GENERATING FINAL SUBMISSION (OPTUNA-OPTIMIZED)")
    print("="*60 + "\n")
    
    # Load Optuna results
    results_file = Path('optimization_results/optimization_results.json')
    if not results_file.exists():
        print("ERROR: Optimization results not found.")
        print("Run: python scripts/run_full_optimization.py first")
        return None
    
    with open(results_file, 'r') as f:
        optuna_results = json.load(f)
    
    # Import strategy functions
    from src.strategies.nifty_trend_strategy import generate_nifty_trend_signals
    from src.strategies.hybrid_adaptive import generate_hybrid_signals
    from src.strategies.ensemble_wrapper import ensemble_backtest
    
    all_trades = []
    portfolio_metrics = {}
    
    # Symbol configurations
    symbols = {
        'NSE:NIFTY50-INDEX': {
            'data_file': 'data/NSE_NIFTY50_INDEX_1hour.csv',
            'strategy': 'trend'
        },
        'NSE:VBL-EQ': {
            'data_file': 'data/NSE_VBL_EQ_1hour.csv',
            'strategy': 'ensemble'
        },
        'NSE:SUNPHARMA-EQ': {
            'data_file': 'data/NSE_SUNPHARMA_EQ_1hour.csv',
            'strategy': 'mean_reversion'
        },
        'NSE:RELIANCE-EQ': {
            'data_file': 'data/NSE_RELIANCE_EQ_1hour.csv',
            'strategy': 'hybrid'
        },
        'NSE:YESBANK-EQ': {
            'data_file': 'data/NSE_YESBANK_EQ_1hour.csv',
            'strategy': 'hybrid'
        }
    }
    
    for symbol, config in symbols.items():
        print(f"Processing: {symbol}")
        
        # Get optimized parameters for this symbol
        if symbol not in optuna_results:
            print(f"  ERROR: No optimization results for {symbol}")
            continue
        
        result = optuna_results[symbol]
        if 'error' in result:
            print(f"  ERROR: {result['error']}")
            continue
        
        params = result['best_params']
        
        # Load data
        data = pd.read_csv(config['data_file'])
        
        # Generate trades using optimized parameters
        if config['strategy'] == 'trend':
            trades_df = generate_nifty_trend_signals(data, params)
        elif config['strategy'] == 'ensemble':
            _, trades_df = ensemble_backtest(data, params)
        elif config['strategy'] == 'hybrid':
            trades_df = generate_hybrid_signals(data, params)
        else:  # mean_reversion
            trades_df = generate_hybrid_signals(data, params)
        
        # Validate
        if len(trades_df) < 120:
            print(f"  ✗ ERROR: Only {len(trades_df)} trades (need ≥120)")
            return None
        
        # Calculate metrics
        total_return = trades_df['pnl'].sum() / 100000 * 100
        trades_df['return_pct'] = trades_df['pnl'] / 100000 * 100
        sharpe = (trades_df['return_pct'].mean() / trades_df['return_pct'].std() 
                  if trades_df['return_pct'].std() > 0 else 0)
        
        print(f"  ✓ Return: {total_return:+.2f}% | Sharpe: {sharpe:.2f} | Trades: {len(trades_df)}")
        
        portfolio_metrics[symbol] = {
            'return': total_return,
            'sharpe': sharpe,
            'trades': len(trades_df)
        }
        
        # Add symbol column
        trades_df['symbol'] = symbol
        all_trades.append(trades_df)
    
    if not all_trades:
        print("\nERROR: No trades generated")
        return None
    
    # Combine all trades
    submission_df = pd.concat(all_trades, ignore_index=True)
    
    # Format submission CSV
    submission_formatted = pd.DataFrame({
        'student_roll_number': '23ME3EP03',
        'strategy_submission_number': 1,
        'symbol': submission_df['symbol'],
        'timeframe': 60,
        'entry_trade_time': pd.to_datetime(submission_df['entry_time']).dt.strftime('%Y-%m-%d %H:%M:%S'),
        'exit_trade_time': pd.to_datetime(submission_df['exit_time']).dt.strftime('%Y-%m-%d %H:%M:%S'),
        'entry_trade_price': submission_df['entry_price'].round(2),
        'exit_trade_price': submission_df['exit_price'].round(2),
        'qty': submission_df['qty'],
        'fees': 48,
        'cumulative_capital_after_trade': 0
    })
    
    # Calculate cumulative capital
    capital = 100000
    cumulative_capitals = []
    for pnl in submission_df['pnl']:
        capital += pnl
        cumulative_capitals.append(capital)
    submission_formatted['cumulative_capital_after_trade'] = cumulative_capitals
    
    # Save submission
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = output_dir / f'23ME3EP03_optuna_submission_{timestamp}.csv'
    submission_formatted.to_csv(filename, index=False)
    
    # Print summary
    print("\n" + "="*60)
    print("SUBMISSION GENERATED")
    print("="*60)
    
    avg_return = np.mean([m['return'] for m in portfolio_metrics.values()])
    avg_sharpe = np.mean([m['sharpe'] for m in portfolio_metrics.values()])
    total_trades = sum([m['trades'] for m in portfolio_metrics.values()])
    
    print(f"\nPortfolio Metrics:")
    print(f"  Average Return: {avg_return:+.2f}%")
    print(f"  Average Sharpe: {avg_sharpe:.3f}")
    print(f"  Total Trades: {total_trades}")
    
    print(f"\nPer-Symbol:")
    for symbol, metrics in portfolio_metrics.items():
        print(f"  {symbol:25s}: Return={metrics['return']:+6.2f}%, "
              f"Sharpe={metrics['sharpe']:5.2f}, Trades={metrics['trades']}")
    
    print(f"\nFile saved: {filename}")
    
    # Estimate rank
    if avg_sharpe >= 1.35:
        rank = "TOP 1-3 🏆🏆🏆"
    elif avg_sharpe >= 1.25:
        rank = "TOP 3-5 🏆🏆"
    elif avg_sharpe >= 1.15:
        rank = "TOP 5-10 🏆"
    else:
        rank = "TOP 10-15"
    
    print(f"\nEstimated Rank: {rank}")
    print("="*60 + "\n")
    
    return filename


def main():
    """Main execution."""
    try:
        filename = generate_optuna_submission()
        
        if filename:
            print("SUCCESS! Ready for submission.")
            print(f"\nNext steps:")
            print(f"1. Review file: {filename}")
            print(f"2. Run final compliance check")
            print(f"3. Submit before deadline")
        else:
            print("FAILED to generate submission.")
            sys.exit(1)
    
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
