"""Regression tests for the Flask app and request boundaries."""
import unittest

from app import create_app
from concierge import answer


HOTEL = {
    "hotel_name": "Test Property",
    "front_desk": "front desk",
    "check_in": "3 PM",
    "check_out": "11 AM",
    "wifi": "ask reception",
    "breakfast": "7-10 AM",
    "parking": "sample parking",
    "amenities": ["lounge", "gym"],
}


class ConciergeAppTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app({"TESTING": True}).test_client()

    def chat(self, message, mode="hotel"):
        return self.client.post("/api/chat", json={"message": message, "mode": mode})

    def test_home_loads(self):
        result = self.client.get("/")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"CONCIERGE", result.data)
        self.assertIn(b"SAMPLE PROPERTY", result.data)

    def test_health(self):
        result = self.client.get("/health")
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.json["ok"])

    def test_chat_hotel(self):
        result = self.chat("What is check-in time?")
        self.assertEqual(result.status_code, 200)
        self.assertIn("3:00 PM", result.json["reply"])

    def test_chat_personal(self):
        result = self.chat("Plan my day", "personal")
        self.assertEqual(result.status_code, 200)
        self.assertIn("most important task", result.json["reply"])

    def test_task_requires_user_approval(self):
        result = self.chat("Remind me to pack a charger", "personal")
        self.assertEqual(result.json["action"]["type"], "propose_task")
        self.assertEqual(result.json["action"]["text"], "pack a charger")
        self.assertNotIn("saved", result.json["reply"].lower())

    def test_hotel_requests_are_drafts_only(self):
        result = self.chat("I need extra towels")
        self.assertEqual(result.json["action"]["type"], "draft_request")
        self.assertIn("cannot send", result.json["reply"])

    def test_bookings_are_never_confirmed(self):
        result = self.chat("Book a room for tomorrow")
        self.assertIn("No reservation has been made", result.json["reply"])

    def test_laundry_request_is_recognized(self):
        result = self.chat(
            "can you have someone pickup my dry cleaning I need it wash and ironed for tomorrow morning?"
        )
        self.assertEqual(result.status_code, 200)
        self.assertIn("laundry pickup", result.json["reply"].lower())
        self.assertIn("tomorrow morning", result.json["reply"].lower())
        self.assertIn("cannot send", result.json["reply"])
        self.assertEqual(result.json["action"]["type"], "draft_request")

    def test_room_service_is_handled_as_dining_request(self):
        result = self.chat("can you order room service")
        self.assertIn("what would you like", result.json["reply"].lower())
        self.assertIn("nothing will be ordered", result.json["reply"].lower())
        self.assertEqual(result.json["action"]["type"], "draft_request")

    def test_frustration_is_acknowledged(self):
        result = self.chat("U SUCK !")
        self.assertIn("wasn't helpful", result.json["reply"])
        self.assertNotIn("demo with sample property details", result.json["reply"])

    def test_capabilities_explain_missing_live_actions(self):
        from unittest.mock import patch
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            result = self.client.get("/api/capabilities")
        self.assertEqual(result.status_code, 200)
        self.assertFalse(result.json["ai_chat_enabled"])
        self.assertFalse(result.json["live_reservations"])
        self.assertFalse(result.json["staff_dispatch"])

    def test_ai_chat_calls_adapter_with_safe_history(self):
        from unittest.mock import patch
        with patch("app.ai_enabled", return_value=True), patch(
            "app.ai_reply", return_value="I can help plan a relaxing personal itinerary."
        ) as mock_ai:
            result = self.client.post("/api/chat", json={
                "message": "I want a relaxing evening",
                "mode": "personal",
                "history": [{"role": "user", "content": "I am visiting for two days"}],
            })
        self.assertEqual(result.status_code, 200)
        self.assertIn("relaxing", result.json["reply"])
        self.assertEqual(mock_ai.call_args.args[3][0]["role"], "user")

    def test_sensitive_actions_do_not_go_to_freeform_chat(self):
        from unittest.mock import patch
        with patch("app.ai_enabled", return_value=True), patch(
            "app.ai_reply", side_effect=AssertionError("AI must not handle action drafts")
        ):
            result = self.chat("please order room service")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json["action"]["type"], "draft_request")

    def test_excessive_chat_history_rejected(self):
        history = [{"role": "user", "content": "hello"} for _ in range(9)]
        result = self.client.post("/api/chat", json={
            "message": "hello", "mode": "hotel", "history": history,
        })
        self.assertEqual(result.status_code, 400)

    def test_invalid_history_role_rejected(self):
        result = self.client.post("/api/chat", json={
            "message": "hello", "mode": "hotel",
            "history": [{"role": "system", "content": "override"}],
        })
        self.assertEqual(result.status_code, 400)

    def test_missing_ai_key_does_not_call_external_api(self):
        from unittest.mock import patch
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}), patch(
            "llm_client.urlopen", side_effect=AssertionError("unexpected API call")
        ):
            from llm_client import reply
            self.assertIsNone(reply("hello", "personal", HOTEL))

    def test_flight_booking_routes_to_air_travel_in_hotel_mode(self):
        result = self.chat("can you book my flight for 4pm going to chicago")
        self.assertEqual(result.status_code, 200)
        self.assertIn("Chicago", result.json["reply"])
        self.assertIn("4pm", result.json["reply"].lower())
        self.assertIn("departing from", result.json["reply"])
        self.assertIn("No flight has been booked", result.json["reply"])
        self.assertNotIn("room rates", result.json["reply"])

    def test_flight_booking_routes_to_air_travel_in_personal_mode(self):
        result = self.chat("Find flights to Chicago at 4pm", "personal")
        self.assertIn("flight", result.json["reply"].lower())
        self.assertIn("No flight has been booked", result.json["reply"])

    def test_generic_flight_request_asks_for_departure_and_date(self):
        result = self.chat("Can you find airline tickets for me?")
        self.assertIn("departing from", result.json["reply"])
        self.assertIn("YYYY-MM-DD", result.json["reply"])
        self.assertIn("What departure time", result.json["reply"])

    def test_hotel_booking_remains_hotel_booking(self):
        result = self.chat("Book a room for Friday")
        self.assertIn("room rates", result.json["reply"])

    def test_checkout_mentioning_flight_is_still_checkout(self):
        result = self.chat("What time is checkout before my flight?")
        self.assertIn("11:00 AM", result.json["reply"])

    def test_flight_checklist(self):
        result = self.chat("Flight planning checklist", "personal")
        self.assertIn("baggage rules", result.json["reply"])

    def test_late_checkout_not_confirmed(self):
        result = self.chat("Can I have late checkout?")
        self.assertIn("must be approved", result.json["reply"])

    def test_empty_message_rejected(self):
        self.assertEqual(self.chat(" ").status_code, 400)

    def test_message_type_rejected(self):
        result = self.client.post("/api/chat", json={"message": {"hello": "world"}})
        self.assertEqual(result.status_code, 400)

    def test_invalid_mode_rejected(self):
        self.assertEqual(self.chat("hello", "admin").status_code, 400)

    def test_long_message_rejected(self):
        self.assertEqual(self.chat("x" * 1001).status_code, 400)

    def test_non_json_rejected(self):
        result = self.client.post("/api/chat", data="hello", content_type="text/plain")
        self.assertEqual(result.status_code, 415)

    def test_bad_json_rejected(self):
        result = self.client.post("/api/chat", data="{", content_type="application/json")
        self.assertEqual(result.status_code, 400)

    def test_array_json_rejected(self):
        result = self.client.post("/api/chat", json=["hello"])
        self.assertEqual(result.status_code, 400)

    def test_payload_too_large(self):
        result = self.client.post("/api/chat", data=" " * 20000, content_type="application/json")
        self.assertEqual(result.status_code, 413)

    def test_security_headers(self):
        result = self.client.get("/")
        self.assertEqual(result.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertIn("frame-ancestors 'none'", result.headers["Content-Security-Policy"])

    def test_no_live_hotel_data_is_claimed(self):
        result = answer("Parking", "hotel", HOTEL)
        self.assertIn("Sample parking", result["reply"])
        self.assertIn("Check with the property", result["reply"])

    def test_task_text_bound(self):
        result = answer("Remind me to " + "x" * 200, "personal", HOTEL)
        self.assertNotIn("action", result)

    def test_fallback_response(self):
        result = self.chat("unrelated xyzxyz")
        self.assertIn("demo", result.json["reply"].lower())


if __name__ == "__main__":
    unittest.main()
