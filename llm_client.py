"""Optional conversational models; no tools, payments, booking, or service authority.

OpenAI hosted chat is opt-in with OPENAI_API_KEY. Ollama local chat is opt-in
with OLLAMA_MODEL, and uses a fixed localhost endpoint (not a user URL).
"""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"
API_ERRORS = (HTTPError, URLError, TimeoutError, OSError, ValueError,
              KeyError, IndexError, TypeError)


def enabled():
    return bool(
        os.environ.get("OLLAMA_MODEL", "").strip()
        or os.environ.get("OPENAI_API_KEY", "").strip()
    )


def reply(message, mode, hotel, history=None):
    """Generate a conversation-only response; return None on config/API failure.

    The provider is selected by local environment, never by a chat message.
    Ollama takes priority if configured, avoiding unexpected hosted API charges.
    No external tool calls or model actions are supported.
    """
    ollama_model = os.environ.get("OLLAMA_MODEL", "").strip()
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not (ollama_model or key):
        return None

    hotel_context = json.dumps(hotel, ensure_ascii=False)
    system = (
        "You are Concierge, a clear, helpful virtual hotel concierge and personal "
        "assistant for a demonstration app. Be conversational and acknowledge "
        "specific requests naturally. Ask at most one or two useful follow-up "
        "questions. Keep most replies under 110 words. "
        "You are NOT connected to hotel staff, laundry, room service, booking, "
        "flights, calendars, customer accounts, payments, or any live inventory. "
        "NEVER claim to have ordered, scheduled, confirmed, sent, paid for, or "
        "reserved anything; never invent actual prices, schedules, amenities, "
        "hotel contacts, or confirmation numbers. Offer to help compose a "
        "request for the guest to contact staff, but clarify it is not submitted. "
        "Only refer to hotel details explicitly present in the JSON below, "
        "which is SAMPLE information, not a real property. "
        "If a guest is upset, acknowledge the specific problem and improve the "
        "answer without canned apologies or excuses. "
        "Do not request payment cards, passwords, or private identifiers. "
        "Current mode: " + mode + ". Example property information: " + hotel_context
    )
    messages = [{"role": "system", "content": system}]
    if isinstance(history, list):
        for entry in history[-8:]:
            if (
                isinstance(entry, dict)
                and entry.get("role") in ("user", "assistant")
                and isinstance(entry.get("content"), str)
                and 0 < len(entry["content"]) <= 1000
            ):
                messages.append({
                    "role": entry["role"], "content": entry["content"]
                })
    messages.append({"role": "user", "content": message})

    if ollama_model:
        payload = json.dumps({
            "model": ollama_model,
            "messages": messages,
            "stream": False,
            "options": {"num_predict": 280, "temperature": 0.4},
        }).encode("utf-8")
        req = Request(OLLAMA_CHAT_URL, data=payload,
                      headers={"Content-Type": "application/json"},
                      method="POST")
        timeout = 35
    else:
        payload = json.dumps({
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "messages": messages,
            "max_tokens": 280,
            "temperature": 0.4,
        }).encode("utf-8")
        req = Request(OPENAI_CHAT_URL, data=payload, headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + key,
        }, method="POST")
        timeout = 12

    try:
        with urlopen(req, timeout=timeout) as response:
            data = json.load(response)
        if ollama_model:
            result = data["message"]["content"]
        else:
            result = data["choices"][0]["message"]["content"]
        if isinstance(result, str) and result.strip():
            return result.strip()[:1800]
    except API_ERRORS:
        return None
    return None
