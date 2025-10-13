import unittest
from example import addition

# Please Start your file with "test_..." so the workflow can identify as it a test

class TestExample(unittest.TestCase):
    def test_add(self):
        self.assertEqual(addition(2, 3), 5)  # Passes if add(2,3) == 5
        self.assertEqual(addition(-1, 1), 0) # Passes if add(-1,1) == 0

if __name__ == '__main__':
    unittest.main()
