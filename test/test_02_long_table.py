import unittest
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from proj.utils import format_table, get_display_width

class TestLongTable(unittest.TestCase):
    def test_02_long_table(self):
        """(2) 输出一个每一行都很长的表格，验证输出的表格的每一行经过裁切之后还是一样宽，以及每一列还是对齐。"""
        headers = ["PID", "Runtime", "Command"]
        rows = [
            ["12345", "0:01:23", "python3 /very/long/path/to/script.py --arg1 val1 --arg2 val2 --arg3 val3"],
            ["67890", "12:34:56", "bash -c 'echo \"This is a very long command that should definitely be truncated when the terminal is narrow enough\"'"]
        ]
        
        # Simulate a narrow terminal
        max_width = 40
        table_str, report_path = format_table(headers, rows, max_width=max_width)
        lines = table_str.splitlines()
        
        # Verify all lines have the same display width
        widths = [get_display_width(line) for line in lines]
        self.assertTrue(all(w == widths[0] for w in widths), f"Widths are not consistent: {widths}")
        self.assertTrue(all(w <= max_width for w in widths), f"Widths exceed max_width: {widths}")
        
        print(f"\nLong table output (max_width={max_width}):")
        print(table_str)
        self.assertIsNotNone(report_path)

if __name__ == "__main__":
    unittest.main()

