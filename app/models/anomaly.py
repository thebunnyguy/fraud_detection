"""
Anomaly detection module using Isolation Forest
"""
import numpy as np
from app.models.loader import ModelLoader


class AnomalyDetector:
    """Isolation Forest anomaly detector"""

    def __init__(self):
        self.loader = ModelLoader()

    def detect_anomaly(self, features: np.ndarray) -> float:
        """
        Detect anomaly score for transaction

        Args:
            features: Feature array (1, 30)

        Returns:
            Anomaly score [0, 1] where higher = more anomalous
        """
        model = self.loader.get_anomaly_model()

        # Isolation Forest decision_function: lower score = more anomalous
        # Typical range: fraud ~0.08, legit ~0.26
        score = model.decision_function(features)[0]

        # Min-max normalize to [0, 1], then invert so higher = more anomalous
        # Using observed ranges: [-0.1, 0.32]
        normalized = (score - (-0.1)) / (0.32 - (-0.1))
        normalized = np.clip(normalized, 0, 1)
        inverted = 1 - normalized  # Invert: low scores become high anomaly

        return float(inverted)

    def detect_batch(self, features: np.ndarray) -> np.ndarray:
        """Detect anomaly scores for multiple transactions"""
        model = self.loader.get_anomaly_model()
        scores = model.decision_function(features)

        # Min-max normalize and invert
        normalized = (scores - (-0.1)) / (0.32 - (-0.1))
        normalized = np.clip(normalized, 0, 1)
        inverted = 1 - normalized

        return inverted
