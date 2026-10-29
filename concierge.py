"""Deterministic concierge responses. No external AI services or invented bookings."""
import re


def response(text, suggestions=None, action=None):
    result = {"reply": text, "suggestions": suggestions or []}
    if action:
        result["action"] = action
    return result


def answer(message, mode, hotel):
    text = message.lower().strip()
    if mode == "personal":
        return personal_answer(message, text)
    return hotel_answer(message, text, hotel)


def is_flight_request(text):
    """Match explicit air-travel language without treating every booking as a flight."""
    return bool(re.search(
        r"\b(?:flight|flights|airfare|airline|airlines|airports?|flying|fly|plane tickets?)\b",
        text,
    ))


def flight_answer(message, text):
    """Guide air-travel planning without claiming external booking capabilities."""
    destination = "Chicago (O'Hare/ORD or Midway/MDW)" if re.search(r"\bchicago\b", text) else None
    time = re.search(r"\b(?:1[0-2]|0?[1-9])(?::[0-5]\d)?\s*(?:am|pm)\b", message, re.I)

    if destination:
        opening = f"I can help you plan travel to {destination}. "
    else:
        opening = "I can help you plan air travel. "

    questions = [
        "Which airport or city are you departing from?",
        "What is your travel date (YYYY-MM-DD)?",
    ]
    if time:
        questions.append(f"Is {time.group(0).strip()} your preferred departure or arrival time?")
    else:
        questions.append("What departure time works for you?")

    return response(
        opening
        + "This demo does not have live flight schedules, fares, or booking access. "
        + "No flight has been booked or paid for. "
        + " ".join(questions),
        ["Flight planning checklist", "Packing checklist"],
    )


def personal_answer(message, text):
    task = re.match(r"^\s*(?:remind me to|remember to|add (?:a )?task(?: to)?|i need to)\s+(.+?)\s*[.!]?\s*$", message, re.I)
    if task:
        task_text = task.group(1).strip().rstrip(".!")
        if len(task_text) > 160:
            return response("Shorten that task to 160 characters before adding it.")
        return response(
            "Here's a task ready for your private checklist. Select Add task to save it on this browser.",
            ["Plan my day", "Packing checklist"],
            {"type": "propose_task", "text": task_text},
        )
    if "flight planning checklist" in text:
        return response(
            "For a flight, confirm your departure and arrival airports, travel date, "
            "departure versus arrival time, baggage rules, ID, and ground transportation. "
            "Check live airline availability before purchasing any ticket.",
            ["Packing checklist", "Plan my day"],
        )
    if is_flight_request(text):
        return flight_answer(message, text)
    if any(word in text for word in ("plan my day", "schedule", "itinerary", "organize my day")):
        return response(
            "Start with your one most important task, then add two smaller tasks. "
            "Put time-sensitive commitments first and leave a break between them. "
            "Use the checklist here to keep track of your plan.",
            ["Remind me to pack my charger", "Packing checklist"],
        )
    if any(word in text for word in ("packing", "pack for", "what to bring")):
        return response(
            "Packing starter list: ID, travel documents, medications, phone charger, "
            "weather-appropriate clothes, toiletries, and reservation details. "
            "Review the list for your own trip and add items to the checklist.",
            ["Remind me to pack my charger", "Plan my day"],
        )
    if any(word in text for word in ("reminder", "notify me", "alarm")):
        return response(
            "I can organize a task in your browser, but I cannot send push notifications "
            "or timed alerts. For an actual alarm, use your phone's reminders app.",
            ["Remind me to call the front desk", "Plan my day"],
        )
    if any(word in text for word in ("hello", "hi ", "hey", "good morning")):
        return response(
            "Hello! I can help with planning, packing, and organizing personal tasks. "
            "What would you like to do first?",
            ["Plan my day", "Packing checklist"],
        )
    return response(
        "I can help you plan your day, make a packing checklist, or draft a to-do item. "
        "Try 'Remind me to pack my charger' to add a task with your approval.",
        ["Plan my day", "Packing checklist", "Remind me to pack my charger"],
    )


