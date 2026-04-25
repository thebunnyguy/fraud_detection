"""
Fraud detection service - orchestrates full prediction pipeline
"""
from typing import Dict, Any, List
from app.services.preprocessing_service import PreprocessingService
from app.models.predictor import FraudPredictor
from app.models.anomaly import AnomalyDetector
from app.models.rules import RuleEngine
from app.models.risk_engine import RiskEngine
from app.models.explainer import FraudExplainer


class FraudDetectionService:
    """Main service orchestrating fraud detection pipeline"""

    def __init__(self):
        self.preprocessor = PreprocessingService()
        self.predictor = FraudPredictor()
        self.anomaly_detector = AnomalyDetector()
        self.rule_engine = RuleEngine()
        self.risk_engine = RiskEngine()
        self.explainer = FraudExplainer()

    def predict(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run full fraud detection pipeline

        Args:
            transaction_data: Transaction dictionary with all features

        Returns:
            Complete prediction result with scores, decision, and explanation
        """
        # Step 1: Validate and extract features
        features = self.preprocessor.validate_and_extract_features(transaction_data)

        # Step 2: Run supervised fraud model
        fraud_prob = self.predictor.predict_fraud_probability(features)

        # Step 3: Run anomaly detection
        anomaly_score = self.anomaly_detector.detect_anomaly(features)

        # Step 4: Apply business rules
        rule_score = self.rule_engine.apply_rules(
            fraud_prob, anomaly_score, transaction_data
        )

        # Step 5: Calculate risk score
        risk_score = self.risk_engine.calculate_risk_score(
            fraud_prob, anomaly_score, rule_score
        )

        # Step 6: Make decision
        decision = self.risk_engine.make_decision(risk_score)

        # Step 7: Generate explanation
        explanation = self.explainer.generate_explanation(
            fraud_prob, anomaly_score, risk_score, decision, transaction_data
        )

        # Step 8: Get top features
        top_features = self.explainer.get_top_features(features)

        return {
            "fraud_probability": round(fraud_prob, 4),
            "anomaly_score": round(anomaly_score, 4),
            "risk_score": risk_score,
            "decision": decision,
            "explanation": explanation,
            "top_features": top_features
        }

    def predict_batch(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process multiple transactions"""
        results = []
        for txn in transactions:
            try:
                result = self.predict(txn)
                result["transaction_id"] = txn.get("transaction_id", "unknown")
                results.append(result)
            except Exception as e:
                results.append({
                    "transaction_id": txn.get("transaction_id", "unknown"),
                    "error": str(e)
                })
        return results
