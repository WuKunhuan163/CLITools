EXPECTED_CPU_LIMIT = 60.0
import unittest
import sys
from pathlib import Path

project_root = Path("/Applications/AITerminalTools")
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class TestExecutorScriptGeneration(unittest.TestCase):
    """Test remote command script generation (no API calls needed)."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "gcs_executor",
            str(project_root / "tool" / "GOOGLE.GCS" / "logic" / "executor.py")
        )
        cls.executor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.executor)

    def test_01_generate_bash_script(self):
        """generate_remote_command_script should produce a valid Python script for bash commands."""
        script, metadata = self.executor.generate_remote_command_script(
            project_root, "echo Hello", as_python=False
        )
        self.assertIsInstance(script, str)
        self.assertIn("echo Hello", script)
        self.assertIn("result_filename", metadata)
        self.assertTrue(metadata["result_filename"].startswith("result_"))

    def test_02_generate_python_script(self):
        """generate_remote_command_script with as_python should produce Python mode script."""
        script, metadata = self.executor.generate_remote_command_script(
            project_root, "print('hello')", as_python=True
        )
        self.assertIsInstance(script, str)
        self.assertIn("print('hello')", script)

    def test_03_script_has_cwd(self):
        """Generated script should include the remote cwd."""
        custom_cwd = "/content/drive/MyDrive/REMOTE_ROOT/projects"
        script, _ = self.executor.generate_remote_command_script(
            project_root, "ls", remote_cwd=custom_cwd
        )
        self.assertIn(custom_cwd, script)

    def test_04_metadata_has_timestamp(self):
        """Metadata should include a timestamp."""
        _, metadata = self.executor.generate_remote_command_script(
            project_root, "pwd"
        )
        self.assertIn("ts", metadata)
        self.assertTrue(metadata["ts"].isdigit())

    def test_05_result_filename_unique(self):
        """Each call should produce a unique result filename."""
        _, m1 = self.executor.generate_remote_command_script(project_root, "cmd1")
        _, m2 = self.executor.generate_remote_command_script(project_root, "cmd2")
        self.assertNotEqual(m1["result_filename"], m2["result_filename"])

    def test_06_shell_type_in_script(self):
        """shell_type parameter should appear in the generated bash script."""
        script, _ = self.executor.generate_remote_command_script(
            project_root, "echo hi", shell_type="zsh"
        )
        self.assertIn("zsh", script)
        self.assertIn("SHELL_BIN", script)

    def test_07_shell_type_default_bash(self):
        """Default shell_type should be bash."""
        script, _ = self.executor.generate_remote_command_script(
            project_root, "echo hi"
        )
        self.assertIn('SHELL_BIN="bash"', script)

    def test_08_python_mode_generates_cell_code(self):
        """as_python=True should generate Python cell code with subprocess.run."""
        script, _ = self.executor.generate_remote_command_script(
            project_root, "print('hi')", as_python=True, shell_type="zsh"
        )
        self.assertIn("subprocess.run", script)
        self.assertIn("zsh", script)
        self.assertIn("capture_output=True", script)


if __name__ == "__main__":
    unittest.main()
