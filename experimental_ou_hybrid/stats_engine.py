"""
STATS ENGINE: Fractal and Entropy Core
Implements Hurst Exponent (R/S) and Shannon Entropy for regime detection.
"""

import numpy as np


class FractalMath:
    @staticmethod
    def hurst_rs(returns: np.ndarray, min_lag: int = 8, max_lag: int = 64) -> float:
        """
        Estimate Hurst exponent H using simplified Rescaled Range (R/S) approach.
        - H < 0.5: Mean-reverting series
        - H = 0.5: Random walk
        - H > 0.5: Trending series
        """
        n = len(returns)
        if n < 2 * max_lag:
            return np.nan
            
        lags = range(min_lag, min(max_lag + 1, n // 2))
        rs_values = []
        lag_values = []
        
        for lag in lags:
            # Number of complete segments
            n_segments = n // lag
            if n_segments < 1:
                continue
                
            rs_segment = []
            for i in range(n_segments):
                segment = returns[i * lag:(i + 1) * lag]
                
                # Center by subtracting mean
                centered = segment - np.mean(segment)
                
                # Cumulative sum
                cumsum = np.cumsum(centered)
                
                # Range
                R = np.max(cumsum) - np.min(cumsum)
                
                # Standard deviation
                S = np.std(segment, ddof=1)
                
                if S > 0:
                    rs_segment.append(R / S)
                    
            if len(rs_segment) > 0:
                rs_values.append(np.mean(rs_segment))
                lag_values.append(lag)
                
        if len(rs_values) < 3:
            return np.nan
            
        # Linear regression: log(R/S) vs log(lag)
        log_lags = np.log(lag_values)
        log_rs = np.log(rs_values)
        
        try:
            H, _ = np.polyfit(log_lags, log_rs, 1)
            return float(H)
        except:
            return np.nan

    @staticmethod
    def shannon_entropy(returns: np.ndarray, bins: int = 20) -> float:
        """
        Estimate Shannon entropy in bits via histogram.
        Higher entropy = more random, lower predictability.
        """
        if len(returns) < bins:
            return np.nan
            
        std = np.std(returns)
        if std == 0:
            return np.nan
            
        # Histogram
        counts, _ = np.histogram(returns, bins=bins)
        
        # Convert to probabilities
        total = np.sum(counts)
        if total == 0:
            return np.nan
            
        probs = counts / total
        
        # Add epsilon to avoid log(0)
        eps = 1e-12
        probs = probs + eps
        probs = probs / np.sum(probs)  # Renormalize
        
        # Shannon entropy
        entropy = -np.sum(probs * np.log2(probs))
        
        return float(entropy)
