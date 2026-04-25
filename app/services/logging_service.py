"""
Logging service for fraud events
"""
import json
from datetime import datetime
from typing import Dict, Any
from app.core.config import FRAUD_LOG_PATH


class FraudLoggingService:
    """Logs suspicious transactions to JSONL file"""

    @staticmethod
    def log_event(
        transaction_id: str,
        decision: str,
        risk_score: int,
        fraud_prob: float,
        anomaly_score: float,
        amount: float
    ):
        """Log fraud event if decision is REVIEW or BLOCK"""
        if decision not in ["REVIEW", "BLOCK"]:
            return

        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "transaction_id": transaction_id,
            "decision": decision,
            "risk_score": risk_score,
            "fraud_probability": fraud_prob,
            "anomaly_score": anomaly_score,
            "amount": amount
        }

        with open(FRAUD_LOG_PATH, "a") as f:
            f.write(json.dumps(event) + "\n")
