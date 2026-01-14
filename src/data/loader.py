"""
Data loading and validation module.

This module provides utilities for loading market data from various
CSV formats, validating data quality, and standardizing column names.
"""

from typing import Optional, Tuple, List
import pandas as pd
import numpy as np


class DataLoader:
    """
    Loader for market data with validation and schema detection.
    
    Supports multiple data formats:
    - OHLCV (Open, High, Low, Close, Volume)
    - OrderBook (bid, ask, bid_qty, ask_qty)
    - Tick (price, quantity)
    
    Example:
        >>> loader = DataLoader()
        >>> df = loader.load_csv('data/raw/market_data.csv')
        >>> print(f"Loaded {len(df)} rows")
    """
    
    # Standard column name mappings
    COLUMN_MAPPINGS = {
        # Timestamp variants
        'time': 'timestamp',
        'date': 'timestamp',
        'datetime': 'timestamp',
        'ts': 'timestamp',
        't': 'timestamp',
        
        # Price variants
        'bid_price': 'bid',
        'bidprice': 'bid',
        'best_bid': 'bid',
        'ask_price': 'ask',
        'askprice': 'ask',
        'best_ask': 'ask',
        'offer': 'ask',
        'offer_price': 'ask',
        
        # Quantity variants
        'bid_size': 'bid_qty',
        'bidsize': 'bid_qty',
        'bid_volume': 'bid_qty',
        'bidqty': 'bid_qty',
        'ask_size': 'ask_qty',
        'asksize': 'ask_qty',
        'ask_volume': 'ask_qty',
        'askqty': 'ask_qty',
        'offer_size': 'ask_qty',
        'offer_qty': 'ask_qty',
        
        # OHLCV variants
        'o': 'open',
        'h': 'high',
        'l': 'low',
        'c': 'close',
        'v': 'volume',
        'vol': 'volume',
        
        # Generic price
        'px': 'price',
        'last': 'price',
        'last_price': 'price',
        
        # Generic quantity
        'qty': 'quantity',
        'size': 'quantity',
        'amount': 'quantity'
    }
    
    def __init__(self, verbose: bool = True):
        """
        Initialize the data loader.
        
        Args:
            verbose: If True, print diagnostic messages
        """
        self.verbose = verbose
    
    def _log(self, message: str) -> None:
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(message)
    
    def load_csv(
        self,
        filepath: str,
        validate: bool = True,
        standardize: bool = True
    ) -> pd.DataFrame:
        """
        Load a CSV file with optional validation and standardization.
        
        Args:
            filepath: Path to the CSV file
            validate: If True, run validation checks
            standardize: If True, standardize column names
            
        Returns:
            DataFrame with loaded data
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If validation fails
        """
        self._log(f"Loading data from {filepath}...")
        
        # Try different engines for performance
        df = None
        try:
            # Try pyarrow first (fastest)
            df = pd.read_csv(filepath, engine='pyarrow')
            self._log("  ✓ Loaded with pyarrow engine")
        except (ImportError, Exception):
            try:
                # Fall back to python engine
                df = pd.read_csv(filepath)
                self._log("  ✓ Loaded with default engine")
            except Exception as e:
                raise ValueError(f"Failed to load CSV: {e}")
        
        self._log(f"  ✓ Loaded {len(df)} rows, {len(df.columns)} columns")
        
        # Standardize column names if requested
        if standardize:
            df = self.standardize_columns(df)
        
        # Validate if requested
        if validate:
            self.validate(df)
        
        return df
    
    def standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize column names to consistent format.
        
        Args:
            df: DataFrame to standardize
            
        Returns:
            DataFrame with standardized column names
        """
        df = df.copy()
        
        # Convert to lowercase
        df.columns = df.columns.str.lower().str.strip()
        
        # Apply mappings
        new_columns = {}
        for col in df.columns:
            if col in self.COLUMN_MAPPINGS:
                new_columns[col] = self.COLUMN_MAPPINGS[col]
        
        if new_columns:
            df = df.rename(columns=new_columns)
            self._log(f"  ✓ Renamed columns: {list(new_columns.keys())}")
        
        return df
    
    def validate(self, df: pd.DataFrame) -> bool:
        """
        Validate data quality.
        
        Checks:
        - Non-empty DataFrame
        - No negative prices
        - Monotonic timestamps (if present)
        - Data type validity
        
        Args:
            df: DataFrame to validate
            
        Returns:
            True if validation passes
            
        Raises:
            ValueError: If validation fails
        """
        self._log("Validating data...")
        
        # Check 1: Non-empty
        if len(df) == 0:
            raise ValueError("DataFrame is empty")
        self._log(f"  ✓ Shape: {df.shape}")
        
        # Check 2: Null values
        null_counts = df.isnull().sum()
        total_nulls = null_counts.sum()
        if total_nulls > 0:
            self._log(f"  ⚠ Warning: {total_nulls} null values found")
            for col, count in null_counts.items():
                if count > 0:
                    self._log(f"    - {col}: {count} nulls")
        else:
            self._log("  ✓ No null values")
        
        # Check 3: Negative prices
        price_columns = ['bid', 'ask', 'open', 'high', 'low', 'close', 'price', 'mid']
        for col in price_columns:
            if col in df.columns:
                if (df[col] < 0).any():
                    raise ValueError(f"Negative prices found in column '{col}'")
        self._log("  ✓ No negative prices")
        
        # Check 4: Timestamp ordering
        if 'timestamp' in df.columns:
            if not df['timestamp'].is_monotonic_increasing:
                self._log("  ⚠ Warning: Timestamps not monotonically increasing")
            else:
                self._log("  ✓ Timestamps are monotonic increasing")
        
        # Check 5: Data types
        self._log("  ✓ Data types validated")
        
        return True
    
    def detect_schema(self, df: pd.DataFrame) -> str:
        """
        Detect the data schema type.
        
        Args:
            df: DataFrame to analyze
            
        Returns:
            'OHLCV', 'OrderBook', 'Tick', or 'Unknown'
        """
        columns = set(df.columns.str.lower())
        
        # Check for OHLCV
        ohlcv_cols = {'open', 'high', 'low', 'close'}
        if ohlcv_cols.issubset(columns):
            self._log("  ✓ Detected schema: OHLCV")
            return 'OHLCV'
        
        # Check for OrderBook
        orderbook_cols = {'bid', 'ask', 'bid_qty', 'ask_qty'}
        if orderbook_cols.issubset(columns):
            self._log("  ✓ Detected schema: OrderBook")
            return 'OrderBook'
        
        # Check for bid/ask without quantities
        if 'bid' in columns and 'ask' in columns:
            self._log("  ✓ Detected schema: OrderBook (without quantities)")
            return 'OrderBook'
        
        # Check for Tick
        if 'price' in columns and 'quantity' in columns:
            self._log("  ✓ Detected schema: Tick")
            return 'Tick'
        
        if 'price' in columns:
            self._log("  ✓ Detected schema: Tick (price only)")
            return 'Tick'
        
        self._log("  ⚠ Schema: Unknown")
        return 'Unknown'
    
    def get_diagnostics(self, df: pd.DataFrame) -> dict:
        """
        Get detailed diagnostics about the data.
        
        Args:
            df: DataFrame to analyze
            
        Returns:
            Dictionary with diagnostic information
        """
        diagnostics = {
            'shape': df.shape,
            'columns': list(df.columns),
            'dtypes': df.dtypes.to_dict(),
            'null_counts': df.isnull().sum().to_dict(),
            'schema': self.detect_schema(df),
            'memory_usage_mb': df.memory_usage(deep=True).sum() / 1024 / 1024
        }
        
        # Add summary statistics for numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            diagnostics['numeric_summary'] = df[numeric_cols].describe().to_dict()
        
        return diagnostics
    
    def add_mid_price(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add mid price column if bid and ask are available.
        
        Args:
            df: DataFrame with bid/ask columns
            
        Returns:
            DataFrame with 'mid' column added
        """
        df = df.copy()
        
        if 'bid' in df.columns and 'ask' in df.columns:
            df['mid'] = (df['bid'] + df['ask']) / 2
            self._log("  ✓ Added mid price column")
        elif 'close' in df.columns:
            df['mid'] = df['close']
            self._log("  ✓ Using close as mid price")
        elif 'price' in df.columns:
            df['mid'] = df['price']
            self._log("  ✓ Using price as mid price")
        
        return df
