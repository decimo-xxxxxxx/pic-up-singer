from flask import Flask, jsonify
import os
import time

app = Flask(__name__)

@app.route('/health')
def health_check():
    status = {
        "status": "healthy",
        "timestamp": time.time(),
        "environment": dict(os.environ)
    }
    return jsonify(status)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)