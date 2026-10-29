"""Flask entry point for a privacy-first concierge demo."""
import json
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from concierge import answer

ROOT = Path(__file__).resolve().parent
MAX_MESSAGE_LENGTH = 1000


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(JSON_SORT_KEYS=False, MAX_CONTENT_LENGTH=16 * 1024)
    if test_config:
        app.config.update(test_config)

    with (ROOT / "hotel.json").open(encoding="utf-8") as source:
        hotel = json.load(source)

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        )
        return response

    @app.get("/")
    def home():
        return render_template("index.html", hotel=hotel)

    @app.get("/health")
    def health():
        return jsonify({"ok": True, "service": "concierge-bot"})

    @app.post("/api/chat")
    def chat():
        if not request.is_json:
            return jsonify({"error": "Send JSON with message and mode."}), 415
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"error": "Invalid JSON object."}), 400
        message = body.get("message")
        mode = body.get("mode", "hotel")
        if not isinstance(message, str) or not message.strip():
            return jsonify({"error": "Message must be nonempty text."}), 400
        if len(message) > MAX_MESSAGE_LENGTH:
            return jsonify({"error": "Message must be 1000 characters or fewer."}), 400
        if mode not in ("hotel", "personal"):
            return jsonify({"error": "Mode must be hotel or personal."}), 400
        return jsonify(answer(message.strip(), mode, hotel))

    return app


app = create_app()

if __name__ == "__main__":
    # Use gunicorn or another production WSGI server for hosted deployments.
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "8000")), debug=False)
