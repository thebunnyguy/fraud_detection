"""
Simple tests for Flask fraud detection API
"""
import json
import pytest
from unittest.mock import Mock, patch
import numpy as np

@pytest.fixture
def client():
    """Create test client"""
    from app import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@patch('app.model')
def test_health_check(mock_model, client):
    """Test health endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'

@patch('app.model')
@patch('app.sqlite3')
def test_score_legitimate_transaction(mock_sqlite, mock_model, client):
    """Test scoring a legitimate transaction"""
    # Mock model prediction
    mock_model.predict_proba.return_value = np.array([[0.85, 0.15]])

    # Mock database
    mock_conn = Mock()
    mock_sqlite.connect.return_value = mock_conn

    response = client.post('/score',
        data=json.dumps({
            'transaction_id': 'test-001',
            'amount': 50.0,
            'time': 1000,
            'v1': -1.3,
            'v2': 0.5
        }),
        content_type='application/json'
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['is_fraud'] is False
    assert data['decision'] == 'APPROVE'
    assert 'fraud_score' in data

@patch('app.model')
@patch('app.sqlite3')
def test_score_fraudulent_transaction(mock_sqlite, mock_model, client):
    """Test scoring a fraudulent transaction"""
    # Mock model prediction
    mock_model.predict_proba.return_value = np.array([[0.1, 0.9]])

    # Mock database
    mock_conn = Mock()
    mock_sqlite.connect.return_value = mock_conn

    response = client.post('/score',
        data=json.dumps({
            'transaction_id': 'test-002',
            'amount': 9999.0,
            'time': 2000,
            'v1': 2.5,
            'v2': -3.0
        }),
        content_type='application/json'
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['is_fraud'] is True
    assert data['decision'] == 'BLOCK'
    assert data['fraud_score'] >= 0.7

@patch('app.sqlite3')
def test_get_transactions(mock_sqlite, client):
    """Test getting transaction history"""
    # Mock database response
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_cursor.fetchall.return_value = [
        ('txn-001', '2026-04-15T10:00:00', 0.15, 0, 50.0),
        ('txn-002', '2026-04-15T10:01:00', 0.92, 1, 9999.0)
    ]
    mock_conn.cursor.return_value = mock_cursor
    mock_sqlite.connect.return_value = mock_conn

    response = client.get('/transactions')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'transactions' in data
    assert data['count'] == 2
