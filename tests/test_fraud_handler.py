"""
tests/test_fraud_handler.py
Run with: pytest tests/ -v
"""

import json
import os
import pytest
from unittest.mock import MagicMock, patch

# Set env vars before importing the handler
os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")
os.environ.setdefault("SAGEMAKER_ENDPOINT", "fraud-xgb-endpoint")
os.environ.setdefault("DYNAMODB_TABLE", "fraud-transactions")
os.environ.setdefault("SNS_TOPIC_ARN", "arn:aws:sns:ap-south-1:123456789:fraud-alerts")
os.environ.setdefault("FRAUD_THRESHOLD", "0.7")


def _make_event(body: dict) -> dict:
    return {"body": json.dumps(body)}


def _make_context():
    ctx = MagicMock()
    ctx.aws_request_id = "test-request-id"
    return ctx


@patch("fraud_handler.sns_client")
@patch("fraud_handler.dynamodb")
@patch("fraud_handler.sagemaker_runtime")
def test_legitimate_transaction(mock_sm, mock_dynamo, mock_sns):
    """Score below threshold → APPROVE, no SNS."""
    mock_sm.invoke_endpoint.return_value = {
        "Body": MagicMock(read=lambda: b"0.12")
    }
    mock_dynamo.Table.return_value.put_item = MagicMock()

    from fraud_handler import lambda_handler

    event = _make_event({
        "transaction_id": "txn-001",
        "amount": 25.0,
        "time": 100,
    })
    response = lambda_handler(event, _make_context())
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["is_fraud"] is False
    assert body["decision"] == "APPROVE"
    mock_sns.publish.assert_not_called()


@patch("fraud_handler.sns_client")
@patch("fraud_handler.dynamodb")
@patch("fraud_handler.sagemaker_runtime")
def test_fraudulent_transaction(mock_sm, mock_dynamo, mock_sns):
    """Score above threshold → BLOCK + SNS fired."""
    mock_sm.invoke_endpoint.return_value = {
        "Body": MagicMock(read=lambda: b"0.92")
    }
    mock_dynamo.Table.return_value.put_item = MagicMock()
    mock_sns.publish = MagicMock()

    from fraud_handler import lambda_handler

    event = _make_event({
        "transaction_id": "txn-002",
        "amount": 9999.0,
        "time": 200,
    })
    response = lambda_handler(event, _make_context())
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["is_fraud"] is True
    assert body["decision"] == "BLOCK"
    mock_sns.publish.assert_called_once()


@patch("fraud_handler.sagemaker_runtime")
def test_bad_request_returns_400(mock_sm):
    """Malformed body → 400."""
    mock_sm.invoke_endpoint.side_effect = Exception("unexpected")

    from fraud_handler import lambda_handler

    event = {"body": "{malformed json"}
    response = lambda_handler(event, _make_context())
    assert response["statusCode"] in (400, 500)


@patch("fraud_handler.sns_client")
@patch("fraud_handler.dynamodb")
@patch("fraud_handler.sagemaker_runtime")
def test_dynamodb_write_called(mock_sm, mock_dynamo, mock_sns):
    """Ensure every transaction is persisted to DynamoDB."""
    mock_sm.invoke_endpoint.return_value = {
        "Body": MagicMock(read=lambda: b"0.05")
    }
    mock_table = MagicMock()
    mock_dynamo.Table.return_value = mock_table

    from fraud_handler import lambda_handler

    event = _make_event({"transaction_id": "txn-003", "amount": 100.0})
    lambda_handler(event, _make_context())

    mock_table.put_item.assert_called_once()
    call_args = mock_table.put_item.call_args[1]["Item"]
    assert call_args["transaction_id"] == "txn-003"
