"""
REST endpoint for the AI Query Service, consumed by the public Client Web
Interface.

Stateless: each request is handled independently, no conversation
history (see architecture.md, Decision 1). Public and anonymous, like
the Client Web Interface itself, so CORS is open to any origin.
"""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

from agent import ask

load_dotenv()

app = Flask(__name__)
CORS(app)


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/ask")
async def ask_question():
    data = request.get_json(silent=True) or {}
    question = data.get("question")

    if not isinstance(question, str) or not question.strip():
        return (
            jsonify(
                {"error": "The 'question' field is required and must be a non-empty string."}
            ),
            400,
        )

    answer = await ask(question.strip())
    return jsonify({"answer": answer})


if __name__ == "__main__":
    port = int(os.environ.get("AI_SERVICE_PORT", 8100))
    app.run(host="0.0.0.0", port=port)
