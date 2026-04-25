# Automated Hybrid Credit Card Fraud Detection System

Production-grade fraud detection system combining supervised learning, anomaly detection, and rule-based decisioning with automated risk scoring and explainability.

## Overview

This system transforms basic fraud classification into a multi-layered decision engine:

- **XGBoost** supervised model for known fraud patterns
- **Isolation Forest** anomaly detector for unusual transactions
- **Rule engine** for business logic and escalation
- **Risk scoring** (0-100) combining all signals
- **3-tier decisions**: APPROVE / REVIEW / BLOCK
- **Automated explanations** with feature importance

## Architecture

```
Transaction Input
    ↓
Preprocessing & Validation
    ↓
┌─────────────────────────────────┐
│  Parallel Model Execution       │
│  • XGBoost (fraud probability)  │
│  • Isolation Forest (anomaly)   │
│  • Rule Engine (business logic) │
└─────────────────────────────────┘
    ↓
Risk Scoring Engine
    ↓
Decision Layer (APPROVE/REVIEW/BLOCK)
    ↓
Explanation Generation
    ↓
Response + Logging
```

## Project Structure

```
fraud_detection/
├── app/
│   ├── api/              # API routes and schemas
│   ├── core/             # Configuration and constants
│   │   └── config.py     # Thresholds, paths, weights
│   ├── models/           # ML model wrappers
│   │   ├── loader.py     # Model loading at startup
│   │   ├── predictor.py  # XGBoost wrapper
│   │   ├── anomaly.py    # Isolation Forest wrapper
│   │   ├── risk_engine.py # Risk scoring logic
│   │   ├── rules.py      # Business rules
│   │   └── explainer.py  # Explanation generation
│   └── services/         # Business logic
│       ├── fraud_service.py        # Main orchestration
│       ├── preprocessing_service.py # Feature validation
│       └── logging_service.py      # Event logging
├── training/
│   └── train_models.py   # Train both XGBoost + Isolation Forest
├── artifacts/            # Saved models (generated)
│   ├── xgboost_model.pkl
│   ├── isolation_forest.pkl
│   └── feature_columns.json
├── logs/
│   └── fraud_events.jsonl # Suspicious transaction log
├── templates/
│   └── dashboard_enhanced.html # Frontend UI
├── tests/
│   └── test_fraud_detection_system.py
├── app_main.py           # Flask backend
└── requirements.txt
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Train Models

```bash
python training/train_models.py
```

This trains both XGBoost and Isolation Forest models on `creditcard.csv` and saves artifacts to `artifacts/`.

**Expected output:**
- `artifacts/xgboost_model.pkl`
- `artifacts/isolation_forest.pkl`
- `artifacts/feature_columns.json`

### 3. Run Backend

```bash
python app_main.py
```

Backend runs on `http://localhost:5000`

### 4. Open Dashboard

Navigate to `http://localhost:5000` in your browser.

## API Endpoints

### Health Check
```bash
GET /health
```

Response:
```json
{
  "status": "healthy",
  "models": {
    "xgboost_loaded": true,
    "anomaly_loaded": true,
    "feature_cols_loaded": true
  }
}
```

### Single Prediction
```bash
POST /predict
Content-Type: application/json

{
  "transaction_id": "txn-123",
  "time": 0,
  "amount": 149.62,
  "v1": -1.359,
  "v2": -0.072,
  ...
  "v28": -0.021
}
```

Response:
```json
{
  "transaction_id": "txn-123",
  "fraud_probability": 0.1234,
  "anomaly_score": 0.2345,
  "risk_score": 25,
  "decision": "APPROVE",
  "explanation": [
    "Low fraud probability - transaction appears legitimate",
    "Transaction follows expected patterns",
    "Transaction approved - risk within acceptable limits"
  ],
  "top_features": [
    {"feature": "V14", "impact": "high"},
    {"feature": "V17", "impact": "medium"},
    {"feature": "Amount", "impact": "low"}
  ]
}
```

### Batch Prediction
```bash
POST /predict/batch
Content-Type: application/json

{
  "transactions": [
    {"transaction_id": "txn-1", "time": 0, "amount": 100, ...},
    {"transaction_id": "txn-2", "time": 10, "amount": 5000, ...}
  ]
}
```

### Transaction History
```bash
GET /transactions?limit=100
```

### Demo Samples
```bash
GET /demo-samples
```