def hotel_answer(message, text, hotel):
    name = hotel["hotel_name"]
    desk = hotel["front_desk"]
    if any(k in text for k in ("emergency", "fire", "medical emergency", "in danger")):
        return response(
            "For an immediate emergency, call local emergency services. "
            f"For hotel assistance, contact the front desk: {desk}.",
            ["Front desk", "Hotel amenities"],
        )
    if any(k in text for k in ("late checkout", "late check-out", "extend checkout", "extend my stay")):
        return response(
            f"Standard checkout is {hotel['check_out']}. Late checkout is subject to "
            "availability and must be approved by the front desk. "
            f"Contact {desk}; I cannot confirm an extension.",
            ["Check-in time", "Front desk"],
        )
    if any(k in text for k in ("check-in", "check in", "checkin", "arrival time")):
        return response(
            f"Sample check-in time for {name}: {hotel['check_in']}. "
            f"Confirm your arrival arrangements with the front desk at {desk}.",
            ["Check-out time", "Parking"],
        )
    if any(k in text for k in ("check-out", "check out", "checkout", "departure")):
        return response(
            f"Sample checkout time for {name}: {hotel['check_out']}. "
            "Ask the front desk about luggage storage or late checkout.",
            ["Late checkout", "Front desk"],
        )
    if any(k in text for k in ("wifi", "wi-fi", "internet", "password")):
        return response(
            f"Wi-Fi information: {hotel['wifi']}. "
            "For a private access code, verify with the front desk; don't share passwords here.",
            ["Breakfast", "Front desk"],
        )
    if any(k in text for k in ("breakfast", "restaurant", "dining", "coffee")):
        return response(
            f"Sample dining information: {hotel['breakfast']}. "
            "Hours and availability should be confirmed with the property.",
            ["Parking", "Hotel amenities"],
        )
    if any(k in text for k in ("parking", "car park", "valet")):
        return response(
            f"Sample parking information: {hotel['parking']}. "
            "Check with the property for pricing and availability.",
            ["Check-in time", "Front desk"],
        )
    if any(k in text for k in ("pool", "gym", "fitness", "spa", "amenit", "facilities")):
        return response(
            "Sample amenities: " + ", ".join(hotel["amenities"]) +
            ". Confirm hours and availability with the front desk.",
            ["Breakfast", "Parking"],
        )
    if any(k in text for k in ("housekeeping", "extra towel", "clean my room", "room service", "maintenance", "broken")):
        detail = message.strip()[:160]
        return response(
            "I can prepare a service request for you to copy, but this demo cannot send "
            "it to hotel staff or confirm service. Contact the front desk for assistance.",
            ["Front desk", "Hotel amenities"],
            {"type": "draft_request", "text": detail},
        )
    if "flight planning checklist" in text:
        return response(
            "To plan your flight, prepare departure and destination airports, travel date, "
            "preferred departure or arrival time, luggage needs, and transport to the hotel. "
            "This demo cannot look up live fares or book tickets.",
            ["Flight to Chicago around 4 PM", "Front desk"],
        )
    if is_flight_request(text):
        return flight_answer(message, text)
    if any(k in text for k in ("book", "reservation", "reserve", "availability", "price", "rate")):
        return response(
            f"I can help you prepare questions for {name}, but I do not have live "
            "room rates, inventory, or booking access. No reservation has been made. "
            f"Please contact {desk} to verify availability and book.",
            ["Check-in time", "Front desk"],
        )
    if any(k in text for k in ("front desk", "contact", "phone", "help", "reception")):
        return response(
            f"Front desk information for this sample hotel: {desk}. "
            "Replace sample details with verified contact information before going live.",
            ["Check-in time", "Hotel amenities"],
        )
    if any(k in text for k in ("hello", "hi ", "hey", "good morning")):
        return response(
            f"Welcome to {name}! I can answer sample questions about check-in, "
            "amenities, dining, parking, and service-request drafts.",
            ["Check-in time", "Breakfast", "Parking"],
        )
    return response(
        "I can help with hotel information and draft service requests. This is a "
        "demo with sample property details, not a connected reservation system.",
        ["Check-in time", "Breakfast", "Hotel amenities", "Front desk"],
    )
