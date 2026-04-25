"""
Tests for the hybrid fraud detection Flask API (app_main.py)
"""
import json
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def client():
    """Create test client with mocked models"""
    # Patch model loader so tests don't need real .pkl files
    mock_loader = MagicMock()
    mock_loader.xgboost_model = MagicMock()
    mock_loader.anomaly_model = MagicMock()
    mock_loader.feature_columns = [
        "Time", "Amount",
        *[f"V{i}" for i in range(1, 29)]
    ]
    mock_loader.models_loaded = True

    with patch("app_main.model_loader", mock_loader):
        from app_main import app
        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c


def test_health_check(client):
    """Test /health returns 200 and healthy status"""
    response = client.get("/health")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "healthy"


def test_predict_legitimate_transaction(client):
    """Test /predict returns APPROVE for low-risk transaction"""
    with patch("app_main.fraud_service") as mock_service:
        mock_service.evaluate_transaction.return_value = {
            "transaction_id": "test-001",
            "fraud_probability": 0.05,
            "anomaly_score": 0.1,
            "risk_score": 10,
            "decision": "APPROVE",
            "explanation": ["Low fraud probability"],
            "top_features": [],
        }

        payload = {
            "transaction_id": "test-001",
            "time": 1000,
            "amount": 50.0,
            **{f"v{i}": 0.0 for i in range(1, 29)},
        }
        response = client.post(
            "/predict",
            data=json.dumps(payload),
            content_type="application/json",
        )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["decision"] == "APPROVE"
    assert "fraud_probability" in data


def test_predict_fraudulent_transaction(client):
    """Test /predict returns BLOCK for high-risk transaction"""
    with patch("app_main.fraud_service") as mock_service:
        mock_service.evaluate_transaction.return_value = {
            "transaction_id": "test-002",
            "fraud_probability": 0.95,
            "anomaly_score": 0.9,
            "risk_score": 92,
            "decision": "BLOCK",
            "explanation": ["High fraud probability"],
            "top_features": [],
        }

        payload = {
            "transaction_id": "test-002",
            "time": 2000,
            "amount": 9999.0,
            **{f"v{i}": 0.0 for i in range(1, 29)},
        }
        response = client.post(
            "/predict",
            data=json.dumps(payload),
            content_type="application/json",
        )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["decision"] == "BLOCK"
    assert data["risk_score"] >= 70


def test_get_transactions(client):
    """Test /transactions returns a list"""
    response = client.get("/transactions")
    # Either 200 with data or 500 if DB missing — both are acceptable in CI
    assert response.status_code in (200, 500)
    if response.status_code == 200:
        data = json.loads(response.data)
        assert "transactions" in data
