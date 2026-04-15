#!/bin/bash
# scripts/create_lambda_layer.sh
# Creates a Lambda layer with XGBoost and scikit-learn dependencies

set -e

REGION="ap-south-1"
LAYER_NAME="fraud-detection-ml-layer"

echo "Creating Lambda layer with ML dependencies..."

# Create layer directory structure
mkdir -p layer/python

# Install dependencies into layer using pre-built wheels
# Use Python 3.11 compatible versions for Lambda
pip install \
  xgboost==2.0.3 \
  scikit-learn==1.5.2 \
  joblib==1.3.2 \
  numpy==2.1.0 \
  --only-binary=:all: \
  --python-version 3.11 \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --abi cp311 \
  -t layer/python/

# Zip the layer
cd layer
zip -r ../ml-layer.zip python/
cd ..

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Upload to S3
BUCKET="fraud-detection-artifacts-${ACCOUNT_ID}"
aws s3 cp ml-layer.zip s3://${BUCKET}/layers/ml-layer.zip --region ${REGION}

# Publish Lambda layer
LAYER_VERSION=$(aws lambda publish-layer-version \
  --layer-name ${LAYER_NAME} \
  --description "XGBoost, scikit-learn, numpy, joblib for fraud detection" \
  --content S3Bucket=${BUCKET},S3Key=layers/ml-layer.zip \
  --compatible-runtimes python3.11 \
  --region ${REGION} \
  --query 'Version' \
  --output text)

echo "✅ Layer published: ${LAYER_NAME} version ${LAYER_VERSION}"
echo "Layer ARN: arn:aws:lambda:${REGION}:${ACCOUNT_ID}:layer:${LAYER_NAME}:${LAYER_VERSION}"
echo ""
echo "Next steps:"
echo "1. Add this layer ARN to your Lambda function"
echo "2. Remove xgboost, scikit-learn, numpy, joblib from lambda/requirements.txt"
echo "3. Redeploy Lambda"
