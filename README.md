# Concierge — Hotel Helper & Personal Assistant

A self-hostable **Flask** concierge demo built for **AI Task Flo**. It includes a responsive chat interface with two modes:

- **Hotel Concierge:** Answer sample questions about check-in, check-out, Wi-Fi, breakfast, parking and amenities. Prepare service-request drafts. It never claims to have made a booking or sent an order.
- **Flight trip planning:** Recognize flight requests in either mode and request origin, travel date, and preferred departure/arrival time. This is an information-gathering demo, **not** live flight search or ticket purchasing.
- **Personal Assistant:** Help plan a day or pack for travel, and propose checklist items. Tasks are added only when a user selects **Add task**, and are saved in that browser's local storage.

The repository began as a README-only project. It works in **offline, rules-based demo mode** without any credentials. Optionally, you can enable **real AI conversation** for general questions. Service and booking actions remain permission-bounded drafts, never silently executed.

## Quick start

Requires Python 3.10+ (Python 3.12 recommended).

~~~bash
git clone https://github.com/rcastrejon91/concierge-bot.git
cd concierge-bot
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
python app.py
~~~

Open **http://127.0.0.1:8000**.

If you are reviewing this in a PR before merging, clone the branch with:

~~~bash
git fetch origin feat/hotel-concierge-personal-assistant
git switch feat/hotel-concierge-personal-assistant
~~~

## Enable conversational AI (optional)

Without an API key, the bot is a **basic demo** and will only recognize preprogrammed topics. To answer more open-ended guest questions, enable the OpenAI API integration. This uses **separate API billing**; a ChatGPT subscription does **not** automatically include API credits.

In PowerShell, from the project directory:

~~~powershell
$env:OPENAI_API_KEY = Read-Host "Enter your OpenAI API key"
$env:OPENAI_MODEL = "gpt-4o-mini"
.\.venv\Scripts\python.exe app.py
~~~

Use a **separately created, restricted API key**. Never paste a real key into chat, GitHub, source files, browser JavaScript, or a public environment variable. The value above exists only in the current PowerShell session. You can remove it with the PowerShell command Remove-Item Env:OPENAI_API_KEY.

Open http://127.0.0.1:8000/api/capabilities to see whether AI chat is enabled. General conversations send the **current message and up to eight recent messages** to the API. The app does not persist transcripts, but requests sent to an external AI service are subject to that provider's terms and data-handling policies.

**The optional AI mode is conversation only:** it cannot contact hotel staff, make reservations, charge cards, set reminders, or buy airline tickets. Service/booking requests use deterministic draft handling; no free-form model output is authorized to call external actions. When the API is unavailable, the app falls back to basic demo responses.

## Run tests

~~~bash
python -m unittest discover -s tests -v
python -m compileall -q app.py concierge.py
~~~

## Docker

~~~bash
docker build -t concierge-bot .
docker run --rm -p 8000:8000 concierge-bot
~~~

Then open http://127.0.0.1:8000.

## Configuration

Edit [hotel.json](hotel.json) to change the sample hotel name, times, front-desk contact, parking, Wi-Fi, and amenities. **All starter hotel details are fictional examples.** Verify information with an actual hotel before any live use.

| Endpoint | Method | Purpose |
| --- | --- | --- |
| / | GET | Responsive guest chat and personal checklist |
| /health | GET | Simple health check |
| /api/chat | POST | Text response in hotel or personal mode |

Chat example:

~~~bash
curl -s http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"What time is check-in?","mode":"hotel"}'
~~~

Responses contain **reply**, **suggestions**, and sometimes **action**, such as **propose_task** or **draft_request**. A proposed action is **not automatically executed**.

## Privacy, security, and limitations

- Chat messages are processed for the current HTTP request only. This app does not save transcripts or send them to an AI provider.
- Checklist items stay in the current browser's local storage. **Do not store secrets, medical records, or sensitive guest details**, particularly on shared devices.
- The demo has **no user authentication, room verification, admin dashboard, push notifications, payment processing, property-management-system integration, email sending, or live reservations**.
- Housekeeping and service requests are **copyable drafts only**; nothing is dispatched to hotel staff.
- The hotel details are examples. Do not represent this project as integrated with a real property until verified and authorized.
- Default mode is deterministic and limited. With a configured API key, general conversation uses a hosted LLM. It is **not** an autonomous agent with tools or purchase authority.
- Production hosting needs HTTPS, request throttling, monitoring, and abuse protection. Future guest authentication, real service routing, email/calendar, or reservation integrations require explicit authorization and appropriate privacy controls.

## Roadmap

1. Configure real property information and verified hotel contacts.
2. Add secure staff authentication and confirmation workflows for service requests.
3. Integrate authorized PMS/booking APIs with explicit booking confirmations.
4. Connect AI Task Flo/Lira behind authenticated model endpoints if you prefer Lira over the optional OpenAI API integration.
5. Add multilingual support and opt-in reminders.

## License

No license has been granted yet. Contact the repository owner before reusing the code outside this project.
