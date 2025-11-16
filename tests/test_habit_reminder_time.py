import unittest
from unittest.mock import MagicMock, patch

import web_app


class HabitReminderTimeTestCase(unittest.TestCase):
    def setUp(self):
        self.app = web_app.app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        # If your update route expects an authenticated session:
        with self.client.session_transaction() as sess:
            sess["useremail"] = "test@example.com"
            sess["useruid"] = "test-uid"

    @patch("web_app.db")
    def test_update_habit_reminder_time(self, mock_db):
        """
        PUT /api/habits/<habit_id> should update reminderTime
        (and optionally reminderEnabled) on the habit document.
        """

        habit_id = "habit-123"

        # Mock Firestore habit doc
        mock_doc_ref = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc_ref.get.return_value = mock_doc

        mock_habits_collection = MagicMock()
        mock_habits_collection.document.return_value = mock_doc_ref

        def collection_side_effect(name):
            if name == "habits":
                return mock_habits_collection
            return MagicMock()

        mock_db.collection.side_effect = collection_side_effect

        # New reminder values to send
        new_time = "08:30"
        payload = {
            "reminderTime": new_time,
            "reminderEnabled": True,
        }

        resp = self.client.put(f"/api/habits/{habit_id}", json=payload)
        self.assertEqual(resp.status_code, 200)

        data = resp.get_json()
        self.assertIsNotNone(data)
        self.assertTrue(data.get("success"))

        # Ensure Firestore update was called with reminderTime changed
        mock_doc_ref.update.assert_called_once()
        update_arg, = mock_doc_ref.update.call_args[0]
        self.assertEqual(update_arg.get("reminderTime"), new_time)
        # Optional: also check reminderEnabled if your route updates it
        self.assertEqual(update_arg.get("reminderEnabled"), True)


if __name__ == "__main__":
    unittest.main()
