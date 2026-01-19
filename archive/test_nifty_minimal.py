import pandas as pd
import sys
sys.path.insert(0, '.')

from src.strategies.nifty_minimal_loss import generate_nifty_minimal_loss_signals

df = pd.read_csv('data/raw/NSE_NIFTY50_INDEX_1hour.csv')

params = {
    'rsi_entry': 25,
    'rsi_exit': 70,
    'max_hold': 8,
    'stop_loss_pct': 0.8,
    'profit_target_pct': 1.2
}

trades = generate_nifty_minimal_loss_signals(df, params)

print(f"Trades: {len(trades)}")
print(f"Return: {trades['pnl'].sum()/100000*100:.2f}%")

if len(trades) > 0:
    returns_pct = trades['pnl'] / 100000 * 100
    sharpe = returns_pct.mean() / returns_pct.std()
    print(f"Sharpe: {sharpe:.4f}")
    print(f"Win Rate: {(trades['pnl'] > 0).sum() / len(trades) * 100:.1f}%")
