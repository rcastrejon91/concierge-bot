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
