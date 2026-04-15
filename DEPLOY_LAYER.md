# Lambda Layer Deployment Instructions

The Lambda layer zip file has been created successfully: `ml-layer.zip` (365MB)

## Step 1: Upload Layer to S3 and Publish

Run these commands in your terminal (AWS credentials must be configured):

```bash
# Get your AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account ID: $ACCOUNT_ID"

# Set S3 bucket name
BUCKET="fraud-detection-artifacts-${ACCOUNT_ID}"
echo "S3 Bucket: $BUCKET"

# Upload layer zip to S3
aws s3 cp ml-layer.zip s3://${BUCKET}/layers/ml-layer.zip --region ap-south-1

# Publish Lambda layer
LAYER_VERSION=$(aws lambda publish-layer-version \
  --layer-name fraud-detection-ml-layer \
  --description "XGBoost, scikit-learn, numpy, joblib for fraud detection" \
  --content S3Bucket=${BUCKET},S3Key=layers/ml-layer.zip \
  --compatible-runtimes python3.11 \
  --region ap-south-1 \
  --query 'Version' \
  --output text)

echo "✅ Layer published: fraud-detection-ml-layer version ${LAYER_VERSION}"
echo "Layer ARN: arn:aws:lambda:ap-south-1:${ACCOUNT_ID}:layer:fraud-detection-ml-layer:${LAYER_VERSION}"
```

## Step 2: Attach Layer to Lambda Function

After publishing the layer, attach it to your Lambda function:

```bash
# Get account ID and construct layer ARN
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
LAYER_ARN="arn:aws:lambda:ap-south-1:${ACCOUNT_ID}:layer:fraud-detection-ml-layer:1"

# Attach layer to Lambda function
aws lambda update-function-configuration \
  --function-name fraud-handler \
  --layers ${LAYER_ARN} \
  --region ap-south-1

# Wait for update to complete
aws lambda wait function-updated \
  --function-name fraud-handler \
  --region ap-south-1

echo "✅ Layer attached to fraud-handler Lambda function"
```

## Step 3: Commit and Push Changes

After the layer is attached, commit and push all code changes:

```bash
git add .
git commit -m "Add Lambda layer support to reduce package size below 70MB"
git push origin main
```

## What Changed

1. **Lambda layer created** with ML dependencies (xgboost, scikit-learn, numpy, joblib)
2. **lambda/requirements.txt** reduced to just boto3/botocore
3. **lambda/fraud_handler.py** updated to load model from local package
4. **.github/workflows/deploy.yml** updated to attach layer during deployment
5. **tests/test_fraud_handler.py** updated to mock local model loading

## Expected Results

- Lambda package size will be ~5-10MB (down from >70MB)
- Layer provides ML dependencies at runtime
- GitHub Actions deployment will succeed
- No functionality changes - same fraud detection logic
