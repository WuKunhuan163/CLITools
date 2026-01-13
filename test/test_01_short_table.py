import unittest
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from proj.utils import format_table, get_display_width

class TestShortTable(unittest.TestCase):
    def test_01_short_table(self):
        """(1) 输出一个短小的正常表格，验证每一行宽度一样。"""
        headers = ["ID", "Name", "Status"]
        rows = [
            ["1", "Alice", "Active"],
            ["2", "Bob", "Inactive"],
            ["3", "Charlie", "Pending"]
        ]
        
        table_str, report_path = format_table(headers, rows)
        lines = table_str.splitlines()
        
        # Verify all lines have the same display width
        widths = [get_display_width(line) for line in lines]
        self.assertTrue(all(w == widths[0] for w in widths), f"Widths are not consistent: {widths}")
        print("\nShort table output:")
        print(table_str)

if __name__ == "__main__":
    unittest.main()

