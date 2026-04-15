# Troubleshooting Log

This document tracks all issues encountered during development and deployment, along with their solutions.

---

## Issue 1: XGBoost Architecture Mismatch (Apple Silicon)

**Date**: 2026-04-14  
**Component**: Model Training (`model/train_and_deploy.py`)  
**Error**: 
```
Library not loaded: @rpath/libomp.dylib
Reason: tried: '/opt/homebrew/Cellar/libomp/19.1.6/lib/libomp.dylib' (mach-o file, but is an incompatible architecture (have 'x86_64', need 'arm64'))
```

**Root Cause**: Corrupted or x86_64 version of libomp installed on ARM64 Mac (Apple Silicon)

**Solution**:
1. Remove corrupted libomp: `brew uninstall libomp`
2. Reinstall using native ARM Homebrew: `/opt/homebrew/bin/brew install libomp`
3. Force reinstall xgboost: `pip install --force-reinstall --no-cache-dir xgboost`

**Prevention**: Always use native ARM Homebrew (`/opt/homebrew/bin/brew`) on Apple Silicon, not Rosetta x86_64 version

---

## Issue 2: SageMaker Endpoint Health Check Failure

**Date**: 2026-04-14  
**Component**: SageMaker Deployment (`model/train_and_deploy.py`)  
**Error**: 
```
The primary container for production variant AllTraffic did not pass the ping health check
```

**CloudWatch Logs**:
```
ModuleNotFoundError: No module named 'inference'
```

**Root Cause**: sklearn container couldn't import `inference.py` module despite proper packaging in `model.tar.gz`

**Attempted Solutions**:
1. ❌ Used SageMaker SDK's `SKLearnModel` class - failed (doesn't exist in SDK v3.x)
2. ❌ Switched to XGBoost container - failed due to ECR permission issues
3. ✅ Manual deployment through AWS Console - succeeded

**Working Solution**: Deploy manually via AWS Console:
- Navigate to SageMaker → Inference → Models
- Create model with XGBoost container image
- Create endpoint configuration
- Deploy endpoint

**Files Involved**:
- `model/train_and_deploy.py` (lines 101-196)
- `model/inference.py` (custom inference script)

---

## Issue 3: GitHub Actions CI/CD Linting Failure

**Date**: 2026-04-14  
**Component**: Lambda Handler (`lambda/fraud_handler.py`)  
**Error**: 
```
Process completed with exit code 1
E221 multiple spaces before operator
```

**Root Cause**: Extra spaces in variable assignments (lines 21-23) violated flake8 E221 rule

**Before**:
```python
ENDPOINT_NAME  = os.environ["SAGEMAKER_ENDPOINT"]
TABLE_NAME     = os.environ["DYNAMODB_TABLE"]
SNS_TOPIC_ARN  = os.environ["SNS_TOPIC_ARN"]
```

**After**:
```python
ENDPOINT_NAME = os.environ["SAGEMAKER_ENDPOINT"]
TABLE_NAME = os.environ["DYNAMODB_TABLE"]
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]
```

**Solution**: Remove extra spaces to comply with PEP 8 style guide

**Verification**:
```bash
flake8 lambda/ --max-line-length=100 --ignore=E501,W503
PYTHONPATH=lambda pytest tests/ -v
```

---

## Issue 4: Model Format Incompatibility

**Date**: 2026-04-14  
**Component**: Model Training (`model/train_and_deploy.py`)  
**Error**: XGBoost container couldn't load joblib-serialized model

**Root Cause**: Used `joblib.dump()` to save XGBoost model, but XGBoost container expects native `.xgboost` format

**Before**:
```python
joblib.dump(model, "model_output/model.joblib")
with tarfile.open("model.tar.gz", "w:gz") as tar:
    tar.add("model_output/model.joblib", arcname="model.joblib")
```

**After**:
```python
model.save_model("model_output/xgboost-model")
with tarfile.open("model.tar.gz", "w:gz") as tar:
    tar.add("model_output/xgboost-model", arcname="xgboost-model")
```

**Solution**: Use XGBoost's native `save_model()` method instead of joblib

**Files Modified**: `model/train_and_deploy.py` (lines 86-92)

---

## Issue 5: IAM Role Trust Policy for SageMaker

**Date**: 2026-04-14  
**Component**: IAM Configuration (`model/train_and_deploy.py`)  
**Error**: SageMaker couldn't assume `fraud-lambda-role`

**Root Cause**: IAM role only trusted `lambda.amazonaws.com`, not `sagemaker.amazonaws.com`

**Solution**: Automatically update trust policy in `train_and_deploy.py` (lines 111-136):
```python
if "sagemaker.amazonaws.com" not in principals:
    # Update trust policy to include SageMaker
    stmt["Principal"]["Service"].append("sagemaker.amazonaws.com")
    iam_client.update_assume_role_policy(...)
```

**Prevention**: Bootstrap script should create role with both services trusted from the start

---

## Common Debugging Commands

### Check SageMaker Endpoint Status
```bash
aws sagemaker describe-endpoint \
  --endpoint-name fraud-xgb-endpoint \
  --region ap-south-1 \
  --query EndpointStatus
```

