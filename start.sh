#!/bin/bash
# Quick start script for fraud detection system

set -e

echo "=========================================="
echo "Fraud Detection System - Quick Start"
echo "=========================================="

# Activate virtual environment
if [ -d "venv" ]; then
    echo "✓ Activating virtual environment..."
    source venv/bin/activate
else
    echo "✗ Virtual environment not found. Run: python3 -m venv venv"
    exit 1
fi

# Check if models exist
if [ ! -f "artifacts/xgboost_model.pkl" ] || [ ! -f "artifacts/isolation_forest.pkl" ]; then
    echo ""
    echo "⚠ Models not found. Training models..."
    python training/train_models.py
fi

echo ""
echo "✓ Starting Flask backend on http://localhost:5000"
echo ""
echo "Dashboard: http://localhost:5000"
echo "Health: http://localhost:5000/health"
echo "API Docs: See README_NEW.md"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python app_main.py
