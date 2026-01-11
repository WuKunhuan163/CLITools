import unittest
import time
class TestSleep5(unittest.TestCase):
    def test_sleep(self):
        time.sleep(5)
        self.assertTrue(True)
if __name__ == '__main__':
    unittest.main()
