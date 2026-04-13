"""
model/inference.py
SageMaker inference script for XGBoost model.
Deployed as entry_point in the SKLearn container.

Expects input in CSV format with 30 features (time, amount, v1-v28).
Returns fraud probability score.
"""

import joblib
import numpy as np
import io
import csv


def model_fn(model_dir):
    """
    Load the model from disk. Called once when the endpoint starts.
    """
    model = joblib.load(f"{model_dir}/model.joblib")
    return model


def input_fn(request_body, request_content_type="text/csv"):
    """
    Parse the incoming request. Expects CSV format.
    """
    if request_content_type == "text/csv":
        stream = io.StringIO(request_body)
        reader = csv.reader(stream)
        features = next(reader)
        return np.array([float(f) for f in features]).reshape(1, -1)
    else:
        raise ValueError(f"Unsupported content type: {request_content_type}")


def predict_fn(data, model):
    """
    Generate prediction. Returns fraud probability (score from 0-1).
    """
    # XGBoost's predict_proba returns [prob_legit, prob_fraud]
    probabilities = model.predict_proba(data)
    fraud_prob = probabilities[0, 1]  # probability of fraud class
    return fraud_prob


def output_fn(prediction, content_type="text/csv"):
    """
    Format the output. Returns the fraud probability as a string.
    """
    if content_type == "text/csv":
        return str(prediction)
    else:
        raise ValueError(f"Unsupported content type: {content_type}")
