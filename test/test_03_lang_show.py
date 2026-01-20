import unittest
import subprocess
from pathlib import Path

class TestLangShow(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).resolve().parent.parent
        self.tool_bin = self.project_root / "bin" / "TOOL"
        if not self.tool_bin.exists():
            subprocess.run(["python3", "setup.py"], cwd=str(self.project_root))

    def run_tool(self, args):
        cmd = [str(self.tool_bin)] + args
        return subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.project_root))

    def test_04_lang_show(self):
        """(4) 测试显示当前语言。"""
        res = self.run_tool(["lang"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("(", res.stdout)
        self.assertIn(")", res.stdout)

if __name__ == "__main__":
    unittest.main()

