"""
Rule-based decision engine
"""
import numpy as np
from typing import Dict, Any


class RuleEngine:
    """Business rules for fraud detection"""

    @staticmethod
    def apply_rules(
        fraud_prob: float,
        anomaly_score: float,
        transaction_data: Dict[str, Any]
    ) -> float:
        """
        Apply business rules and return rule score [0, 1]

        Args:
            fraud_prob: Supervised fraud probability
            anomaly_score: Anomaly detection score
            transaction_data: Original transaction data

        Returns:
            Rule score contribution [0, 1]
        """
        rule_score = 0.0
        amount = transaction_data.get("amount", 0)

        # Rule 1: Very high amount
        if amount > 5000:
            rule_score += 0.3
        elif amount > 2000:
            rule_score += 0.15

        # Rule 2: High fraud + high anomaly = escalate
        if fraud_prob > 0.7 and anomaly_score > 0.7:
            rule_score += 0.4

        # Rule 3: Moderate fraud + strong anomaly
        if 0.4 <= fraud_prob < 0.7 and anomaly_score > 0.8:
            rule_score += 0.3

        # Rule 4: Zero amount transactions (suspicious)
        if amount == 0:
            rule_score += 0.2

        return min(rule_score, 1.0)
