#!/usr/bin/env python3
"""Test CDMCP session timeout and cleanup mechanisms."""
import sys
import time
import unittest
import importlib.util
from pathlib import Path

_r = Path(__file__).resolve().parent.parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from interface.resolve import setup_paths
setup_paths(__file__)

EXPECTED_TIMEOUT = 300
EXPECTED_CPU_LIMIT = 40.0

SM_PATH = str(Path(__file__).resolve().parent.parent.parent /
              "GOOGLE.CDMCP" / "logic" / "cdp" / "session_manager.py")


def _load_sm():
    spec = importlib.util.spec_from_file_location("sm_test", SM_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestSessionIdleTimeout(unittest.TestCase):
    def test_idle_expiry(self):
        sm = _load_sm()
        s = sm.create_session("test_idle_exp", timeout_sec=600, idle_timeout_sec=3)
        self.assertFalse(s.is_expired())
        time.sleep(4)
        self.assertTrue(s.is_expired())
        info = s.expiry_info()
        self.assertTrue(info["idle_expired"])
        self.assertFalse(info["absolute_expired"])
        sm.close_session("test_idle_exp")

    def test_touch_resets_idle(self):
        sm = _load_sm()
        s = sm.create_session("test_touch", timeout_sec=600, idle_timeout_sec=4)
        time.sleep(2)
        s.touch()
        time.sleep(2)
        self.assertFalse(s.is_expired())
        sm.close_session("test_touch")

    def test_cleanup_expired_removes(self):
        sm = _load_sm()
        sm.create_session("test_cleanup_exp", timeout_sec=600, idle_timeout_sec=2)
        time.sleep(3)
        expired = sm._cleanup_expired()
        self.assertIn("test_cleanup_exp", expired)
        self.assertIsNone(sm.get_session("test_cleanup_exp"))


class TestSessionCloseCleanup(unittest.TestCase):
    def test_close_resets_fields(self):
        sm = _load_sm()
        s = sm.create_session("test_close_fields", timeout_sec=600)
        s._http_port = 12345
        s._demo_pid = None
        s.close()
        self.assertIsNone(s.lifetime_tab_id)
        self.assertFalse(s._booted)
        self.assertIsNone(s._http_port)
        sm.close_session("test_close_fields")


if __name__ == "__main__":
    unittest.main()
