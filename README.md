# Fraud Detection System — CI/CD on AWS

Real-time transaction fraud scoring using XGBoost + AWS Lambda,  
deployed automatically via GitHub Actions on every push to `main`.

---

## Architecture

```
GitHub Push
    │
    ├─ [Test] pytest + flake8
    ├─ [Build] zip Lambda package → upload to S3
    └─ [Deploy] aws lambda update-function-code → smoke test → SNS notify
                            │
                    API Gateway (REST)
                            │
                       Lambda (Python 3.11)
                       ├─ SageMaker XGBoost endpoint  ← scores transaction
                       ├─ DynamoDB                    ← stores result
                       └─ SNS                         ← alerts if fraud
```

---

## One-time setup (do this before first push)

### 1. Clone and install
```bash
git clone https://github.com/YOUR_USERNAME/fraud-detection.git
cd fraud-detection
pip install boto3 sagemaker xgboost scikit-learn pandas
```

### 2. Configure AWS CLI
```bash
aws configure
# Enter: Access Key, Secret Key, Region (ap-south-1), output (json)
```

### 3. Bootstrap AWS infrastructure
```bash
python scripts/bootstrap_aws.py
```
This creates: S3 bucket, DynamoDB table, SNS topic, IAM role, Lambda function, API Gateway endpoint.

### 4. Train model & deploy SageMaker endpoint
```bash
# Download dataset first
kaggle datasets download -d mlg-ulb/creditcardfraud
unzip creditcard.csv.zip

python model/train_and_deploy.py
```
Takes ~5 minutes to deploy. Note the endpoint name: `fraud-xgb-endpoint`.

### 5. Add GitHub Secrets
Go to your repo → **Settings → Secrets and variables → Actions**:

| Secret | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | Your IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | Your IAM user secret key |
| `SAGEMAKER_ENDPOINT_NAME` | `fraud-xgb-endpoint` |
| `SNS_TOPIC_ARN` | Printed by bootstrap script |

### 6. Push — pipeline triggers automatically
```bash
git add .
git commit -m "Initial fraud detection system"
git push origin main
```

---

## Testing the live endpoint

```bash
curl -X POST https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/prod/score \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "test-001",
    "amount": 9999.99,
    "time": 50000,
    "v1": -3.5, "v2": 2.1, "v3": -4.2,
    "v4": 1.8, "v5": -0.9, "v6": 0.3,
    "v7": -3.1, "v8": 0.6, "v9": -0.7,
    "v10": -2.8, "v11": 1.4, "v12": -5.1,
    "v13": 0.2, "v14": -4.7, "v15": 0.5,
    "v16": -0.8, "v17": -3.9, "v18": -0.4,
    "v19": 0.1, "v20": 0.3, "v21": 0.7,
    "v22": -0.2, "v23": 0.0, "v24": -0.5,
    "v25": 0.4, "v26": 0.1, "v27": 0.0, "v28": 0.05
  }'
```

Expected response:
```json
{
  "transaction_id": "test-001",
  "fraud_score": 0.9231,
  "is_fraud": true,
  "decision": "BLOCK"
}
```

---

## Project structure

```
fraud-detection/
├── .github/
│   └── workflows/
│       └── deploy.yml          ← CI/CD pipeline
├── lambda/
│   ├── fraud_handler.py        ← Lambda entry point
│   └── requirements.txt
├── model/
│   ├── train_and_deploy.py     ← Train XGBoost + deploy endpoint
│   └── inference.py            ← SageMaker inference script
├── scripts/
│   └── bootstrap_aws.py        ← One-time AWS infra setup
├── tests/
│   └── test_fraud_handler.py   ← Unit tests (mocked AWS)
└── README.md
```

---

## AWS Free Tier usage

| Service | Free Tier | This project uses |
|---|---|---|
| Lambda | 1M requests/month | ~100 test calls |
| API Gateway | 1M calls/month | ~100 test calls |
| DynamoDB | 25GB, 200M requests | < 1MB |
| SNS | 1M publishes | < 100 |
| S3 | 5GB | < 50MB |
| SageMaker | 250hr ml.t2.medium (2 months) | 1 endpoint |

**Cost: $0** within free tier limits. Delete the SageMaker endpoint when not in use to avoid charges after the free tier expires.

```bash
# Delete endpoint to stop billing
aws sagemaker delete-endpoint --endpoint-name fraud-xgb-endpoint
```
