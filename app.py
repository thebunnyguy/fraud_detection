"""
Flask API for fraud detection - Oracle Cloud deployment
"""
import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify
import joblib
import numpy as np

app = Flask(__name__)

# Load model
MODEL_PATH = os.getenv("MODEL_PATH", "fraud_model.pkl")
model = joblib.load(MODEL_PATH)

# Database setup
DB_PATH = os.getenv("DB_PATH", "fraud_transactions.db")

def init_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT UNIQUE,
            timestamp TEXT,
            fraud_score REAL,
            is_fraud INTEGER,
            amount REAL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Feature order (must match training)
FEATURE_COLS = ["time", "amount"] + [f"v{i}" for i in range(1, 29)]
FRAUD_THRESHOLD = float(os.getenv("FRAUD_THRESHOLD", "0.7"))

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "model_loaded": model is not None})

@app.route("/score", methods=["POST"])
def score_transaction():
    """Score a transaction for fraud"""
    try:
        data = request.get_json()
        transaction_id = data.get("transaction_id", f"txn-{datetime.utcnow().timestamp()}")

        # Extract features in correct order
        features = [data.get(col, 0.0) for col in FEATURE_COLS]
        X = np.array(features).reshape(1, -1)

        # Predict fraud probability
        fraud_prob = model.predict_proba(X)[0, 1]
        score = float(fraud_prob)
        is_fraud = score >= FRAUD_THRESHOLD

        # Store in database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO transactions
            (transaction_id, timestamp, fraud_score, is_fraud, amount)
            VALUES (?, ?, ?, ?, ?)
        """, (
            transaction_id,
            datetime.utcnow().isoformat(),
            score,
            int(is_fraud),
            data.get("amount", 0.0)
        ))
        conn.commit()
        conn.close()

        return jsonify({
            "transaction_id": transaction_id,
            "fraud_score": round(score, 4),
            "is_fraud": is_fraud,
            "decision": "BLOCK" if is_fraud else "APPROVE"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/transactions", methods=["GET"])
def get_transactions():
    """Get transaction history"""
    try:
        limit = request.args.get("limit", 100, type=int)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT transaction_id, timestamp, fraud_score, is_fraud, amount
            FROM transactions
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        transactions = [
            {
                "transaction_id": row[0],
                "timestamp": row[1],
                "fraud_score": row[2],
                "is_fraud": bool(row[3]),
                "amount": row[4]
            }
            for row in rows
        ]

        return jsonify({"transactions": transactions, "count": len(transactions)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
