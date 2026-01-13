import unittest
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from proj.utils import format_table, get_display_width

class TestArabicTable(unittest.TestCase):
    def test_03_arabic_table(self):
        """(3) 阿拉伯语表格，验证从右往左显示的功能。"""
        headers = ["المعرف", "الاسم", "الحالة"]
        rows = [
            ["١", "أليس", "نشط"],
            ["٢", "باسم", "غير نشط"],
            ["٣", "جميل", "قيد الانتظار"]
        ]
        
        # Test RTL display
        table_str, report_path = format_table(headers, rows, is_rtl=True)
        lines = table_str.splitlines()
        
        # Verify RTL markers are present in header and data rows (but not separator)
        self.assertIn("\u202b", lines[1])
        self.assertIn("\u202c", lines[1])
        self.assertIn("\u202b", lines[3])
        self.assertIn("\u202c", lines[3])
        
        # Verify all lines have the same display width (ignoring markers)
        widths = [get_display_width(line) for line in lines]
        self.assertTrue(all(w == widths[0] for w in widths), f"Widths are not consistent: {widths}")
        
        print("\nArabic (RTL) table output:")
        # Note: Terminal might not render RTL correctly depending on environment, 
        # but we check the presence of markers and consistent width.
        print(table_str)

if __name__ == "__main__":
    unittest.main()

