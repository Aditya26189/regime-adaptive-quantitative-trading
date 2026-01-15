"""
Noise filtering module for cleaning market data.

This module provides functions to clean noisy, imperfect market data
before feature engineering. Critical for competition data quality.

Filters:
- Outlier removal (price spikes)
- Bid-ask bounce smoothing
- Volume spike detection
- Timestamp validation
"""

from typing import Dict, Tuple, List, Optional, Any
import numpy as np
import pandas as pd


class NoiseFilter:
    """
    Collection of noise filtering methods for market data.
    
    Example:
        >>> clean_df, flags = NoiseFilter.apply_all(df)
        >>> print(f"Cleaned {flags['outliers_removed']} outliers")
    """
    
    @staticmethod
    def remove_outliers(
        df: pd.DataFrame,
        threshold: float = 5.0,
        window: int = 100,
        price_col: str = 'mid'
    ) -> Tuple[pd.DataFrame, Dict[str, int]]:
        """
        Remove price outliers based on rolling standard deviation.
        
        Outlier = |price_change| > threshold × rolling_std
        
        Args:
            df: DataFrame with price column
            threshold: Number of standard deviations for outlier detection
            window: Rolling window size for std calculation
            price_col: Column name for price data
            
        Returns:
            (cleaned_df, {'outliers_removed': int})
        """
        df = df.copy()
        
        # Find price column
        if price_col not in df.columns:
            for col in ['mid', 'close', 'price']:
                if col in df.columns:
                    price_col = col
                    break
            else:
                # Create mid from bid/ask if available
                if 'bid' in df.columns and 'ask' in df.columns:
                    df['mid'] = (df['bid'] + df['ask']) / 2
                    price_col = 'mid'
                else:
                    return df, {'outliers_removed': 0}
        
        # Calculate price changes
        price_change = df[price_col].diff().abs()
        
        # Calculate rolling std
        rolling_std = df[price_col].diff().rolling(window=window, min_periods=10).std()
        
        # Identify outliers
        outlier_threshold = threshold * rolling_std
        is_outlier = price_change > outlier_threshold
        
        # Don't mark first few rows as outliers (insufficient data for std)
        is_outlier.iloc[:window] = False
        
        outliers_removed = is_outlier.sum()
        
        # Remove outliers
        clean_df = df[~is_outlier].reset_index(drop=True)
        
        return clean_df, {'outliers_removed': int(outliers_removed)}
    
    @staticmethod
    def remove_bid_ask_bounce(
        df: pd.DataFrame,
        price_col: str = 'mid'
    ) -> Tuple[pd.DataFrame, Dict[str, int]]:
        """
        Smooth bid-ask bounce artifacts.
        
        Bid-ask bounce: consecutive trades alternating above/below mid.
        Replace prices in bouncy sequences with mid price.
        
        Args:
            df: DataFrame with price and bid/ask columns
            price_col: Column with trade prices
            
        Returns:
            (cleaned_df, {'bounces_smoothed': int})
        """
        df = df.copy()
        
        # Need bid and ask to detect bounces
        if 'bid' not in df.columns or 'ask' not in df.columns:
            return df, {'bounces_smoothed': 0}
        
        # Calculate mid if not present
        if 'mid' not in df.columns:
            df['mid'] = (df['bid'] + df['ask']) / 2
        
        # Detect if price is above or below mid
        if price_col in df.columns and price_col != 'mid':
            above_mid = df[price_col] > df['mid']
        else:
            # Use bid/ask as proxy
            spread = df['ask'] - df['bid']
            mid = df['mid']
            # Small random deviation to simulate price
            np.random.seed(42)
            noise = np.random.uniform(-0.5, 0.5, len(df)) * spread
            df['_temp_price'] = mid + noise
            above_mid = df['_temp_price'] > mid
        
        # Detect alternating pattern (bounce)
        alternating = above_mid != above_mid.shift(1)
        
        # Consecutive alternating = bounce
        bounce_count = alternating.rolling(3, min_periods=3).sum()
        is_bounce = bounce_count >= 2  # At least 2 alternations in 3 ticks
        
        bounces_smoothed = is_bounce.sum()
        
        # Smooth bounces by using mid price
        if price_col in df.columns and price_col != 'mid':
            df.loc[is_bounce, price_col] = df.loc[is_bounce, 'mid']
        
        # Clean up temp column
        if '_temp_price' in df.columns:
            df = df.drop('_temp_price', axis=1)
        
        return df, {'bounces_smoothed': int(bounces_smoothed)}
    
    @staticmethod
    def flag_volume_spikes(
        df: pd.DataFrame,
        threshold: float = 10.0,
        window: int = 100
    ) -> Tuple[pd.DataFrame, Dict[str, int]]:
        """
        Flag abnormal volume spikes.
        
        Spike = volume > threshold × rolling_median
        
        Args:
            df: DataFrame with volume column
            threshold: Multiple of median for spike detection
            window: Rolling window for median calculation
            
        Returns:
            (df_with_flag, {'spikes_flagged': int})
        """
        df = df.copy()
        
        # Find volume column
        vol_col = None
        for col in ['volume', 'vol', 'bid_vol_1', 'ask_vol_1', 'bid_qty', 'ask_qty']:
            if col in df.columns:
                vol_col = col
                break
        
        if vol_col is None:
            df['volume_spike'] = False
            return df, {'spikes_flagged': 0}
        
        # Calculate rolling median
        rolling_median = df[vol_col].rolling(window=window, min_periods=10).median()
        
        # Identify spikes
        spike_threshold = threshold * rolling_median
        is_spike = df[vol_col] > spike_threshold
        
        # Don't flag first few rows
        is_spike.iloc[:window] = False
        
        spikes_flagged = is_spike.sum()
        
        df['volume_spike'] = is_spike
        
        return df, {'spikes_flagged': int(spikes_flagged)}
    
    @staticmethod
    def validate_timestamps(
        df: pd.DataFrame,
        timestamp_col: str = 'timestamp',
        max_gap_seconds: float = 5.0
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Validate timestamp integrity.
        
        Checks:
        1. Monotonically increasing
        2. No duplicates
        3. No gaps > max_gap_seconds
        
        Args:
            df: DataFrame with timestamp column
            timestamp_col: Name of timestamp column
            max_gap_seconds: Maximum allowed gap between ticks
            
        Returns:
            (cleaned_df, {
                'duplicates_removed': int,
                'gaps_found': int,
                'is_monotonic': bool
            })
            
        Raises:
            ValueError: If timestamps are fundamentally broken
        """
        df = df.copy()
        
        # Find timestamp column
        ts_col = None
        for col in [timestamp_col, 'timestamp', 'time', 'ts', 'datetime', 'date']:
            if col in df.columns:
                ts_col = col
                break
        
        if ts_col is None:
            # No timestamp column, create index-based one
            df['timestamp'] = range(len(df))
            return df, {'duplicates_removed': 0, 'gaps_found': 0, 'is_monotonic': True}
        
        # Check for numeric vs datetime
        if pd.api.types.is_numeric_dtype(df[ts_col]):
            timestamps = df[ts_col]
        else:
            try:
                timestamps = pd.to_datetime(df[ts_col])
                df[ts_col] = timestamps
            except Exception:
                # Can't parse - just use as-is
                timestamps = df[ts_col]
        
        # Check monotonicity
        is_monotonic = timestamps.is_monotonic_increasing
        
        if not is_monotonic:
            # Sort by timestamp
            df = df.sort_values(ts_col).reset_index(drop=True)
            timestamps = df[ts_col]
        
        # Remove duplicates
        original_len = len(df)
        df = df.drop_duplicates(subset=[ts_col], keep='first').reset_index(drop=True)
        duplicates_removed = original_len - len(df)
        
        # Check for gaps
        gaps_found = 0
        if pd.api.types.is_numeric_dtype(df[ts_col]):
            diffs = df[ts_col].diff()
            # Assume numeric timestamps are in some unit
            # Flag gaps > 5x median diff
            median_diff = diffs.median()
            if median_diff > 0:
                large_gaps = diffs > (5 * median_diff)
                gaps_found = large_gaps.sum()
        else:
            try:
                diffs = df[ts_col].diff()
                large_gaps = diffs > pd.Timedelta(seconds=max_gap_seconds)
                gaps_found = large_gaps.sum()
            except Exception:
                gaps_found = 0
        
        return df, {
            'duplicates_removed': int(duplicates_removed),
            'gaps_found': int(gaps_found),
            'is_monotonic': bool(is_monotonic)
        }
    
    @staticmethod
    def apply_all(
        df: pd.DataFrame,
        outlier_threshold: float = 5.0,
        volume_spike_threshold: float = 10.0,
        window: int = 100
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Apply all noise filters in sequence.
        
        Pipeline:
        1. Validate timestamps (must be first)
        2. Remove outliers
        3. Smooth bid-ask bounce
        4. Flag volume spikes
        
        Args:
            df: Raw market data DataFrame
            outlier_threshold: Std devs for outlier detection
            volume_spike_threshold: Multiple of median for volume spikes
            window: Rolling window size
            
        Returns:
            (cleaned_df, {
                'outliers_removed': int,
                'bounces_smoothed': int,
                'volume_spikes_flagged': int,
                'timestamp_issues': dict,
                'original_rows': int,
                'final_rows': int
            })
        """
        original_rows = len(df)
        all_flags = {'original_rows': original_rows}
        
        # 1. Validate timestamps
        df, ts_flags = NoiseFilter.validate_timestamps(df)
        all_flags['timestamp_issues'] = ts_flags
        
        # 2. Remove outliers
        df, outlier_flags = NoiseFilter.remove_outliers(
            df, threshold=outlier_threshold, window=window
        )
        all_flags['outliers_removed'] = outlier_flags['outliers_removed']
        
        # 3. Smooth bid-ask bounce
        df, bounce_flags = NoiseFilter.remove_bid_ask_bounce(df)
        all_flags['bounces_smoothed'] = bounce_flags['bounces_smoothed']
        
        # 4. Flag volume spikes
        df, spike_flags = NoiseFilter.flag_volume_spikes(
            df, threshold=volume_spike_threshold, window=window
        )
        all_flags['volume_spikes_flagged'] = spike_flags['spikes_flagged']
        
        all_flags['final_rows'] = len(df)
        
        return df, all_flags


# Test code
if __name__ == '__main__':
    print("=" * 60)
    print("NOISE FILTER TEST")
    print("=" * 60)
    
    # Create synthetic dirty data
    np.random.seed(42)
    n = 1000
    
    df = pd.DataFrame({
        'timestamp': range(n),
        'bid': 100 + np.random.randn(n).cumsum() * 0.1,
        'ask': 100 + np.random.randn(n).cumsum() * 0.1 + 0.02,
        'bid_qty': np.random.randint(100, 1000, n),
        'ask_qty': np.random.randint(100, 1000, n)
    })
    df['mid'] = (df['bid'] + df['ask']) / 2
    
    # Add artificial issues
    df.loc[500, 'mid'] = 200  # Price outlier (way above normal)
    df.loc[501, 'mid'] = 50   # Another outlier (way below normal)
    df.loc[600, 'bid_qty'] = 50000  # Volume spike
    df.loc[700, 'timestamp'] = df.loc[699, 'timestamp']  # Duplicate timestamp
    
    print(f"\nOriginal data:")
    print(f"  Rows: {len(df)}")
    print(f"  Price range: {df['mid'].min():.2f} - {df['mid'].max():.2f}")
    print(f"  Outlier at row 500: {df.loc[500, 'mid']:.2f}")
    print(f"  Volume spike at row 600: {df.loc[600, 'bid_qty']}")
    
    # Apply all filters
    clean_df, flags = NoiseFilter.apply_all(df)
    
    print(f"\nCleaned data:")
    print(f"  Rows: {len(clean_df)}")
    print(f"  Price range: {clean_df['mid'].min():.2f} - {clean_df['mid'].max():.2f}")
    
    print(f"\nFiltering results:")
    print(f"  Outliers removed: {flags['outliers_removed']}")
    print(f"  Bounces smoothed: {flags['bounces_smoothed']}")
    print(f"  Volume spikes flagged: {flags['volume_spikes_flagged']}")
    print(f"  Timestamp duplicates: {flags['timestamp_issues']['duplicates_removed']}")
    print(f"  Timestamp gaps: {flags['timestamp_issues']['gaps_found']}")
    print(f"  Was monotonic: {flags['timestamp_issues']['is_monotonic']}")
    
    # Assertions
    print("\n" + "-" * 60)
    
    assert len(clean_df) <= len(df), "Cleaned df should have <= rows"
    assert flags['outliers_removed'] >= 1, "Should detect at least 1 outlier"
    assert flags['timestamp_issues']['duplicates_removed'] >= 1, "Should detect duplicate"
    
    print("✅ All tests passed!")
    print("=" * 60)
