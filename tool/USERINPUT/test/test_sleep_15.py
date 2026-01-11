import unittest
import time
class TestSleep15(unittest.TestCase):
    def test_sleep(self):
        time.sleep(15)
        self.assertTrue(True)
if __name__ == '__main__':
    unittest.main()
