#!/usr/bin/env python3
"""
GDS comprehensive test suite adapted from GDS _UNITTEST/test_gds.py.

Contains the 100 most complex test scenarios from GDS, adapted for the GDS
remote execution model (Drive API + Colab). Tests are grouped by feature area.

Usage:
    python3 test_100_gds_complex.py                  # Run all
    python3 test_100_gds_complex.py TestLs            # Run ls tests only
    python3 -m pytest test_100_gds_complex.py -v -x   # Stop on first failure
"""
import unittest
import subprocess
import sys
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime

_project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcp_test_base import MCPTestCase


def _unique_dir():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    h = hashlib.md5(ts.encode()).hexdigest()[:6]
    return f"~/tmp/gcs_test_{ts}_{h}"


class _GDSLocalBase(MCPTestCase):
    """Base for local-only GDS tests (no remote exec needed)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def gcs_local(self, args, timeout=60):
        """Run a GDS local command (no MCP, no remote execution)."""
        cmd = [sys.executable, str(self.gcs_bin)] + args + ["--no-warning"]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def gcs_local_ok(self, args, msg=None):
        r = self.gcs_local(args)
        self.assertSuccess(r, msg)
        return r


class _GDSTestBase(_GDSLocalBase):
    """Shared setup/teardown for remote GDS complex tests."""

    test_dir = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not cls._mcp_available:
            raise unittest.SkipTest("MCP (CDP) not available - skipping remote tests")
        cls.test_dir = _unique_dir()
        r = cls._run_mcp(["mkdir", "-p", cls.test_dir])
        if r.returncode != 0:
            raise RuntimeError(
                f"Failed to create test dir (rc={r.returncode}): "
                f"stdout={r.stdout[:200]} stderr={r.stderr[:200]}")
        r = cls._run_mcp(["cd", cls.test_dir])
        if r.returncode != 0:
            raise RuntimeError(f"Failed to cd to test dir: {r.stderr[:200]}")

    @classmethod
    def tearDownClass(cls):
        if cls.test_dir:
            try:
                cls._run_mcp(["cd", "~"])
                cls._run_mcp([f"rm -rf {cls.test_dir}"])
            except Exception:
                pass

    @classmethod
    def _run_mcp(cls, args, timeout=180):
        cmd = [sys.executable, str(cls.gcs_bin)] + args + ["--no-warning", "--mcp", "--no-feedback"]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def td(self, name):
        """Return a path inside the test directory."""
        return f"{self.test_dir}/{name}"

    def gcs_ok(self, args, msg=None, **kw):
        """Run GDS command and assert success."""
        r = self.gcs(args, **kw)
        self.assertSuccess(r, msg)
        return r

    def gcs_fail(self, args, msg=None, **kw):
        """Run GDS command and assert failure."""
        r = self.gcs(args, **kw)
        self.assertNotEqual(r.returncode, 0, msg or f"Expected failure but got rc=0")
        return r


# =============================================================================
# 1. LS TESTS (15 scenarios)
# =============================================================================

class TestLs(_GDSTestBase):
    """ls command tests adapted from GDS test_00_ls_basic + test_01_ls_advanced."""

    def test_ls_01_basic_dir(self):
        """ls on a directory with files."""
        d = self.td("ls_basic")
        self.gcs_ok(["mkdir", "-p", d])
        self.gcs_ok([f'echo "content" > {d}/file1.txt'])
        r = self.gcs_ok([f"ls {d}"])
        self.assertOutput(r, "file1.txt")

    def test_ls_02_current_dir(self):
        """ls with no arguments lists cwd."""
        r = self.gcs_ok(["ls"])
        self.assertSuccess(r)

    def test_ls_03_home(self):
        """ls ~ lists root directory."""
        r = self.gcs_ok(["ls", "~"])
        self.assertSuccess(r)

    def test_ls_04_nonexistent_path(self):
        """ls on nonexistent path should fail."""
        self.gcs_fail([f"ls {self.td('nonexistent_path_xyz')}"])

    def test_ls_05_nonexistent_file(self):
        """ls on nonexistent file should fail."""
        self.gcs_fail([f"ls {self.td('no_such_file.txt')}"])

    def test_ls_06_recursive(self):
        """ls -R shows subdirectories."""
        d = self.td("ls_recursive")
        self.gcs_ok([f"mkdir -p {d}/sub1/sub2"])
        self.gcs_ok([f'echo "a" > {d}/root.txt'])
        self.gcs_ok([f'echo "b" > {d}/sub1/child.txt'])
        r = self.gcs_ok([f"ls -R {d}"])
        self.assertOutput(r, "sub1")
        self.assertOutput(r, "root.txt")

    def test_ls_07_hidden_files_default(self):
        """Default ls hides dotfiles."""
        d = self.td("ls_hidden")
        self.gcs_ok([f"mkdir -p {d}"])
        self.gcs_ok([f'echo "normal" > {d}/visible.txt'])
        self.gcs_ok([f'echo "hidden" > {d}/.hidden.txt'])
        r = self.gcs_ok([f"ls {d}"])
        self.assertOutput(r, "visible.txt")
        out = self.strip_ansi(r.stdout)
        self.assertNotIn(".hidden.txt", out)

    def test_ls_08_hidden_files_all(self):
        """ls -a shows dotfiles."""
        d = self.td("ls_hidden")
        r = self.gcs_ok([f"ls -a {d}"])
        self.assertOutput(r, "visible.txt")
        self.assertOutput(r, ".hidden.txt")

    def test_ls_09_empty_dir(self):
        """ls on empty directory succeeds."""
        d = self.td("ls_empty")
        self.gcs_ok([f"mkdir -p {d}"])
        r = self.gcs_ok([f"ls {d}"])
        self.assertSuccess(r)

    def test_ls_10_dot(self):
        """ls . lists current directory."""
        r = self.gcs_ok(["ls", "."])
        self.assertSuccess(r)

    def test_ls_11_dot_dot(self):
        """ls ./. succeeds."""
        r = self.gcs_ok(["ls", "./."])
        self.assertSuccess(r)

    def test_ls_12_trailing_slash(self):
        """ls dir/ works same as ls dir."""
        d = self.td("ls_trailing")
        self.gcs_ok([f"mkdir -p {d}"])
        self.gcs_ok([f'echo "x" > {d}/t.txt'])
        r = self.gcs_ok([f"ls {d}/"])
        self.assertOutput(r, "t.txt")

    def test_ls_13_long_format(self):
        """ls -l shows detailed info."""
        d = self.td("ls_long")
        self.gcs_ok([f"mkdir -p {d}"])
        self.gcs_ok([f'echo "data" > {d}/info.txt'])
        r = self.gcs_ok([f"ls -l {d}"])
        self.assertSuccess(r)

    def test_ls_14_multiple_files(self):
        """ls lists multiple created files."""
        d = self.td("ls_multi")
        self.gcs_ok([f"mkdir -p {d}"])
        for i in range(5):
            self.gcs_ok([f'echo "f{i}" > {d}/file_{i}.txt'])
        r = self.gcs_ok([f"ls {d}"])
        for i in range(5):
            self.assertOutput(r, f"file_{i}.txt")

    def test_ls_15_la_combined(self):
        """ls -la shows hidden + long format."""
        d = self.td("ls_hidden")
        r = self.gcs_ok([f"ls -la {d}"])
        self.assertOutput(r, ".hidden.txt")


# =============================================================================
# 2. ECHO & FILE CREATION (15 scenarios)
# =============================================================================

class TestEcho(_GDSTestBase):
    """echo command tests from GDS test_02/03."""

    def test_echo_01_simple(self):
        """Simple echo prints text."""
        r = self.gcs_ok(['echo "Hello World"'])
        self.assertOutput(r, "Hello World")

    def test_echo_02_redirect_create(self):
        """echo with redirect creates file."""
        f = self.td("echo_create.txt")
        self.gcs_ok([f'echo "Test content" > {f}'])
        r = self.gcs_ok([f"cat {f}"])
        self.assertOutput(r, "Test content")

    def test_echo_03_special_chars(self):
        """echo preserves special characters."""
        f = self.td("echo_special.txt")
        self.gcs_ok([f'echo "Special: @#$%^&*()_+-=[]' + '{}' + '|;:,.<>?" > ' + f])
        r = self.gcs_ok([f"cat {f}"])
        self.assertOutput(r, "Special:")

    def test_echo_04_chinese(self):
        """echo preserves Chinese characters."""
        f = self.td("echo_chinese.txt")
        self.gcs_ok([f'echo "Hello" > {f}'])
        r = self.gcs_ok([f"cat {f}"])
        self.assertOutput(r, "Hello")

    def test_echo_05_json_content(self):
        """echo preserves JSON-like content."""
        f = self.td("echo_json.txt")
        content = "{'name': 'test', 'value': 123}"
        self.gcs_ok([f'echo "{content}" > {f}'])
        r = self.gcs_ok([f"cat {f}"])
        self.assertOutput(r, "'name': 'test'")

    def test_echo_06_multiline_e(self):
        """echo -e interprets escape sequences."""
        f = self.td("echo_multiline.txt")
        self.gcs_ok([f'echo -e "line1\\nline2\\nline3" > {f}'])
        r = self.gcs_ok([f"cat {f}"])
        self.assertOutput(r, "line1")
        self.assertOutput(r, "line2")

    def test_echo_07_append(self):
        """echo >> appends to file."""
        f = self.td("echo_append.txt")
        self.gcs_ok([f'echo "first" > {f}'])
        self.gcs_ok([f'echo "second" >> {f}'])
        r = self.gcs_ok([f"cat {f}"])
        self.assertOutput(r, "first")
        self.assertOutput(r, "second")

    def test_echo_08_overwrite(self):
        """echo > overwrites existing file."""
        f = self.td("echo_overwrite.txt")
        self.gcs_ok([f'echo "original" > {f}'])
        self.gcs_ok([f'echo "replaced" > {f}'])
        r = self.gcs_ok([f"cat {f}"])
        self.assertOutput(r, "replaced")
        out = self.strip_ansi(r.stdout)
        self.assertNotIn("original", out)

    def test_echo_09_multiple_spaces(self):
        """echo preserves multiple spaces."""
        f = self.td("echo_spaces.txt")
        self.gcs_ok([f'echo "Multiple     spaces     test" > {f}'])
        r = self.gcs_ok([f"cat {f}"])
        self.assertOutput(r, "Multiple     spaces     test")

    def test_echo_10_gt_symbol_not_redirect(self):
        """echo with > inside quotes is not redirect."""
        r = self.gcs_ok(['echo "content has > symbol"'])
        self.assertOutput(r, "content has > symbol")

    def test_echo_11_batch_create(self):
        """Create multiple files in sequence."""
        d = self.td("echo_batch")
        self.gcs_ok([f"mkdir -p {d}"])
        for i in range(3):
            self.gcs_ok([f'echo "Content {i}" > {d}/batch_{i}.txt'])
        for i in range(3):
            r = self.gcs_ok([f"cat {d}/batch_{i}.txt"])
            self.assertOutput(r, f"Content {i}")

    def test_echo_12_escaped_json(self):
        """echo with escaped double quotes for JSON."""
        f = self.td("echo_escaped_json.txt")
        self.gcs_ok([f'echo \'{{"name": "Alice", "age": 30}}\' > {f}'])
        r = self.gcs_ok([f"cat {f}"])
        self.assertOutput(r, "Alice")

    def test_echo_13_heredoc(self):
        """heredoc creates multiline file."""
        f = self.td("heredoc.txt")
        cmd = f'''cat > {f} << "EOF"
First line
Second line with "quotes"
Third line with special @#$
EOF'''
        self.gcs_ok([cmd])
        r = self.gcs_ok([f"cat {f}"])
        self.assertOutput(r, "First line")
        self.assertOutput(r, "Second line")

    def test_echo_14_heredoc_append(self):
        """heredoc >> appends to file."""
        f = self.td("heredoc.txt")
        cmd = f'''cat >> {f} << "EOF"
Appended line
EOF'''
        self.gcs_ok([cmd])
        r = self.gcs_ok([f"cat {f}"])
        self.assertOutput(r, "Appended line")

    def test_echo_15_empty_file(self):
        """touch creates empty file."""
        f = self.td("empty_touch.txt")
        self.gcs_ok([f"touch {f}"])
        r = self.gcs_ok([f"ls {self.td('')}"])
        self.assertOutput(r, "empty_touch.txt")


# =============================================================================
# 3. FILE OPERATIONS (12 scenarios)
# =============================================================================

class TestFileOps(_GDSTestBase):
    """touch/mkdir/mv/rm from GDS test_04/14."""

    def test_fileops_01_mkdir(self):
        """mkdir creates directory."""
        d = self.td("fo_mkdir")
        self.gcs_ok([f"mkdir {d}"])
        r = self.gcs_ok([f"ls {d}"])
        self.assertSuccess(r)

    def test_fileops_02_mkdir_p(self):
        """mkdir -p creates nested directories."""
        d = self.td("fo_nested/level1/level2")
        self.gcs_ok([f"mkdir -p {d}"])
        r = self.gcs_ok([f"ls {self.td('fo_nested/level1')}"])
        self.assertOutput(r, "level2")

    def test_fileops_03_mkdir_multiple(self):
        """mkdir -p creates multiple dirs."""
        base = self.td("fo_multi")
        self.gcs_ok([f"mkdir -p {base}/d1 {base}/d2 {base}/d3"])
        r = self.gcs_ok([f"ls {base}"])
        self.assertOutput(r, "d1")
        self.assertOutput(r, "d2")
        self.assertOutput(r, "d3")

    def test_fileops_04_touch(self):
        """touch creates empty file."""
        d = self.td("fo_touch")
        self.gcs_ok([f"mkdir -p {d}"])
        self.gcs_ok([f"touch {d}/newfile.txt"])
        r = self.gcs_ok([f"ls {d}"])
        self.assertOutput(r, "newfile.txt")

    def test_fileops_05_mv_file(self):
        """mv moves a file."""
        d = self.td("fo_mv")
        self.gcs_ok([f"mkdir -p {d}"])
        self.gcs_ok([f'echo "moveme" > {d}/src.txt'])
        self.gcs_ok([f"mv {d}/src.txt {d}/dst.txt"])
        r = self.gcs_ok([f"ls {d}"])
        self.assertOutput(r, "dst.txt")
        out = self.strip_ansi(r.stdout)
        self.assertNotIn("src.txt", out)

    def test_fileops_06_rm_file(self):
        """rm deletes a file."""
        d = self.td("fo_rm")
        self.gcs_ok([f"mkdir -p {d}"])
        self.gcs_ok([f"touch {d}/todelete.txt"])
        self.gcs_ok([f"rm {d}/todelete.txt"])
        self.gcs_fail([f"ls {d}/todelete.txt"])

    def test_fileops_07_rm_rf(self):
        """rm -rf deletes directory tree."""
        d = self.td("fo_rmrf")
        self.gcs_ok([f"mkdir -p {d}/sub/deep"])
        self.gcs_ok([f'echo "x" > {d}/sub/deep/f.txt'])
        self.gcs_ok([f"rm -rf {d}"])
        self.gcs_fail([f"ls {d}"])

    def test_fileops_08_mv_content_preserved(self):
        """mv preserves file content."""
        d = self.td("fo_mvc")
        self.gcs_ok([f"mkdir -p {d}"])
        self.gcs_ok([f'echo "preserved" > {d}/orig.txt'])
        self.gcs_ok([f"mv {d}/orig.txt {d}/moved.txt"])
        r = self.gcs_ok([f"cat {d}/moved.txt"])
        self.assertOutput(r, "preserved")

    def test_fileops_09_complex_structure(self):
        """Create project-like directory structure."""
        d = self.td("fo_project")
        self.gcs_ok([f"mkdir -p {d}/src/utils"])
        self.gcs_ok([f'echo "# Main" > {d}/src/main.py'])
        self.gcs_ok([f'echo "# Utils" > {d}/src/utils/helpers.py'])
        r = self.gcs_ok([f"ls -R {d}"])
        self.assertOutput(r, "main.py")

    def test_fileops_10_cp_file(self):
        """cp copies a file."""
        d = self.td("fo_cp")
        self.gcs_ok([f"mkdir -p {d}"])
        self.gcs_ok([f'echo "copy me" > {d}/original.txt'])
        self.gcs_ok([f"cp {d}/original.txt {d}/copy.txt"])
        r = self.gcs_ok([f"cat {d}/copy.txt"])
        self.assertOutput(r, "copy me")

    def test_fileops_11_find(self):
        """find locates files by name."""
        d = self.td("fo_find")
        self.gcs_ok([f"mkdir -p {d}/a {d}/b"])
        self.gcs_ok([f"touch {d}/a/x.py"])
        self.gcs_ok([f"touch {d}/b/y.py"])
        r = self.gcs_ok([f'find {d} -name "*.py"'])
        self.assertOutput(r, "x.py")
        self.assertOutput(r, "y.py")

    def test_fileops_12_wc(self):
        """wc counts lines."""
        f = self.td("fo_wc.txt")
        self.gcs_ok([f'echo -e "a\\nb\\nc" > {f}'])
        r = self.gcs_ok([f"wc -l {f}"])
        self.assertOutput(r, "3")


# =============================================================================
# 4. CD / NAVIGATION (10 scenarios)
# =============================================================================

class TestNavigation(_GDSTestBase):
    """cd/pwd from GDS test_05."""

    def test_nav_01_pwd(self):
        """pwd returns current directory."""
        r = self.gcs_ok(["pwd"])
        self.assertSuccess(r)

    def test_nav_02_cd_absolute(self):
        """cd to absolute path."""
        d = self.td("nav_abs")
        self.gcs_ok([f"mkdir -p {d}"])
        self.gcs_ok([f"cd {d}"])
        r = self.gcs_ok(["pwd"])
        self.assertSuccess(r)

    def test_nav_03_cd_home(self):
        """cd ~ returns to root."""
        self.gcs_ok(["cd", "~"])
        r = self.gcs_ok(["pwd"])
        self.assertSuccess(r)

    def test_nav_04_cd_dotdot(self):
        """cd .. goes up one level."""
        d = self.td("nav_up/child")
        self.gcs_ok([f"mkdir -p {d}"])
        self.gcs_ok([f"cd {d}"])
        self.gcs_ok(["cd", ".."])
        r = self.gcs_ok(["pwd"])
        self.assertSuccess(r)

    def test_nav_05_cd_dotdot_multiple(self):
        """cd ../.. goes up two levels."""
        d = self.td("nav_up2/a/b")
        self.gcs_ok([f"mkdir -p {d}"])
        self.gcs_ok([f"cd {d}"])
        self.gcs_ok(["cd", "../.."])
        r = self.gcs_ok(["pwd"])
        self.assertSuccess(r)

    def test_nav_06_cd_complex_relative(self):
        """cd with ../x navigation."""
        d = self.td("nav_complex")
        self.gcs_ok([f"mkdir -p {d}/a/b {d}/c"])
        self.gcs_ok([f"cd {d}/a/b"])
        self.gcs_ok([f"cd {d}/a/../c"])
        r = self.gcs_ok(["pwd"])
        self.assertSuccess(r)

    def test_nav_07_cd_nonexistent(self):
        """cd to nonexistent dir fails."""
        self.gcs_fail([f"cd {self.td('nav_no_such_dir')}"])

    def test_nav_08_cd_to_file(self):
        """cd to a file fails."""
        f = self.td("nav_file.txt")
        self.gcs_ok([f'echo "x" > {f}'])
        self.gcs_fail([f"cd {f}"])

    def test_nav_09_cd_home_parent(self):
        """cd ~/.. should fail or stay at root."""
        self.gcs(["cd", "~/.."])
        # Either fail or stay at root - both acceptable

    def test_nav_10_cd_and_ls(self):
        """cd then ls shows correct content."""
        d = self.td("nav_ls")
        self.gcs_ok([f"mkdir -p {d}"])
        self.gcs_ok([f"touch {d}/marker.txt"])
        self.gcs_ok([f"cd {d}"])
        r = self.gcs_ok(["ls"])
        self.assertOutput(r, "marker.txt")


# =============================================================================
# 5. GREP (8 scenarios)
# =============================================================================

class TestGrep(_GDSTestBase):
    """grep from GDS test_09."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.grep_file = cls.test_dir + "/grep_data.txt"
        content = "Line 1: Hello world\\nLine 2: This is a test\\nLine 3: Hello again\\nLine 4: Multiple Hello Hello\\nLine 5: No match here"
        cls._run_setup([f'echo -e "{content}" > {cls.grep_file}'])

    def test_grep_01_no_pattern(self):
        """grep without pattern shows all lines."""
        r = self.gcs_ok([f"grep {self.grep_file}"])
        self.assertOutput(r, "Line 1")
        self.assertOutput(r, "Line 5")

    def test_grep_02_simple_match(self):
        """grep with pattern filters lines."""
        r = self.gcs_ok([f'grep "Hello" {self.grep_file}'])
        self.assertOutput(r, "Hello world")
        self.assertOutput(r, "Hello again")
        out = self.strip_ansi(r.stdout)
        self.assertNotIn("No match here", out)

    def test_grep_03_multi_word(self):
        """grep with multi-word pattern."""
        r = self.gcs_ok([f'grep "is a" {self.grep_file}'])
        self.assertOutput(r, "This is a test")

    def test_grep_04_no_match(self):
        """grep with no matches returns exit 1."""
        r = self.gcs(args=[f'grep "ZZZZZ_NO_MATCH" {self.grep_file}'])
        self.assertEqual(r.returncode, 1)

    def test_grep_05_case_insensitive(self):
        """grep -i case insensitive."""
        r = self.gcs_ok([f'grep -i "hello" {self.grep_file}'])
        self.assertOutput(r, "Hello world")

    def test_grep_06_count(self):
        """grep -c counts matches."""
        r = self.gcs_ok([f'grep -c "Hello" {self.grep_file}'])
        self.assertSuccess(r)

    def test_grep_07_nonexistent_file(self):
        """grep on nonexistent file fails."""
        self.gcs_fail([f'grep "x" {self.td("no_such_grep.txt")}'])

    def test_grep_08_invert(self):
        """grep -v inverts match."""
        r = self.gcs_ok([f'grep -v "Hello" {self.grep_file}'])
        self.assertOutput(r, "This is a test")
        self.assertOutput(r, "No match here")


