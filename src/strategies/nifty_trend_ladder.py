import pandas as pd
import numpy as np
import json
import os

class NIFTYTrendLadderStrategy:
    """
    Trend-following strategy optimized for NIFTY50 index
    Based on academic evidence: 1-hour intraday exhibits momentum persistence
    """
    
    def __init__(self, params):
        self.params = params
        
    def generate_signals(self, df):
        """Generate trend-following signals with momentum confirmation"""
        df = df.copy()
        
        # EMA calculation
        ema_fast_period = self.params.get('ema_fast', 8)
        ema_slow_period = self.params.get('ema_slow', 21)
        
        df['ema_fast'] = df['close'].ewm(span=ema_fast_period, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=ema_slow_period, adjust=False).mean()
        
        # Volatility filter
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(14).std() * 100
        vol_min = self.params.get('vol_min_pct', 0.005)
        
        # Momentum confirmation (price above EMA_fast by threshold)
        momentum_threshold = self.params.get('momentum_threshold', 0.003)  # 0.3%
        df['momentum_confirm'] = (df['close'] > df['ema_fast'] * (1 + momentum_threshold))
        
        # Trend signal
        df['trend_up'] = (
            (df['ema_fast'] > df['ema_slow']) &
            df['momentum_confirm'] &
            (df['volatility'] > vol_min)
        )
        
        # Time filter (avoid noise hours)
        df['hour'] = pd.to_datetime(df['datetime']).dt.hour
        allowed_hours = self.params.get('allowed_hours', [10, 11, 12, 13, 14])
        df['time_filter'] = df['hour'].isin(allowed_hours)
        
        # Final signal
        df['signal_long'] = df['trend_up'] & df['time_filter']
        
        return df
    
    def backtest_with_ladder_exits(self, df, initial_capital=100000):
        """
        Backtest with 3-tier profit-taking ladder:
        - Exit 50% at RSI > 60 or +1.0% gain
        - Exit 25% at RSI > 70 or +1.8% gain
        - Exit 25% at RSI > 80 or max_hold or stop_loss
        """
        df = self.generate_signals(df)
        
        # Calculate RSI for exit signals
        df['RSI'] = self.calculate_rsi(df['close'], period=2)
        
        trades = []
        capital = initial_capital
        in_position = False
        
        # Position tracking
        entry_price = 0
        entry_time = None
        entry_qty = 0
        remaining_qty = 0
        bars_held = 0
        
        # Ladder tracking
        ladder_exits = {
            'tier1': {'triggered': False, 'fraction': 0.50, 'rsi_threshold': 60, 'gain_threshold': 1.0},
            'tier2': {'triggered': False, 'fraction': 0.25, 'rsi_threshold': 70, 'gain_threshold': 1.8},
            'tier3': {'triggered': False, 'fraction': 0.25, 'rsi_threshold': 80, 'gain_threshold': 3.0},
        }
        
        fee_per_order = 24
        max_hold = self.params.get('max_hold_bars', 5)
        stop_loss_pct = self.params.get('stop_loss_pct', 2.0)
        
        partial_exits = []
        
        for i in range(50, len(df)):
            current_time = df['datetime'].iloc[i]
            current_hour = pd.to_datetime(current_time).hour
            current_minute = pd.to_datetime(current_time).minute
            current_close = df['close'].iloc[i]
            current_rsi = df['RSI'].iloc[i]
            
            # ENTRY LOGIC
            if not in_position:
                if df['signal_long'].iloc[i]:
                    # Enter position
                    entry_qty = int((initial_capital - fee_per_order) * 0.95 / current_close)
                    
                    if entry_qty > 0:
                        entry_price = current_close
                        entry_time = current_time
                        remaining_qty = entry_qty
                        capital -= fee_per_order
                        in_position = True
                        bars_held = 0
                        
                        # Reset ladder
                        for tier in ladder_exits.values():
                            tier['triggered'] = False
                        
                        partial_exits = []
            
            # EXIT LOGIC (LADDER)
            else:
                bars_held += 1
                current_return_pct = ((current_close - entry_price) / entry_price) * 100
                
                # Check each tier
                for tier_name, tier in ladder_exits.items():
                    if not tier['triggered']:
                        # Trigger condition: RSI OR gain threshold
                        if (current_rsi > tier['rsi_threshold']) or (current_return_pct >= tier['gain_threshold']):
                            # Exit this fraction
                            exit_qty = int(entry_qty * tier['fraction'])
                            if exit_qty > 0 and remaining_qty >= exit_qty:
                                gross_pnl = exit_qty * (current_close - entry_price)
                                net_pnl = gross_pnl - fee_per_order
                                capital += (exit_qty * current_close) - fee_per_order
                                remaining_qty -= exit_qty
                                
                                partial_exits.append({
                                    'tier': tier_name,
                                    'qty': exit_qty,
                                    'exit_price': current_close,
                                    'exit_time': current_time,
                                    'pnl': net_pnl,
                                    'return_pct': current_return_pct
                                })
                                
                                tier['triggered'] = True
                
                # Full exit conditions
                stop_loss_hit = current_return_pct <= -stop_loss_pct
                time_exit = bars_held >= max_hold
                eod_exit = (current_hour >= 15 and current_minute >= 15)
                trend_broken = current_close < df['ema_fast'].iloc[i]
                
                full_exit = stop_loss_hit or time_exit or eod_exit or trend_broken or remaining_qty == 0
                
                if full_exit and remaining_qty > 0:
                    # Exit remaining position
                    gross_pnl = remaining_qty * (current_close - entry_price)
                    net_pnl = gross_pnl - fee_per_order
                    capital += (remaining_qty * current_close) - fee_per_order
                    
                    partial_exits.append({
                        'tier': 'final',
                        'qty': remaining_qty,
                        'exit_price': current_close,
                        'exit_time': current_time,
                        'pnl': net_pnl,
                        'return_pct': current_return_pct
                    })
                    
                    remaining_qty = 0
                
                # Record trade if fully closed
                if remaining_qty == 0:
                    total_pnl = sum([e['pnl'] for e in partial_exits])
                    # Ensure exit_price is a scalar float, not a Series/Array
                    # Handle weighted average exit price
                    total_exit_value = sum([e['qty'] * e['exit_price'] for e in partial_exits])
                    avg_exit_price = total_exit_value / entry_qty if entry_qty > 0 else current_close
                    
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'entry_price': entry_price,
                        'exit_price': avg_exit_price,
                        'qty': entry_qty,
                        'pnl': total_pnl,
                        'capital': capital,
                        'bars_held': bars_held,
                        'return_pct': ((avg_exit_price - entry_price) / entry_price) * 100,
                        'ladder_exits': len(partial_exits),
                        'exit_reason': 'ladder' if len(partial_exits) > 1 else 'full'
                    })
                    
                    in_position = False
                    partial_exits = []
        
        metrics = self.calculate_metrics(trades, initial_capital, capital)
        return trades, metrics
    
    def calculate_rsi(self, close, period=2):
        """Calculate RSI indicator"""
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)
    
    def calculate_metrics(self, trades, initial_capital, final_capital):
        """Calculate performance metrics"""
        if len(trades) == 0:
            return {
                'total_trades': 0,
                'sharpe_ratio': 0,
                'total_return_pct': 0,
                'win_rate': 0,
                'max_drawdown_pct': 0,
                'final_capital': final_capital
            }
        
        trades_df = pd.DataFrame(trades)
        
        total_trades = len(trades_df)
        total_return_pct = (final_capital - initial_capital) / initial_capital * 100
        
        wins = (trades_df['pnl'] > 0).sum()
        win_rate = (wins / total_trades) * 100
        
        returns = (trades_df['pnl'] / initial_capital) * 100
        if returns.std() > 0:
            trades_per_year = 1500 / (len(trades_df) / 250) if len(trades_df) > 0 else 1
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(min(trades_per_year, 252))
        else:
            sharpe_ratio = 0
        
        # Drawdown
        capital_curve = trades_df['capital'].values
        running_max = np.maximum.accumulate(capital_curve)
        drawdown = (capital_curve - running_max) / running_max * 100
        max_drawdown_pct = drawdown.min()
        
        return {
            'total_trades': total_trades,
            'sharpe_ratio': sharpe_ratio,
            'total_return_pct': total_return_pct,
            'win_rate': win_rate,
            'max_drawdown_pct': max_drawdown_pct,
            'final_capital': final_capital,
            'avg_trade_pnl': trades_df['pnl'].mean(),
            'max_return': trades_df['return_pct'].max(),
            'min_return': trades_df['return_pct'].min(),
        }


