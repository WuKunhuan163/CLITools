#!/usr/bin/env python3
import unittest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to sys.path
script_dir = Path(__file__).resolve().parent
tool_root = script_dir.parent
project_root = tool_root.parent.parent
sys.path.append(str(project_root))

from tool.READ.main import ReadTool

class TestReadTool(unittest.TestCase):
    def setUp(self):
        self.tool = ReadTool()

    def test_init(self):
        self.assertEqual(self.tool.tool_name, "READ")

    @patch('sys.stdout')
    def test_demo(self, mock_stdout):
        with patch('sys.argv', ['tool/READ/main.py', '--demo']):
            self.tool.run()
            # Verify it ran without crashing

    def test_translation(self):
        # Verify translations are loaded
        desc = self.tool.get_translation("tool_READ_desc", "Default")
        self.assertNotEqual(desc, "Default")

if __name__ == "__main__":
    unittest.main()
