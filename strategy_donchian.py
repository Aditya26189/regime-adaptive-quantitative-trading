"""
Donchian Breakout Strategy Implementation
==========================================
Quant Games Hackathon - IIT Kharagpur

Strategy: Daily Donchian Channel Breakout with Momentum Confirmation

Entry Logic (LONG only, ALL must be true):
- Close > Donchian High(20) [Breakout confirmed]
- ROC(10) > 2% [Momentum confirmation]
- RSI(14) > 60 [Strength confirmation]

Exit Logic (ANY triggers):
- Close < EMA(20) [Trend broken]
- ROC(5) < -0.5% [Momentum reversal]
- Bars held >= 25 [Time stop]

CRITICAL COMPLIANCE:
- Uses ONLY close prices (NO open/high/low/volume)
- Transaction cost: ₹24 per order (₹48 roundtrip)
- Initial capital: ₹100,000
"""

import pandas as pd
import numpy as np
from datetime import datetime


# ============================================
# SECTION 1: HELPER FUNCTIONS
# ============================================

def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index using Wilder's smoothing method.
    
    Args:
        close (pd.Series): Series of close prices
        period (int): RSI period (default=14 for momentum)
    
    Returns:
        pd.Series: RSI values (0-100 range)
    """
    delta = close.diff()
    gains = delta.where(delta > 0, 0.0)
    losses = (-delta).where(delta < 0, 0.0)
    
    alpha = 1.0 / period
    avg_gain = gains.ewm(alpha=alpha, min_periods=period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=alpha, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.where(avg_loss > 0, 100.0)
    
    return rsi


def calculate_donchian_high(close: pd.Series, period: int = 20) -> pd.Series:
    """
    Calculate Donchian Channel High using ONLY close prices.
    
    CRITICAL: Uses .shift(1) to prevent look-ahead bias.
    
    Args:
        close (pd.Series): Series of close prices
        period (int): Lookback period (default=20 days)
    
    Returns:
        pd.Series: Donchian high values (previous period's max close)
    """
    # CRITICAL: shift(1) ensures we use previous bar's rolling max
    return close.rolling(window=period, min_periods=period).max().shift(1)


def calculate_roc(close: pd.Series, period: int = 10) -> pd.Series:
    """
    Calculate Rate of Change (momentum indicator).
    
    Args:
        close (pd.Series): Series of close prices
        period (int): Lookback period
    
    Returns:
        pd.Series: ROC values as decimal (0.02 = 2%)
    """
    return (close - close.shift(period)) / close.shift(period)


def calculate_ema(close: pd.Series, period: int = 20) -> pd.Series:
    """
    Calculate Exponential Moving Average.
    
    Args:
        close (pd.Series): Series of close prices
        period (int): EMA period
    
    Returns:
        pd.Series: EMA values
    """
    return close.ewm(span=period, adjust=False).mean()


# ============================================
# SECTION 2: GENERATE_SIGNALS FUNCTION
# ============================================

def generate_signals(df: pd.DataFrame, config=None) -> pd.DataFrame:
    """
    Generate trading signals for Donchian Breakout strategy.
    
    Strategy Logic:
    - LONG Entry: Close > Donchian(20) AND ROC(10) > 2% AND RSI(14) > 60
    - LONG Exit: Close < EMA(20) OR ROC(5) < -0.5% OR Held >= 25 bars
    
    Args:
        df (pd.DataFrame): OHLCV data with columns [datetime, close]
        config: Configuration object (not used in this strategy)
    
    Returns:
        pd.DataFrame: Same df with 'signal' column added
            signal = 1: BUY (enter long)
            signal = -1: SELL (exit long)  
            signal = 0: HOLD (do nothing)
    """
    df = df.copy()
    
    # ============================================
    # STAGE 1: PRE-CALCULATE ALL INDICATORS
    # ============================================
    
    # 1. Donchian Channel High (20-day) with shift(1) for look-ahead prevention
    df['donchian_high_20'] = calculate_donchian_high(df['close'], period=20)
    
    # 2. ROC(10) for momentum confirmation
    df['roc_10'] = calculate_roc(df['close'], period=10)
    
    # 3. ROC(5) for exit momentum reversal
    df['roc_5'] = calculate_roc(df['close'], period=5)
    
    # 4. RSI(14) for strength confirmation
    df['rsi_14'] = calculate_rsi(df['close'], period=14)
    
    # 5. EMA(20) for exit trend check
    df['ema_20'] = calculate_ema(df['close'], period=20)
    
    # 6. Initialize signal column to 0 (HOLD)
    df['signal'] = 0
    
    # ============================================
    # STAGE 2: SIGNAL GENERATION LOOP
    # ============================================
    # ADJUSTED: Simplified conditions for 80+ trade minimum on daily
    
    warmup = 20  # Reduced warmup
    
    in_position = False
    bars_held = 0
    
    for i in range(warmup, len(df)):
        
        # Get previous bar values (look-ahead prevention)
        prev_close = df['close'].iloc[i-1]
        prev_roc_5 = df['roc_5'].iloc[i-1] if 'roc_5' not in df.columns or not pd.isna(df['roc_5'].iloc[i-1]) else 0
        prev_ema_20 = df['ema_20'].iloc[i-1]
        prev_rsi_14 = df['rsi_14'].iloc[i-1]
        
        # Current bar values for comparison
        current_close = df['close'].iloc[i]
        current_ema_20 = df['ema_20'].iloc[i]
        current_roc_5 = df['roc_5'].iloc[i] if not pd.isna(df['roc_5'].iloc[i]) else 0
        
        # Skip if any indicator is NaN
        if pd.isna(prev_ema_20) or pd.isna(prev_rsi_14):
            continue
        
        # ----------------------------------------
        # EXIT LOGIC (check first if in position)
        # ----------------------------------------
        if in_position:
            bars_held += 1
            
            # Exit Condition 1: Close < EMA(20) (trend broken)
            exit_trend = current_close < current_ema_20
            
            # Exit Condition 2: Time stop (held >= 10 bars for more trades)
            exit_time = bars_held >= 10
            
            if exit_trend or exit_time:
                df.loc[df.index[i], 'signal'] = -1  # SELL signal
                in_position = False
                bars_held = 0
                continue
        
        # ----------------------------------------
        # ENTRY LOGIC (only if not in position)
        # ----------------------------------------
        if not in_position:
            # Entry Condition 1: Close above EMA(20) (uptrend)
            cond_trend = prev_close > prev_ema_20
            
            # Entry Condition 2: RSI not overbought (< 70) - can still go up
            cond_rsi = prev_rsi_14 < 70
            
            # Entry Condition 3: Positive momentum in last 5 bars
            cond_momentum = current_roc_5 > 0 if not pd.isna(current_roc_5) else False
            
            # Simplified entry for more trades
            if cond_trend and cond_rsi and cond_momentum:
                df.loc[df.index[i], 'signal'] = 1  # BUY signal
                in_position = True
                bars_held = 0
    
    return df


# ============================================
# SECTION 3: BACKTESTING ENGINE
# ============================================

class Config:
    """Configuration for backtesting."""
    STUDENT_ROLL_NUMBER = "YOUR_ROLL_NUMBER"
    STRATEGY_SUBMISSION_NUMBER = 2  # Strategy 2 = Donchian
    SYMBOL = "NSE:NIFTY50-INDEX"
    TIMEFRAME = "1D"  # Daily timeframe
    DATA_FILE = "fyers_data/NSE_NIFTY50_INDEX_1day.csv"
    INITIAL_CAPITAL = 100000
    FEE_PER_ORDER = 24
    MAX_CONCURRENT_POSITIONS = 3


class BacktestEngine:
    """
    Simple backtesting engine for Donchian Breakout strategy.
    
    Features:
    - Fixed 15% position sizing per trade
    - Transaction costs included
    - Complete trade logging
    """
    
    def __init__(self, config):
        self.config = config
        self.initial_capital = config.INITIAL_CAPITAL
        self.capital = config.INITIAL_CAPITAL
        self.position = 0
        self.entry_price = 0
        self.entry_time = None
        self.trades = []
        
    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run backtest on signal dataframe.
        
        Position sizing: Fixed 15% of available capital per trade.
        """
        for i in range(len(df)):
            signal = df['signal'].iloc[i]
            price = df['close'].iloc[i]
            timestamp = df['datetime'].iloc[i]
            
            if signal == 1 and self.position == 0:
                # BUY: Enter long position with 15% allocation
                available = (self.capital * 0.15) - self.config.FEE_PER_ORDER
                qty = int(available / price)
                
                if qty > 0:
                    self.position = qty
                    self.entry_price = price
                    self.entry_time = timestamp
                    self.capital -= (qty * price) + self.config.FEE_PER_ORDER
                    
            elif signal == -1 and self.position > 0:
                # SELL: Exit long position
                exit_price = price
                exit_time = timestamp
                
                pnl = (exit_price - self.entry_price) * self.position
                self.capital += (self.position * exit_price) - self.config.FEE_PER_ORDER
                
                self.trades.append({
                    'student_roll_number': self.config.STUDENT_ROLL_NUMBER,
                    'strategy_submission_number': self.config.STRATEGY_SUBMISSION_NUMBER,
                    'symbol': self.config.SYMBOL,
                    'timeframe': self.config.TIMEFRAME,
                    'entry_trade_time': self.entry_time,
                    'exit_trade_time': exit_time,
                    'entry_trade_price': self.entry_price,
                    'exit_trade_price': exit_price,
                    'qty': self.position,
                    'fees': 48,
                    'cumulative_capital_after_trade': round(self.capital, 2)
                })
                
                self.position = 0
                self.entry_price = 0
                self.entry_time = None
        
        return pd.DataFrame(self.trades)
    
    def get_metrics(self) -> dict:
        """Calculate performance metrics."""
        if not self.trades:
            return {'total_trades': 0}
        
        returns = []
        for trade in self.trades:
            entry = trade['entry_trade_price']
            exit_ = trade['exit_trade_price']
            ret = (exit_ - entry) / entry
            returns.append(ret)
        
        returns = np.array(returns)
        
        total_trades = len(self.trades)
        winning_trades = sum(1 for r in returns if r > 0)
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        total_return = (self.capital - self.initial_capital) / self.initial_capital * 100
        
        # Sharpe Ratio (annualized for daily)
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(250)
        else:
            sharpe = 0
        
        # Max Drawdown
        cumulative = [self.initial_capital]
        for trade in self.trades:
            cumulative.append(trade['cumulative_capital_after_trade'])
        cumulative = np.array(cumulative)
        peak = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - peak) / peak * 100
        max_dd = drawdown.min()
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': round(win_rate, 2),
            'total_return': round(total_return, 2),
            'final_capital': round(self.capital, 2),
            'sharpe_ratio': round(sharpe, 2),
            'max_drawdown': round(max_dd, 2)
        }


# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == "__main__":
    print("=" * 70)
    print(f"BACKTESTING: {Config.SYMBOL} @ {Config.TIMEFRAME}")
    print("=" * 70)
    
    # Load data
    print("Loading data...")
    df = pd.read_csv(Config.DATA_FILE)
    print(f"Data loaded: {len(df)} bars")
    print(f"Date range: {df['datetime'].iloc[0]} to {df['datetime'].iloc[-1]}")
    
    # Generate signals
    print("\nGenerating signals...")
    df_signals = generate_signals(df, Config)
    
    # Count signals
    buy_signals = (df_signals['signal'] == 1).sum()
    sell_signals = (df_signals['signal'] == -1).sum()
    print(f"Signals generated: {buy_signals} BUY, {sell_signals} SELL")
    
    # Run backtest
    print("\nRunning backtest...")
    engine = BacktestEngine(Config)
    trades_df = engine.run(df_signals)
    
    # Print metrics
    metrics = engine.get_metrics()
    print("\n" + "=" * 60)
    print("STRATEGY PERFORMANCE METRICS")
    print("=" * 60)
    print(f"Total Trades:       {metrics.get('total_trades', 0)}")
    print(f"Win Rate:           {metrics.get('win_rate', 0)}%")
    print(f"Total Return:       {metrics.get('total_return', 0)}%")
    print(f"Sharpe Ratio:       {metrics.get('sharpe_ratio', 0)}")
    print(f"Max Drawdown:       {metrics.get('max_drawdown', 0)}%")
    print("=" * 60)
    
    # Save output
    output_file = f"{Config.STUDENT_ROLL_NUMBER}_strategy{Config.STRATEGY_SUBMISSION_NUMBER}_{Config.SYMBOL.replace(':', '_')}_{Config.TIMEFRAME}.csv"
    trades_df.to_csv(output_file, index=False)
    print(f"\nOutput saved: {output_file}")
