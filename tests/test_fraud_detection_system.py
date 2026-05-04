"""
Comprehensive tests for fraud detection system
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import json

# Test preprocessing
def test_preprocessing_valid_input():
    from app.services.preprocessing_service import PreprocessingService

    data = {
        "time": 0,
        "amount": 100.0,
        **{f"v{i}": float(i) for i in range(1, 29)}
    }

    features = PreprocessingService.validate_and_extract_features(data)
    assert features.shape == (1, 30)
    assert features[0, 0] == 0  # time
    assert features[0, 1] == 100.0  # amount


def test_preprocessing_missing_features():
    from app.services.preprocessing_service import PreprocessingService

    data = {"time": 0, "amount": 100.0}  # Missing v1-v28

    with pytest.raises(ValueError, match="Missing required features"):
        PreprocessingService.validate_and_extract_features(data)


def test_preprocessing_invalid_types():
    from app.services.preprocessing_service import PreprocessingService

    data = {
        "time": "invalid",
        "amount": 100.0,
        **{f"v{i}": float(i) for i in range(1, 29)}
    }

    with pytest.raises(ValueError, match="must be numeric"):
        PreprocessingService.validate_and_extract_features(data)


def test_preprocessing_nan_values():
    from app.services.preprocessing_service import PreprocessingService

    data = {
        "time": float('nan'),
        "amount": 100.0,
        **{f"v{i}": float(i) for i in range(1, 29)}
    }

    with pytest.raises(ValueError, match="NaN or Inf"):
        PreprocessingService.validate_and_extract_features(data)


# Test risk scoring
def test_risk_score_calculation():
    from app.models.risk_engine import RiskEngine

    # High risk scenario
    risk_score = RiskEngine.calculate_risk_score(0.9, 0.8, 0.7)
    assert 70 <= risk_score <= 100

    # Low risk scenario
    risk_score = RiskEngine.calculate_risk_score(0.1, 0.1, 0.0)
    assert 0 <= risk_score <= 30


def test_risk_score_bounds():
    from app.models.risk_engine import RiskEngine

    # Test upper bound
    risk_score = RiskEngine.calculate_risk_score(1.0, 1.0, 1.0)
    assert risk_score == 100

    # Test lower bound
    risk_score = RiskEngine.calculate_risk_score(0.0, 0.0, 0.0)
    assert risk_score == 0


def test_decision_thresholds():
    from app.models.risk_engine import RiskEngine

    assert RiskEngine.make_decision(20) == "APPROVE"
    assert RiskEngine.make_decision(39) == "APPROVE"
    assert RiskEngine.make_decision(40) == "REVIEW"
    assert RiskEngine.make_decision(69) == "REVIEW"
    assert RiskEngine.make_decision(70) == "BLOCK"
    assert RiskEngine.make_decision(100) == "BLOCK"


# Test rule engine
def test_rule_engine_high_amount():
    from app.models.rules import RuleEngine

    score = RuleEngine.apply_rules(0.3, 0.3, {"amount": 6000})
    assert score > 0.2  # High amount should boost score


def test_rule_engine_zero_amount():
    from app.models.rules import RuleEngine

    score = RuleEngine.apply_rules(0.3, 0.3, {"amount": 0})
    assert score > 0.1  # Zero amount is suspicious


def test_rule_engine_escalation():
    from app.models.rules import RuleEngine

    # High fraud + high anomaly should escalate
    score = RuleEngine.apply_rules(0.8, 0.8, {"amount": 100})
    assert score > 0.3


# Test explainer
def test_explainer_generates_explanations():
    from app.models.explainer import FraudExplainer

    explainer = FraudExplainer()
    explanations = explainer.generate_explanation(
        fraud_prob=0.8,
        anomaly_score=0.7,
        risk_score=85,
        decision="BLOCK",
        transaction_data={"amount": 100}
    )

    assert len(explanations) > 0
    assert any("fraud" in exp.lower() for exp in explanations)


def test_explainer_decision_specific():
    from app.models.explainer import FraudExplainer

    explainer = FraudExplainer()

    # BLOCK decision
    explanations = explainer.generate_explanation(
        0.9, 0.8, 90, "BLOCK", {"amount": 100}
    )
    assert any("block" in exp.lower() for exp in explanations)

    # APPROVE decision
    explanations = explainer.generate_explanation(
        0.1, 0.1, 10, "APPROVE", {"amount": 100}
    )
    assert any("approve" in exp.lower() for exp in explanations)


# Test API endpoints
@pytest.fixture
def client():
    from app_main import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'status' in data
    assert 'models' in data


@patch('app_main.fraud_service')
@patch('app_main.sqlite3')
def test_predict_endpoint_success(mock_sqlite, mock_service, client):
    # Mock fraud service response
    mock_service.predict.return_value = {
        "fraud_probability": 0.15,
        "anomaly_score": 0.20,
        "risk_score": 25,
        "decision": "APPROVE",
        "explanation": ["Low risk"],
        "top_features": []
    }

    # Mock database
    mock_conn = Mock()
    mock_sqlite.connect.return_value = mock_conn

    payload = {
        "transaction_id": "test-001",
        "time": 0,
        "amount": 100.0,
        **{f"v{i}": 0.0 for i in range(1, 29)}
    }

    response = client.post('/predict',
        data=json.dumps(payload),
        content_type='application/json'
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['decision'] == 'APPROVE'
    assert 'fraud_probability' in data
    assert 'anomaly_score' in data
    assert 'risk_score' in data


@patch('app_main.fraud_service')
def test_predict_endpoint_validation_error(mock_service, client):
    mock_service.predict.side_effect = ValueError("Missing features")

    payload = {"transaction_id": "test-001"}  # Incomplete

    response = client.post('/predict',
        data=json.dumps(payload),
        content_type='application/json'
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data


@patch('app_main.fraud_service')
def test_batch_predict_endpoint(mock_service, client):
    mock_service.predict_batch.return_value = [
        {"transaction_id": "txn-1", "decision": "APPROVE", "risk_score": 20},
        {"transaction_id": "txn-2", "decision": "BLOCK", "risk_score": 85}
    ]

    payload = {
        "transactions": [
            {"transaction_id": "txn-1", "time": 0, "amount": 50, **{f"v{i}": 0.0 for i in range(1, 29)}},
            {"transaction_id": "txn-2", "time": 10, "amount": 5000, **{f"v{i}": 1.0 for i in range(1, 29)}}
        ]
    }

    response = client.post('/predict/batch',
        data=json.dumps(payload),
        content_type='application/json'
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['count'] == 2
    assert len(data['results']) == 2


def test_demo_samples_endpoint(client):
    response = client.get('/demo-samples')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'low_risk' in data
    assert 'medium_risk' in data
    assert 'high_risk' in data
    assert 'transaction_id' in data['low_risk']
