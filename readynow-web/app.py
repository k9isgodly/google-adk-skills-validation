"""ReadyNow! FEMA Emergency Assistant — Flask Web Application.

Serves a custom chat frontend and proxies messages to the
deployed Agent Engine backend on Vertex AI.
"""

import os
import logging
import uuid

import vertexai
from flask import Flask, render_template, request, jsonify

# ── Config ──────────────────────────────────────────────────
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
AGENT_ENGINE_ID = os.environ.get("AGENT_ENGINE_ID", "")

# ── Init ────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ReadyNow-Web")

app = Flask(__name__)

vertexai.init(project=PROJECT_ID, location=LOCATION)
client = vertexai.Client(project=PROJECT_ID, location=LOCATION)
remote_agent = client.agent_engines.get(name=AGENT_ENGINE_ID)

logger.info("ReadyNow! Web connected to Agent Engine: %s", AGENT_ENGINE_ID)


@app.route("/")
def index():
    """Serve the main chat UI."""
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """Send a user message to Agent Engine and return the response."""
    data = request.get_json()
    user_message = data.get("message", "").strip()
    user_id = data.get("user_id", str(uuid.uuid4()))

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    logger.info("User [%s]: %s", user_id, user_message[:100])

    try:
        last_event = None
        for event in remote_agent.stream_query(
            user_id=user_id,
            message=user_message,
        ):
            last_event = event

        if last_event and "content" in last_event:
            response_text = last_event["content"]["parts"][0]["text"]
        else:
            response_text = "I'm sorry, I couldn't process that request. Please try again."

        logger.info("Agent: %s", response_text[:100])
        return jsonify({"response": response_text})

    except Exception as e:
        logger.error("Agent Engine error: %s", str(e))
        return jsonify({"error": "An error occurred. Please try again."}), 500


@app.route("/health")
def health():
    """Health check endpoint for Cloud Run."""
    return "OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
