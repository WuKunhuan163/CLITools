"""
GCS Shell Type Test

Tests shell type switching and executor shell_type integration.
Does NOT test remote installation (requires apt-get on Colab).
"""
EXPECTED_TIMEOUT = 60
EXPECTED_CPU_LIMIT = 60.0

import unittest
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent.parent

from mcp_test_base import MCPTestCase


class TestShellType(MCPTestCase):
    """Test shell type management commands."""

    def test_01_show_type(self):
        """--shell type should show current shell type."""
        res = self.gcs(["--shell", "type"], use_mcp=False, timeout=15)
        output = self.strip_ansi(res.stdout)
        self.assertSuccess(res)
        self.assertIn("shell type", output.lower())

    def test_02_switch_to_zsh(self):
        """--shell type zsh should switch and confirm."""
        res = self.gcs(["--shell", "type", "zsh"], use_mcp=False, timeout=15)
        output = self.strip_ansi(res.stdout)
        self.assertSuccess(res)
        self.assertIn("zsh", output.lower())

    def test_03_verify_zsh_active(self):
        """After switching, --shell type should report zsh."""
        res = self.gcs(["--shell", "type"], use_mcp=False, timeout=15)
        output = self.strip_ansi(res.stdout)
        self.assertIn("zsh", output.lower())

    def test_04_switch_back_to_bash(self):
        """Switch back to bash."""
        res = self.gcs(["--shell", "type", "bash"], use_mcp=False, timeout=15)
        self.assertSuccess(res)

    def test_05_invalid_shell_type(self):
        """Unsupported shell type should show error."""
        res = self.gcs(["--shell", "type", "tcsh"], use_mcp=False, timeout=15)
        output = self.strip_ansi(res.stdout + res.stderr)
        self.assertIn("unknown", output.lower())

    def test_06_executor_generates_shell_type(self):
        """Executor should include specified shell_type in generated script."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "gcs_executor",
            str(project_root / "tool" / "GOOGLE.GCS" / "logic" / "executor.py")
        )
        executor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(executor)

        script, _ = executor.generate_remote_command_script(
            project_root, "echo test", shell_type="zsh"
        )
        self.assertIn("zsh", script)
        self.assertIn("REMOTE_ENV/shell/zsh/bin/zsh", script)


if __name__ == "__main__":
    unittest.main()
