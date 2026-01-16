"""
PER-SYMBOL PARAMETER OPTIMIZATION
Finds optimal RSI/volatility thresholds for EACH symbol independently
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import itertools
from datetime import datetime
import json

# ============================================================================
# CONFIGURATION
# ============================================================================

STUDENT_ROLL_NUMBER = "23ME3EP03"  # UPDATE THIS TO YOUR ROLL NUMBER

SYMBOLS_CONFIG = {
    'NIFTY50': {
        'symbol': 'NSE:NIFTY50-INDEX',
        'file': 'fyers_data/NSE_NIFTY50_INDEX_1hour.csv',
        'timeframe': '60',
        'type': 'trending'  # Index tends to trend
    },
    'RELIANCE': {
        'symbol': 'NSE:RELIANCE-EQ',
        'file': 'fyers_data/NSE_RELIANCE_EQ_1hour.csv',
        'timeframe': '60',
        'type': 'mean_reverting'  # Already profitable
    },
    'VBL': {
        'symbol': 'NSE:VBL-EQ',
        'file': 'fyers_data/NSE_VBL_EQ_1hour.csv',
        'timeframe': '60',
        'type': 'mean_reverting'  # Already profitable
    },
    'YESBANK': {
        'symbol': 'NSE:YESBANK-EQ',
        'file': 'fyers_data/NSE_YESBANK_EQ_1hour.csv',
        'timeframe': '60',
        'type': 'trending'  # High volatility, trending
    },
    'SUNPHARMA': {
        'symbol': 'NSE:SUNPHARMA-EQ',
        'file': 'fyers_data/NSE_SUNPHARMA_EQ_1hour.csv',
        'timeframe': '60',
        'type': 'mean_reverting'  # Best performer
    }
}

# Parameter search space - EXPANDED for better optimization
PARAM_GRID = {
    'mean_reverting': {
        'rsi_entry': [10, 12, 15, 18, 20, 25, 30, 35, 40],  # Wide range including extreme oversold
        'rsi_exit': [55, 60, 65, 70, 75, 80, 85, 90],  # Including very high exits
        'vol_min': [0.001, 0.0015, 0.002, 0.003, 0.004, 0.005],  # More volatility options
        'allowed_hours': [[9, 10, 11], [9, 10, 11, 12], [9, 10, 11, 12, 13], [10, 11, 12, 13]],  # Various windows
        'max_hold': [3, 4, 5, 6, 8, 10, 12]  # Including very short holds
    },
    'trending': {
        'rsi_entry': [8, 10, 12, 15, 18, 20, 25, 30, 35],  # Very strict to looser
        'rsi_exit': [55, 60, 65, 70, 75, 80, 85, 90],  
        'vol_min': [0.002, 0.003, 0.004, 0.005, 0.007],  # Higher vol filters
        'allowed_hours': [[9, 10], [9, 10, 11], [9, 10, 11, 12], [10, 11, 12]],  # Morning focus
        'max_hold': [2, 3, 4, 5, 6, 8]  # Very short to medium holds
    }
}

# ============================================================================
# INDICATOR CALCULATIONS
# ============================================================================

def calculate_rsi(close: pd.Series, period: int = 2) -> pd.Series:
    """RSI calculation using Wilder's smoothing"""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))

def calculate_volatility(close: pd.Series, period: int = 14) -> pd.Series:
    """Close-based volatility (Rule 12 compliant)"""
    rolling_max = close.rolling(window=period).max()
    rolling_min = close.rolling(window=period).min()
    return (rolling_max - rolling_min) / close

# ============================================================================
# BACKTESTING ENGINE
# ============================================================================

