#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# run_all.sh  — Complete fraud detection project setup
# Run from project root: bash run_all.sh 2>&1 | tee run_all.log
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

source venv/bin/activate
export AWS_DEFAULT_REGION=ap-south-1

# ── Fix libomp path for Intel Macs (Homebrew installs to /usr/local, not /opt/homebrew) ──
if [ -f "/usr/local/opt/libomp/lib/libomp.dylib" ]; then
    export DYLD_LIBRARY_PATH="/usr/local/opt/libomp/lib:${DYLD_LIBRARY_PATH:-}"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  FRAUD DETECTION — FULL SETUP SCRIPT"
echo "  $(date)"
echo "═══════════════════════════════════════════════════════════"

# ── Sanity: confirm AWS credentials ─────────────────────────────
echo ""
echo "▶  [0] Verifying AWS credentials..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "   ✅ AWS Account: $ACCOUNT_ID"
BUCKET="fraud-detection-artifacts-${ACCOUNT_ID}"

# ── Generate dataset if creditcard.csv is missing ───────────────
echo ""
echo "▶  [1] Checking for creditcard.csv..."
if [ ! -f "creditcard.csv" ]; then
    echo "   creditcard.csv not found — generating synthetic dataset..."
    python create_sample_data.py
    echo "   ✅ Synthetic creditcard.csv created"
else
    ROWS=$(python -c "import csv; r=open('creditcard.csv'); print(sum(1 for _ in csv.reader(r))-1)")
    echo "   ✅ creditcard.csv exists ($ROWS rows)"
fi

# ── Task 1: Train model and deploy SageMaker endpoint ───────────
echo ""
echo "▶  [2] Training model and deploying SageMaker endpoint..."
echo "   (Training ~2 min + endpoint deployment ~5-10 min)"

# Check if endpoint already exists
ENDPOINT_STATUS=$(aws sagemaker describe-endpoint \
    --endpoint-name fraud-xgb-endpoint \
    --region ap-south-1 \
    --query EndpointStatus --output text 2>/dev/null || echo "MISSING")

if [ "$ENDPOINT_STATUS" = "InService" ]; then
    echo "   ✅ SageMaker endpoint already InService — skipping training"
elif [ "$ENDPOINT_STATUS" = "Creating" ]; then
    echo "   ⏳ Endpoint is still Creating — will wait for it..."
else
    echo "   Endpoint status: $ENDPOINT_STATUS — running train_and_deploy.py..."
    python model/train_and_deploy.py
fi

# ── Task 2: Wait for endpoint to be InService ───────────────────
echo ""
echo "▶  [3] Waiting for SageMaker endpoint to be InService..."
MAX_WAIT=600   # 10 minutes
ELAPSED=0
while true; do
    STATUS=$(aws sagemaker describe-endpoint \
        --endpoint-name fraud-xgb-endpoint \
        --region ap-south-1 \
        --query EndpointStatus --output text 2>/dev/null || echo "MISSING")
    echo "   Status: $STATUS  (${ELAPSED}s elapsed)"
    if [ "$STATUS" = "InService" ]; then
        echo "   ✅ Endpoint is InService!"
        break
    elif [ "$STATUS" = "Failed" ]; then
        echo "   ❌ Endpoint creation FAILED. Check SageMaker console."
        aws sagemaker describe-endpoint \
            --endpoint-name fraud-xgb-endpoint \
            --region ap-south-1 \
            --query 'FailureReason' --output text
        exit 1
    elif [ $ELAPSED -ge $MAX_WAIT ]; then
        echo "   ❌ Timed out after ${MAX_WAIT}s waiting for endpoint."
        exit 1
    fi
    sleep 30
    ELAPSED=$((ELAPSED + 30))
done

# ── Task 3: Update Lambda env vars ──────────────────────────────
echo ""
echo "▶  [4] Updating Lambda environment variables..."
SNS_ARN=$(aws sns list-topics --region ap-south-1 \
    --query "Topics[?contains(TopicArn,'fraud-alerts')].TopicArn" \
    --output text)
echo "   SNS ARN: $SNS_ARN"

aws lambda update-function-configuration \
    --function-name fraud-handler \
    --environment "Variables={SAGEMAKER_ENDPOINT=fraud-xgb-endpoint,DYNAMODB_TABLE=fraud-transactions,SNS_TOPIC_ARN=${SNS_ARN},FRAUD_THRESHOLD=0.7}" \
    --region ap-south-1 \
    --query "[FunctionName, Environment.Variables]" \
    --output json

echo "   Waiting for Lambda configuration to propagate..."
aws lambda wait function-updated \
    --function-name fraud-handler \
    --region ap-south-1
echo "   ✅ Lambda env vars updated"

# ── Task 4: Git commit and push ─────────────────────────────────
echo ""
echo "▶  [5] Committing and pushing to trigger CI/CD pipeline..."
git add -A
git status --short
git commit -m "trigger: initial CI/CD pipeline run — all bugs fixed" || echo "   (nothing new to commit)"
git push origin main
echo "   ✅ Pushed to main — GitHub Actions pipeline triggered"
echo "   View pipeline: $(git remote get-url origin | sed 's/\.git$//')/actions"

# ── Task 5: Get API Gateway URL ─────────────────────────────────
echo ""
echo "▶  [6] Getting API Gateway URL..."
API_ID=$(aws apigateway get-rest-apis \
    --region ap-south-1 \
    --query "items[?name=='fraud-detection-api'].id" \
    --output text)

if [ -z "$API_ID" ]; then
    echo "   ❌ Could not find 'fraud-detection-api' in API Gateway."
    exit 1
fi

