import unittest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to sys.path
def find_root():
    curr = Path(__file__).resolve().parent
    while curr != curr.parent:
        if (curr / "tool.json").exists() and (curr / "bin").exists():
            return curr
        curr = curr.parent
    return None

project_root = find_root()
if project_root and str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tool.iCloud.tool.iCloudPD.main import main

class TestICloudPD(unittest.TestCase):
    @patch('sys.argv', ['iCloudPD', '--since', '2024-04-19', '--before', '2024-04-20'])
    @patch('tool.iCloud.tool.iCloudPD.main.ToolBase')
    @patch('tool.iCloud.logic.interface.main.get_icloud_interface')
    def test_main_arg_parsing(self, mock_get_interface, mock_tool_base):
        # Mock ToolBase.handle_command_line to return False (not handled)
        mock_tool_instance = mock_tool_base.return_value
        mock_tool_instance.handle_command_line.return_value = False
        
        # Mock iCloud interface to return a failure early so we don't proceed to real logic
        mock_interface = mock_get_interface.return_value
        mock_interface["run_login_gui"].return_value = {"status": "cancelled"}
        
        # Run main and expect SystemExit due to auth failure
        with self.assertRaises(SystemExit):
            main()
            
        # Verify ToolBase was initialized with correct name
        mock_tool_base.assert_called_with("iCloudPD")

if __name__ == "__main__":
    unittest.main()

