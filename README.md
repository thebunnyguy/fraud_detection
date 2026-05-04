# Fraud Detection System — Oracle Cloud Free Tier

Real-time credit card fraud detection API using a hybrid XGBoost + Isolation Forest ML system, deployed on Oracle Cloud Always Free with Docker and automated CI/CD.

**Cost: $0/month forever** 🎉

---

## Features

- ✅ Hybrid fraud scoring — XGBoost classifier + Isolation Forest anomaly detection
- ✅ Risk engine with three decision outcomes: `APPROVE` / `REVIEW` / `BLOCK`
- ✅ Explanation engine — human-readable reasoning for each decision
- ✅ Batch prediction endpoint
- ✅ Transaction history storage (SQLite)
- ✅ Interactive dashboard UI at `/`
- ✅ Docker containerised deployment (gunicorn)
- ✅ GitHub Actions CI/CD → Oracle Cloud VM

---

## Project Structure

```
.
├── app_main.py                     # Main Flask application entry point
├── app/                            # Core application package
│   ├── core/config.py              # Config (DB path, thresholds)
│   ├── models/
│   │   ├── loader.py               # Model loader (XGBoost + Isolation Forest)
│   │   ├── predictor.py            # XGBoost fraud scorer
│   │   ├── anomaly.py              # Isolation Forest anomaly detector
│   │   ├── risk_engine.py          # Risk score calculation + decision logic
│   │   ├── rules.py                # Hard-coded rule overrides
│   │   └── explainer.py            # Human-readable explanation generator
│   └── services/
│       ├── fraud_service.py        # Orchestrates full prediction pipeline
│       ├── preprocessing_service.py# Feature validation + extraction
│       └── logging_service.py      # Suspicious transaction logging
├── artifacts/
│   ├── xgboost_model.pkl           # Trained XGBoost model
│   ├── isolation_forest.pkl        # Trained Isolation Forest model
│   └── feature_columns.json        # Feature column order
├── templates/
│   └── dashboard.html              # Frontend dashboard UI
├── training/
│   └── train_models.py             # Training script (produces artifacts/)
├── tests/
│   ├── test_app.py                 # Flask endpoint tests
│   └── test_fraud_detection_system.py  # Unit tests for app/ modules
├── Dockerfile                      # Docker container (gunicorn app_main:app)
├── requirements.txt                # Python dependencies
├── start.sh                        # Local dev startup script
└── .github/workflows/
    └── oracle-deploy.yml           # CI/CD: test → build → deploy to Oracle Cloud
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Train models (if not using pre-trained artifacts)

Pre-trained models are included in `artifacts/`. To retrain from scratch:

```bash
# Requires creditcard.csv from Kaggle:
# https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
python training/train_models.py
```

### 3. Run locally

```bash
# Option A: shell script
bash start.sh

# Option B: Flask dev server
PYTHONPATH=. python app_main.py

