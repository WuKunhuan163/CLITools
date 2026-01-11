import unittest

class TestUserInputBasic(unittest.TestCase):
    def test_basic_check(self):
        """A simple check for USERINPUT."""
        self.assertTrue(True)

    def test_another_check(self):
        """Another simple check."""
        self.assertFalse(False)

if __name__ == '__main__':
    unittest.main()
