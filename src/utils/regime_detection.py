"""
Regime Detection System using Close Prices Only
Implements Kaufman Efficiency Ratio (KER) for market regime classification
Rule 12 Compliant: Uses ONLY close prices
"""

import pandas as pd
import numpy as np
from typing import Dict

class RegimeDetector:
    """
    Detects market regimes (trending vs mean-reverting) using KER.
    """
    
    @staticmethod
    def calculate_ker(close: pd.Series, period: int = 10) -> pd.Series:
        """
        Kaufman Efficiency Ratio - measures path efficiency.
        
        Formula: |Net Change| / Sum(|Absolute Changes|)
        
        Values:
        - 0.0-0.25: Highly noisy (mean-reverting)
        - 0.25-0.50: Mixed regime
        - 0.50-1.00: Efficient trend
        
        Args:
            close: Series of close prices
            period: Lookback period (default 10)
            
        Returns:
            Series of KER values (0-1)
        """
        # Net directional change over period
        direction = close.diff(period).abs()
        
        # Sum of all individual changes (path length)
        volatility = close.diff().abs().rolling(window=period).sum()
        
        # Calculate efficiency ratio
        ker = direction / (volatility + 1e-10)  # Avoid division by zero
        
        return ker.fillna(0)
    
    @staticmethod
    def classify_regime(ker: pd.Series, 
                       ker_threshold_mean_rev: float = 0.30,
                       ker_threshold_trend: float = 0.50) -> pd.Series:
        """
        Classify market regime based on KER.
        
        Args:
            ker: Series of KER values
            ker_threshold_mean_rev: Below this = mean-reverting
            ker_threshold_trend: Above this = trending
            
        Returns:
            Series with regime labels: 'MEAN_REV', 'MIXED', 'TREND'
        """
        regime = pd.Series('MIXED', index=ker.index)
        regime[ker < ker_threshold_mean_rev] = 'MEAN_REV'
        regime[ker > ker_threshold_trend] = 'TREND'
        
        return regime
    
    @staticmethod
    def get_regime_statistics(close: pd.Series, period: int = 10) -> Dict:
        """
        Calculate comprehensive regime statistics for a symbol.
        """
        ker = RegimeDetector.calculate_ker(close, period)
        regime = RegimeDetector.classify_regime(ker)
        
        stats = {
            'ker_mean': ker.mean(),
            'ker_std': ker.std(),
            'ker_median': ker.median(),
            'pct_mean_rev': (regime == 'MEAN_REV').sum() / len(regime) * 100,
            'pct_mixed': (regime == 'MIXED').sum() / len(regime) * 100,
            'pct_trend': (regime == 'TREND').sum() / len(regime) * 100,
        }
        
        return stats

# Initialize for easy import
regime_detector = RegimeDetector()
