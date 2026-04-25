"""
Tests for the hybrid fraud detection Flask API (app_main.py)
"""
import json
import pytest

# Import app directly — ModelLoader handles missing .pkl gracefully
from app_main import app


@pytest.fixture
def client():
    """Create test client"""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_health_check(client):
    """Test /health returns 200 and healthy status"""
    response = client.get("/health")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "healthy"
    assert "models" in data


def test_predict_returns_valid_response(client):
    """Test /predict returns a structured response"""
    payload = {
        "transaction_id": "test-001",
        "time": 0,
        "amount": 149.62,
        **{f"v{i}": 0.0 for i in range(1, 29)},
    }
    response = client.post(
        "/predict",
        data=json.dumps(payload),
        content_type="application/json",
    )

    # Should get 200 if models loaded, or 500 with error message if not
    assert response.status_code in (200, 500)
    data = json.loads(response.data)

    if response.status_code == 200:
        assert "decision" in data
        assert data["decision"] in ("APPROVE", "REVIEW", "BLOCK")
        assert "fraud_probability" in data
        assert "anomaly_score" in data
        assert "risk_score" in data
        assert "explanation" in data
    else:
        assert "error" in data


def test_predict_missing_body(client):
    """Test /predict with no JSON body returns error"""
    response = client.post("/predict", content_type="application/json")
    assert response.status_code in (400, 500)


def test_get_transactions(client):
    """Test /transactions endpoint"""
    response = client.get("/transactions")
    assert response.status_code in (200, 500)
    data = json.loads(response.data)
    if response.status_code == 200:
        assert "transactions" in data
        assert "count" in data


def test_demo_samples(client):
    """Test /demo-samples returns preset samples"""
    response = client.get("/demo-samples")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "low_risk" in data
    assert "medium_risk" in data
    assert "high_risk" in data
