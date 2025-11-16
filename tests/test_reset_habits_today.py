import unittest
from unittest.mock import MagicMock, patch

import web_app


class ResetHabitsTodayTestCase(unittest.TestCase):
    def setUp(self):
        # Use the Flask app defined in web_app.py
        self.app = web_app.app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        # Seed a fake logged-in user in the session (useruid matches how habits store userID)
        with self.client.session_transaction() as sess:
            sess["useremail"] = "test@example.com"
            sess["useruid"] = "test-uid"

    @patch("web_app.db")
    def test_reset_habits_today_sets_is_completed_false(self, mock_db):
        """
        Ensure /reset-habits-today iterates over the user's habits
        and calls update to clear isCompletedToday.
        """

        # Mock Firestore habits collection query:
        # db.collection('habits').where('userID', '==', user_id).stream()
        mock_habit_doc1 = MagicMock()
        mock_habit_doc2 = MagicMock()

        mock_habits_collection = MagicMock()
        mock_habits_collection.where.return_value = mock_habits_collection
        mock_habits_collection.stream.return_value = [mock_habit_doc1, mock_habit_doc2]

        # db.collection('habits') -> mock_habits_collection
        def collection_side_effect(name):
            if name == "habits":
                return mock_habits_collection
            return MagicMock()

        mock_db.collection.side_effect = collection_side_effect

        # If your route uses a Firestore batch (as in the earlier suggestion)
        mock_batch = MagicMock()
        mock_db.batch.return_value = mock_batch

        # Call the endpoint
        resp = self.client.put("/reset-habits-today")
        self.assertEqual(resp.status_code, 200)

        data = resp.get_json()
        self.assertIsNotNone(data)
        self.assertTrue(data.get("success"))

        # Assert the batch update was called for each habit doc and committed once
        self.assertTrue(mock_db.batch.called)
        self.assertEqual(mock_batch.update.call_count, 2)
        mock_batch.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