### View CloudWatch Logs
```bash
aws logs tail /aws/sagemaker/Endpoints/fraud-xgb-endpoint --follow --region ap-south-1
```

### Test Lambda Locally
```bash
aws lambda invoke \
  --function-name fraud-handler \
  --payload '{"body": "{\"transaction_id\":\"test-001\",\"amount\":50,\"time\":1000,\"v1\":-1.3,\"v2\":0.5}"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/response.json
```

### View Lambda Logs
```bash
aws logs tail /aws/lambda/fraud-handler --follow --region ap-south-1
```

### Run Tests Locally
```bash
# All tests
PYTHONPATH=lambda pytest tests/ -v

# Specific test
PYTHONPATH=lambda pytest tests/test_fraud_handler.py::test_fraudulent_transaction -v

# With coverage
PYTHONPATH=lambda pytest tests/ -v --cov=lambda --cov-report=term-missing
```

### Lint Code
```bash
flake8 lambda/ --max-line-length=100 --ignore=E501,W503
```

---

## Known Limitations

1. **SageMaker Endpoint Cost**: ml.t2.medium costs ~$0.05/hour. Delete endpoint when not in use:
   ```bash
   aws sagemaker delete-endpoint --endpoint-name fraud-xgb-endpoint
   ```

2. **Feature Order Dependency**: Model expects features in exact order: `["time", "amount", "v1", ..., "v28"]`. Any change requires retraining.

3. **Dataset Size**: `creditcard.csv` is 143.84 MB, tracked via Git LFS. Clone requires LFS: `git lfs pull`

4. **CI/CD Secrets**: GitHub Actions requires 4 secrets configured:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `SAGEMAKER_ENDPOINT_NAME`
   - `SNS_TOPIC_ARN`

---

## Quick Reference: File Locations

| Component | File Path | Purpose |
|-----------|-----------|---------|
| Lambda Handler | `lambda/fraud_handler.py` | API Gateway entry point |
| Model Training | `model/train_and_deploy.py` | Train & deploy XGBoost |
| Inference Script | `model/inference.py` | SageMaker custom inference |
| Tests | `tests/test_fraud_handler.py` | Unit tests with mocks |
| CI/CD Pipeline | `.github/workflows/deploy.yml` | GitHub Actions workflow |
| Bootstrap | `scripts/bootstrap_aws.py` | One-time AWS setup |
| Dataset | `creditcard.csv` | Kaggle fraud dataset (Git LFS) |

---

## Next Steps When Issues Occur

1. **Check this file first** for similar issues
2. **Check CloudWatch logs** for runtime errors
3. **Verify AWS resources exist** (endpoint, table, topic, role)
4. **Run tests locally** before pushing to GitHub
5. **Check GitHub Actions logs** for CI/CD failures
6. **Verify environment variables** are set correctly

---

## Issue 6: Interpreter Mismatch in Active Virtual Environment

**Date**: 2026-04-16  
**Component**: Test Execution (`pytest`)  
**Error**: 
```
ModuleNotFoundError: No module named 'flask'
ModuleNotFoundError: No module named 'numpy'
```

**Symptom**: Tests fail with import errors despite packages being installed and virtual environment being active.

**Root Cause**: Virtual environment was active (`source venv/bin/activate`), but `pytest` resolved to the global system executable instead of the venv interpreter. This caused tests to run with the wrong Python environment, missing all venv-installed dependencies.

**Evidence**:
```bash
$ which python
/Users/manuk/Downloads/projects/fraud_detection/venv/bin/python  # ✅ correct

$ which pytest
/Library/Frameworks/Python.framework/Versions/3.13/bin/pytest  # ❌ wrong (global)
```

**Attempted Solutions**:
1. ❌ Assumed missing dependencies, tried reinstalling packages
2. ❌ Modified test imports and PYTHONPATH
3. ❌ Deleted test files thinking they were obsolete
4. ✅ Used `python -m pytest` to force venv interpreter

**Correct Fix**:
```bash
# Instead of bare pytest
pytest tests/ -v  # ❌ uses global pytest

# Use module invocation
python -m pytest tests/test_app.py -v  # ✅ uses venv python

# Or use explicit venv path
./venv/bin/python -m pytest tests/test_app.py -v  # ✅ explicit venv
```

**CI/CD Fix** (`.github/workflows/oracle-deploy.yml`):
```yaml
- name: Install dependencies
  run: |
    python -m pip install -r requirements.txt
    python -m pip install pytest pytest-cov

- name: Run tests
  run: |
    PYTHONPATH=. python -m pytest tests/test_app.py -v
```

**Prevention**:
- Always use `python -m pytest` instead of bare `pytest`
- Always use `python -m pip` instead of bare `pip`
- When a package seems "installed but not found," verify interpreter alignment with `which python` vs `which <command>` before changing code or deleting tests
- In CI, prefer module invocation (`python -m`) for all Python tools to ensure correct interpreter
- Run only active tests (`test_app.py` for Oracle deployment, not old AWS Lambda tests)

**Files Modified**: `.github/workflows/oracle-deploy.yml`

---

*Last Updated: 2026-04-16*
