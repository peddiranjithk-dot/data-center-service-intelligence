"""Data Center Service Intelligence - Flask API + dashboard."""
from flask import Flask, jsonify, render_template

import analytics
from db import init_db

app = Flask(__name__)


@app.route("/")
def dashboard():
    return render_template("index.html")


@app.route("/api/summary")
def api_summary():
    return jsonify(analytics.summary())


@app.route("/api/services")
def api_services():
    return jsonify(analytics.service_health())


@app.route("/api/anomalies")
def api_anomalies():
    return jsonify(analytics.detect_anomalies())


@app.route("/api/incidents")
def api_incidents():
    return jsonify(analytics.recent_incidents())


@app.route("/api/racks")
def api_racks():
    return jsonify(analytics.rack_power())


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
