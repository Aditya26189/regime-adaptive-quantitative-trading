"""
OU PROCESS: Ornstein-Uhlenbeck Calibration Module
Fits OU process parameters for mean-reversion trading.
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class OUParams:
    theta: float      # Mean reversion speed
    mu: float         # Long-term mean
    sigma_eq: float   # Equilibrium volatility
    half_life: float  # Time to revert 50%
    valid: bool       # Whether calibration is valid


class OrnsteinUhlenbeck:
    @staticmethod
    def fit(series: np.ndarray, dt: float = 1.0) -> OUParams:
        """
        Fit an OU process to a price/spread series using AR(1)/OLS.
        
        Model: X_{t+1} = alpha + beta * X_t + eps_t
        
        Derive:
          theta = -ln(beta) / dt
          mu    = alpha / (1 - beta)
          sigma_eq = sigma_resid / sqrt(2 * theta)
          half_life = ln(2) / theta
        """
        n = len(series)
        if n < 50:
            return OUParams(theta=0, mu=0, sigma_eq=np.inf, half_life=np.inf, valid=False)
            
        # Build regression: Y = alpha + beta * X
        X = series[:-1]
        Y = series[1:]
        
        # OLS: beta = Cov(X,Y) / Var(X), alpha = mean(Y) - beta * mean(X)
        mean_x = np.mean(X)
        mean_y = np.mean(Y)
        
        var_x = np.var(X, ddof=1)
        if var_x == 0:
            return OUParams(theta=0, mu=0, sigma_eq=np.inf, half_life=np.inf, valid=False)
            
        cov_xy = np.mean((X - mean_x) * (Y - mean_y))
        
        beta = cov_xy / var_x
        alpha = mean_y - beta * mean_x
        
        # Stability checks
        if beta >= 0.999 or beta <= 0:
            return OUParams(theta=0, mu=0, sigma_eq=np.inf, half_life=np.inf, valid=False)
            
        # Derive OU parameters
        theta = -np.log(beta) / dt
        
        if theta <= 0:
            return OUParams(theta=0, mu=0, sigma_eq=np.inf, half_life=np.inf, valid=False)
            
        mu = alpha / (1 - beta)
        
        # Residuals
        residuals = Y - (alpha + beta * X)
        sigma_resid = np.std(residuals, ddof=1)
        
        # Equilibrium volatility
        sigma_eq = sigma_resid / np.sqrt(2 * theta * dt)
        
        # Half-life
        half_life = np.log(2) / theta
        
        return OUParams(
            theta=float(theta),
            mu=float(mu),
            sigma_eq=float(sigma_eq),
            half_life=float(half_life),
            valid=True
        )
