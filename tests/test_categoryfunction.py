# tests/test_category_route_unittest.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
#since it's in a subfolder and main is in the rootfolder, i needed to tell it to search on the root folder for main.py

import unittest
from main import app, habits

class TestCategoryRoute(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        # Reset habits before each test
        global habits
        habits[:] = [
            {"id": 1, "name": "Drink water", "completed": False, "category": "Health"},
            {"id": 2, "name": "Exercise", "completed": False, "category": "Fitness"},
            {"id": 3, "name": "Meditate", "completed": True, "category": "health"},
            {"id": 4, "name": "Read", "completed": False, "category": "Productivity"},
        ]

    def test_health_category(self):
        resp = self.client.get("/habits/category/Health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        names = sorted([h["name"] for h in data])
        self.assertEqual(names, ["Drink water", "Meditate"])

    def test_lowercase_category(self):
        resp = self.client.get("/habits/category/fitness")
        data = resp.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Exercise")

    def test_unknown_category(self):
        resp = self.client.get("/habits/category/Nonexistent")
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data, [])

if __name__ == "__main__":
    unittest.main()
