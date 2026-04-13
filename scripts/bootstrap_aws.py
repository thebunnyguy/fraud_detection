#!/usr/bin/env python3
"""
scripts/bootstrap_aws.py
Creates all AWS free-tier resources for the fraud detection project.
Run ONCE before your first CI/CD push.

Usage:
    pip install boto3
    python scripts/bootstrap_aws.py
"""

import boto3
import json
import sys
import time

REGION         = "ap-south-1"
ACCOUNT_ID     = boto3.client("sts").get_caller_identity()["Account"]
LAMBDA_ROLE    = f"arn:aws:iam::{ACCOUNT_ID}:role/fraud-lambda-role"
S3_BUCKET      = f"fraud-detection-artifacts-{ACCOUNT_ID}"
DYNAMO_TABLE   = "fraud-transactions"
SNS_TOPIC_NAME = "fraud-alerts"
LAMBDA_NAME    = "fraud-handler"
API_NAME       = "fraud-detection-api"

session  = boto3.Session(region_name=REGION)
s3       = session.client("s3")
dynamo   = session.client("dynamodb")
sns      = session.client("sns")
iam      = session.client("iam")
lam      = session.client("lambda")
apigw    = session.client("apigateway")

def step(msg):
    print(f"\n{'─'*60}\n▶  {msg}")

def ok(msg):
    print(f"   ✅ {msg}")


# ── 1. S3 bucket ──────────────────────────────────────────────
step("Creating S3 bucket for Lambda artifacts")
try:
    if REGION == "us-east-1":
        s3.create_bucket(Bucket=S3_BUCKET)
    else:
        s3.create_bucket(
            Bucket=S3_BUCKET,
            CreateBucketConfiguration={"LocationConstraint": REGION},
        )
    ok(f"Bucket created: {S3_BUCKET}")
except s3.exceptions.BucketAlreadyOwnedByYou:
    ok(f"Bucket already exists: {S3_BUCKET}")


# ── 2. DynamoDB table ─────────────────────────────────────────
step("Creating DynamoDB table")
try:
    dynamo.create_table(
        TableName=DYNAMO_TABLE,
        AttributeDefinitions=[{"AttributeName": "transaction_id", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "transaction_id", "KeyType": "HASH"}],
        BillingMode="PAY_PER_REQUEST",  # free tier friendly
    )
    ok(f"DynamoDB table created: {DYNAMO_TABLE}")
except dynamo.exceptions.ResourceInUseException:
    ok(f"DynamoDB table already exists: {DYNAMO_TABLE}")


# ── 3. SNS topic ──────────────────────────────────────────────
step("Creating SNS topic")
response     = sns.create_topic(Name=SNS_TOPIC_NAME)
SNS_TOPIC_ARN = response["TopicArn"]
ok(f"SNS topic ARN: {SNS_TOPIC_ARN}")

email = input("\n   Enter your email for fraud alerts (or press Enter to skip): ").strip()
if email:
    sns.subscribe(TopicArn=SNS_TOPIC_ARN, Protocol="email", Endpoint=email)
    print(f"   📧 Confirmation email sent to {email} — check inbox and confirm.")


# ── 4. IAM role for Lambda ────────────────────────────────────
step("Creating IAM role for Lambda")
trust_policy = json.dumps({
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "lambda.amazonaws.com"},
        "Action": "sts:AssumeRole",
    }]
})
try:
    role = iam.create_role(
        RoleName="fraud-lambda-role",
        AssumeRolePolicyDocument=trust_policy,
        Description="Lambda role for fraud detection project",
    )
    LAMBDA_ROLE = role["Role"]["Arn"]
    # Attach managed policies
    for policy in [
        "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess",
        "arn:aws:iam::aws:policy/AmazonSNSFullAccess",
        "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess",
    ]:
        iam.attach_role_policy(RoleName="fraud-lambda-role", PolicyArn=policy)
    ok(f"Role created: {LAMBDA_ROLE}")
    print("   Waiting 10s for IAM propagation...")
    time.sleep(10)
except iam.exceptions.EntityAlreadyExistsException:
    LAMBDA_ROLE = f"arn:aws:iam::{ACCOUNT_ID}:role/fraud-lambda-role"
    ok(f"Role already exists: {LAMBDA_ROLE}")


# ── 5. Lambda function (placeholder zip) ─────────────────────
step("Creating Lambda function (placeholder)")
import zipfile, io

buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as zf:
    zf.writestr("fraud_handler.py", 'def lambda_handler(e,c): return {"statusCode":200,"body":"placeholder"}')
buf.seek(0)

try:
    fn = lam.create_function(
        FunctionName=LAMBDA_NAME,
        Runtime="python3.11",
        Role=LAMBDA_ROLE,
        Handler="fraud_handler.lambda_handler",
        Code={"ZipFile": buf.read()},
        Timeout=30,
        MemorySize=256,
        Environment={"Variables": {
            "SAGEMAKER_ENDPOINT": "fraud-xgb-endpoint",
            "DYNAMODB_TABLE": DYNAMO_TABLE,
            "SNS_TOPIC_ARN": SNS_TOPIC_ARN,
            "FRAUD_THRESHOLD": "0.7",
        }},
    )
    LAMBDA_ARN = fn["FunctionArn"]
    ok(f"Lambda created: {LAMBDA_ARN}")
except lam.exceptions.ResourceConflictException:
    fn = lam.get_function(FunctionName=LAMBDA_NAME)
    LAMBDA_ARN = fn["Configuration"]["FunctionArn"]
    ok(f"Lambda already exists: {LAMBDA_ARN}")


# ── 6. API Gateway ────────────────────────────────────────────
step("Creating API Gateway REST API")
api = apigw.create_rest_api(name=API_NAME, endpointConfiguration={"types": ["REGIONAL"]})
api_id   = api["id"]
root_id  = apigw.get_resources(restApiId=api_id)["items"][0]["id"]

resource = apigw.create_resource(restApiId=api_id, parentId=root_id, pathPart="score")
res_id   = resource["id"]

apigw.put_method(
    restApiId=api_id, resourceId=res_id,
    httpMethod="POST", authorizationType="NONE",
)
apigw.put_integration(
    restApiId=api_id, resourceId=res_id,
    httpMethod="POST", type="AWS_PROXY",
    integrationHttpMethod="POST",
    uri=f"arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/{LAMBDA_ARN}/invocations",
)

# Allow API Gateway to invoke Lambda
try:
    lam.add_permission(
        FunctionName=LAMBDA_NAME, StatementId="apigw-invoke",
        Action="lambda:InvokeFunction", Principal="apigateway.amazonaws.com",
        SourceArn=f"arn:aws:execute-api:{REGION}:{ACCOUNT_ID}:{api_id}/*/*/score",
    )
except lam.exceptions.ResourceConflictException:
    pass

apigw.create_deployment(restApiId=api_id, stageName="prod")
ENDPOINT_URL = f"https://{api_id}.execute-api.{REGION}.amazonaws.com/prod/score"
ok(f"API Gateway endpoint: {ENDPOINT_URL}")


# ── 7. Summary ────────────────────────────────────────────────
print(f"""
{'═'*60}
  BOOTSTRAP COMPLETE — add these to GitHub Secrets:
{'═'*60}
  AWS_ACCESS_KEY_ID       → your IAM user key
  AWS_SECRET_ACCESS_KEY   → your IAM user secret
  SAGEMAKER_ENDPOINT_NAME → fraud-xgb-endpoint
  SNS_TOPIC_ARN           → {SNS_TOPIC_ARN}

  Your API endpoint: {ENDPOINT_URL}
{'═'*60}
""")
