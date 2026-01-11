import unittest
import time
class TestSleep10(unittest.TestCase):
    def test_sleep(self):
        time.sleep(10)
        self.assertTrue(True)
if __name__ == '__main__':
    unittest.main()
