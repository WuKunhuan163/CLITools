import unittest
import os
import shutil

class TestTerminalPermission(unittest.TestCase):
    def test_terminal_size_permission(self):
        """Test if os.get_terminal_size() is accessible without permission errors."""
        try:
            size = os.get_terminal_size()
            print(f"\nDetected terminal size: {size.columns} columns, {size.lines} lines")
            self.assertGreater(size.columns, 0)
            self.assertGreater(size.lines, 0)
        except OSError as e:
            # Catch the specific errors reported in restricted environments
            # [Errno 102] Operation not supported on socket
            # [Errno 25] Inappropriate ioctl for device (happens when piped)
            print(f"\nTerminal size detection failed: {e}")
            if e.errno in [102, 25]:
                self.skipTest(f"Terminal size detection not supported in this environment ({e}).")
            else:
                raise e

    def test_shutil_get_terminal_size(self):
        """Test if shutil.get_terminal_size() falls back gracefully."""
        # This one should never raise OSError, it has a fallback
        size = shutil.get_terminal_size(fallback=(80, 24))
        print(f"shutil.get_terminal_size fallback: {size.columns}x{size.lines}")
        self.assertGreaterEqual(size.columns, 0)

if __name__ == "__main__":
    unittest.main()

