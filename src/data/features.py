"""
Feature engineering module for market data.

This module provides functions to compute derived features from raw
market data including returns, volatility, spread, order book imbalance,
and microprice.
"""

from typing import List, Optional
import pandas as pd
import numpy as np


class FeatureEngine:
    """
    Feature engineering for market data.
    
    Computes derived features with careful attention to avoiding
    lookahead bias (all features use only past data at each point).
    
    Example:
        >>> engine = FeatureEngine()
        >>> df = engine.add_all(df)
        >>> print(df.columns)
    """
    
    def __init__(self, verbose: bool = True):
        """
        Initialize the feature engine.
        
        Args:
            verbose: If True, print progress messages
        """
        self.verbose = verbose
    
    def _log(self, message: str) -> None:
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(message)
    
    def add_returns(
        self,
        df: pd.DataFrame,
        periods: List[int] = [1],
        price_col: str = 'mid'
    ) -> pd.DataFrame:
        """
        Add return columns for specified periods.
        
        Uses log returns: log(price_t / price_{t-period})
        
        Args:
            df: DataFrame with price data
            periods: List of periods to compute returns for
            price_col: Column to use for price (default: 'mid')
            
        Returns:
            DataFrame with return columns added
        """
        df = df.copy()
        
        # Ensure price column exists
        if price_col not in df.columns:
            if 'close' in df.columns:
                price_col = 'close'
            elif 'price' in df.columns:
                price_col = 'price'
            elif 'bid' in df.columns and 'ask' in df.columns:
                df['mid'] = (df['bid'] + df['ask']) / 2
                price_col = 'mid'
            else:
                raise ValueError("No valid price column found")
        
        for period in periods:
            col_name = f'returns_{period}' if period > 1 else 'returns'
            df[col_name] = np.log(df[price_col] / df[price_col].shift(period))
        
        self._log(f"  ✓ Added returns for periods: {periods}")
        return df
    
    def add_volatility(
        self,
        df: pd.DataFrame,
        window: int = 20,
        returns_col: str = 'returns'
    ) -> pd.DataFrame:
        """
        Add rolling volatility column.
        
        Volatility is the rolling standard deviation of returns.
        
        Args:
            df: DataFrame with returns data
            window: Rolling window size
            returns_col: Column containing returns
            
        Returns:
            DataFrame with 'volatility' column added
        """
        df = df.copy()
        
        # Ensure returns column exists
        if returns_col not in df.columns:
            df = self.add_returns(df, periods=[1])
        
        df['volatility'] = df[returns_col].rolling(window=window).std()
        
        self._log(f"  ✓ Added volatility (window={window})")
        return df
    
    def add_spread(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add spread column (ask - bid).
        
        Args:
            df: DataFrame with bid/ask data
            
        Returns:
            DataFrame with 'spread' column added
        """
        df = df.copy()
        
        if 'bid' not in df.columns or 'ask' not in df.columns:
            self._log("  ⚠ Cannot add spread: bid/ask columns missing")
            return df
        
        df['spread'] = df['ask'] - df['bid']
        
        # Also add relative spread (as percentage of mid)
        if 'mid' in df.columns:
            df['spread_pct'] = df['spread'] / df['mid']
        elif 'bid' in df.columns and 'ask' in df.columns:
            df['spread_pct'] = df['spread'] / ((df['bid'] + df['ask']) / 2)
        
        self._log("  ✓ Added spread and spread_pct")
        return df
    
    def add_obi(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add Order Book Imbalance (OBI) column.
        
        OBI = (bid_qty - ask_qty) / (bid_qty + ask_qty)
        
        Range: -1 (all ask) to +1 (all bid)
        Positive values indicate buying pressure.
        
        Args:
            df: DataFrame with bid_qty/ask_qty data
            
        Returns:
            DataFrame with 'obi' column added
        """
        df = df.copy()
        
        if 'bid_qty' not in df.columns or 'ask_qty' not in df.columns:
            self._log("  ⚠ Cannot add OBI: bid_qty/ask_qty columns missing")
            return df
        
        total_qty = df['bid_qty'] + df['ask_qty']
        
        # Avoid division by zero
        df['obi'] = np.where(
            total_qty > 0,
            (df['bid_qty'] - df['ask_qty']) / total_qty,
            0.0
        )
        
        self._log("  ✓ Added OBI (order book imbalance)")
        return df
    
    def add_microprice(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add microprice column.
        
        Microprice is a quantity-weighted mid price that better reflects
        the true price when order book is imbalanced.
        
        microprice = (bid * ask_qty + ask * bid_qty) / (bid_qty + ask_qty)
        
        When ask_qty > bid_qty (selling pressure), microprice pulls toward bid.
        When bid_qty > ask_qty (buying pressure), microprice pulls toward ask.
        
        Args:
            df: DataFrame with bid/ask and quantity data
            
        Returns:
            DataFrame with 'microprice' column added
        """
        df = df.copy()
        
        required_cols = ['bid', 'ask', 'bid_qty', 'ask_qty']
        if not all(col in df.columns for col in required_cols):
            self._log("  ⚠ Cannot add microprice: required columns missing")
            return df
        
        total_qty = df['bid_qty'] + df['ask_qty']
        
        # Avoid division by zero
        df['microprice'] = np.where(
            total_qty > 0,
            (df['bid'] * df['ask_qty'] + df['ask'] * df['bid_qty']) / total_qty,
            (df['bid'] + df['ask']) / 2  # Fall back to mid
        )
        
        # Also add microprice deviation from mid
        if 'mid' not in df.columns:
            df['mid'] = (df['bid'] + df['ask']) / 2
        
        df['microprice_deviation'] = df['microprice'] - df['mid']
        
        self._log("  ✓ Added microprice and microprice_deviation")
        return df
    
    def add_rolling_mean(
        self,
        df: pd.DataFrame,
        window: int = 20,
        price_col: str = 'mid'
    ) -> pd.DataFrame:
        """
        Add rolling mean (moving average) column.
        
        Args:
            df: DataFrame with price data
            window: Window size for rolling mean
            price_col: Column to compute mean for
            
        Returns:
            DataFrame with rolling mean column added
        """
        df = df.copy()
        
        if price_col not in df.columns:
            self._log(f"  ⚠ Cannot add rolling mean: {price_col} column missing")
            return df
        
        col_name = f'ma_{window}'
        df[col_name] = df[price_col].rolling(window=window).mean()
        
        self._log(f"  ✓ Added {col_name}")
        return df
    
    def add_z_score(
        self,
        df: pd.DataFrame,
        window: int = 20,
        price_col: str = 'mid'
    ) -> pd.DataFrame:
        """
        Add z-score column for mean reversion signals.
        
        z = (price - rolling_mean) / rolling_std
        
        Args:
            df: DataFrame with price data
            window: Window size for rolling calculations
            price_col: Column to compute z-score for
            
        Returns:
            DataFrame with 'z_score' column added
        """
        df = df.copy()
        
        if price_col not in df.columns:
            self._log(f"  ⚠ Cannot add z-score: {price_col} column missing")
            return df
        
        rolling_mean = df[price_col].rolling(window=window).mean()
        rolling_std = df[price_col].rolling(window=window).std()
        
        # Avoid division by zero
        df['z_score'] = np.where(
            rolling_std > 0,
            (df[price_col] - rolling_mean) / rolling_std,
            0.0
        )
        
        self._log(f"  ✓ Added z_score (window={window})")
        return df
    
    def add_momentum(
        self,
        df: pd.DataFrame,
        fast_window: int = 5,
        slow_window: int = 20,
        price_col: str = 'mid'
    ) -> pd.DataFrame:
        """
        Add momentum indicators (fast and slow moving averages).
        
        Args:
            df: DataFrame with price data
            fast_window: Window for fast MA
            slow_window: Window for slow MA
            price_col: Price column to use
            
        Returns:
            DataFrame with momentum indicators added
        """
        df = df.copy()
        
        if price_col not in df.columns:
            self._log(f"  ⚠ Cannot add momentum: {price_col} column missing")
            return df
        
        df['ma_fast'] = df[price_col].rolling(window=fast_window).mean()
        df['ma_slow'] = df[price_col].rolling(window=slow_window).mean()
        df['ma_diff'] = df['ma_fast'] - df['ma_slow']
        
        self._log(f"  ✓ Added momentum (fast={fast_window}, slow={slow_window})")
        return df
    
    def add_all(
        self,
        df: pd.DataFrame,
        window: int = 20,
        include_orderbook: bool = True
    ) -> pd.DataFrame:
        """
        Add all available features to the DataFrame.
        
        Args:
            df: Input DataFrame
            window: Window size for rolling calculations
            include_orderbook: If True, add order book features (OBI, microprice)
            
        Returns:
            DataFrame with all features added
        """
        self._log("Adding features...")
        
        # Ensure mid price exists
        if 'mid' not in df.columns:
            if 'bid' in df.columns and 'ask' in df.columns:
                df = df.copy()
                df['mid'] = (df['bid'] + df['ask']) / 2
                self._log("  ✓ Added mid price")
            elif 'close' in df.columns:
                df = df.copy()
                df['mid'] = df['close']
            elif 'price' in df.columns:
                df = df.copy()
                df['mid'] = df['price']
        
        # Add core features
        df = self.add_returns(df, periods=[1, 5])
        df = self.add_volatility(df, window=window)
        df = self.add_z_score(df, window=window)
        df = self.add_momentum(df, fast_window=5, slow_window=window)
        
        # Add spread if bid/ask available
        if 'bid' in df.columns and 'ask' in df.columns:
            df = self.add_spread(df)
        
        # Add order book features if available
        if include_orderbook and 'bid_qty' in df.columns and 'ask_qty' in df.columns:
            df = self.add_obi(df)
            df = self.add_microprice(df)
        
        # Count features added
        feature_cols = [c for c in df.columns if c not in ['timestamp', 'bid', 'ask', 'bid_qty', 'ask_qty', 'open', 'high', 'low', 'close', 'volume']]
        self._log(f"  ✓ Total features: {len(feature_cols)}")
        
        return df
    
    def fill_missing(
        self,
        df: pd.DataFrame,
        method: str = 'ffill'
    ) -> pd.DataFrame:
        """
        Fill missing values created by feature engineering.
        
        Args:
            df: DataFrame to fill
            method: Fill method ('ffill', 'bfill', 'drop')
            
        Returns:
            DataFrame with missing values handled
        """
        df = df.copy()
        
        initial_nulls = df.isnull().sum().sum()
        
        if method == 'ffill':
            df = df.ffill()
        elif method == 'bfill':
            df = df.bfill()
        elif method == 'drop':
            df = df.dropna()
        
        final_nulls = df.isnull().sum().sum()
        self._log(f"  ✓ Filled {initial_nulls - final_nulls} missing values")
        
        return df
