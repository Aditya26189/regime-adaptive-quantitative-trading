"""
TREND FOLLOWING STRATEGY - "PULSE ENGINE"
For trending instruments: NIFTY50, YESBANK

Strategy Logic:
- Entry: Fast EMA > Slow EMA (trend confirmed) AND price pulse (momentum surge)
- Exit: Price crosses below Fast EMA (trend reversal) OR max hold period

Rule 12 Compliant: Uses ONLY close prices
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class TrendConfig:
    """Configuration for trend-following strategy"""
    STUDENT_ROLL_NUMBER = "23ME3EP03"
    STRATEGY_SUBMISSION_NUMBER = 1
    
    # Transaction costs
    INITIAL_CAPITAL = 100000
    FEE_PER_ORDER = 24
    POSITION_SIZE = 0.95  # Use 95% of capital
    
    # Default parameters
    EMA_FAST = 8
    EMA_SLOW = 21
    VOL_LOOKBACK = 20
    PULSE_MULT = 0.4
    MAX_HOLD = 20
    ALLOWED_HOURS = [9, 10, 11, 12, 13]

class Indicators:
    """Indicator calculations (Rule 12 compliant)"""
    
    @staticmethod
    def ema(close: pd.Series, span: int) -> pd.Series:
        """Exponential Moving Average"""
        return close.ewm(span=span, adjust=False).mean()
    
    @staticmethod
    def volatility(close: pd.Series, period: int = 20) -> pd.Series:
        """Close-to-close volatility (absolute price changes)"""
        price_change = close.diff()
        return price_change.abs().rolling(window=period).mean()

def calculate_trend_signals(df: pd.DataFrame, params: Dict) -> pd.Series:
    """
    Generate trend-following signals
    
    Args:
        df: DataFrame with 'close' column
        params: Dictionary with strategy parameters
    
    Returns:
        Series with signals: 1=entry, -1=exit, 0=hold
    """
    close = df['close']
    
    # Parameters
    ema_fast_span = params.get('ema_fast', TrendConfig.EMA_FAST)
    ema_slow_span = params.get('ema_slow', TrendConfig.EMA_SLOW)
    vol_lookback = params.get('vol_lookback', TrendConfig.VOL_LOOKBACK)
    pulse_mult = params.get('pulse_mult', TrendConfig.PULSE_MULT)
    
    # Calculate indicators
    ema_fast = Indicators.ema(close, ema_fast_span)
    ema_slow = Indicators.ema(close, ema_slow_span)
    
    # Volatility-based pulse detection
    price_change = close.diff()
    volatility = Indicators.volatility(close, vol_lookback)
    
    # Signal conditions
    trend_up = ema_fast > ema_slow
    
    # Pulse: Price moves faster than normal volatility
    pulse_up = price_change > (pulse_mult * volatility)
    
    # Generate signals
    signals = pd.Series(0, index=df.index)
    
    # Entry: Trend confirmed + Momentum pulse
    entry_long = trend_up & pulse_up
    
    # Exit: Close crosses below fast EMA
    exit_long = close < ema_fast
    
    signals[entry_long] = 1
    signals[exit_long] = -1
    
    return signals

def backtest_trend_strategy(df: pd.DataFrame, params: Dict, config: TrendConfig = None) -> Tuple[List[Dict], Dict]:
    """
    Backtest trend-following strategy with state machine
    """
    if config is None:
        config = TrendConfig()
    
    # Add datetime column if not present
    if 'datetime' not in df.columns and df.index.name == 'datetime':
        df = df.reset_index()
    
    # Calculate signals
    raw_signals = calculate_trend_signals(df, params)
    
    # Add EMA for exit logic
    ema_fast = Indicators.ema(df['close'], params.get('ema_fast', config.EMA_FAST))
    
    # Initialize backtest state
    trades = []
    capital = config.INITIAL_CAPITAL
    
    in_position = False
    entry_price = 0
    entry_time = None
    entry_capital = 0
    entry_qty = 0
    bars_held = 0
    
    max_hold = params.get('max_hold', config.MAX_HOLD)
    allowed_hours = params.get('allowed_hours', config.ALLOWED_HOURS)
    
    # Trading loop
    for i in range(50, len(df)):
        current_time = df['datetime'].iloc[i]
        current_hour = current_time.hour
        current_minute = current_time.minute
        current_close = df['close'].iloc[i]
        
        signal = raw_signals.iloc[i]
        
        # === ENTRY LOGIC ===
        if not in_position and signal == 1:
            # Time filter
            if current_hour not in allowed_hours:
                continue
            if current_hour >= 14 and current_minute >= 30:
                continue
            
            # Enter position
            qty = int((capital - config.FEE_PER_ORDER) * config.POSITION_SIZE / current_close)
            
            if qty > 0:
                entry_price = current_close
                entry_time = current_time
                entry_capital = capital
                entry_qty = qty
                capital -= config.FEE_PER_ORDER
                in_position = True
                bars_held = 0
        
        # === EXIT LOGIC ===
        elif in_position:
            bars_held += 1
            
            # Exit conditions
            trend_exit = current_close < ema_fast.iloc[i-1]
            time_exit = bars_held >= max_hold
            eod_exit = current_hour >= 15 and current_minute >= 15
            
            if trend_exit or time_exit or eod_exit:
                exit_price = current_close
                exit_time = current_time
                
                # Calculate P&L
                gross_pnl = entry_qty * (exit_price - entry_price)
                capital = entry_capital + gross_pnl - (2 * config.FEE_PER_ORDER)
                
                # Record trade
                trades.append({
                    'student_roll_number': config.STUDENT_ROLL_NUMBER,
                    'strategy_submission_number': config.STRATEGY_SUBMISSION_NUMBER,
                    'symbol': params['symbol'],
                    'timeframe': params.get('timeframe', '60'),
                    'entry_trade_time': entry_time,
                    'exit_trade_time': exit_time,
                    'entry_trade_price': entry_price,
                    'exit_trade_price': exit_price,
                    'qty': entry_qty,
                    'fees': 2 * config.FEE_PER_ORDER,
                    'cumulative_capital_after_trade': capital
                })
                
                # Reset state
                in_position = False
                bars_held = 0
    
    # Calculate metrics
    if len(trades) == 0:
        metrics = {
            'trades': 0,
            'return': 0,
            'win_rate': 0,
            'sharpe': 0,
            'final_capital': capital
        }
    else:
        trades_df = pd.DataFrame(trades)
        pnl = (trades_df['exit_trade_price'] - trades_df['entry_trade_price']) * trades_df['qty'] - trades_df['fees']
        
        winning_trades = (pnl > 0).sum()
        total_return = (capital - config.INITIAL_CAPITAL) / config.INITIAL_CAPITAL * 100
        win_rate = (winning_trades / len(trades_df)) * 100
        
        returns_pct = ((trades_df['exit_trade_price'] - trades_df['entry_trade_price']) / trades_df['entry_trade_price'] * 100)
        sharpe = (returns_pct.mean() / returns_pct.std()) * np.sqrt(len(returns_pct)) if returns_pct.std() > 0 else 0
        
        metrics = {
            'trades': len(trades_df),
            'return': total_return,
            'win_rate': win_rate,
            'sharpe': sharpe,
            'final_capital': capital
        }
    
    return trades, metrics

def run_trend_strategy(symbol: str, params: Dict = None) -> Tuple[List[Dict], Dict]:
    """
    High-level function to run trend strategy on a symbol
    """
    # Symbol-specific file paths
    symbol_files = {
        'NIFTY50': {
            'file': 'data/raw/NSE_NIFTY50_INDEX_1hour.csv',
            'symbol_code': 'NSE:NIFTY50-INDEX'
        },
        'YESBANK': {
            'file': 'data/raw/NSE_YESBANK_EQ_1hour.csv',
            'symbol_code': 'NSE:YESBANK-EQ'
        }
    }
    
    if symbol not in symbol_files:
        raise ValueError(f"Symbol {symbol} not configured for trend strategy")
    
    # Load data
    df = pd.read_csv(symbol_files[symbol]['file'])
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    # Default parameters per symbol
    default_params = {
        'NIFTY50': {
            'symbol': symbol_files[symbol]['symbol_code'],
            'timeframe': '60',
            'ema_fast': 8,
            'ema_slow': 21,
            'pulse_mult': 0.3,  # More sensitive
            'max_hold': 20,
            'allowed_hours': [9, 10, 11, 12, 13]
        },
        'YESBANK': {
            'symbol': symbol_files[symbol]['symbol_code'],
            'timeframe': '60',
            'ema_fast': 5,
            'ema_slow': 15,
            'pulse_mult': 0.4,
            'max_hold': 15,
            'allowed_hours': [9, 10, 11, 12, 13]
        }
    }
    
    # Merge with user params
    final_params = default_params[symbol].copy()
    if params:
        final_params.update(params)
    
    # Run backtest
    config = TrendConfig()
    trades, metrics = backtest_trend_strategy(df, final_params, config)
    
    return trades, metrics

# ============================================================================
# TESTING INTERFACE
# ============================================================================

def main():
    """Test the trend strategy on NIFTY50 and YESBANK"""
    print("="*70)
    print("TREND FOLLOWING STRATEGY - TESTING")
    print("="*70)
    
    for symbol in ['NIFTY50', 'YESBANK']:
        print(f"\n{'='*70}")
        print(f"Testing {symbol}")
        print(f"{'='*70}")
        
        trades, metrics = run_trend_strategy(symbol)
        
        print(f"\nResults:")
        print(f"  Trades: {metrics['trades']}")
        print(f"  Return: {metrics['return']:.2f}%")
        print(f"  Win Rate: {metrics['win_rate']:.1f}%")
        print(f"  Sharpe: {metrics['sharpe']:.2f}")
        print(f"  Final Capital: ₹{metrics['final_capital']:,.2f}")
        
        # Compliance check
        if metrics['trades'] >= 120:
            print(f"  ✅ Trade count: {metrics['trades']} (>= 120)")
        else:
            print(f"  ❌ Trade count: {metrics['trades']} (< 120) - FAIL")
        
        if metrics['return'] > 0:
            print(f"  ✅ Return: {metrics['return']:.2f}% (positive)")
        else:
            print(f"  ⚠️  Return: {metrics['return']:.2f}% (negative)")

if __name__ == "__main__":
    main()
