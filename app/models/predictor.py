"""
Predictor module - runs XGBoost fraud prediction
"""
import numpy as np
from app.models.loader import ModelLoader


class FraudPredictor:
    """XGBoost fraud probability predictor"""

    def __init__(self):
        self.loader = ModelLoader()

    def predict_fraud_probability(self, features: np.ndarray) -> float:
        """
        Predict fraud probability for transaction

        Args:
            features: Feature array (1, 30)

        Returns:
            Fraud probability [0, 1]
        """
        model = self.loader.get_xgboost_model()
        prob = model.predict_proba(features)[0, 1]
        return float(prob)

    def predict_batch(self, features: np.ndarray) -> np.ndarray:
        """Predict fraud probabilities for multiple transactions"""
        model = self.loader.get_xgboost_model()
        probs = model.predict_proba(features)[:, 1]
        return probs
