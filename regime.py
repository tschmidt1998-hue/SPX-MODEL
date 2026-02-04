import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

class RegimeSwitchingModel:
    def __init__(self):
        self.model_above = LinearRegression()
        self.model_below = LinearRegression()
        self.is_fitted = False

    def fit(self, X: pd.DataFrame, y: pd.Series, price: pd.Series, gamma_flip: float):
        """
        Fits two separate models based on the regime defined by Gamma Flip.
        
        :param X: Features (DataFrame).
        :param y: Target (Series).
        :param price: Series of underlying prices corresponding to X/y.
        :param gamma_flip: The Gamma Flip level (scalar).
        """
        # Identify Regimes
        mask_above = price > gamma_flip
        mask_below = price <= gamma_flip
        
        X_above = X[mask_above]
        y_above = y[mask_above]
        
        X_below = X[mask_below]
        y_below = y[mask_below]
        
        if not X_above.empty:
            self.model_above.fit(X_above, y_above)
        
        if not X_below.empty:
            self.model_below.fit(X_below, y_below)
            
        self.is_fitted = True

    def predict(self, X: pd.DataFrame, current_price: float, gamma_flip: float):
        """
        Predicts using the appropriate model for the current regime.
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted")
            
        if current_price > gamma_flip:
            return self.model_above.predict(X)
        else:
            return self.model_below.predict(X)

    def get_betas(self):
        """Returns the coefficients for both regimes."""
        return {
            'above': self.model_above.coef_ if hasattr(self.model_above, 'coef_') else None,
            'below': self.model_below.coef_ if hasattr(self.model_below, 'coef_') else None
        }
