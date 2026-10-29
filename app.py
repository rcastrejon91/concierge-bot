"""Flask entry point for a privacy-first concierge demo."""
import json
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from concierge import answer, requires_deterministic_handling
from llm_client import enabled as ai_enabled, reply as ai_reply

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

    @app.get("/api/capabilities")
    def capabilities():
        return jsonify({
            "ai_chat_enabled": ai_enabled(),
            "live_reservations": False,
            "staff_dispatch": False,
            "flight_booking": False,
        })

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
        history = body.get("history", [])
        if not isinstance(history, list) or len(history) > 8 or any(
            not isinstance(item, dict)
            or item.get("role") not in ("user", "assistant")
            or not isinstance(item.get("content"), str)
            or not 0 < len(item["content"]) <= MAX_MESSAGE_LENGTH
            for item in history
        ):
            return jsonify({"error": "Invalid conversation history."}), 400
        message = message.strip()
        if ai_enabled() and not requires_deterministic_handling(message.lower()):
            reply = ai_reply(message, mode, hotel, history)
            if reply:
                return jsonify({"reply": reply, "suggestions": []})
        return jsonify(answer(message, mode, hotel))

    return app


app = create_app()

if __name__ == "__main__":
    # Use gunicorn or another production WSGI server for hosted deployments.
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "8000")), debug=False)