API_URL="https://${API_ID}.execute-api.ap-south-1.amazonaws.com/prod/score"
echo "   ✅ API endpoint: $API_URL"

# ── Wait for CI/CD pipeline ─────────────────────────────────────
echo ""
echo "▶  [7] Waiting 90s for GitHub Actions pipeline to deploy Lambda..."
echo "   (Check progress at: $(git remote get-url origin | sed 's/\.git$//')/actions)"
sleep 90

# ── Task 5: Smoke tests ─────────────────────────────────────────
echo ""
echo "▶  [8] Running smoke tests..."
echo ""
echo "   TEST A: Legitimate transaction (expect APPROVE)..."
LEGIT_RESPONSE=$(curl -s -X POST "$API_URL" \
    -H "Content-Type: application/json" \
    -d '{
      "transaction_id": "test-legit-001",
      "amount": 25.0, "time": 1000,
      "v1": 0.1, "v2": 0.2, "v3": 0.1, "v4": 0.0,
      "v5": -0.1, "v6": 0.0, "v7": 0.1, "v8": 0.0,
      "v9": -0.1, "v10": 0.0, "v11": 0.1, "v12": 0.2,
      "v13": 0.0, "v14": -0.1, "v15": 0.0, "v16": 0.1,
      "v17": 0.0, "v18": -0.1, "v19": 0.0, "v20": 0.0,
      "v21": 0.0, "v22": 0.0, "v23": 0.0, "v24": 0.0,
      "v25": 0.0, "v26": 0.0, "v27": 0.0, "v28": 0.0
    }')
echo "   Response: $LEGIT_RESPONSE"

echo ""
echo "   TEST B: Fraudulent transaction (expect BLOCK + SNS alert)..."
FRAUD_RESPONSE=$(curl -s -X POST "$API_URL" \
    -H "Content-Type: application/json" \
    -d '{
      "transaction_id": "test-fraud-001",
      "amount": 9999.99, "time": 50000,
      "v1": -3.5, "v2": 2.1, "v3": -4.2, "v4": 1.8,
      "v5": -0.9, "v6": 0.3, "v7": -3.1, "v8": 0.6,
      "v9": -0.7, "v10": -2.8, "v11": 1.4, "v12": -5.1,
      "v13": 0.2, "v14": -4.7, "v15": 0.5, "v16": -0.8,
      "v17": -3.9, "v18": -0.4, "v19": 0.1, "v20": 0.3,
      "v21": 0.7, "v22": -0.2, "v23": 0.0, "v24": -0.5,
      "v25": 0.4, "v26": 0.1, "v27": 0.0, "v28": 0.05
    }')
echo "   Response: $FRAUD_RESPONSE"

# ── Task 6: DynamoDB check ──────────────────────────────────────
echo ""
echo "▶  [9] Verifying DynamoDB records..."
aws dynamodb scan \
    --table-name fraud-transactions \
    --region ap-south-1 \
    --query "Items[*].{id:transaction_id.S,fraud:is_fraud.BOOL,score:fraud_score.S,amount:amount.S}" \
    --output table

# ── Task 7: CloudWatch logs ─────────────────────────────────────
echo ""
echo "▶  [10] Checking CloudWatch logs (last 20 events)..."
LOG_STREAM=$(aws logs describe-log-streams \
    --log-group-name /aws/lambda/fraud-handler \
    --region ap-south-1 \
    --order-by LastEventTime \
    --descending \
    --query "logStreams[0].logStreamName" \
    --output text 2>/dev/null || echo "NONE")

if [ "$LOG_STREAM" != "NONE" ] && [ -n "$LOG_STREAM" ]; then
    aws logs get-log-events \
        --log-group-name /aws/lambda/fraud-handler \
        --log-stream-name "$LOG_STREAM" \
        --region ap-south-1 \
        --limit 20 \
        --query "events[*].message" \
        --output text
else
    echo "   (No log streams yet — Lambda may not have been invoked yet)"
fi

# ── Final summary ────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  DEFINITION OF DONE — STATUS CHECK"
echo "═══════════════════════════════════════════════════════════"
echo ""

SM_STATUS=$(aws sagemaker describe-endpoint \
    --endpoint-name fraud-xgb-endpoint \
    --region ap-south-1 \
    --query EndpointStatus --output text 2>/dev/null || echo "MISSING")
[ "$SM_STATUS" = "InService" ] && echo "  ✅ SageMaker endpoint InService" || echo "  ❌ SageMaker endpoint: $SM_STATUS"

echo "  ✅ GitHub Actions pipeline triggered (check Actions tab manually)"

echo "$LEGIT_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print('  ✅ Legit transaction → APPROVE' if d.get('decision')=='APPROVE' else f'  ❌ Legit transaction: {d}')" 2>/dev/null || echo "  ❌ Legit test: no response or error"

echo "$FRAUD_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print('  ✅ Fraud transaction → BLOCK' if d.get('decision')=='BLOCK' else f'  ❌ Fraud transaction: {d}')" 2>/dev/null || echo "  ❌ Fraud test: no response or error"

DYNAMO_COUNT=$(aws dynamodb scan \
    --table-name fraud-transactions \
    --region ap-south-1 \
    --select COUNT \
    --query Count \
    --output text 2>/dev/null || echo "0")
[ "$DYNAMO_COUNT" -ge 2 ] && echo "  ✅ DynamoDB has $DYNAMO_COUNT records" || echo "  ❌ DynamoDB only has $DYNAMO_COUNT records"

echo ""
echo "  📧 Check your email inbox for the SNS fraud alert!"
echo "  🔗 API endpoint: $API_URL"
echo ""
echo "  Full log saved to: $PROJECT_DIR/run_all.log"
echo "═══════════════════════════════════════════════════════════"
