"""
fraud_handler.py — Lambda entry point for real-time fraud scoring.
Invoked by API Gateway, loads XGBoost model from Lambda package,
writes result to DynamoDB, and fires SNS if fraud detected.
"""

import json
import os
import boto3
import logging
import joblib
import numpy as np
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Clients (initialised outside handler for Lambda warm-start reuse)
dynamodb = boto3.resource("dynamodb")
sns_client = boto3.client("sns")

TABLE_NAME = os.environ["DYNAMODB_TABLE"]
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]
FRAUD_THRESHOLD = float(os.environ.get("FRAUD_THRESHOLD", "0.7"))

# Feature order expected by the XGBoost model (Kaggle credit card dataset)
FEATURE_COLS = ["time", "amount"] + [f"v{i}" for i in range(1, 29)]

# Load model once at cold start (reused across warm invocations)
model = None

def load_model():
    """Load XGBoost model from Lambda package."""
    global model
    if model is None:
        # Model is packaged in Lambda zip at root level
        model = joblib.load("fraud_model.pkl")
        logger.info("Model loaded successfully")
    return model


def lambda_handler(event, context):
    try:
        # Load model on first invocation
        clf = load_model()

        body = json.loads(event.get("body", "{}"))
        transaction_id = body.get("transaction_id", context.aws_request_id)

        # Build feature vector in correct order
        features = [body.get(col, 0.0) for col in FEATURE_COLS]
        X = np.array(features).reshape(1, -1)

        # --- Score with local model ---
        fraud_prob = clf.predict_proba(X)[0, 1]  # probability of fraud class
        score = float(fraud_prob)
        is_fraud = score >= FRAUD_THRESHOLD

        logger.info(json.dumps({
            "transaction_id": transaction_id,
            "fraud_score": score,
            "is_fraud": is_fraud,
        }))

        # --- Write to DynamoDB ---
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(Item={
            "transaction_id": transaction_id,
            "timestamp": datetime.utcnow().isoformat(),
            "fraud_score": str(round(score, 4)),
            "is_fraud": is_fraud,
            "amount": str(body.get("amount", 0)),
        })

        # --- Alert via SNS if fraud ---
        if is_fraud:
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject="🚨 Fraud Detected",
                Message=(
                    f"Transaction {transaction_id} flagged as FRAUD.\n"
                    f"Score: {score:.4f}  |  Amount: ${body.get('amount', 'N/A')}\n"
                    f"Timestamp: {datetime.utcnow().isoformat()}"
                ),
            )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "transaction_id": transaction_id,
                "fraud_score": round(score, 4),
                "is_fraud": is_fraud,
                "decision": "BLOCK" if is_fraud else "APPROVE",
            }),
        }

    except KeyError as e:
        logger.error(f"Missing field: {e}")
        return {"statusCode": 400, "body": json.dumps({"error": f"Missing field: {e}"})}
    except Exception as e:
        logger.error(f"Unhandled error: {e}", exc_info=True)
        return {"statusCode": 500, "body": json.dumps({"error": "Internal server error"})}
