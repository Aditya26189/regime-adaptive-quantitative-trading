"""
REGIME FILTER: Simple Market Regime Classifier
Uses Hurst exponent and Shannon entropy to detect market regimes.
"""

import enum
import numpy as np
from collections import deque
from .stats_engine import FractalMath


class RegimeState(enum.Enum):
    MEAN_REVERSION = 1
    MOMENTUM = 2
    NEUTRAL = 3


class MarketRegimeClassifier:
    def __init__(self, window: int = 500):
        self.window = window
        self.returns_buffer = deque(maxlen=window)
        self.entropy_buffer = deque(maxlen=200)
        
    def update_and_classify(self, new_return: float) -> RegimeState:
        """
        Add new return and classify current regime.
        
        Rules:
          - H < 0.45 and entropy_z > 0 → MEAN_REVERSION
          - H > 0.55 and entropy_z < -1 → MOMENTUM
          - Else → NEUTRAL
        """
        self.returns_buffer.append(new_return)
        
        # Need sufficient data
        if len(self.returns_buffer) < 200:
            return RegimeState.NEUTRAL
            
        returns = np.array(self.returns_buffer)
        
        # Compute Hurst
        H = FractalMath.hurst_rs(returns)
        
        # Compute Entropy
        E = FractalMath.shannon_entropy(returns)
        
        if np.isnan(H) or np.isnan(E):
            return RegimeState.NEUTRAL
            
        # Update entropy buffer for z-score
        self.entropy_buffer.append(E)
        
        if len(self.entropy_buffer) < 50:
            return RegimeState.NEUTRAL
            
        # Entropy z-score
        entropy_arr = np.array(self.entropy_buffer)
        entropy_mean = np.mean(entropy_arr)
        entropy_std = np.std(entropy_arr)
        
        if entropy_std == 0:
            entropy_z = 0
        else:
            entropy_z = (E - entropy_mean) / entropy_std
            
        # Classification rules
        if H < 0.45 and entropy_z > 0:
            return RegimeState.MEAN_REVERSION
        elif H > 0.55 and entropy_z < -1:
            return RegimeState.MOMENTUM
        else:
            return RegimeState.NEUTRAL
