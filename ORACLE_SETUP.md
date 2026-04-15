# Oracle Cloud Free Tier Setup Guide

Complete guide to deploy fraud detection system on Oracle Cloud Always Free tier.

---

## Part 1: Oracle Cloud Account Setup

### 1.1 Create Oracle Cloud Account
1. Go to https://www.oracle.com/cloud/free/
2. Click "Start for free"
3. Fill in details (email, country, etc.)
4. Verify email and complete registration
5. **Important**: You'll need a credit card for verification, but won't be charged

### 1.2 Create a Compute Instance (VM)
1. Login to Oracle Cloud Console
2. Navigate to: **Compute → Instances → Create Instance**
3. Configure:
   - **Name**: `fraud-detection-vm`
   - **Image**: Ubuntu 22.04 (Always Free eligible)
   - **Shape**: VM.Standard.E2.1.Micro (Always Free - 1 OCPU, 1GB RAM)
   - **Networking**: Use default VCN (Virtual Cloud Network)
   - **Add SSH Keys**: 
     - Generate new key pair OR upload your existing public key
     - **SAVE THE PRIVATE KEY** - you'll need it to connect
4. Click **Create**
5. Wait 2-3 minutes for instance to provision

### 1.3 Configure Firewall Rules
1. Go to your instance details page
2. Click on the **Subnet** link
3. Click on the **Default Security List**
4. Click **Add Ingress Rules**
5. Add rule for HTTP traffic:
   - **Source CIDR**: `0.0.0.0/0`
   - **Destination Port**: `8080`
   - **Description**: `Fraud Detection API`
6. Click **Add Ingress Rules**

### 1.4 Get Your VM's Public IP
1. Go back to **Compute → Instances**
2. Click on your instance name
3. Copy the **Public IP Address** (e.g., `123.45.67.89`)
4. Save this - you'll need it for deployment

---

## Part 2: VM Setup (SSH into your VM)

### 2.1 Connect to VM
```bash
# Replace with your private key path and public IP
ssh -i /path/to/your-private-key ubuntu@YOUR_PUBLIC_IP

# Example:
# ssh -i ~/.ssh/oracle_key ubuntu@123.45.67.89
```

### 2.2 Install Docker
```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group (no need for sudo)
sudo usermod -aG docker ubuntu

# Start Docker
sudo systemctl enable docker
sudo systemctl start docker

# Verify installation
docker --version
```

### 2.3 Create Data Directory
```bash
# Create directory for persistent database storage
sudo mkdir -p /opt/fraud-detection/data
sudo chown ubuntu:ubuntu /opt/fraud-detection/data
```

### 2.4 Configure Ubuntu Firewall
```bash
# Allow port 8080
sudo ufw allow 8080/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

---

## Part 3: GitHub Secrets Configuration

### 3.1 Prepare SSH Key for GitHub Actions
```bash
# On your LOCAL machine (not the VM)
# If you don't have the private key as text, convert it:
cat /path/to/your-private-key

# Copy the ENTIRE output including:
# -----BEGIN OPENSSH PRIVATE KEY-----
# ... key content ...
# -----END OPENSSH PRIVATE KEY-----
```

### 3.2 Add Secrets to GitHub Repository
1. Go to your GitHub repository
2. Click **Settings → Secrets and variables → Actions**
3. Click **New repository secret**
4. Add these three secrets:

**Secret 1: ORACLE_SSH_KEY**
- Name: `ORACLE_SSH_KEY`
- Value: Paste the entire private key content from step 3.1

**Secret 2: ORACLE_HOST**
- Name: `ORACLE_HOST`
- Value: Your VM's public IP (e.g., `123.45.67.89`)

**Secret 3: ORACLE_USER**
- Name: `ORACLE_USER`
- Value: `ubuntu`

---

## Part 4: Deploy the Application

### 4.1 Train the Model Locally
```bash
# On your LOCAL machine, in the project directory
python model/train_model.py

# This creates: lambda/fraud_model.pkl
```

### 4.2 Commit and Push
```bash
git add .
git commit -m "Add Oracle Cloud deployment configuration"
git push origin main
```

### 4.3 Monitor Deployment
1. Go to GitHub repository
2. Click **Actions** tab
3. Watch the workflow run:
   - ✅ Test job (runs pytest)
   - ✅ Build job (creates Docker image)
   - ✅ Deploy job (deploys to Oracle Cloud)

---

## Part 5: Test Your API

### 5.1 Health Check
```bash
# Replace with your VM's public IP
curl http://YOUR_PUBLIC_IP:8080/health
```

Expected response:
```json
{"status": "healthy", "model_loaded": true}
```

### 5.2 Score a Transaction
```bash
curl -X POST http://YOUR_PUBLIC_IP:8080/score \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "test-001",
    "amount": 50.0,
    "time": 1000,
    "v1": -1.3,
    "v2": 0.5,
    "v3": 0.0,
    "v4": 0.0,
    "v5": 0.0,
    "v6": 0.0,
    "v7": 0.0,
    "v8": 0.0,
    "v9": 0.0,
    "v10": 0.0,
    "v11": 0.0,
    "v12": 0.0,
    "v13": 0.0,
    "v14": 0.0,
    "v15": 0.0,
    "v16": 0.0,
    "v17": 0.0,
    "v18": 0.0,
    "v19": 0.0,
    "v20": 0.0,
    "v21": 0.0,
    "v22": 0.0,
    "v23": 0.0,
    "v24": 0.0,
    "v25": 0.0,
    "v26": 0.0,
    "v27": 0.0,
    "v28": 0.0
  }'
```

Expected response:
```json
{
  "transaction_id": "test-001",
  "fraud_score": 0.1234,
  "is_fraud": false,
  "decision": "APPROVE"
}
```

### 5.3 View Transaction History
```bash
curl http://YOUR_PUBLIC_IP:8080/transactions
```

---

## Part 6: Troubleshooting

### Check if Docker container is running
```bash
ssh -i /path/to/key ubuntu@YOUR_PUBLIC_IP
docker ps
```

### View container logs
```bash
docker logs fraud-api
```

### Restart container
```bash
docker restart fraud-api
```

### Check firewall
```bash
sudo ufw status
```

### Test from VM itself
```bash
curl http://localhost:8080/health
```

---

## Cost Breakdown

**Oracle Cloud Always Free Tier:**
- ✅ 2 AMD Compute VMs (we use 1)
- ✅ 200GB Block Storage
- ✅ 10GB outbound data transfer/month
- ✅ **$0/month forever**

**GitHub Actions:**
- ✅ 2,000 minutes/month free for public repos
- ✅ 500MB storage free
- ✅ **$0/month**

**Total Cost: $0/month** 🎉

---

## What You Get

✅ Real-time fraud detection API  
✅ Transaction history storage (SQLite)  
✅ Automated CI/CD pipeline  
✅ Docker containerized deployment  
✅ Always-on service (no cold starts)  
✅ Completely free forever  

---

## Next Steps

1. Add email/SMS alerts using free SMTP services (SendGrid, Mailgun)
2. Add authentication (API keys, JWT)
3. Set up monitoring with free tier of Grafana Cloud
4. Add rate limiting to prevent abuse
5. Create a simple web dashboard

---

## Support

If you encounter issues:
1. Check GitHub Actions logs
2. SSH into VM and check Docker logs
3. Verify firewall rules in Oracle Cloud Console
4. Test locally with `docker build` and `docker run`
