"""
Local test script for fraud detection API
Run this before deploying to verify everything works
"""
import requests
import json

BASE_URL = "http://localhost:8080"

def test_health():
    """Test health endpoint"""
    print("Testing /health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")
    assert response.status_code == 200

def test_score_legitimate():
    """Test scoring a legitimate transaction"""
    print("Testing legitimate transaction...")
    data = {
        "transaction_id": "test-001",
        "amount": 50.0,
        "time": 1000,
        **{f"v{i}": 0.0 for i in range(1, 29)}
    }
    data["v1"] = -1.3
    data["v2"] = 0.5

    response = requests.post(f"{BASE_URL}/score", json=data)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}\n")
    assert response.status_code == 200
    assert result["is_fraud"] is False

def test_score_fraudulent():
    """Test scoring a fraudulent transaction"""
    print("Testing fraudulent transaction...")
    data = {
        "transaction_id": "test-002",
        "amount": 9999.0,
        "time": 2000,
        **{f"v{i}": 0.0 for i in range(1, 29)}
    }
    data["v1"] = 2.5
    data["v2"] = -3.0

    response = requests.post(f"{BASE_URL}/score", json=data)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}\n")
    assert response.status_code == 200

def test_get_transactions():
    """Test getting transaction history"""
    print("Testing /transactions endpoint...")
    response = requests.get(f"{BASE_URL}/transactions")
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Found {result['count']} transactions\n")
    assert response.status_code == 200

if __name__ == "__main__":
    print("=" * 50)
    print("Fraud Detection API - Local Tests")
    print("=" * 50 + "\n")

    try:
        test_health()
        test_score_legitimate()
        test_score_fraudulent()
        test_get_transactions()

        print("=" * 50)
        print("✅ All tests passed!")
        print("=" * 50)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
