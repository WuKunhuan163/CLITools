EXPECTED_CPU_LIMIT = 95.0
import unittest
import subprocess
import sys
import re
from pathlib import Path


class TestToolStatus(unittest.TestCase):
    """Test TOOL status command."""

    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent
        cls.tool_bin = cls.project_root / "bin" / "TOOL"
        if not cls.tool_bin.exists():
            cls.tool_bin = cls.project_root / "main.py"

    @staticmethod
    def _strip_ansi(text):
        return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    def _run_tool(self, args, timeout=30):
        cmd = [sys.executable, str(self.tool_bin)] + args
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                             cwd=str(self.project_root))
        return res

    def test_status_runs(self):
        """TOOL status should exit 0 and produce output."""
        res = self._run_tool(["status"])
        self.assertEqual(res.returncode, 0, f"TOOL status failed: {res.stderr}")
        output = self._strip_ansi(res.stdout)
        self.assertIn("AITerminalTools Status", output)

    def test_status_shows_header(self):
        """Status output should show the table header."""
        res = self._run_tool(["status"])
        output = self._strip_ansi(res.stdout)
        self.assertIn("Tool", output)
        self.assertIn("Installed", output)
        self.assertIn("Tests", output)

    def test_status_shows_count(self):
        """Status output should show an installed/total count."""
        res = self._run_tool(["status"])
        output = self._strip_ansi(res.stdout)
        self.assertRegex(output, r'\d+/\d+ tools installed')


class TestToolConfigShow(unittest.TestCase):
    """Test TOOL config show command."""

    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent
        cls.tool_bin = cls.project_root / "bin" / "TOOL"
        if not cls.tool_bin.exists():
            cls.tool_bin = cls.project_root / "main.py"

    @staticmethod
    def _strip_ansi(text):
        return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    def _run_tool(self, args, timeout=30):
        cmd = [sys.executable, str(self.tool_bin)] + args
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                             cwd=str(self.project_root))
        return res

    def test_config_show_runs(self):
        """TOOL config show should exit 0."""
        res = self._run_tool(["config", "show"])
        self.assertEqual(res.returncode, 0, f"TOOL config show failed: {res.stderr}")
        output = self._strip_ansi(res.stdout)
        self.assertIn("Global Configuration", output)


class TestToolRule(unittest.TestCase):
    """Test TOOL rule command."""

    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent
        cls.tool_bin = cls.project_root / "bin" / "TOOL"
        if not cls.tool_bin.exists():
            cls.tool_bin = cls.project_root / "main.py"

    @staticmethod
    def _strip_ansi(text):
        return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    def _run_tool(self, args, timeout=30):
        cmd = [sys.executable, str(self.tool_bin)] + args
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                             cwd=str(self.project_root))
        return res

    def test_rule_shows_output(self):
        """TOOL rule should produce the AI agent rule text."""
        res = self._run_tool(["rule"])
        self.assertEqual(res.returncode, 0, f"TOOL rule failed: {res.stderr}")
        output = self._strip_ansi(res.stdout)
        self.assertIn("AI AGENT TOOL RULES", output)
        self.assertIn("INSTALLED TOOLS", output)

    def test_rule_shows_skills(self):
        """TOOL rule should include available skills section."""
        res = self._run_tool(["rule"])
        output = self._strip_ansi(res.stdout)
        self.assertIn("SKILLS", output)


if __name__ == "__main__":
    unittest.main()
