"""
Full NIFTY50 optimization (1000 iterations)
"""

import pandas as pd
import json
from datetime import datetime
from src.strategies.nifty_trend_strategy import optimize_nifty_trend_parameters, calculate_sharpe_ratio

print("="*60)
print("NIFTY50 FULL OPTIMIZATION - 1000 ITERATIONS")
print("="*60)
print(f"Started: {datetime.now().strftime('%H:%M:%S')}")

# Load data
data = pd.read_csv('data/raw/NSE_NIFTY50_INDEX_1hour.csv')

# Full optimization
# Using 1000 iterations for deep search
params, trades_df = optimize_nifty_trend_parameters(data, n_iterations=1000, verbose=True)

if params is None:
    print("\n❌ OPTIMIZATION FAILED!")
    exit(1)

# Calculate comprehensive metrics
total_return = trades_df['pnl'].sum() / 100000 * 100
sharpe = calculate_sharpe_ratio(trades_df)
win_rate = (trades_df['pnl'] > 0).sum() / len(trades_df) * 100
avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if (trades_df['pnl'] > 0).any() else 0
avg_loss = trades_df[trades_df['pnl'] < 0]['pnl'].mean() if (trades_df['pnl'] < 0).any() else 0
max_win = trades_df['pnl'].max()
max_loss = trades_df['pnl'].min()

print(f"\n{'='*60}")
print(f"FINAL OPTIMIZATION RESULTS")
print(f"{'='*60}")
print(f"Return: {total_return:+.2f}% (Target: +4% to +6%)")
print(f"Sharpe: {sharpe:.3f} (Target: > 1.2)")
print(f"Trades: {len(trades_df)} (Min: 120)")
print(f"Win Rate: {win_rate:.1f}%")
print(f"Avg Win: ₹{avg_win:.0f}")
print(f"Avg Loss: ₹{avg_loss:.0f}")

# Save optimal parameters (Use NpEncoder)
import numpy as np
class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)

output = {
    'NIFTY50_TREND': params,
    'metrics': {
        'return': total_return,
        'sharpe': sharpe,
        'trades': len(trades_df),
        'win_rate': win_rate,
    },
    'timestamp': datetime.now().isoformat(),
}

with open('output/nifty_trend_optimized_params.json', 'w') as f:
    json.dump(output, f, indent=2, cls=NpEncoder)

print(f"\n✓ Parameters saved to output/nifty_trend_optimized_params.json")

# Save trades
trades_df.to_csv('output/nifty50_optimized_trades.csv', index=False)
print(f"✓ Trades saved to output/nifty50_optimized_trades.csv")
