# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Real-time fraud detection system using XGBoost ML model deployed on AWS with automated CI/CD. The system scores credit card transactions via API Gateway → Lambda → SageMaker, stores results in DynamoDB, and sends SNS alerts for fraudulent transactions.

**Tech Stack**: Python 3.11, XGBoost, AWS Lambda, SageMaker, DynamoDB, SNS, API Gateway, GitHub Actions

**Region**: ap-south-1 (Mumbai)

## Development Commands

### Testing
```bash
# Run all tests with coverage
PYTHONPATH=lambda pytest tests/ -v

# Run specific test
PYTHONPATH=lambda pytest tests/test_fraud_handler.py::test_fraudulent_transaction -v

# Lint code
flake8 lambda/ --max-line-length=100 --ignore=E501,W503
```

### Model Training & Deployment
```bash
# Train model and deploy to SageMaker (run once, takes ~5-7 minutes)
python model/train_and_deploy.py

# Check endpoint status
aws sagemaker describe-endpoint --endpoint-name fraud-xgb-endpoint --region ap-south-1 --query EndpointStatus

# Delete endpoint to stop billing
aws sagemaker delete-endpoint --endpoint-name fraud-xgb-endpoint
```

### AWS Infrastructure
```bash
# Bootstrap all AWS resources (run once before first deployment)
python scripts/bootstrap_aws.py

# Test Lambda locally (after deployment)
aws lambda invoke \
  --function-name fraud-handler \
  --payload '{"body": "{\"transaction_id\":\"test-001\",\"amount\":50,\"time\":1000,\"v1\":-1.3,\"v2\":0.5}"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/response.json

# View Lambda logs
aws logs tail /aws/lambda/fraud-handler --follow --region ap-south-1
```

## Architecture

### Data Flow
1. **API Gateway** receives POST to `/score` endpoint with transaction JSON
2. **Lambda** (`lambda/fraud_handler.py`) extracts features in correct order
3. **SageMaker** XGBoost endpoint scores transaction (returns 0-1 probability)
4. **DynamoDB** stores transaction result in `fraud-transactions` table
5. **SNS** publishes alert to `fraud-alerts` topic if score ≥ threshold (default 0.7)

### Key Components

**Lambda Handler** (`lambda/fraud_handler.py`)
- Entry point: `lambda_handler(event, context)`
- Expects 30 features in specific order: `time, amount, v1-v28`
- Environment variables: `SAGEMAKER_ENDPOINT`, `DYNAMODB_TABLE`, `SNS_TOPIC_ARN`, `FRAUD_THRESHOLD`
- Returns JSON with `transaction_id`, `fraud_score`, `is_fraud`, `decision`

**SageMaker Inference** (`model/inference.py`)
- Custom inference script for sklearn container
- Functions: `model_fn()`, `input_fn()`, `predict_fn()`, `output_fn()`
- Accepts CSV input, returns fraud probability as string

**Model Training** (`model/train_and_deploy.py`)
- Trains XGBoost on Kaggle credit card fraud dataset
- Uses `scale_pos_weight` to handle class imbalance
- Packages model with inference code into `model.tar.gz`
- Deploys to SageMaker endpoint using sklearn container

**Bootstrap Script** (`scripts/bootstrap_aws.py`)
- Creates: S3 bucket, DynamoDB table, SNS topic, IAM role, Lambda function, API Gateway
- Bucket naming: `fraud-detection-artifacts-{ACCOUNT_ID}`
- Sets up Lambda with placeholder code (CI/CD updates it)

### CI/CD Pipeline (`.github/workflows/deploy.yml`)

**Trigger**: Push to `main` or PR

**Jobs**:
1. **Test**: Lint with flake8, run pytest with mocked AWS services
2. **Build**: Install dependencies, zip Lambda package, upload to S3
3. **Deploy**: Update Lambda code, set environment variables, smoke test, SNS notification

**Required GitHub Secrets**:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `SAGEMAKER_ENDPOINT_NAME` (should be `fraud-xgb-endpoint`)
- `SNS_TOPIC_ARN`

## Important Constraints

### Feature Order is Critical
The model expects features in this exact order: `["time", "amount", "v1", "v2", ..., "v28"]`

Both `lambda/fraud_handler.py` and `model/train_and_deploy.py` define `FEATURE_COLS` - these MUST match. Any change to feature order requires retraining and redeploying the model.

### AWS Resource Naming
- S3 bucket suffix is AWS account ID, not GitHub username
- Lambda function name: `fraud-handler`
- DynamoDB table: `fraud-transactions`
- SNS topic: `fraud-alerts`
- SageMaker endpoint: `fraud-xgb-endpoint`

### Testing Approach
Tests use `unittest.mock` to mock AWS services (`sagemaker_runtime`, `dynamodb`, `sns_client`). Tests verify:
- Legitimate transactions (score < threshold) → APPROVE, no SNS
- Fraudulent transactions (score ≥ threshold) → BLOCK, SNS fired
- DynamoDB write happens for every transaction
- Error handling for malformed requests

### SageMaker Container
Uses sklearn container: `720646828776.dkr.ecr.ap-south-1.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3`

The container expects:
- Model artifact: `model.tar.gz` containing `model.joblib` and `code/inference.py`
- Environment variables: `SAGEMAKER_PROGRAM=inference.py`, `SAGEMAKER_SUBMIT_DIRECTORY=<s3_uri>`

## Common Gotchas

1. **IAM Role Trust Policy**: The `fraud-lambda-role` must trust both `lambda.amazonaws.com` and `sagemaker.amazonaws.com`. The bootstrap script handles Lambda, but `train_and_deploy.py` adds SageMaker trust.

2. **Dataset Location**: `train_and_deploy.py` looks for `creditcard.csv` in both `model/` directory and project root. Download from Kaggle: `kaggle datasets download -d mlg-ulb/creditcardfraud`

3. **Lambda Package Size**: Dependencies are installed to `lambda/package/` then zipped. Keep `lambda/requirements.txt` minimal (currently just boto3).

4. **Endpoint Deployment Time**: SageMaker endpoint creation/update takes 5-7 minutes. Use `aws sagemaker describe-endpoint` to check status.

5. **Free Tier Limits**: SageMaker ml.t2.medium is free for 250 hours over 2 months. Delete endpoint when not in use to avoid charges.

## File Structure
```
lambda/
  fraud_handler.py       # Lambda entry point
  requirements.txt       # Lambda dependencies (boto3)
model/
  train_and_deploy.py    # Train XGBoost, deploy to SageMaker
  inference.py           # SageMaker inference script
scripts/
  bootstrap_aws.py       # One-time AWS infrastructure setup
tests/
  test_fraud_handler.py  # Unit tests with mocked AWS
.github/workflows/
  deploy.yml             # CI/CD pipeline
```
