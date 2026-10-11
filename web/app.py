"""
web/app.py
Golden Gate Glory – Veteran Career Navigator
Flask entry-point for the Phase 1 front-end.

Serves index.html and exposes ORCHESTRATE_ENDPOINT + ORCHESTRATE_API_KEY
to the template so the values never have to be hard-coded in HTML.

Environment variables (set via .env locally, or OpenShift Secret in-cluster):
    ORCHESTRATE_ENDPOINT  – full watsonx Orchestrate agent REST URL
    ORCHESTRATE_API_KEY   – IBM Cloud API key (keep secret)
    USE_MOCK              – set to "true" to enable mock mode (default: "true")
    PORT                  – port to bind (default: 8080)
"""

import os
from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def index():
    return render_template(
        "index.html",
        orchestrate_endpoint=os.environ.get("ORCHESTRATE_ENDPOINT", ""),
        orchestrate_api_key=os.environ.get("ORCHESTRATE_API_KEY", ""),
        use_mock=os.environ.get("USE_MOCK", "true").lower() != "false",
    )


@app.route("/healthz")
def healthz():
    """Liveness probe endpoint for OpenShift."""
    return {"status": "ok"}, 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    # debug=False in production; gunicorn handles concurrency
    app.run(host="0.0.0.0", port=port, debug=False)
