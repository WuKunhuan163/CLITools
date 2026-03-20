EXPECTED_CPU_LIMIT = 60.0
EXPECTED_TIMEOUT = 300
import unittest
import subprocess
import sys
import re
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent.parent


def _has_service_account_key():
    key_path = project_root / "data" / "google_cloud_console" / "console_key.json"
    return key_path.exists()


@unittest.skipUnless(_has_service_account_key(), "Service account key not configured")
class TestCdNavigation(unittest.TestCase):
    """Test cd and pwd commands for remote directory navigation."""

    @classmethod
    def setUpClass(cls):
        cls.gcs_bin = project_root / "bin" / "GDS" / "GDS"

    @staticmethod
    def _strip_ansi(text):
        return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    def _run_gcs(self, args, timeout=90):
        cmd = [sys.executable, str(self.gcs_bin), "--no-warning"] + args
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def test_01_cd_tilde_then_pwd(self):
        """cd ~ followed by pwd should show ~."""
        self._run_gcs(["cd", "~"])
        res = self._run_gcs(["pwd"])
        output = self._strip_ansi(res.stdout).strip()
        self.assertEqual(output, "~")

    def test_02_cd_subdir_via_ls(self):
        """cd into a subdirectory listed by ls should update pwd."""
        ls_res = self._run_gcs(["ls", "~"])
        output = self._strip_ansi(ls_res.stdout)
        dirs = [l.rstrip("/") for l in output.strip().splitlines() if l.strip().endswith("/")]
        if not dirs:
            self.skipTest("No subdirectories found in remote root")
        target = dirs[0]
        cd_res = self._run_gcs(["cd", f"~/{target}"])
        self.assertEqual(cd_res.returncode, 0,
                         f"cd ~/{target} failed: {self._strip_ansi(cd_res.stderr)}")
        pwd_res = self._run_gcs(["pwd"])
        pwd_out = self._strip_ansi(pwd_res.stdout).strip()
        self.assertEqual(pwd_out, f"~/{target}")
        # Reset
        self._run_gcs(["cd", "~"])

    def test_03_cd_invalid_dir(self):
        """cd to a nonexistent directory should return non-zero and print bash-like error."""
        res = self._run_gcs(["cd", "~/this_dir_does_not_exist_xyz"])
        self.assertNotEqual(res.returncode, 0, "cd to invalid dir should return non-zero")
        error_output = self._strip_ansi(res.stderr)
        self.assertIn("No such file or directory", error_output,
                       f"Expected bash-like error, got: {error_output}")


if __name__ == "__main__":
    unittest.main()
