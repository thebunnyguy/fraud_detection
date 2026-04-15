# Fraud Detection System - Oracle Cloud Free Tier

Real-time fraud detection API using XGBoost ML model, deployed on Oracle Cloud Always Free tier with automated CI/CD.

**Cost: $0/month forever** 🎉

## Features

- ✅ Real-time fraud scoring API (Flask + XGBoost)
- ✅ Transaction history storage (SQLite)
- ✅ Docker containerized deployment
- ✅ GitHub Actions CI/CD pipeline
- ✅ Completely free infrastructure (Oracle Cloud Always Free)

## Quick Start

### 1. Train the Model Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Train model (creates fraud_model.pkl)
python model/train_model.py
```

### 2. Test Locally

```bash
# Build and run Docker container
docker build -t fraud-detection-api .
docker run -p 8080:8080 fraud-detection-api

# In another terminal, run tests
pip install requests
python test_local.py
```

### 3. Deploy to Oracle Cloud

Follow the complete setup guide: [ORACLE_SETUP.md](ORACLE_SETUP.md)

**Summary:**
1. Create Oracle Cloud account (always free tier)
2. Provision Ubuntu VM (VM.Standard.E2.1.Micro)
3. Configure GitHub secrets (SSH key, host, user)
4. Push to main branch → auto-deploy via GitHub Actions

## API Endpoints

### Health Check
```bash
curl http://YOUR_VM_IP:8080/health
```

### Score Transaction
```bash
curl -X POST http://YOUR_VM_IP:8080/score \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "txn-001",
    "amount": 50.0,
    "time": 1000,
    "v1": -1.3,
    "v2": 0.5,
    ...
  }'
```

Response:
```json
{
  "transaction_id": "txn-001",
  "fraud_score": 0.1234,
  "is_fraud": false,
  "decision": "APPROVE"
}
```

### Get Transaction History
```bash
curl http://YOUR_VM_IP:8080/transactions?limit=10
```

## Architecture

```
┌─────────────┐
│   GitHub    │
│   Actions   │ ← Push to main
└──────┬──────┘
       │ CI/CD Pipeline
       ↓
┌─────────────────────────────┐
│   Oracle Cloud Free VM      │
│  (Ubuntu + Docker)          │
│                             │
│  ┌───────────────────────┐  │
│  │  Flask API            │  │
│  │  + XGBoost Model      │  │
│  │  + SQLite DB          │  │
│  └───────────────────────┘  │
│                             │
│  Port 8080 (Public)         │
└─────────────────────────────┘
```

## Project Structure

```
.
├── app.py                      # Flask API application
├── Dockerfile                  # Docker container config
├── requirements.txt            # Python dependencies
├── fraud_model.pkl            # Trained XGBoost model
├── model/
│   └── train_model.py         # Model training script
├── tests/
│   └── test_app.py            # API unit tests
├── test_local.py              # Local integration tests
├── .github/workflows/
│   └── oracle-deploy.yml      # CI/CD pipeline
├── ORACLE_SETUP.md            # Complete setup guide
└── README.md                  # This file
```

## Development

### Run Tests
```bash
pytest tests/ -v
```

### Local Development
```bash
# Run Flask directly (for development)
python app.py

# Or with Docker
docker build -t fraud-detection-api .
docker run -p 8080:8080 fraud-detection-api
```

### Environment Variables
- `PORT`: API port (default: 8080)
- `FRAUD_THRESHOLD`: Fraud score threshold (default: 0.7)
- `DB_PATH`: SQLite database path (default: fraud_transactions.db)
- `MODEL_PATH`: Model file path (default: fraud_model.pkl)

## CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/oracle-deploy.yml`):

1. **Test**: Run pytest on every push/PR
2. **Build**: Create Docker image (only on main branch)
3. **Deploy**: SSH to Oracle Cloud VM and deploy container

### Required GitHub Secrets
- `ORACLE_SSH_KEY`: Private SSH key for VM access
- `ORACLE_HOST`: VM public IP address
- `ORACLE_USER`: SSH username (usually `ubuntu`)

## Cost Breakdown

| Service | Cost |
|---------|------|
| Oracle Cloud VM (Always Free) | $0 |
| Oracle Cloud Storage (200GB) | $0 |
| GitHub Actions (2000 min/month) | $0 |
| **Total** | **$0/month** |

## Tech Stack

- **ML Model**: XGBoost 2.0.3
- **API Framework**: Flask 3.0.0
- **Database**: SQLite
- **Container**: Docker
- **CI/CD**: GitHub Actions
- **Hosting**: Oracle Cloud Always Free Tier
- **Python**: 3.11

## Model Details

- **Dataset**: Kaggle Credit Card Fraud Detection
- **Algorithm**: XGBoost Classifier
- **Features**: 30 features (time, amount, v1-v28)
- **Threshold**: 0.7 (configurable)
- **Training**: See `model/train_model.py`

## Troubleshooting

### Container not starting
```bash
ssh ubuntu@YOUR_VM_IP
docker logs fraud-api
```

### API not responding
```bash
# Check if container is running
docker ps

# Check firewall
sudo ufw status

# Test from VM itself
curl http://localhost:8080/health
```

### Deployment failed
- Check GitHub Actions logs
- Verify GitHub secrets are set correctly
- Ensure VM is running and accessible

## Next Steps

- [ ] Add authentication (API keys, JWT)
- [ ] Add email/SMS alerts for fraud detection
- [ ] Create web dashboard for monitoring
- [ ] Add rate limiting
- [ ] Set up monitoring with Grafana Cloud (free tier)

## License

MIT