Returns preset legitimate and fraudulent transaction samples for testing.

## Risk Scoring Formula

```python
risk_score = 100 * (
    0.65 * fraud_probability +
    0.25 * anomaly_score +
    0.10 * rule_score
)
```

**Weights** (configurable in [app/core/config.py](app/core/config.py)):
- Fraud probability: 65%
- Anomaly score: 25%
- Rule engine: 10%

## Decision Thresholds

| Risk Score | Decision |
|------------|----------|
| 0-39       | APPROVE  |
| 40-69      | REVIEW   |
| 70-100     | BLOCK    |

Thresholds configurable in [app/core/config.py](app/core/config.py).

## Business Rules

Current rules in [app/models/rules.py](app/models/rules.py):

1. **High amount escalation**: Transactions >$5000 boost risk
2. **Zero amount flag**: $0 transactions marked suspicious
3. **Combined signal escalation**: High fraud + high anomaly → escalate
4. **Moderate fraud + strong anomaly**: Triggers review

Rules are honest to available features (no fake location/device logic).

## Model Training Details

### XGBoost
- 300 estimators, max_depth=6
- Handles class imbalance via `scale_pos_weight`
- Trained on 80% of data, evaluated on 20%
- Metrics: ROC-AUC, PR-AUC, precision, recall

### Isolation Forest
- Trained on legitimate transactions only
- Contamination=0.001 (expected fraud rate)
- Detects anomalies via isolation depth
- Scores normalized to [0, 1]

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov=training

# Run specific test
pytest tests/test_fraud_detection_system.py::test_risk_score_calculation -v
```

## Configuration

All configuration in [app/core/config.py](app/core/config.py):

```python
# Decision thresholds
APPROVE_THRESHOLD = 39
REVIEW_THRESHOLD = 69

# Risk scoring weights
RISK_WEIGHT_FRAUD = 0.65
RISK_WEIGHT_ANOMALY = 0.25
RISK_WEIGHT_RULES = 0.10

# Paths
ARTIFACTS_DIR = BASE_DIR / "artifacts"
LOGS_DIR = BASE_DIR / "logs"
```

## Dataset Requirements

Expects Kaggle Credit Card Fraud dataset with columns:
- `Time`, `Amount`, `V1`-`V28`, `Class`

Download:
```bash
kaggle datasets download -d mlg-ulb/creditcardfraud
unzip creditcardfraud.zip
```

Place `creditcard.csv` in project root.

## Logging

Suspicious transactions (REVIEW/BLOCK) logged to `logs/fraud_events.jsonl`:

```json
{"timestamp": "2026-04-23T10:30:00", "transaction_id": "txn-456", "decision": "BLOCK", "risk_score": 85, ...}
```

## Limitations & Honesty

This is a research/demo system based on anonymized PCA features (V1-V28):

- **Not production-ready** for real banking without additional validation
- **No real-world signals** like device fingerprinting, location, velocity
- **Anonymized features** limit interpretability
- **Static thresholds** may need tuning for specific use cases
- **No online learning** or model retraining pipeline

Designed to demonstrate hybrid fraud detection architecture, not replace production systems.

## Metrics & Evaluation

Why accuracy is insufficient for fraud detection:

- **Class imbalance**: ~0.17% fraud rate in dataset
- **Cost asymmetry**: False negatives (missed fraud) more costly than false positives
- **Better metrics**: Precision, Recall, F1, PR-AUC, ROC-AUC

Training script reports all relevant metrics.

## Future Enhancements

Potential improvements (not implemented):

- SHAP values for better explainability
- Model retraining pipeline
- A/B testing framework
- Real-time feature engineering
- Ensemble methods
- Threshold optimization via business cost functions

## Troubleshooting

**Models not loading:**
- Ensure `training/train_models.py` completed successfully
- Check `artifacts/` directory contains `.pkl` files

**Import errors:**
- Verify all dependencies installed: `pip install -r requirements.txt`
- Check Python version ≥3.8

**Frontend not updating:**
- Hard refresh browser (Cmd+Shift+R / Ctrl+Shift+R)
- Check browser console for errors

## License

MIT

## Acknowledgments

- Dataset: [Kaggle Credit Card Fraud Detection](https://www.kaggle.com/mlg-ulb/creditcardfraud)
- XGBoost, scikit-learn, Flask communities