# Option C: gunicorn (mirrors production)
gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 120 app_main:app
```

### 4. Run tests

```bash
PYTHONPATH=. pytest tests/ -v
```

### 5. Deploy to Oracle Cloud

Follow [ORACLE_SETUP.md](ORACLE_SETUP.md) for full provisioning steps.

**Summary:**
1. Create Oracle Cloud account (Always Free tier)
2. Provision Ubuntu VM (`VM.Standard.E2.1.Micro`)
3. Add GitHub Secrets: `ORACLE_SSH_KEY`, `ORACLE_HOST`, `ORACLE_USER`
4. Push to `main` → GitHub Actions auto-builds Docker image and deploys

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Interactive dashboard UI |
| `GET` | `/health` | Health check — model load status |
| `POST` | `/predict` | Score a single transaction |
| `POST` | `/predict/batch` | Score multiple transactions |
| `GET` | `/transactions` | Transaction history (`?limit=N`) |
| `GET` | `/demo-samples` | Preset low/medium/high risk samples |

### POST `/predict`

**Request:**
```json
{
  "transaction_id": "txn-001",
  "time": 0,
  "amount": 149.62,
  "v1": -1.359,
  "v2": -0.072,
  "...": "...",
  "v28": -0.021
}
```

**Response:**
```json
{
  "transaction_id": "txn-001",
  "fraud_probability": 0.0412,
  "anomaly_score": 0.1823,
  "risk_score": 18,
  "decision": "APPROVE",
  "explanation": ["Low fraud probability (4.1%)", "Normal spending pattern"],
  "top_features": []
}
```

Decisions: `APPROVE` (risk < 40) · `REVIEW` (40–69) · `BLOCK` (≥ 70)

### GET `/health`

```json
{
  "status": "healthy",
  "models": {
    "xgboost": true,
    "isolation_forest": true,
    "feature_columns": true
  }
}
```

### POST `/predict/batch`

```json
{
  "transactions": [
    { "transaction_id": "txn-1", "time": 0, "amount": 50.0, "v1": 0.0, "...": "..." },
    { "transaction_id": "txn-2", "time": 10, "amount": 5000.0, "v1": -2.3, "...": "..." }
  ]
}
```

---

## Architecture

```
┌─────────────┐
│   GitHub    │
│   Actions   │ ← Push to main
└──────┬──────┘
       │ CI/CD: test → build Docker → deploy via SSH
       ↓
┌──────────────────────────────────────┐
│       Oracle Cloud Free VM           │
│       (Ubuntu + Docker)              │
│                                      │
│  ┌────────────────────────────────┐  │
│  │  gunicorn app_main:app         │  │
│  │  ├── XGBoost fraud scorer      │  │
│  │  ├── Isolation Forest anomaly  │  │
│  │  ├── Risk engine + rules       │  │
│  │  ├── SQLite transaction store  │  │
│  │  └── Dashboard UI (/)          │  │
│  └────────────────────────────────┘  │
│  Port 8080 (public)                  │
└──────────────────────────────────────┘
```

**Prediction pipeline:**

```
Request → PreprocessingService (validate + extract features)
        → FraudPredictor (XGBoost probability)
        → AnomalyDetector (Isolation Forest score)
        → RuleEngine (hard-coded overrides)
        → RiskEngine (weighted risk score + decision)
        → FraudExplainer (human-readable explanation)
        → Response
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `5000` | Flask dev server port |
| `FRAUD_THRESHOLD` | `0.7` | Score threshold for BLOCK decision |
| `DB_PATH` | `fraud_transactions.db` | SQLite database path |

---

## CI/CD Pipeline

Workflow: `.github/workflows/oracle-deploy.yml`

1. **Test** — `PYTHONPATH=. pytest tests/test_app.py -v` (every push/PR)
2. **Build** — Docker image built and saved as artifact (main branch only)
3. **Deploy** — SSH to Oracle Cloud VM, load image, restart container

### Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `ORACLE_SSH_KEY` | Private SSH key for VM access |
| `ORACLE_HOST` | VM public IP address |
| `ORACLE_USER` | SSH username (usually `ubuntu`) |

---

## Model Details

- **Dataset**: Kaggle Credit Card Fraud Detection (284,807 transactions, 492 fraudulent)
- **XGBoost**: Binary classifier, `scale_pos_weight` for class imbalance
- **Isolation Forest**: Unsupervised anomaly detection
- **Features**: 30 features (`time`, `amount`, `v1`–`v28`)
- **Training**: `training/train_models.py`

---

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues.

```bash
# Container logs
ssh ubuntu@YOUR_VM_IP docker logs fraud-api

# Health check from VM
curl http://localhost:8080/health

# Re-run tests locally
PYTHONPATH=. pytest tests/ -v
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| ML Models | XGBoost 2.0, scikit-learn Isolation Forest |
| API | Flask 3.0, gunicorn |
| Database | SQLite |
| Container | Docker |
| CI/CD | GitHub Actions |
| Hosting | Oracle Cloud Always Free |
| Python | 3.11 |

---

## License

MIT
