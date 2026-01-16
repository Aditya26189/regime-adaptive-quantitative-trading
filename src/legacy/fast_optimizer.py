"""
FAST RANDOM SEARCH OPTIMIZER
Uses random sampling to quickly find profitable parameters for each symbol
"""

import pandas as pd
import numpy as np
from typing import Dict, List
import random
from datetime import datetime
import json

# ============================================================================
# CONFIGURATION
# ============================================================================

STUDENT_ROLL_NUMBER = "23ME3EP03"

SYMBOLS_CONFIG = {
    'NIFTY50': {
        'symbol': 'NSE:NIFTY50-INDEX',
        'file': 'fyers_data/NSE_NIFTY50_INDEX_1hour.csv',
        'timeframe': '60',
        'type': 'trending'
    },
    'RELIANCE': {
        'symbol': 'NSE:RELIANCE-EQ',
        'file': 'fyers_data/NSE_RELIANCE_EQ_1hour.csv',
        'timeframe': '60',
        'type': 'mean_reverting'
    },
    'VBL': {
        'symbol': 'NSE:VBL-EQ',
        'file': 'fyers_data/NSE_VBL_EQ_1hour.csv',
        'timeframe': '60',
        'type': 'mean_reverting'
    },
    'YESBANK': {
        'symbol': 'NSE:YESBANK-EQ',
        'file': 'fyers_data/NSE_YESBANK_EQ_1hour.csv',
        'timeframe': '60',
        'type': 'trending'
    },
    'SUNPHARMA': {
        'symbol': 'NSE:SUNPHARMA-EQ',
        'file': 'fyers_data/NSE_SUNPHARMA_EQ_1hour.csv',
        'timeframe': '60',
        'type': 'mean_reverting'
    }
}

# Ranges for random sampling
PARAM_RANGES = {
    'rsi_entry': (5, 45),
    'rsi_exit': (50, 95),
    'vol_min': (0.0005, 0.01),
    'allowed_hours_choices': [
        [9], [9, 10], [9, 10, 11], [9, 10, 11, 12], [9, 10, 11, 12, 13],
        [10, 11], [10, 11, 12], [10, 11, 12, 13], [11, 12, 13],
        [9, 11, 13]  # Skip hours
    ],
    'max_hold': (1, 15)
}

NUM_RANDOM_SAMPLES = 500  # Test 500 random combinations per symbol

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

def backtest_symbol(df: pd.DataFrame, params: Dict) -> Dict:
    """Backtest single symbol with given parameters"""
    df = df.copy()
    df['rsi2'] = calculate_rsi(df['close'])
    df['volatility'] = calculate_volatility(df['close'])
    
    trades = []
    capital = 100000
    FEE = 24
    
    in_position = False
    entry_price = 0
    entry_capital = capital
    entry_qty = 0
    bars_held = 0
    
    for i in range(50, len(df)):
        current_time = df['datetime'].iloc[i]
        current_hour = current_time.hour
        current_minute = current_time.minute
        current_close = df['close'].iloc[i]
        
        prev_rsi = df['rsi2'].iloc[i-1]
        prev_vol = df['volatility'].iloc[i-1]
        
        if pd.isna(prev_rsi) or pd.isna(prev_vol):
            continue
        
        if not in_position:
            if current_hour not in params['allowed_hours']:
                continue
            if current_hour >= 14 and current_minute >= 30:
                continue
            
            if (prev_rsi < params['rsi_entry'] and 
                prev_vol > params['vol_min']):
                
                qty = int((capital - FEE) * 0.95 / current_close)
                
                if qty > 0:
                    entry_price = current_close
                    entry_capital = capital
                    entry_qty = qty
                    capital -= FEE
                    in_position = True
                    bars_held = 0
        else:
            bars_held += 1
            
            exit_signal = (
                prev_rsi > params['rsi_exit'] or
                bars_held >= params['max_hold'] or
                (current_hour >= 15 and current_minute >= 15)
            )
            
            if exit_signal:
                exit_price = current_close
                gross_pnl = entry_qty * (exit_price - entry_price)
                capital = entry_capital + gross_pnl - (2 * FEE)
                
                trades.append({
                    'pnl': gross_pnl - FEE,
                    'return_pct': (exit_price - entry_price) / entry_price * 100
                })
                
                in_position = False
                bars_held = 0
    
    if len(trades) == 0:
        return {
            'trades': 0,
            'return': -100,  # Penalty for no trades
            'win_rate': 0,
            'sharpe': -100,
            'params': params
        }
    
    trades_df = pd.DataFrame(trades)
    winning_trades = (trades_df['pnl'] > 0).sum()
    win_rate = winning_trades / len(trades_df) * 100
    total_return = (capital - 100000) / 100000 * 100
    
    returns = trades_df['return_pct'].values
    sharpe = (returns.mean() / returns.std()) * np.sqrt(len(returns)) if returns.std() > 0 else 0
    
    return {
        'trades': len(trades_df),
        'return': total_return,
        'win_rate': win_rate,
        'sharpe': sharpe,
        'params': params
    }

