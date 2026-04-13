"""
model/train_and_deploy.py
Train XGBoost on Kaggle credit card fraud dataset,
then deploy to a SageMaker real-time endpoint.

Run this ONCE locally (or in a SageMaker notebook) before
the CI/CD pipeline starts referencing the endpoint.

Requirements:
    pip install sagemaker xgboost scikit-learn pandas boto3
Dataset:
    kaggle datasets download -d mlg-ulb/creditcardfraud
    unzip creditcard.csv.zip
"""

import boto3
import sagemaker
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from xgboost import XGBClassifier
import tarfile, os, joblib

REGION        = "ap-south-1"
ENDPOINT_NAME = "fraud-xgb-endpoint"
ACCOUNT_ID    = boto3.client("sts", region_name=REGION).get_caller_identity()["Account"]
BUCKET        = f"fraud-detection-artifacts-{ACCOUNT_ID}"

# Directory containing this script (model/) — where inference.py lives
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Dataset path: look next to the script first, then in project root
_script_csv = os.path.join(SCRIPT_DIR, "creditcard.csv")
_root_csv   = os.path.join(os.path.dirname(SCRIPT_DIR), "creditcard.csv")
CSV_PATH    = _script_csv if os.path.exists(_script_csv) else _root_csv

# ── 1. Load & prepare data ────────────────────────────────────
print(f"Loading dataset from {CSV_PATH} ...")
df = pd.read_csv(CSV_PATH)

# Normalise column names to lowercase so both Kaggle (V1, Time, Amount)
# and synthetic (v1, time, amount) datasets work identically.
df.columns = [c.lower() for c in df.columns]
print(f"Dataset: {df.shape[0]:,} rows | Fraud rate: {df['class'].mean()*100:.3f}%")

# Feature order MUST match what Lambda sends: time, amount, v1…v28
FEATURE_ORDER = ["time", "amount"] + [f"v{i}" for i in range(1, 29)]
X = df[FEATURE_ORDER]
y = df["class"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ── 2. Train XGBoost (handles class imbalance via scale_pos_weight) ──
fraud_ratio = (y_train == 0).sum() / (y_train == 1).sum()
print(f"\nTraining XGBoost (scale_pos_weight={fraud_ratio:.1f})...")

model = XGBClassifier(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=fraud_ratio,
    eval_metric="auc",
    random_state=42,
    n_jobs=-1,
)
model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=50,
)

# ── 3. Evaluate ───────────────────────────────────────────────
y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]

print("\n── Evaluation ──")
print(classification_report(y_test, y_pred, target_names=["Legit", "Fraud"]))
print(f"ROC-AUC: {roc_auc_score(y_test, y_prob):.4f}")

# ── 4. Save & package model for SageMaker ────────────────────
os.makedirs("model_output", exist_ok=True)
joblib.dump(model, "model_output/model.joblib")

with tarfile.open("model.tar.gz", "w:gz") as tar:
    tar.add("model_output/model.joblib", arcname="model.joblib")

print("\nModel saved to model.tar.gz")

# ── 5. Upload to S3 ───────────────────────────────────────────
s3 = boto3.client("s3", region_name=REGION)
s3.upload_file("model.tar.gz", BUCKET, "model/model.tar.gz")
model_s3_uri = f"s3://{BUCKET}/model/model.tar.gz"
print(f"Uploaded to {model_s3_uri}")

# ── 6. Deploy to SageMaker using boto3 directly ──────────────
import json as _json
import time as _time
import tarfile
import shutil

# Get the IAM role ARN
iam_client = boto3.client("iam", region_name=REGION)
role = iam_client.get_role(RoleName="fraud-lambda-role")["Role"]["Arn"]
print(f"Using IAM role: {role}")

# Ensure the role trusts SageMaker
trust = iam_client.get_role(RoleName="fraud-lambda-role")["Role"]["AssumeRolePolicyDocument"]
principals = []
for stmt in trust.get("Statement", []):
    p = stmt.get("Principal", {})
    if isinstance(p.get("Service"), list):
        principals.extend(p["Service"])
    elif isinstance(p.get("Service"), str):
        principals.append(p["Service"])

