"""Optional hosted conversational mode; disabled unless explicitly configured.

Only text is sent to the model; no tools, payments, bookings, or service actions.
The URL is fixed to prevent arbitrary endpoint requests.
"""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


def enabled():
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def reply(message, mode, hotel, history=None):
    """Return model text or None if not configured/unavailable.

    Never forward API error bodies or credentials to users. Caller falls back to
    deterministic responses. This function has no tools or action privileges.
    """
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
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
        "hotel contacts, or a confirmation number. Offer to help compose a "
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
    try:
        with urlopen(req, timeout=12) as response:
            data = json.load(response)
        result = data["choices"][0]["message"]["content"]
        if isinstance(result, str) and result.strip():
            return result.strip()[:1800]
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError, IndexError, TypeError):
        return None
    return None
