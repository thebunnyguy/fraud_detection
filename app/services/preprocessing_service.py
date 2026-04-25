"""
Preprocessing service for transaction data
"""
import numpy as np
from typing import Dict, List, Any
from app.core.config import FEATURE_COLS


class PreprocessingService:
    """Handles feature extraction and validation"""

    @staticmethod
    def validate_and_extract_features(data: Dict[str, Any]) -> np.ndarray:
        """
        Extract features in correct order and validate

        Args:
            data: Transaction dictionary

        Returns:
            Feature array ready for model input

        Raises:
            ValueError: If required features are missing or invalid
        """
        missing = [col for col in FEATURE_COLS if col not in data]
        if missing:
            raise ValueError(f"Missing required features: {missing}")

        features = []
        for col in FEATURE_COLS:
            val = data[col]
            try:
                features.append(float(val))
            except (TypeError, ValueError):
                raise ValueError(f"Feature '{col}' must be numeric, got: {val}")

        arr = np.array(features).reshape(1, -1)

        if np.isnan(arr).any() or np.isinf(arr).any():
            raise ValueError("Features contain NaN or Inf values")

        return arr

    @staticmethod
    def validate_batch(transactions: List[Dict[str, Any]]) -> np.ndarray:
        """Validate and extract features from multiple transactions"""
        if not transactions:
            raise ValueError("Empty transaction list")

        feature_arrays = []
        for i, txn in enumerate(transactions):
            try:
                features = PreprocessingService.validate_and_extract_features(txn)
                feature_arrays.append(features)
            except ValueError as e:
                raise ValueError(f"Transaction {i}: {str(e)}")

        return np.vstack(feature_arrays)
