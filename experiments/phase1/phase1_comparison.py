
"""
Compare all Phase 1 techniques and select best configuration per symbol
"""

import json
import pandas as pd
import os
import sys

def compare_phase1_results():
    """Load all Phase 1 results and create comparison"""
    
    # Load results from each technique
    output_dir = 'output'
    if not os.path.exists(output_dir):
        # Maybe run from nested script? try ../../output
        output_dir = '../../output'
        
    try:
        with open(os.path.join(output_dir, 'phase1_nifty_trend.json'), 'r') as f:
            nifty_trend = json.load(f)
    except FileNotFoundError:
        nifty_trend = None
    
    try:
        with open(os.path.join(output_dir, 'phase1_vol_adaptive.json'), 'r') as f:
            vol_adaptive = json.load(f)
    except FileNotFoundError:
         vol_adaptive = {}
    
    try:
        with open(os.path.join(output_dir, 'phase1_profit_ladders.json'), 'r') as f:
            profit_ladders = json.load(f)
    except FileNotFoundError:
        profit_ladders = {}
    
    # Baseline (current submission)
    baseline = {
        'NIFTY50': {'sharpe': 0.006, 'trades': 133},
        'RELIANCE': {'sharpe': 1.683, 'trades': 128},
        'VBL': {'sharpe': 1.574, 'trades': 127},
        'YESBANK': {'sharpe': 1.036, 'trades': 132},
        'SUNPHARMA': {'sharpe': 3.132, 'trades': 134},
    }
    
    # Build comparison table
    comparison = []
    
    for symbol in ['NIFTY50', 'RELIANCE', 'VBL', 'YESBANK', 'SUNPHARMA']:
        row = {
            'Symbol': symbol,
            'Baseline_Sharpe': baseline[symbol]['sharpe'],
            'Baseline_Trades': baseline[symbol]['trades'],
        }
        
        # Add Phase 1 results
        if symbol == 'NIFTY50' and nifty_trend and 'sharpe' in nifty_trend:
            row['Phase1_Sharpe'] = nifty_trend['sharpe']
            row['Phase1_Trades'] = nifty_trend['trades']
            row['Improvement'] = nifty_trend['sharpe'] - baseline[symbol]['sharpe']
            row['Best_Technique'] = 'Trend+Ladder'
        
        elif symbol in ['YESBANK', 'RELIANCE'] and symbol in vol_adaptive and vol_adaptive[symbol]:
            row['Phase1_Sharpe'] = vol_adaptive[symbol]['sharpe']
            row['Phase1_Trades'] = vol_adaptive[symbol]['trades']
            row['Improvement'] = vol_adaptive[symbol]['sharpe'] - baseline[symbol]['sharpe']
            row['Best_Technique'] = 'Vol-Adaptive RSI'
        
        elif symbol in profit_ladders and profit_ladders[symbol]:
            # Compare profit ladder vs adaptive RSI for overlap symbols if needed, but current logic prefers ladder for overlapped symbols if run?
            # Recheck preference:
            # Code structure: if first matched, used.
            # Only YESBANK and RELIANCE are in vol_adaptive.
            # RELIANCE, VBL, YESBANK are in profit_ladders.
            # So rely on specific checks. 
            # Logic below: 
            # If symbol in vol_adaptive use that?
            # Let's verify which yielded better Sharpe if both available.
            
            p1_sharpe = profit_ladders[symbol]['sharpe']
            p1_trades = profit_ladders[symbol]['trades']
            method = 'Profit Ladder'
            
            # Check if vol_adaptive was better for YESBANK/RELIANCE
            if symbol in vol_adaptive and vol_adaptive[symbol]:
                vol_sharpe = vol_adaptive[symbol]['sharpe']
                if vol_sharpe > p1_sharpe:
                    p1_sharpe = vol_sharpe
                    p1_trades = vol_adaptive[symbol]['trades']
                    method = 'Vol-Adaptive RSI'
            
            row['Phase1_Sharpe'] = p1_sharpe
            row['Phase1_Trades'] = p1_trades
            row['Improvement'] = p1_sharpe - baseline[symbol]['sharpe']
            row['Best_Technique'] = method
        
        else:
            # Keep baseline (SUNPHARMA) or fallback
            row['Phase1_Sharpe'] = baseline[symbol]['sharpe']
            row['Phase1_Trades'] = baseline[symbol]['trades']
            row['Improvement'] = 0.0
            row['Best_Technique'] = 'Baseline (don\'t touch)'
        
        comparison.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(comparison)
    
    # Calculate portfolio metrics
    baseline_portfolio = sum([baseline[s]['sharpe'] for s in baseline]) / 5
    phase1_portfolio = df['Phase1_Sharpe'].mean()
    total_improvement = phase1_portfolio - baseline_portfolio
    
    print("\n" + "="*80)
    print("PHASE 1 RESULTS COMPARISON")
    print("="*80)
    print(df.to_string(index=False))
    
    print("\n" + "="*80)
    print("PORTFOLIO SUMMARY")
    print("="*80)
    print(f"Baseline Portfolio Sharpe:   {baseline_portfolio:.3f}")
    print(f"Phase 1 Portfolio Sharpe:    {phase1_portfolio:.3f}")
    print(f"Total Improvement:           +{total_improvement:.3f}")
    print(f"Total Trades:                {df['Phase1_Trades'].sum()}")
    
    if phase1_portfolio >= 1.70:
        print("\n✅ PHASE 1 SUCCESS: Target 1.70+ achieved!")
    else:
        print(f"\n⚠️ PHASE 1 PARTIAL: {phase1_portfolio:.3f} < 1.70 target")
    
    # Save final config
    final_config = {}
    for _, row in df.iterrows():
        symbol = row['Symbol']
        final_config[symbol] = {
            'sharpe': row['Phase1_Sharpe'],
            'trades': row['Phase1_Trades'],
            'technique': row['Best_Technique'],
            'improvement': row['Improvement']
        }
    
    with open(os.path.join(output_dir, 'phase1_final_config.json'), 'w') as f:
        json.dump({
            'portfolio_sharpe': phase1_portfolio,
            'baseline_sharpe': baseline_portfolio,
            'improvement': total_improvement,
            'symbol_configs': final_config
        }, f, indent=2)
    
    print(f"\n✅ Final Phase 1 config saved to: {os.path.join(output_dir, 'phase1_final_config.json')}")
    
    return final_config, phase1_portfolio

if __name__ == "__main__":
    final_config, portfolio_sharpe = compare_phase1_results()
