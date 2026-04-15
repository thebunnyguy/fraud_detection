"""
Flask API for fraud detection - Oracle Cloud deployment
"""
import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template
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

@app.route("/", methods=["GET"])
def dashboard():
    """Serve dashboard UI"""
    return render_template("dashboard.html")

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

@app.route("/demo-samples", methods=["GET"])
def demo_samples():
    """Return preset legitimate and fraudulent transaction samples"""
    return jsonify({
        "legitimate": {
            "transaction_id": "DEMO-LEGIT-001",
            "time": 0,
            "amount": 149.62,
            "v1": -1.3598071336738,
            "v2": -0.0727811733098497,
            "v3": 2.53634673796914,
            "v4": 1.37815522427443,
            "v5": -0.338320769942518,
            "v6": 0.462387777762292,
            "v7": 0.239598554061257,
            "v8": 0.0986979012610507,
            "v9": 0.363786969611213,
            "v10": 0.0907941719789316,
            "v11": -0.551599533260813,
            "v12": -0.617800855762348,
            "v13": -0.991389847235408,
            "v14": -0.311169353699879,
            "v15": 1.46817697209427,
            "v16": -0.470400525259478,
            "v17": 0.207971241929242,
            "v18": 0.0257905801985591,
            "v19": 0.403992960255733,
            "v20": 0.251412098239705,
            "v21": -0.018306777944153,
            "v22": 0.277837575558899,
            "v23": -0.110473910188767,
            "v24": 0.0669280749146731,
            "v25": 0.128539358273528,
            "v26": -0.189114843888824,
            "v27": 0.133558376740387,
            "v28": -0.0210530534538215
        },
        "fraudulent": {
            "transaction_id": "DEMO-FRAUD-001",
            "time": 406,
            "amount": 0.0,
            "v1": -2.3122265423263,
            "v2": 1.95199201064158,
            "v3": -1.60985073229769,
            "v4": 3.9979055875468,
            "v5": -0.522187864667764,
            "v6": -1.42654531920595,
            "v7": -2.53738730624579,
            "v8": 1.39165724829804,
            "v9": -2.77008927719433,
            "v10": -2.77227214465915,
            "v11": 3.20203320709635,
            "v12": -2.89990738849473,
            "v13": -0.595221881324605,
            "v14": -4.28925378244217,
            "v15": 0.389724120274487,
            "v16": -1.14074717980657,
            "v17": -2.83005567450437,
            "v18": -0.0168224681808257,
            "v19": 0.416955705037907,
            "v20": 0.126910559061474,
            "v21": 0.517232370861764,
            "v22": -0.0350493686052974,
            "v23": -0.465211076182388,
            "v24": 0.320198198514526,
            "v25": 0.0445191674731724,
            "v26": 0.177839798284401,
            "v27": 0.261145002567677,
            "v28": -0.143275874698919
        }
    })

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
