# test_example.py
import unittest
from HabitHive import filter_habits

TEST_HABITS = [
    {"id": 1, "name": "Drink water", "completed": False, "category": "Health"},
    {"id": 2, "name": "Exercise", "completed": False, "category": "Fitness"},
]

class TestHabitFunctions(unittest.TestCase):
    
    def test_filter_health_category(self):
        result = filter_habits("Health")
        names = [h["name"] for h in result]
        self.assertEqual(sorted(names), ["Drink water"])

    def test_filter_no_match(self):
        result = filter_habits("Nonexistent")
        self.assertEqual(result, [])

if __name__ == "__main__":
    unittest.main()
