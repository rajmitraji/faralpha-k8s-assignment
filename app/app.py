import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_db():
    mongo_host = os.environ.get("MONGO_HOST", "localhost")
    mongo_port = os.environ.get("MONGO_PORT", "27017")
    mongo_user = os.environ.get("MONGO_USERNAME", "")
    mongo_pass = os.environ.get("MONGO_PASSWORD", "")
    mongo_db = os.environ.get("MONGO_DB", "flaskdb")

    if mongo_user and mongo_pass:
        uri = f"mongodb://{mongo_user}:{mongo_pass}@{mongo_host}:{mongo_port}/{mongo_db}?authSource=admin"
    else:
        uri = f"mongodb://{mongo_host}:{mongo_port}/{mongo_db}"

    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    return client[mongo_db]


@app.route("/")
def home():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"Welcome to the Flask app! The current time is: {current_time}"


@app.route("/data", methods=["POST"])
def insert_data():
    if not request.is_json:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    data = request.get_json()
    if not data:
        return jsonify({"error": "Empty JSON body is not allowed"}), 400

    try:
        db = get_db()
        db.data.insert_one(data)
        return jsonify({"status": "Data inserted"}), 201
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"MongoDB connection error: {e}")
        return jsonify({"error": "Database connection failed. Please try again later."}), 503
    except Exception as e:
        logger.error(f"Unexpected error during insert: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500


@app.route("/data", methods=["GET"])
def get_data():
    try:
        db = get_db()
        documents = list(db.data.find({}, {"_id": 0}))
        return jsonify(documents), 200
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"MongoDB connection error: {e}")
        return jsonify({"error": "Database connection failed. Please try again later."}), 503
    except Exception as e:
        logger.error(f"Unexpected error during fetch: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