if "sagemaker.amazonaws.com" not in principals:
    print("Updating IAM trust policy to include sagemaker.amazonaws.com ...")
    for stmt in trust["Statement"]:
        svc = stmt.get("Principal", {}).get("Service")
        if svc:
            if isinstance(svc, str):
                stmt["Principal"]["Service"] = [svc, "sagemaker.amazonaws.com"]
            elif isinstance(svc, list) and "sagemaker.amazonaws.com" not in svc:
                svc.append("sagemaker.amazonaws.com")
    iam_client.update_assume_role_policy(
        RoleName="fraud-lambda-role",
        PolicyDocument=_json.dumps(trust),
    )
    print("Waiting 10s for IAM propagation...")
    _time.sleep(10)
else:
    print("SageMaker trust already present in role.")

# Package inference code with model
print("\nPackaging model with inference code...")
os.makedirs("code", exist_ok=True)
shutil.copy(os.path.join(SCRIPT_DIR, "inference.py"), "code/inference.py")

with tarfile.open("model.tar.gz", "w:gz") as tar:
    tar.add("model_output/model.joblib", arcname="model.joblib")
    tar.add("code/inference.py", arcname="code/inference.py")

# Re-upload the complete package
s3.upload_file("model.tar.gz", BUCKET, "model/model.tar.gz")
print(f"Uploaded complete package to {model_s3_uri}")

# Create SageMaker model using sklearn container
sm_client = boto3.client("sagemaker", region_name=REGION)

# Use sklearn container image (hardcoded for ap-south-1)
container_image = f"720646828776.dkr.ecr.{REGION}.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3"

model_name = f"fraud-xgb-model-{int(_time.time())}"
print(f"\nCreating SageMaker model: {model_name}")

try:
    sm_client.create_model(
        ModelName=model_name,
        PrimaryContainer={
            "Image": container_image,
            "ModelDataUrl": model_s3_uri,
            "Environment": {
                "SAGEMAKER_PROGRAM": "inference.py",
                "SAGEMAKER_SUBMIT_DIRECTORY": model_s3_uri,
            }
        },
        ExecutionRoleArn=role,
    )
    print(f"Model created: {model_name}")
except Exception as e:
    print(f"Model creation note: {e}")

# Create endpoint configuration
endpoint_config_name = f"fraud-xgb-config-{int(_time.time())}"
print(f"Creating endpoint configuration: {endpoint_config_name}")

try:
    sm_client.create_endpoint_config(
        EndpointConfigName=endpoint_config_name,
        ProductionVariants=[{
            "VariantName": "AllTraffic",
            "ModelName": model_name,
            "InitialInstanceCount": 1,
            "InstanceType": "ml.t2.medium",
        }]
    )
    print(f"Endpoint config created: {endpoint_config_name}")
except Exception as e:
    print(f"Endpoint config note: {e}")

# Create or update endpoint
print(f"\nDeploying endpoint: {ENDPOINT_NAME} (this takes ~5-7 min)...")

try:
    # Try to update existing endpoint
    sm_client.update_endpoint(
        EndpointName=ENDPOINT_NAME,
        EndpointConfigName=endpoint_config_name,
    )
    print(f"Updating existing endpoint: {ENDPOINT_NAME}")
except sm_client.exceptions.ClientError:
    # Create new endpoint if it doesn't exist
    sm_client.create_endpoint(
        EndpointName=ENDPOINT_NAME,
        EndpointConfigName=endpoint_config_name,
    )
    print(f"Creating new endpoint: {ENDPOINT_NAME}")

print(f"✅ Endpoint deployment initiated: {ENDPOINT_NAME}")
print("Run the following to check status:")
print(f"  aws sagemaker describe-endpoint --endpoint-name {ENDPOINT_NAME} --region {REGION} --query EndpointStatus")