def generate_random_params():
    """Generate random parameter combination"""
    return {
        'rsi_entry': random.randint(PARAM_RANGES['rsi_entry'][0], PARAM_RANGES['rsi_entry'][1]),
        'rsi_exit': random.randint(PARAM_RANGES['rsi_exit'][0], PARAM_RANGES['rsi_exit'][1]),
        'vol_min': round(random.uniform(PARAM_RANGES['vol_min'][0], PARAM_RANGES['vol_min'][1]), 4),
        'allowed_hours': random.choice(PARAM_RANGES['allowed_hours_choices']),
        'max_hold': random.randint(PARAM_RANGES['max_hold'][0], PARAM_RANGES['max_hold'][1])
    }

def optimize_symbol(symbol_name: str, df: pd.DataFrame, num_samples: int = NUM_RANDOM_SAMPLES) -> Dict:
    """Find optimal parameters using random search"""
    print(f"\n{'='*70}")
    print(f"OPTIMIZING: {symbol_name}")
    print(f"{'='*70}")
    print(f"Testing {num_samples} random parameter combinations...")
    
    results = []
    valid_results = []
    best_positive = None
    
    for i in range(num_samples):
        if (i + 1) % 100 == 0:
            print(f"  Progress: {i + 1}/{num_samples}")
        
        params = generate_random_params()
        # Ensure RSI entry < RSI exit
        if params['rsi_entry'] >= params['rsi_exit'] - 10:
            params['rsi_exit'] = min(95, params['rsi_entry'] + 30)
        
        result = backtest_symbol(df, params)
        results.append(result)
        
        # Track valid results (≥120 trades)
        if result['trades'] >= 120:
            valid_results.append(result)
            
            # Track best positive return
            if result['return'] > 0 and (best_positive is None or result['return'] > best_positive['return']):
                best_positive = result
                print(f"  🎯 Found positive return: {result['return']:.2f}% with {result['trades']} trades")
    
    # Sort valid results by return
    if len(valid_results) > 0:
        valid_results.sort(key=lambda x: x['return'], reverse=True)
        print(f"\n✅ Found {len(valid_results)} combinations with 120+ trades")
        
        # If we found positive returns, use those
        positive_results = [r for r in valid_results if r['return'] > 0]
        if len(positive_results) > 0:
            print(f"✅ Found {len(positive_results)} combinations with POSITIVE returns!")
            best = positive_results[0]
        else:
            # Use least negative
            best = valid_results[0]
            print(f"⚠️  No positive returns found, using least negative: {best['return']:.2f}%")
    else:
        # Fallback to best trade count
        results.sort(key=lambda x: x['trades'], reverse=True)
        best = results[0]
        print(f"⚠️  No combinations with 120+ trades, best has {best['trades']}")
    
    print(f"\n✅ BEST PARAMETERS:")
    print(f"   Trades: {best['trades']}")
    print(f"   Return: {best['return']:.2f}%")
    print(f"   Win Rate: {best['win_rate']:.1f}%")
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

def main():
    """Optimize all symbols using random search"""
    print("="*70)
    print("FAST RANDOM SEARCH OPTIMIZER")
    print("="*70)
    print(f"\nTesting {NUM_RANDOM_SAMPLES} random combinations per symbol")
    print("Goal: Find profitable parameters while meeting 120-trade minimum\n")
    
    random.seed(42)  # Reproducibility
    
    optimal_params = {}
    total_return = 0
    total_trades = 0
    
    for symbol_name, config in SYMBOLS_CONFIG.items():
        # Load data once per symbol
        df = pd.read_csv(config['file'])
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        
        result = optimize_symbol(symbol_name, df)
        optimal_params[symbol_name] = result
        total_return += result['metrics']['return']
        total_trades += result['metrics']['trades']
    
    avg_return = total_return / len(SYMBOLS_CONFIG)
    
    print("\n" + "="*70)
    print("OPTIMIZATION COMPLETE - PORTFOLIO SUMMARY")
    print("="*70)
    
    for symbol, data in optimal_params.items():
        metrics = data['metrics']
        status = "✅" if metrics['trades'] >= 120 else "❌"
        ret_status = "🟢" if metrics['return'] > 0 else "🔴"
        print(f"\n{status} {ret_status} {symbol}:")
        print(f"   Trades: {metrics['trades']}")
        print(f"   Return: {metrics['return']:.2f}%")
        print(f"   Win Rate: {metrics['win_rate']:.1f}%")
    
    print(f"\n{'='*70}")
    print(f"PORTFOLIO METRICS:")
    print(f"   Total Trades: {total_trades}")
    print(f"   Average Return: {avg_return:.2f}%")
    
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
    
    print(f"\n✅ Saved to: optimal_params_per_symbol.json")
    print(f"📝 NEXT: python submission_generator_optimized.py")
    
    return optimal_params

if __name__ == "__main__":
    import time
    start = time.time()
    main()
    print(f"\n⏱️ Time: {(time.time()-start)/60:.1f} minutes")
