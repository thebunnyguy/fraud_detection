"""
Model loader - loads all ML artifacts at startup
"""
import joblib
import json
from pathlib import Path
from typing import Optional, Dict, Any
from app.core.config import (
    XGBOOST_MODEL_PATH,
    ANOMALY_MODEL_PATH,
    FEATURE_COLS_PATH,
    FEATURE_COLS
)


class ModelLoader:
    """Singleton model loader"""

    _instance = None
    _models_loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Only initialize if not already done
        if not hasattr(self, 'xgboost_model'):
            self.xgboost_model = None
            self.anomaly_model = None
            self.feature_cols = None

    def load_models(self) -> Dict[str, Any]:
        """Load all models and return status"""
        if self._models_loaded:
            return self._get_status()

        errors = []

        # Load XGBoost
        if XGBOOST_MODEL_PATH.exists():
            try:
                self.xgboost_model = joblib.load(XGBOOST_MODEL_PATH)
            except Exception as e:
                errors.append(f"XGBoost load failed: {e}")
        else:
            errors.append(f"XGBoost model not found at {XGBOOST_MODEL_PATH}")

        # Load Isolation Forest
        if ANOMALY_MODEL_PATH.exists():
            try:
                self.anomaly_model = joblib.load(ANOMALY_MODEL_PATH)
            except Exception as e:
                errors.append(f"Anomaly model load failed: {e}")
        else:
            errors.append(f"Anomaly model not found at {ANOMALY_MODEL_PATH}")

        # Load feature columns
        if FEATURE_COLS_PATH.exists():
            try:
                with open(FEATURE_COLS_PATH) as f:
                    self.feature_cols = json.load(f)
            except Exception as e:
                errors.append(f"Feature columns load failed: {e}")
        else:
            self.feature_cols = FEATURE_COLS

        self._models_loaded = True

        status = self._get_status()
        status["errors"] = errors
        return status

    def _get_status(self) -> Dict[str, Any]:
        return {
            "xgboost_loaded": self.xgboost_model is not None,
            "anomaly_loaded": self.anomaly_model is not None,
            "feature_cols_loaded": self.feature_cols is not None
        }

    def get_xgboost_model(self):
        if not self.xgboost_model:
            raise RuntimeError("XGBoost model not loaded")
        return self.xgboost_model

    def get_anomaly_model(self):
        if not self.anomaly_model:
            raise RuntimeError("Anomaly model not loaded")
        return self.anomaly_model

    def get_feature_cols(self):
        return self.feature_cols or FEATURE_COLS
