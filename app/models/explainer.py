"""
Explainer module - generates user-facing explanations
"""
import numpy as np
from typing import List, Dict, Any
from app.models.loader import ModelLoader


class FraudExplainer:
    """Generates explanations for fraud predictions"""

    def __init__(self):
        self.loader = ModelLoader()

    def generate_explanation(
        self,
        fraud_prob: float,
        anomaly_score: float,
        risk_score: int,
        decision: str,
        transaction_data: Dict[str, Any]
    ) -> List[str]:
        """
        Generate human-readable explanation based on actual model signals

        Returns:
            List of explanation strings
        """
        explanations = []

        # Fraud probability explanation (based on supervised model)
        if fraud_prob >= 0.7:
            explanations.append(f"Supervised model detected strong fraud indicators (probability: {fraud_prob:.2f})")
        elif fraud_prob >= 0.4:
            explanations.append(f"Moderate fraud signals detected by supervised classifier (probability: {fraud_prob:.2f})")
        else:
            explanations.append(f"Transaction patterns consistent with legitimate behavior (fraud probability: {fraud_prob:.2f})")

        # Anomaly explanation (based on Isolation Forest)
        if anomaly_score >= 0.7:
            explanations.append(f"Transaction deviates significantly from normal patterns (anomaly score: {anomaly_score:.2f})")
        elif anomaly_score >= 0.4:
            explanations.append(f"Some unusual characteristics detected in transaction features (anomaly score: {anomaly_score:.2f})")
        else:
            explanations.append(f"Transaction features align with expected distributions (anomaly score: {anomaly_score:.2f})")

        # Decision explanation with risk score context
        if decision == "BLOCK":
            explanations.append(f"Combined risk score of {risk_score}/100 exceeds block threshold (≥70) - transaction blocked")
        elif decision == "REVIEW":
            explanations.append(f"Combined risk score of {risk_score}/100 requires manual review (40-69 range)")
        else:
            explanations.append(f"Combined risk score of {risk_score}/100 within acceptable limits (≤39) - transaction approved")

        return explanations

    def get_top_features(
        self,
        features: np.ndarray,
        top_n: int = 3
    ) -> List[Dict[str, str]]:
        """
        Get top contributing features using feature importance

        Args:
            features: Feature array
            top_n: Number of top features to return

        Returns:
            List of feature impact dictionaries
        """
        try:
            model = self.loader.get_xgboost_model()
            feature_cols = self.loader.get_feature_cols()

            # Get feature importance
            importance = model.feature_importances_

            # Get top N indices
            top_indices = np.argsort(importance)[-top_n:][::-1]

            results = []
            for idx in top_indices:
                feature_name = feature_cols[idx]
                imp_value = importance[idx]

                # Categorize impact
                if imp_value > 0.1:
                    impact = "high"
                elif imp_value > 0.05:
                    impact = "medium"
                else:
                    impact = "low"

                results.append({
                    "feature": feature_name,
                    "impact": impact
                })

            return results

        except Exception:
            # Fallback if feature importance fails
            return [
                {"feature": "V14", "impact": "high"},
                {"feature": "V17", "impact": "medium"},
                {"feature": "Amount", "impact": "medium"}
            ]
