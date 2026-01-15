import unittest
import subprocess
from pathlib import Path
import os
import sys

# Add project root to path so we can import proj.utils
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from proj.utils import format_table

class TestArabicAllFeatures(unittest.TestCase):
    def setUp(self):
        self.tool_bin = project_root / "bin" / "TOOL"
        if not self.tool_bin.exists():
            subprocess.run(["python3", "setup.py"], cwd=str(project_root))

    def run_tool(self, args, env=None):
        cmd = [str(self.tool_bin)] + args
        current_env = os.environ.copy()
        if env:
            current_env.update(env)
        return subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_root), env=current_env)

    def test_08_arabic_table_various_scenarios(self):
        """(8) 测试阿拉伯语表格的各种显示情况。"""
        headers = ["الاسم", "الوصف", "الحالة"]
        
        # Scenario 1: Long content with truncation
        rows = [
            ["أداة المستخدم", "هذا وصف طويل جداً يتجاوز العرض المعتاد للعمود للتحقق من التقطيع", "نشط"],
            ["أداة الخلفية", "إدارة العمليات في الخلفية", "مكتمل"]
        ]
        
        # Simulate format_table with terminal width constraint
        # We manually call format_table with is_rtl=True
        from proj.utils import set_rtl_mode
        set_rtl_mode(True)
        output_tuple = format_table(headers, rows)
        output = output_tuple[0]
        print("\n--- Arabic Table (Standard) ---")
        print(output)
        
        # Check for Arabic text
        self.assertIn("الاسم", output)
        
        # Scenario 2: ANSI colors
        rows_colored = [
            ["\033[1;32mأداة\033[0m", "وصف ملون", "\033[1;31mخطأ\033[0m"]
        ]
        output_colored_tuple = format_table(headers, rows_colored)
        output_colored = output_colored_tuple[0]
        print("\n--- Arabic Table (Colored) ---")
        print(output_colored)
        self.assertIn("\033[1;32m", output_colored)
        set_rtl_mode(False)
        
    def test_09_arabic_command_output(self):
        """(9) 测试 TOOL lang list 在阿拉伯语环境下的输出。"""
        # Set TOOL_LANGUAGE to ar
        res = self.run_tool(["lang", "list"], env={"TOOL_LANGUAGE": "ar"})
        self.assertEqual(res.returncode, 0)
        print("\n--- TOOL lang list (ar) ---")
        print(res.stdout)
        
        # Check for Arabic headers in the table output
        self.assertIn("اللغات المدعومة", res.stdout)
        self.assertIn("تغطية المفاتيح", res.stdout)
        self.assertIn("العربية", res.stdout)

if __name__ == "__main__":
    unittest.main()