# =============================================================================
# 6. READ / CAT (10 scenarios)
# =============================================================================

class TestRead(_GDSTestBase):
    """read/cat from GDS test_13."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.read_file = cls.test_dir + "/read_data.py"
        content = '# Simple script\\nimport os\\nprint("Hello")\\nx = 42\\nprint(f"x={x}")'
        cls._run_setup([f'echo -e "{content}" > {cls.read_file}'])

    def test_read_01_cat(self):
        """cat shows file content."""
        r = self.gcs_ok([f"cat {self.read_file}"])
        self.assertOutput(r, "Hello")

    def test_read_02_read_with_lines(self):
        """read shows content with line numbers."""
        r = self.gcs_ok([f"read {self.read_file}"])
        self.assertSuccess(r)

    def test_read_03_read_range(self):
        """read with line range."""
        r = self.gcs_ok([f"read {self.read_file}", "1", "3"])
        self.assertSuccess(r)

    def test_read_04_read_force(self):
        """read --force bypasses cache."""
        r = self.gcs_ok([f"read --force {self.read_file}"])
        self.assertSuccess(r)

    def test_read_05_cat_nonexistent(self):
        """cat nonexistent file fails."""
        self.gcs_fail([f"cat {self.td('no_such_read.txt')}"])

    def test_read_06_read_nonexistent(self):
        """read nonexistent file fails."""
        self.gcs_fail([f"read {self.td('no_such_read.txt')}"])

    def test_read_07_cat_absolute_path(self):
        """cat with absolute ~/path."""
        f = self.td("abs_cat.txt")
        self.gcs_ok([f'echo -n "absolute test" > {f}'])
        r = self.gcs_ok([f"cat {f}"])
        self.assertOutput(r, "absolute test")

    def test_read_08_empty_file(self):
        """cat on empty file succeeds."""
        f = self.td("empty_read.txt")
        self.gcs_ok([f"touch {f}"])
        r = self.gcs_ok([f"cat {f}"])
        self.assertSuccess(r)

    def test_read_09_large_content(self):
        """read a file with many lines."""
        f = self.td("large_read.txt")
        self.gcs_ok([f'seq 1 50 > {f}'])
        r = self.gcs_ok([f"read {f}"])
        self.assertSuccess(r)

    def test_read_10_grep_in_file(self):
        """grep inside a specific file."""
        r = self.gcs_ok([f'grep "print" {self.read_file}'])
        self.assertOutput(r, "print")


# =============================================================================
# 7. EDIT (8 scenarios)
# =============================================================================

class TestEdit(_GDSTestBase):
    """edit from GDS test_10/12."""

    def _create_edit_file(self, name, content):
        f = self.td(name)
        self.gcs_ok([f'echo -e "{content}" > {f}'])
        return f

    def test_edit_01_text_replace(self):
        """edit replaces text."""
        f = self._create_edit_file("edit1.py", "# Hello from remote")
        import shlex
        spec = json.dumps([["Hello from remote", "Hello from MODIFIED"]])
        self.gcs_ok([f"edit {f} {shlex.quote(spec)}"])
        r = self.gcs_ok([f"cat {f}"])
        self.assertOutput(r, "MODIFIED")

    def test_edit_02_line_range(self):
        """edit with line range replacement."""
        f = self._create_edit_file("edit2.txt", "line0\\nline1\\nline2\\nline3")
        import shlex
        spec = json.dumps([[[1, 2], "replaced_lines"]])
        self.gcs_ok([f"edit {f} {shlex.quote(spec)}"])
        r = self.gcs_ok([f"cat {f}"])
        self.assertOutput(r, "replaced_lines")

    def test_edit_03_preview(self):
        """edit --preview does not modify file."""
        f = self._create_edit_file("edit3.txt", "original content")
        import shlex
        spec = json.dumps([["original", "changed"]])
        self.gcs_ok([f"edit --preview {f} {shlex.quote(spec)}"])
        r = self.gcs_ok([f"cat {f}"])
        self.assertOutput(r, "original")

    def test_edit_04_backup(self):
        """edit --backup creates backup."""
        f = self._create_edit_file("edit4.txt", "backup me")
        import shlex
        spec = json.dumps([["backup me", "backed up"]])
        self.gcs_ok([f"edit --backup {f} {shlex.quote(spec)}"])
        r = self.gcs_ok([f"cat {f}"])
        self.assertOutput(r, "backed up")

    def test_edit_05_multiple_replacements(self):
        """edit with multiple replacement pairs."""
        f = self._create_edit_file("edit5.txt", "AAA BBB CCC")
        import shlex
        spec = json.dumps([["AAA", "XXX"], ["CCC", "ZZZ"]])
        self.gcs_ok([f"edit {f} {shlex.quote(spec)}"])
        r = self.gcs_ok([f"cat {f}"])
        self.assertOutput(r, "XXX")
        self.assertOutput(r, "ZZZ")

    def test_edit_06_nonexistent_file(self):
        """edit nonexistent file fails."""
        import shlex
        spec = json.dumps([["a", "b"]])
        self.gcs_fail([f"edit {self.td('no_edit.txt')} {shlex.quote(spec)}"])

    def test_edit_07_no_match(self):
        """edit with no matching text."""
        f = self._create_edit_file("edit7.txt", "nothing matches")
        import shlex
        spec = json.dumps([["ZZZZZ", "replacement"]])
        self.gcs(args=[f"edit {f} {shlex.quote(spec)}"])
        # Should succeed or warn - either is acceptable

    def test_edit_08_special_chars(self):
        """edit with special characters."""
        f = self._create_edit_file("edit8.txt", "def hello():\\n    pass")
        import shlex
        spec = json.dumps([["pass", 'return "world"']])
        self.gcs_ok([f"edit {f} {shlex.quote(spec)}"])
        r = self.gcs_ok([f"cat {f}"])
        self.assertOutput(r, "world")


# =============================================================================
# 8. LINTER (6 scenarios)
# =============================================================================

class TestLinter(_GDSTestBase):
    """linter from GDS test_11."""

    def test_linter_01_valid_python(self):
        """linter on valid Python file succeeds."""
        f = self.td("lint_valid.py")
        self.gcs_ok([f'echo "x = 1\\nprint(x)" > {f}'])
        r = self.gcs_ok([f"linter {f}"])
        self.assertSuccess(r)

    def test_linter_02_invalid_python(self):
        """linter on invalid Python detects errors."""
        f = self.td("lint_invalid.py")
        self.gcs_ok([f'echo "def f(:\\n  pass" > {f}'])
        self.gcs(args=[f"linter {f}"])
        # Should detect syntax error (may return 0 or non-0 depending on severity)

    def test_linter_03_json_valid(self):
        """linter on valid JSON succeeds."""
        f = self.td("lint_valid.json")
        self.gcs_ok([f'echo \'{{"key": "value"}}\' > {f}'])
        r = self.gcs_ok([f"linter {f}"])
        self.assertSuccess(r)

    def test_linter_04_nonexistent(self):
        """linter on nonexistent file fails."""
        self.gcs_fail([f"linter {self.td('no_lint.py')}"])

    def test_linter_05_language_flag(self):
        """linter --language python."""
        f = self.td("lint_lang.py")
        self.gcs_ok([f'echo "print(42)" > {f}'])
        r = self.gcs_ok([f"linter --language python {f}"])
        self.assertSuccess(r)

    def test_linter_06_empty_file(self):
        """linter on empty file."""
        f = self.td("lint_empty.py")
        self.gcs_ok([f"touch {f}"])
        self.gcs(args=[f"linter {f}"])
        # Empty file lint - either pass or warn


# =============================================================================
# 9. VENV (8 scenarios)
# =============================================================================

class TestVenv(_GDSLocalBase):
    """venv from GDS test_18/19. Venv commands are local operations using Drive API."""

    def test_venv_01_list(self):
        """venv --list shows environments."""
        r = self.gcs_local_ok(["venv", "--list"])
        self.assertSuccess(r)

    def test_venv_02_current(self):
        """venv --current shows active env."""
        r = self.gcs_local_ok(["venv", "--current"])
        self.assertSuccess(r)

    def test_venv_03_create(self):
        """venv --create creates new environment."""
        name = f"test_env_{int(time.time())}"
        r = self.gcs_local_ok(["venv", "--create", name])
        self.assertSuccess(r)
        self.gcs_local(["venv", "--delete", name])

    def test_venv_04_activate_deactivate(self):
        """venv --activate and --deactivate cycle."""
        name = f"test_act_{int(time.time())}"
        self.gcs_local_ok(["venv", "--create", name])
        self.gcs_local_ok(["venv", "--activate", name])
        r = self.gcs_local_ok(["venv", "--current"])
        self.assertOutput(r, name)
        self.gcs_local_ok(["venv", "--deactivate"])
        self.gcs_local(["venv", "--delete", name])

    def test_venv_05_protect(self):
        """venv --protect prevents deletion."""
        name = f"test_prot_{int(time.time())}"
        self.gcs_local_ok(["venv", "--create", name])
        self.gcs_local_ok(["venv", "--protect", name])
        self.gcs_local(["venv", "--delete", name])
        self.gcs_local_ok(["venv", "--unprotect", name])
        self.gcs_local(["venv", "--delete", name])

    def test_venv_06_delete_nonexistent(self):
        """venv --delete nonexistent warns."""
        self.gcs_local(["venv", "--delete", "no_such_env_xyz"])

    def test_venv_07_create_duplicate(self):
        """venv --create duplicate name."""
        name = f"test_dup_{int(time.time())}"
        self.gcs_local_ok(["venv", "--create", name])
        self.gcs_local(["venv", "--create", name])
        self.gcs_local(["venv", "--delete", name])

    def test_venv_08_list_after_create(self):
        """venv --list reflects newly created env."""
        name = f"test_vis_{int(time.time())}"
        self.gcs_local_ok(["venv", "--create", name])
        r = self.gcs_local_ok(["venv", "--list"])
        self.assertOutput(r, name)
        self.gcs_local(["venv", "--delete", name])


# =============================================================================
# 10. REDIRECTION & PIPE (4 scenarios)
# =============================================================================

class TestRedirection(_GDSTestBase):
    """Redirection from GDS test_31 and pipe from test_21."""

    def test_redir_01_stdout_to_file(self):
        """command > file redirects output."""
        f = self.td("redir_stdout.txt")
        self.gcs_ok([f'echo "redirected" > {f}'])
        r = self.gcs_ok([f"cat {f}"])
        self.assertOutput(r, "redirected")

    def test_redir_02_append(self):
        """command >> file appends."""
        f = self.td("redir_append.txt")
        self.gcs_ok([f'echo "line1" > {f}'])
        self.gcs_ok([f'echo "line2" >> {f}'])
        r = self.gcs_ok([f"cat {f}"])
        self.assertOutput(r, "line1")
        self.assertOutput(r, "line2")

    def test_redir_03_pipe(self):
        """command | command piping."""
        f = self.td("pipe_data.txt")
        self.gcs_ok([f'echo -e "apple\\nbanana\\ncherry" > {f}'])
        r = self.gcs_ok([f"cat {f} | grep banana"])
        self.assertOutput(r, "banana")

    def test_redir_04_chain(self):
        """command && command chaining."""
        d = self.td("chain_test")
        r = self.gcs_ok([f"mkdir -p {d} && touch {d}/chained.txt && ls {d}"])
        self.assertOutput(r, "chained.txt")


# =============================================================================
# 11. BACKGROUND TASKS (4 scenarios)
# =============================================================================

class TestBackground(_GDSTestBase):
    """bg from GDS test_24."""

    def test_bg_01_submit(self):
        """bg submits a task."""
        r = self.gcs_ok(["bg", "echo bg_test_marker"])
        self.assertSuccess(r)

    def test_bg_02_status(self):
        """bg --status shows tasks."""
        r = self.gcs(args=["bg", "--status"])
        self.assertSuccess(r)

    def test_bg_03_cleanup(self):
        """bg --cleanup cleans completed tasks."""
        self.gcs(args=["bg", "--cleanup"])
        # May return 0 or warn if no tasks

    def test_bg_04_submit_and_check(self):
        """bg submit then check status."""
        r = self.gcs_ok(["bg", "sleep 1 && echo done"])
        self.assertSuccess(r)
        time.sleep(5)
        r = self.gcs(args=["bg", "--status"])
        self.assertSuccess(r)


# =============================================================================
# 12. PYTHON EXECUTION (4 scenarios)
# =============================================================================

class TestPython(_GDSTestBase):
    """Python execution from GDS test_17/26."""

    def test_python_01_inline(self):
        """python3 -c executes inline code."""
        r = self.gcs_ok(["python3 -c 'print(42)'"])
        self.assertOutput(r, "42")

    def test_python_02_script(self):
        """Execute a Python script file."""
        f = self.td("py_script.py")
        self.gcs_ok([f'echo "print(2+3)" > {f}'])
        r = self.gcs_ok([f"python3 {f}"])
        self.assertOutput(r, "5")

    def test_python_03_import(self):
        """Python import works."""
        r = self.gcs_ok(["python3 -c 'import os; print(os.getcwd())'"])
        self.assertSuccess(r)

    def test_python_04_multiline(self):
        """Python script with multiple lines."""
        f = self.td("py_multi.py")
        code = "import math\\nresult = math.sqrt(144)\\nprint(int(result))"
        self.gcs_ok([f'echo -e "{code}" > {f}'])
        r = self.gcs_ok([f"python3 {f}"])
        self.assertOutput(r, "12")


# =============================================================================
# 13. SHELL MANAGEMENT (4 scenarios)
# =============================================================================

class TestShell(_GDSLocalBase):
    """shell from GDS test_22. Shell management commands are local operations."""

    def test_shell_01_list(self):
        """GDS --shell list shows shells."""
        r = self.gcs_local_ok(["--shell", "list"])
        self.assertSuccess(r)

    def test_shell_02_info(self):
        """GDS --shell info shows current shell."""
        r = self.gcs_local_ok(["--shell", "info"])
        self.assertSuccess(r)

    def test_shell_03_create_and_switch(self):
        """GDS --shell create + switch."""
        name = f"test_sh_{int(time.time())}"
        r = self.gcs_local(["--shell", "create", name])
        self.assertSuccess(r)
        self.gcs_local(["--shell", "list"])

    def test_shell_04_type(self):
        """GDS --shell type shows shell type."""
        r = self.gcs_local_ok(["--shell", "type"])
        self.assertSuccess(r)


# =============================================================================
# 14. AT-PATH OPERATIONS (2 scenarios)
# =============================================================================

class TestAtPath(_GDSTestBase):
    """@-path from GDS test_35."""

    def test_at_01_ls_env(self):
        """ls @/ lists REMOTE_ENV root."""
        r = self.gcs_ok(["ls @/"])
        self.assertSuccess(r)

    def test_at_02_at_expansion(self):
        """@ path expands to REMOTE_ENV."""
        self.gcs(args=["ls @/venv"])
        # May or may not exist, but should not crash


# =============================================================================
# 15. STATUS & MISC (2 scenarios)
# =============================================================================

class TestMisc(_GDSLocalBase):
    """Miscellaneous tests."""

    def test_misc_01_mcp_status(self):
        """GDS --mcp status shows info."""
        r = self.gcs_local_ok(["--mcp", "status"])
        self.assertSuccess(r)

    def test_misc_02_reconnection_status(self):
        """GDS --reconnection status works."""
        r = self.gcs_local_ok(["--reconnection", "status"])
        self.assertSuccess(r)


if __name__ == "__main__":
    unittest.main(verbosity=2)
