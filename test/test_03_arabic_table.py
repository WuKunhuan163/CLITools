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
        from proj.utils import set_rtl_mode
        set_rtl_mode(True)
        table_str, report_path = format_table(headers, rows)
        lines = table_str.splitlines()
        
        # Verify consistent width (ignoring markers which are now handled by print)
        widths = [get_display_width(line) for line in lines]
        self.assertTrue(all(w == widths[0] for w in widths), f"Widths are not consistent: {widths}")
        
        print("\nArabic (RTL) table output:")
        print(table_str)
        set_rtl_mode(False)

if __name__ == "__main__":
    unittest.main()

