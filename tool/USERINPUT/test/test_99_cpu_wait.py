import unittest
import time

EXPECTED_CPU_LIMIT = 20.0

class TestCPUWaiting(unittest.TestCase):
    def test_wait(self):
        print("Test started after waiting for CPU!")
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()