def backtest_symbol(df: pd.DataFrame, params: Dict, symbol_name: str) -> Dict:
    """
    Backtest single symbol with given parameters
    
    Args:
        df: DataFrame with datetime, close columns
        params: Dict with rsi_entry, rsi_exit, vol_min, allowed_hours, max_hold
        symbol_name: Symbol identifier for logging
    
    Returns:
        Dict with metrics: trades, return, win_rate, sharpe, avg_win, avg_loss
    """
    # Calculate indicators
    df = df.copy()
    df['rsi2'] = calculate_rsi(df['close'])
    df['volatility'] = calculate_volatility(df['close'])
    
    # Initialize backtest
    trades = []
    capital = 100000
    FEE = 24
    
    in_position = False
    entry_price = 0
    entry_time = None
    entry_capital = capital
    entry_qty = 0
    bars_held = 0
    
    # Trading loop
    for i in range(50, len(df)):
        current_time = df['datetime'].iloc[i]
        current_hour = current_time.hour
        current_minute = current_time.minute
        current_close = df['close'].iloc[i]
        
        prev_rsi = df['rsi2'].iloc[i-1]
        prev_vol = df['volatility'].iloc[i-1]
        
        # Skip if indicators are NaN
        if pd.isna(prev_rsi) or pd.isna(prev_vol):
            continue
        
        # === ENTRY LOGIC ===
        if not in_position:
            # Time filter
            if current_hour not in params['allowed_hours']:
                continue
            if current_hour >= 14 and current_minute >= 30:
                continue
            
            # Entry conditions
            if (prev_rsi < params['rsi_entry'] and 
                prev_vol > params['vol_min']):
                
                # Calculate position size
                qty = int((capital - FEE) * 0.95 / current_close)
                
                if qty > 0:
                    entry_price = current_close
                    entry_time = current_time
                    entry_capital = capital
                    entry_qty = qty
                    capital -= FEE
                    in_position = True
                    bars_held = 0
        
        # === EXIT LOGIC ===
        else:
            bars_held += 1
            
            # Exit conditions
            exit_signal = (
                prev_rsi > params['rsi_exit'] or
                bars_held >= params['max_hold'] or
                (current_hour >= 15 and current_minute >= 15)
            )
            
            if exit_signal:
                exit_price = current_close
                exit_time = current_time
                
                # Calculate P&L
                gross_pnl = entry_qty * (exit_price - entry_price)
                net_pnl = gross_pnl - FEE
                capital = entry_capital + gross_pnl - (2 * FEE)
                
                trades.append({
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl': net_pnl,
                    'return_pct': (exit_price - entry_price) / entry_price * 100
                })
                
                in_position = False
                bars_held = 0
    
    # Calculate metrics
    if len(trades) == 0:
        return {
            'trades': 0,
            'return': 0,
            'win_rate': 0,
            'sharpe': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'params': params
        }
    
    trades_df = pd.DataFrame(trades)
    winning_trades = (trades_df['pnl'] > 0).sum()
    win_rate = winning_trades / len(trades_df) * 100
    total_return = (capital - 100000) / 100000 * 100
    
    returns = trades_df['return_pct'].values
    sharpe = (returns.mean() / returns.std()) * np.sqrt(len(returns)) if returns.std() > 0 else 0
    
    avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
    avg_loss = trades_df[trades_df['pnl'] <= 0]['pnl'].mean() if len(trades_df) - winning_trades > 0 else 0
    
    return {
        'trades': len(trades_df),
        'return': total_return,
        'win_rate': win_rate,
        'sharpe': sharpe,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'params': params
    }

# ============================================================================
# OPTIMIZATION ENGINE
# ============================================================================

