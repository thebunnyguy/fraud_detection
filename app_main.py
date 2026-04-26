"""
Enhanced Flask API for fraud detection with hybrid scoring
"""
import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

from app.models.loader import ModelLoader
from app.services.fraud_service import FraudDetectionService
from app.services.logging_service import FraudLoggingService
from app.core.config import DB_PATH

app = Flask(__name__)
CORS(app)

# Load models at startup
print("Loading models...")
loader = ModelLoader()
status = loader.load_models()

if status.get("errors"):
    print("WARNING: Some models failed to load:")
    for error in status["errors"]:
        print(f"  - {error}")
else:
    print("All models loaded successfully")

# Initialize services
fraud_service = FraudDetectionService()
logging_service = FraudLoggingService()


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
            anomaly_score REAL,
            risk_score INTEGER,
            decision TEXT,
            amount REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


init_db()


@app.route("/", methods=["GET"])
def dashboard():
    """Serve dashboard UI"""
    return render_template("dashboard.html")


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    model_status = loader._get_status()
    return jsonify({
        "status": "healthy",
        "models": model_status
    })


@app.route("/predict", methods=["POST"])
def predict():
    """
    Enhanced prediction endpoint with full hybrid scoring

    Request body:
    {
        "transaction_id": "txn-123",
        "time": 0,
        "amount": 149.62,
        "v1": -1.359, ..., "v28": -0.021
    }

    Response:
    {
        "transaction_id": "txn-123",
        "fraud_probability": 0.1234,
        "anomaly_score": 0.2345,
        "risk_score": 45,
        "decision": "REVIEW",
        "explanation": [...],
        "top_features": [...]
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        transaction_id = data.get("transaction_id", f"txn-{datetime.utcnow().timestamp()}")

        # Run full fraud detection pipeline
        result = fraud_service.predict(data)
        result["transaction_id"] = transaction_id

        # Store in database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO transactions
            (transaction_id, timestamp, fraud_score, anomaly_score, risk_score, decision, amount)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            transaction_id,
            datetime.utcnow().isoformat(),
            result["fraud_probability"],
            result["anomaly_score"],
            result["risk_score"],
            result["decision"],
            data.get("amount", 0.0)
        ))
        conn.commit()
        conn.close()

        # Log suspicious transactions
        logging_service.log_event(
            transaction_id,
            result["decision"],
            result["risk_score"],
            result["fraud_probability"],
            result["anomaly_score"],
            data.get("amount", 0.0)
        )

        return jsonify(result)

    except ValueError as e:
        return jsonify({"error": f"Validation error: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


@app.route("/predict/batch", methods=["POST"])
def predict_batch():
    """
    Batch prediction endpoint

    Request body:
    {
        "transactions": [
            {"transaction_id": "txn-1", "time": 0, "amount": 100, ...},
            {"transaction_id": "txn-2", "time": 10, "amount": 200, ...}
        ]
    }
    """
    try:
        data = request.get_json()
        transactions = data.get("transactions", [])

        if not transactions:
            return jsonify({"error": "No transactions provided"}), 400

        results = fraud_service.predict_batch(transactions)

        return jsonify({
            "results": results,
            "count": len(results)
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
            SELECT transaction_id, timestamp, fraud_score, anomaly_score,
                   risk_score, decision, amount
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
                "anomaly_score": row[3],
                "risk_score": row[4],
                "decision": row[5],
                "amount": row[6]
            }
            for row in rows
        ]

        return jsonify({"transactions": transactions, "count": len(transactions)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/demo-samples", methods=["GET"])
def demo_samples():
    """Return preset low, medium, and high risk transaction samples"""
    return jsonify({
        "low_risk": {
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
        "medium_risk": {
            "transaction_id": "DEMO-REVIEW-001",
            "time": 12393,
            "amount": 179.66,
            "v1": -4.064,
            "v2": 3.101,
            "v3": -1.188,
            "v4": 3.265,
            "v5": -1.904,
            "v6": 0.320,
            "v7": -0.955,
            "v8": -3.278,
            "v9": 2.821,
            "v10": 1.015,
            "v11": 3.187,
            "v12": -7.004,
            "v13": 0.873,
            "v14": -6.221,
            "v15": -0.904,
            "v16": -3.075,
            "v17": -5.045,
            "v18": -1.718,
            "v19": -0.662,
            "v20": -0.532,
            "v21": 1.689,
            "v22": -0.079,
            "v23": 0.194,
            "v24": 0.479,
            "v25": -0.507,
            "v26": -0.410,
            "v27": -3.036,
            "v28": -0.631
        },
        "high_risk": {
            "transaction_id": "DEMO-BLOCK-001",
            "time": 406,
            "amount": 0.0,
            "v1": -2.312,
            "v2": 1.952,
            "v3": -1.610,
            "v4": 3.998,
            "v5": -0.522,
            "v6": -1.427,
            "v7": -2.537,
            "v8": 1.392,
            "v9": -2.770,
            "v10": -2.772,
            "v11": 3.202,
            "v12": -2.900,
            "v13": -0.595,
            "v14": -4.289,
            "v15": 0.390,
            "v16": -1.141,
            "v17": -2.830,
            "v18": -0.017,
            "v19": 0.417,
            "v20": 0.127,
            "v21": 0.517,
            "v22": -0.035,
            "v23": -0.465,
            "v24": 0.320,
            "v25": 0.045,
            "v26": 0.178,
            "v27": 0.261,
            "v28": -0.143
        }
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
