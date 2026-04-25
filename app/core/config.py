"""
Configuration module for fraud detection system
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
ARTIFACTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Model paths
XGBOOST_MODEL_PATH = ARTIFACTS_DIR / "xgboost_model.pkl"
ANOMALY_MODEL_PATH = ARTIFACTS_DIR / "isolation_forest.pkl"
FEATURE_COLS_PATH = ARTIFACTS_DIR / "feature_columns.json"
SCALER_PATH = ARTIFACTS_DIR / "scaler.pkl"

# Feature configuration
FEATURE_COLS = ["time", "amount"] + [f"v{i}" for i in range(1, 29)]

# Decision thresholds
FRAUD_THRESHOLD = float(os.getenv("FRAUD_THRESHOLD", "0.5"))
APPROVE_THRESHOLD = 39  # 0-39 = APPROVE
REVIEW_THRESHOLD = 69   # 40-69 = REVIEW
                        # 70-100 = BLOCK

# Risk scoring weights
RISK_WEIGHT_FRAUD = 0.65
RISK_WEIGHT_ANOMALY = 0.25
RISK_WEIGHT_RULES = 0.10

# Anomaly detection
ANOMALY_CONTAMINATION = 0.001  # Expected fraud rate in training data

# Logging
FRAUD_LOG_PATH = LOGS_DIR / "fraud_events.jsonl"

# Database
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "fraud_transactions.db"))
