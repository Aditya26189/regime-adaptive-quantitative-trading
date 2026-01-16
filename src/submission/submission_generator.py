"""
SUBMISSION GENERATOR - Uses per-symbol optimized parameters
Generates final CSV for competition submission
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from typing import Dict, List
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import SYMBOLS_CONFIG, STUDENT_ROLL_NUMBER, OPTIMIZER_PARAMS_FILE, OUTPUT_DIR
from src.utils.indicators import calculate_rsi, calculate_volatility

STRATEGY_NUMBER = 1

def generate_trades_for_symbol(symbol_name: str, params: Dict) -> List[Dict]:
    """Generate trades for a single symbol using optimized parameters"""
    config = SYMBOLS_CONFIG[symbol_name]
    print(f"\nProcessing {symbol_name}...")
    print(f"Parameters: {params}")
    
    # Load data
    try:
        df = pd.read_csv(config['file'])
    except FileNotFoundError:
        print(f"❌ Error: File not found: {config['file']}")
        return []
        
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    # Calculate indicators
    df['rsi2'] = calculate_rsi(df['close'])
    df['volatility'] = calculate_volatility(df['close'])
    
    # Run backtest
    trades = []
    capital = 100000
    FEE = 24
    
    in_position = False
    entry_price = 0
    entry_time = None
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
        
        # ENTRY
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
                    entry_time = current_time
                    entry_capital = capital
                    entry_qty = qty
                    capital -= FEE
                    in_position = True
                    bars_held = 0
        
        # EXIT
        else:
            bars_held += 1
            
            exit_signal = (
                prev_rsi > params['rsi_exit'] or
                bars_held >= params['max_hold'] or
                (current_hour >= 15 and current_minute >= 15)
            )
            
            if exit_signal:
                exit_price = current_close
                exit_time = current_time
                
                gross_pnl = entry_qty * (exit_price - entry_price)
                net_pnl = gross_pnl - FEE
                capital = entry_capital + gross_pnl - (2 * FEE)
                
                trades.append({
                    'student_roll_number': STUDENT_ROLL_NUMBER,
                    'strategy_submission_number': STRATEGY_NUMBER,
                    'symbol': config['symbol'],
                    'timeframe': config['timeframe'],
                    'entry_trade_time': entry_time,
                    'exit_trade_time': exit_time,
                    'entry_trade_price': entry_price,
                    'exit_trade_price': exit_price,
                    'qty': entry_qty,
                    'fees': 2 * FEE,
                    'cumulative_capital_after_trade': capital
                })
                
                in_position = False
                bars_held = 0
    
    print(f"  Generated {len(trades)} trades")
    
    if len(trades) > 0:
        trades_df = pd.DataFrame(trades)
        pnl = (trades_df['exit_trade_price'] - trades_df['entry_trade_price']) * trades_df['qty'] - trades_df['fees']
        total_return = (capital - 100000) / 100000 * 100
        win_rate = (pnl > 0).sum() / len(pnl) * 100
        print(f"  Return: {total_return:.2f}%")
        print(f"  Win Rate: {win_rate:.1f}%")
    
    return trades

def main():
    """Generate final submission using optimized per-symbol parameters"""
    print("="*70)
    print("GENERATING OPTIMIZED SUBMISSION")
    print("="*70)
    
    # Load optimal parameters
    try:
        with open(OPTIMIZER_PARAMS_FILE, 'r') as f:
            optimal_params = json.load(f)
        print(f"\n✅ Loaded optimal parameters from: {OPTIMIZER_PARAMS_FILE}")
    except FileNotFoundError:
        print(f"\n❌ ERROR: {OPTIMIZER_PARAMS_FILE} not found")
        print("   Please run src/optimizers/fast_optimizer.py first!")
        return
    
    # Generate trades for all symbols
    all_trades = []
    
    for symbol_name in SYMBOLS_CONFIG.keys():
        if symbol_name in optimal_params:
            params = optimal_params[symbol_name]['params']
            trades = generate_trades_for_symbol(symbol_name, params)
            all_trades.extend(trades)
        else:
            print(f"\n⚠️  WARNING: No optimal params found for {symbol_name}")
    
    if len(all_trades) == 0:
        print("\n❌ ERROR: No trades generated!")
        return
    
    # Create submission DataFrame
    submission_df = pd.DataFrame(all_trades)
    submission_df = submission_df.sort_values(['symbol', 'entry_trade_time'])
    
    # Validation
    print("\n" + "="*70)
    print("VALIDATION CHECKS")
    print("="*70)
    
    all_valid = True
    for symbol_name, config in SYMBOLS_CONFIG.items():
        symbol_trades = submission_df[submission_df['symbol'] == config['symbol']]
        trade_count = len(symbol_trades)
        
        if trade_count >= 120:
            print(f"✅ {symbol_name}: {trade_count} trades (≥ 120)")
        else:
            print(f"❌ {symbol_name}: {trade_count} trades (< 120) - FAIL")
            all_valid = False
    
    # Performance summary
    print("\n" + "="*70)
    print("PER-SYMBOL PERFORMANCE")
    print("="*70)
    
    total_return = 0
    
    for symbol_name, config in SYMBOLS_CONFIG.items():
        symbol_trades = submission_df[submission_df['symbol'] == config['symbol']]
        
        if len(symbol_trades) > 0:
            final_capital = symbol_trades.iloc[-1]['cumulative_capital_after_trade']
            symbol_return = (final_capital - 100000) / 100000 * 100
            total_return += symbol_return
            
            pnl = (symbol_trades['exit_trade_price'] - symbol_trades['entry_trade_price']) * symbol_trades['qty'] - symbol_trades['fees']
            win_rate = (pnl > 0).sum() / len(pnl) * 100
            
            print(f"{symbol_name:12} | Trades: {len(symbol_trades):3} | Return: {symbol_return:>7.2f}% | Win Rate: {win_rate:>5.1f}%")
    
    avg_return = total_return / len(SYMBOLS_CONFIG)
    total_trades = len(submission_df)
    
    print(f"\n{'='*70}")
    print(f"PORTFOLIO SUMMARY")
    print(f"{'='*70}")
    print(f"Total Trades: {total_trades}")
    print(f"Average Return: {avg_return:.2f}%")
    print(f"Expected Capital: ₹{100000 * (1 + avg_return/100):,.2f}")
    print(f"{'='*70}")
    
    # Save submission
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"{STUDENT_ROLL_NUMBER}_optimized_submission_{timestamp}.csv"
    
    submission_df.to_csv(output_file, index=False)
    
    print(f"\n✅ Submission saved: {output_file}")
    
    # Get file size
    import os
    file_size = os.path.getsize(output_file) / 1024
    print(f"   File size: {file_size:.1f} KB")
    
    # Final checks
    print("\n" + "="*70)
    print("FINAL CHECKS")
    print("="*70)
    
    required_cols = [
        'student_roll_number', 'strategy_submission_number', 'symbol',
        'timeframe', 'entry_trade_time', 'exit_trade_time',
        'entry_trade_price', 'exit_trade_price', 'qty', 'fees',
        'cumulative_capital_after_trade'
    ]
    
    if list(submission_df.columns) == required_cols:
        print("✅ Column format correct")
    else:
        print("❌ Column format incorrect")
        print(f"   Expected: {required_cols}")
        print(f"   Got: {list(submission_df.columns)}")
    
    if total_trades >= 600:
        print(f"✅ Total trade count sufficient ({total_trades})")
    else:
        print(f"⚠️  Total trade count: {total_trades} (expected 600+)")
    
    if all_valid:
        print("\n" + "="*70)
        print("✅ READY FOR SUBMISSION!")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("⚠️  SOME SYMBOLS BELOW 120 TRADES - Review manually")
        print("="*70)

if __name__ == "__main__":
    main()
