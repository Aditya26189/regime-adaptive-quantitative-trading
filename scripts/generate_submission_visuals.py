"""
Generate visual analysis charts for final submission.
Creates equity curves, drawdown analysis, and symbol performance charts.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
from pathlib import Path
from datetime import datetime

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = [12, 7]
plt.rcParams['font.size'] = 10
plt.rcParams['lines.linewidth'] = 2

# Colors
COLORS = {
    'Portfolio': '#1f77b4',
    'VBL': '#ff7f0e',
    'RELIANCE': '#2ca02c',
    'SUNPHARMA': '#d62728',
    'YESBANK': '#9467bd',
    'NIFTY50': '#8c564b'
}

def load_data():
    base_dir = Path.cwd()
    file_path = base_dir / "submission/final/FINAL_SUBMISSION.csv"
    
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return None
        
    df = pd.read_csv(file_path)
    df['entry_trade_time'] = pd.to_datetime(df['entry_trade_time'])
    df['exit_trade_time'] = pd.to_datetime(df['exit_trade_time'])
    return df

def generate_equity_curve(df):
    """Generate portfolio equity curve"""
    # Sort by exit time
    df_sorted = df.sort_values('exit_trade_time')
    
    # Calculate PnL per trade
    df_sorted['pnl'] = (df_sorted['exit_trade_price'] - df_sorted['entry_trade_price']) * df_sorted['qty'] - df_sorted['fees']
    
    # Cumulative PnL
    df_sorted['cumulative_pnl'] = df_sorted['pnl'].cumsum()
    df_sorted['equity'] = 500000 + df_sorted['cumulative_pnl'] # Initial 100k * 5 symbols approx
    
    # Plot
    plt.figure()
    plt.plot(df_sorted['exit_trade_time'], df_sorted['equity'], label='Portfolio Equity', color=COLORS['Portfolio'])
    plt.title('Portfolio Equity Curve (All Strategies)', fontsize=14, pad=20)
    plt.xlabel('Date')
    plt.ylabel('Equity (INR)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Add stats box
    total_ret = (df_sorted['equity'].iloc[-1] - 500000) / 500000 * 100
    sharpe = 1.486 # Hardcoded from report
    trades = len(df_sorted)
    
    stats_text = f"Total Return: {total_ret:.1f}%\nSharpe Ratio: {sharpe}\nTotal Trades: {trades}"
    plt.text(0.02, 0.95, stats_text, transform=plt.gca().transAxes, 
             bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'), verticalalignment='top')
             
    plt.tight_layout()
    plt.savefig('reports/figures/equity_curve_portfolio.png', dpi=300)
    plt.close()
    print("Generated: equity_curve_portfolio.png")

def generate_per_symbol_curves(df):
    """Generate normalized equity curves per symbol"""
    plt.figure()
    
    symbols = df['symbol'].unique()
    
    for symbol in symbols:
        sym_df = df[df['symbol'] == symbol].copy().sort_values('exit_trade_time')
        sym_df['pnl'] = (sym_df['exit_trade_price'] - sym_df['entry_trade_price']) * sym_df['qty'] - sym_df['fees']
        sym_df['cum_pnl'] = sym_df['pnl'].cumsum()
        
        # Normalize to percentage return on 100k capital
        sym_df['return_pct'] = (sym_df['cum_pnl'] / 100000) * 100
        
        # Map symbol name for color
        color_key = symbol.replace('NSE:', '').replace('-EQ', '').replace('-INDEX', '')
        
        plt.plot(sym_df['exit_trade_time'], sym_df['return_pct'], label=color_key, color=COLORS.get(color_key, 'gray'))
        
    plt.title('Strategy Performance by Symbol', fontsize=14, pad=20)
    plt.xlabel('Date')
    plt.ylabel('Return on Capital (%)')
    plt.legend(loc='upper left')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('reports/figures/equity_curve_per_symbol.png', dpi=300)
    plt.close()
    print("Generated: equity_curve_per_symbol.png")

def generate_drawdown_chart(df):
    """Generate drawdown analysis"""
    df_sorted = df.sort_values('exit_trade_time')
    df_sorted['pnl'] = (df_sorted['exit_trade_price'] - df_sorted['entry_trade_price']) * df_sorted['qty'] - df_sorted['fees']
    df_sorted['equity'] = 500000 + df_sorted['pnl'].cumsum()
    
    # Calculate drawdown
    rolling_max = df_sorted['equity'].cummax()
    drawdown = (df_sorted['equity'] - rolling_max) / rolling_max * 100
    
    plt.figure()
    plt.fill_between(df_sorted['exit_trade_time'], drawdown, 0, color='red', alpha=0.3, label='Drawdown')
    plt.plot(df_sorted['exit_trade_time'], drawdown, color='red', linewidth=1)
    
    plt.title('Portfolio Drawdown Analysis', fontsize=14, pad=20)
    plt.xlabel('Date')
    plt.ylabel('Drawdown (%)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # horizontal line for max drawdown
    min_dd = drawdown.min()
    plt.axhline(y=min_dd, color='black', linestyle='--', alpha=0.5)
    plt.text(df_sorted['exit_trade_time'].iloc[0], min_dd, f" Max DD: {min_dd:.2f}%", verticalalignment='bottom')
    
    plt.tight_layout()
    plt.savefig('reports/figures/drawdown_chart.png', dpi=300)
    plt.close()
    print("Generated: drawdown_chart.png")

def main():
    print("Generating submission visuals...")
    Path("reports/figures").mkdir(parents=True, exist_ok=True)
    
    df = load_data()
    if df is not None:
        generate_equity_curve(df)
        generate_per_symbol_curves(df)
        generate_drawdown_chart(df)
        print("Done!")

if __name__ == "__main__":
    main()
