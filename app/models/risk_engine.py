"""
Risk scoring engine - combines fraud, anomaly, and rule scores
"""
from typing import Dict, Any
from app.core.config import (
    RISK_WEIGHT_FRAUD,
    RISK_WEIGHT_ANOMALY,
    RISK_WEIGHT_RULES,
    APPROVE_THRESHOLD,
    REVIEW_THRESHOLD
)


class RiskEngine:
    """Combines multiple signals into final risk score and decision"""

    @staticmethod
    def calculate_risk_score(
        fraud_prob: float,
        anomaly_score: float,
        rule_score: float
    ) -> int:
        """
        Calculate final risk score [0-100]

        Args:
            fraud_prob: Supervised fraud probability [0, 1]
            anomaly_score: Anomaly detection score [0, 1]
            rule_score: Rule engine score [0, 1]

        Returns:
            Risk score [0-100]
        """
        weighted_score = (
            RISK_WEIGHT_FRAUD * fraud_prob +
            RISK_WEIGHT_ANOMALY * anomaly_score +
            RISK_WEIGHT_RULES * rule_score
        )

        risk_score = int(weighted_score * 100)
        return max(0, min(100, risk_score))

    @staticmethod
    def make_decision(risk_score: int) -> str:
        """
        Make final decision based on risk score

        Args:
            risk_score: Risk score [0-100]

        Returns:
            Decision: APPROVE, REVIEW, or BLOCK
        """
        if risk_score <= APPROVE_THRESHOLD:
            return "APPROVE"
        elif risk_score <= REVIEW_THRESHOLD:
            return "REVIEW"
        else:
            return "BLOCK"
