import unittest
import subprocess
import sys
import os
import tempfile
import shutil
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from logic.git.engine import auto_squash_if_needed, DEFAULT_SQUASH_CONFIG


def run_git(args, cwd):
    return subprocess.run(
        ["/usr/bin/git"] + args,
        cwd=cwd, capture_output=True, text=True
    )


def create_test_repo(num_commits, tmp_dir):
    """Creates a temporary git repo with N commits, each adding a line to file.txt."""
    run_git(["init"], cwd=tmp_dir)
    run_git(["config", "user.email", "test@test.com"], cwd=tmp_dir)
    run_git(["config", "user.name", "Test"], cwd=tmp_dir)

    file_path = os.path.join(tmp_dir, "file.txt")
    for i in range(1, num_commits + 1):
        with open(file_path, "a") as f:
            f.write(f"line {i}\n")
        # Also create an extra file for some commits to test binary/multi-file handling
        if i % 5 == 0:
            extra = os.path.join(tmp_dir, f"extra_{i}.txt")
            with open(extra, "w") as f:
                f.write(f"extra content {i}\n")
        run_git(["add", "."], cwd=tmp_dir)
        run_git(["commit", "-m", f"Commit {i}"], cwd=tmp_dir)


def get_tree_sha(cwd):
    res = run_git(["rev-parse", "HEAD^{tree}"], cwd=cwd)
    return res.stdout.strip()


def get_commit_count(cwd):
    res = run_git(["rev-list", "--count", "HEAD"], cwd=cwd)
    return int(res.stdout.strip())


def get_commit_messages(cwd):
    res = run_git(["log", "--format=%s", "--reverse"], cwd=cwd)
    return res.stdout.strip().split("\n")


class TestGitSquash(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="git_squash_test_")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_01_no_squash_below_threshold(self):
        """Squash should not trigger when total commits < base * 2."""
        create_test_repo(15, self.tmp_dir)
        tree_before = get_tree_sha(self.tmp_dir)
        count_before = get_commit_count(self.tmp_dir)

        result = auto_squash_if_needed(cwd=self.tmp_dir)

        self.assertFalse(result)
        self.assertEqual(get_tree_sha(self.tmp_dir), tree_before)
        self.assertEqual(get_commit_count(self.tmp_dir), count_before)

    def test_02_no_squash_not_multiple_of_base(self):
        """Squash should not trigger when commit count is not a multiple of base."""
        create_test_repo(23, self.tmp_dir)
        tree_before = get_tree_sha(self.tmp_dir)

        result = auto_squash_if_needed(cwd=self.tmp_dir)

        self.assertFalse(result)
        self.assertEqual(get_tree_sha(self.tmp_dir), tree_before)

    def test_03_squash_20_commits_reduces(self):
        """With 20 commits and base=10, freq=0.5 zone drops every other old commit."""
        create_test_repo(20, self.tmp_dir)
        tree_before = get_tree_sha(self.tmp_dir)
        count_before = get_commit_count(self.tmp_dir)

        result = auto_squash_if_needed(cwd=self.tmp_dir)

        self.assertTrue(result)
        self.assertEqual(get_tree_sha(self.tmp_dir), tree_before,
                         "Tree hash mismatch: squash altered file content!")
        new_count = get_commit_count(self.tmp_dir)
        self.assertLess(new_count, count_before)
        self.assertEqual(new_count, 15)

    def test_04_squash_60_commits_preserves_tree(self):
        """Squashing 60 commits must preserve the exact file tree."""
        create_test_repo(60, self.tmp_dir)
        tree_before = get_tree_sha(self.tmp_dir)
        count_before = get_commit_count(self.tmp_dir)

        result = auto_squash_if_needed(cwd=self.tmp_dir)

        self.assertTrue(result)
        self.assertEqual(get_tree_sha(self.tmp_dir), tree_before,
                         "Tree hash mismatch: squash altered file content!")
        new_count = get_commit_count(self.tmp_dir)
        self.assertLess(new_count, count_before)
        self.assertGreater(new_count, 0)

    def test_05_file_content_intact_after_squash(self):
        """After squashing, all file content must be byte-identical."""
        create_test_repo(60, self.tmp_dir)
        file_path = os.path.join(self.tmp_dir, "file.txt")
        with open(file_path, "r") as f:
            content_before = f.read()

        auto_squash_if_needed(cwd=self.tmp_dir)

        with open(file_path, "r") as f:
            content_after = f.read()
        self.assertEqual(content_before, content_after)

    def test_06_recent_commits_preserved(self):
        """The 10 most recent commits (level 1, freq=1.0) should be individually kept."""
        create_test_repo(60, self.tmp_dir)

        auto_squash_if_needed(cwd=self.tmp_dir)

        messages = get_commit_messages(self.tmp_dir)
        # The newest 10 should be preserved as individual commits
        recent_10 = messages[-10:]
        for i, msg in enumerate(recent_10):
            expected = f"Commit {51 + i}"
            self.assertEqual(msg, expected,
                             f"Recent commit {i} should be '{expected}', got '{msg}'")

    def test_07_squash_messages_present(self):
        """Squash groups should produce GIT_MAINTENANCE commit messages."""
        create_test_repo(60, self.tmp_dir)

        auto_squash_if_needed(cwd=self.tmp_dir)

        messages = get_commit_messages(self.tmp_dir)
        squash_msgs = [m for m in messages if m.startswith("GIT_MAINTENANCE:")]
        self.assertGreater(len(squash_msgs), 0,
                           "Expected at least one GIT_MAINTENANCE squash commit")

    def test_08_backup_ref_created(self):
        """A backup ref should be created before squashing."""
        create_test_repo(60, self.tmp_dir)
        original_head = run_git(["rev-parse", "HEAD"], cwd=self.tmp_dir).stdout.strip()

        auto_squash_if_needed(cwd=self.tmp_dir)

        # Check backup refs exist
        res = run_git(["for-each-ref", "refs/backup/"], cwd=self.tmp_dir)
        self.assertIn(original_head, res.stdout,
                       "Backup ref should point to original HEAD")

    def test_09_double_squash_stable(self):
        """Running squash twice: second run should be a no-op."""
        create_test_repo(60, self.tmp_dir)

        result1 = auto_squash_if_needed(cwd=self.tmp_dir)
        self.assertTrue(result1)

        tree_after_first = get_tree_sha(self.tmp_dir)
        count_after_first = get_commit_count(self.tmp_dir)

        result2 = auto_squash_if_needed(cwd=self.tmp_dir)
        # After first squash, count is no longer a multiple of base, so no-op
        self.assertFalse(result2)
        self.assertEqual(get_tree_sha(self.tmp_dir), tree_after_first)
        self.assertEqual(get_commit_count(self.tmp_dir), count_after_first)

    def test_10_custom_config(self):
        """Squashing with a custom config (smaller base) should work correctly."""
        create_test_repo(10, self.tmp_dir)
        tree_before = get_tree_sha(self.tmp_dir)

        config = {
            "base": 5,
            "levels": [
                {"level": 1, "frequency": 1},
                {"level": 2, "frequency": 0.5},
            ]
        }
        result = auto_squash_if_needed(cwd=self.tmp_dir, config=config)

        self.assertTrue(result)
        self.assertEqual(get_tree_sha(self.tmp_dir), tree_before,
                         "Tree hash mismatch with custom config!")


if __name__ == "__main__":
    unittest.main()