def optimize_symbol(symbol_name: str) -> Dict:
    """
    Find optimal parameters for a specific symbol
    
    Args:
        symbol_name: One of 'NIFTY50', 'RELIANCE', 'VBL', 'YESBANK', 'SUNPHARMA'
    
    Returns:
        Dict with best_params and metrics
    """
    print(f"\n{'='*70}")
    print(f"OPTIMIZING: {symbol_name}")
    print(f"{'='*70}")
    
    # Load configuration
    config = SYMBOLS_CONFIG[symbol_name]
    symbol_type = config['type']
    
    # Load data
    print(f"Loading data from {config['file']}...")
    df = pd.read_csv(config['file'])
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    print(f"Data loaded: {len(df)} bars from {df['datetime'].min()} to {df['datetime'].max()}")
    
    # Get parameter grid
    grid = PARAM_GRID[symbol_type]
    
    # Generate all parameter combinations
    param_combinations = []
    for rsi_entry, rsi_exit, vol_min, hours, hold in itertools.product(
        grid['rsi_entry'],
        grid['rsi_exit'],
        grid['vol_min'],
        grid['allowed_hours'],
        grid['max_hold']
    ):
        param_combinations.append({
            'rsi_entry': rsi_entry,
            'rsi_exit': rsi_exit,
            'vol_min': vol_min,
            'allowed_hours': hours,
            'max_hold': hold
        })
    
    print(f"Testing {len(param_combinations)} parameter combinations...")
    print(f"Symbol type: {symbol_type}")
    
    # Test all combinations
    results = []
    valid_results = []
    
    for idx, params in enumerate(param_combinations):
        if (idx + 1) % 50 == 0:
            print(f"  Progress: {idx + 1}/{len(param_combinations)} combinations tested...")
        
        result = backtest_symbol(df.copy(), params, symbol_name)
        results.append(result)
        
        # Only keep results that meet trade count requirement
        if result['trades'] >= 120:
            valid_results.append(result)
    
    # Check if we have any valid results
    if len(valid_results) == 0:
        print(f"\n⚠️  WARNING: No parameter combinations achieved 120+ trades!")
        print(f"   Best trade count: {max([r['trades'] for r in results])}")
        print(f"   Falling back to best available combination...")
        
        # Use best result even if below 120 trades
        results_df = pd.DataFrame(results)
    else:
        results_df = pd.DataFrame(valid_results)
        print(f"\n✅ Found {len(valid_results)} valid combinations with 120+ trades")
    
    # Rank by composite score (return + win_rate)
    results_df['score'] = results_df['return'] + (results_df['win_rate'] / 10)
    results_df = results_df.sort_values('score', ascending=False).reset_index(drop=True)
    
    # Display top 5
    print(f"\nTop 5 Parameter Sets:")
    print(f"{'='*100}")
    print(f"{'Rank':<5} {'Trades':<8} {'Return':<10} {'Win%':<8} {'Sharpe':<8} {'RSI Entry':<10} {'Hours':<20}")
    print(f"{'='*100}")
    
    for idx, row in results_df.head(5).iterrows():
        params = row['params']
        print(f"{idx+1:<5} {row['trades']:<8} {row['return']:>8.2f}% {row['win_rate']:>6.1f}% "
              f"{row['sharpe']:>7.2f} {params['rsi_entry']:<10} {str(params['allowed_hours']):<20}")
    
    # Select best
    best = results_df.iloc[0]
    
    print(f"\n✅ BEST PARAMETERS SELECTED:")
    print(f"   Trades: {best['trades']}")
    print(f"   Return: {best['return']:.2f}%")
    print(f"   Win Rate: {best['win_rate']:.1f}%")
    print(f"   Sharpe: {best['sharpe']:.2f}")
    print(f"   Avg Win: ₹{best['avg_win']:.2f}")
    print(f"   Avg Loss: ₹{best['avg_loss']:.2f}")
    print(f"   Parameters: {best['params']}")
    
    return {
        'symbol': symbol_name,
        'best_params': best['params'],
        'metrics': {
            'trades': int(best['trades']),
            'return': float(best['return']),
            'win_rate': float(best['win_rate']),
            'sharpe': float(best['sharpe'])
        }
    }

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """
    Optimize all 5 symbols individually and save results
    """
    print("="*70)
    print("PER-SYMBOL PARAMETER OPTIMIZATION")
    print("="*70)
    print("\nStrategy: Find best parameters for EACH symbol independently")
    print("Goal: Maximize total portfolio return while meeting trade minimums\n")
    
    optimal_params = {}
    total_return = 0
    total_trades = 0
    
    # Optimize each symbol
    for symbol_name in SYMBOLS_CONFIG.keys():
        result = optimize_symbol(symbol_name)
        optimal_params[symbol_name] = result
        total_return += result['metrics']['return']
        total_trades += result['metrics']['trades']
    
    # Portfolio summary
    avg_return = total_return / len(SYMBOLS_CONFIG)
    
    print("\n" + "="*70)
    print("OPTIMIZATION COMPLETE - PORTFOLIO SUMMARY")
    print("="*70)
    
    for symbol, data in optimal_params.items():
        metrics = data['metrics']
        status = "✅" if metrics['trades'] >= 120 else "❌"
        print(f"\n{status} {symbol}:")
        print(f"   Trades: {metrics['trades']}")
        print(f"   Return: {metrics['return']:.2f}%")
        print(f"   Win Rate: {metrics['win_rate']:.1f}%")
        print(f"   Params: {data['best_params']}")
    
    print(f"\n{'='*70}")
    print(f"PORTFOLIO METRICS:")
    print(f"   Total Trades: {total_trades}")
    print(f"   Average Return: {avg_return:.2f}%")
    print(f"   Expected Final Capital: ₹{100000 * (1 + avg_return/100):,.2f}")
    
    # Estimate rank
    if avg_return > 4:
        rank_estimate = "Top 15-20"
    elif avg_return > 2:
        rank_estimate = "Top 20-30"
    elif avg_return > 0:
        rank_estimate = "Top 30-45"
    else:
        rank_estimate = "Below 50th"
    
    print(f"   Estimated Rank: {rank_estimate} / 100")
    print(f"{'='*70}")
    
    # Save results
    save_data = {}
    for symbol, data in optimal_params.items():
        save_data[symbol] = {
            'params': data['best_params'],
            'metrics': data['metrics']
        }
    
    with open('optimal_params_per_symbol.json', 'w') as f:
        json.dump(save_data, f, indent=2)
    
    print(f"\n✅ Optimal parameters saved to: optimal_params_per_symbol.json")
    print(f"\n📝 NEXT STEP:")
    print(f"   Run: python submission_generator_optimized.py")
    print(f"   This will create your final submission CSV using these optimized parameters")
    
    return optimal_params

if __name__ == "__main__":
    import time
    start_time = time.time()
    
    optimal_params = main()
    
    elapsed = time.time() - start_time
    print(f"\n⏱️  Total optimization time: {elapsed/60:.1f} minutes")