# TESTING SCRIPT
def test_nifty_trend_ladder():
    """Test NIFTY50 trend-following with profit ladders"""
    
    # Load NIFTY50 data
    # Assuming run from root dir
    csv_path = 'data/raw/NSE_NIFTY50_INDEX_1hour.csv'
    if not os.path.exists(csv_path):
        # Retry with just data/ if raw not present (based on my check earlier, raw IS present)
        csv_path = 'data/NSE_NIFTY50_INDEX_1hour.csv'
        
    df = pd.read_csv(csv_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    # Parameter grid to test (RELAXED for Rescue)
    param_grid = [
        # Rescue Config 1: Very Low Vol Threshold
        {
            'ema_fast': 8,
            'ema_slow': 21,
            'momentum_threshold': 0.002,
            'vol_min_pct': 0.003, # Lowered from 0.005
            'max_hold_bars': 6,
            'stop_loss_pct': 2.0,
            'allowed_hours': [10, 11, 12, 13, 14, 15]
        },
        
        # Rescue Config 2: Scalper (Fast EMA, Low Thresholds)
        {
            'ema_fast': 5,
            'ema_slow': 13,
            'momentum_threshold': 0.001,
            'vol_min_pct': 0.003,
            'max_hold_bars': 4,
            'stop_loss_pct': 1.5,
            'allowed_hours': [10, 11, 12, 13, 14, 15]
        },
        
        # Rescue Config 3: Widenet (Standard EMA, Low Vol)
        {
            'ema_fast': 8,
            'ema_slow': 21,
            'momentum_threshold': 0.001,
            'vol_min_pct': 0.002,
            'max_hold_bars': 8,
            'stop_loss_pct': 2.5,
            'allowed_hours': [9, 10, 11, 12, 13, 14, 15]
        },
    ]
    
    results = []
    
    print("="*70)
    print("TESTING: NIFTY50 TREND-FOLLOWING + PROFIT LADDERS")
    print("="*70)
    
    for idx, params in enumerate(param_grid):
        print(f"\n[Test {idx+1}/{len(param_grid)}] Testing params: {params}")
        
        strategy = NIFTYTrendLadderStrategy(params)
        trades, metrics = strategy.backtest_with_ladder_exits(df)
        
        print(f"  Trades: {metrics['total_trades']}")
        print(f"  Sharpe: {metrics['sharpe_ratio']:.3f}")
        print(f"  Return: {metrics['total_return_pct']:.2f}%")
        print(f"  Win Rate: {metrics['win_rate']:.1f}%")
        print(f"  Max DD: {metrics['max_drawdown_pct']:.2f}%")
        
        results.append({
            'params': params,
            'metrics': metrics,
            'trades': trades # Note: trades not serializable directly if datetime obj, careful with json dump later
        })
    
    # Find best configuration
    valid_results = [r for r in results if r['metrics']['total_trades'] >= 120]
    
    os.makedirs('output', exist_ok=True)
    
    if valid_results:
        best = max(valid_results, key=lambda x: x['metrics']['sharpe_ratio'])
        
        print("\n" + "="*70)
        print("BEST CONFIGURATION (NIFTY50 TREND LADDER)")
        print("="*70)
        print(f"Sharpe: {best['metrics']['sharpe_ratio']:.3f}")
        print(f"Trades: {best['metrics']['total_trades']}")
        print(f"Return: {best['metrics']['total_return_pct']:.2f}%")
        print(f"Win Rate: {best['metrics']['win_rate']:.1f}%")
        print(f"Parameters: {best['params']}")
        
        # Save to file
        with open('output/phase1_nifty_trend.json', 'w') as f:
            json.dump({
                'sharpe': best['metrics']['sharpe_ratio'],
                'trades': best['metrics']['total_trades'],
                'return': best['metrics']['total_return_pct'],
                'params': best['params']
            }, f, indent=2)
            
        print("Saved to output/phase1_nifty_trend.json")
        return best
    else:
        print("\n❌ NO VALID CONFIGURATIONS (all <120 trades)")
        # Save empty/failed state
        with open('output/phase1_nifty_trend.json', 'w') as f:
            json.dump({}, f)
        return None

if __name__ == "__main__":
    test_nifty_trend_ladder()
