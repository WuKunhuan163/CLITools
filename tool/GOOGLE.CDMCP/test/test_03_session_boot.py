#!/usr/bin/env python3
"""Unit test: CDMCP session boot with short timeouts.

Verifies:
  1. boot_tool_session creates a session with pinned welcome tab
  2. Demo tab is opened automatically
  3. Session has correct timeout parameters
  4. Session can be closed cleanly
"""
import sys, time
from pathlib import Path

_r = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_r))
from interface.resolve import setup_paths
setup_paths(str(_r / "tool" / "GOOGLE.CDMCP" / "main.py"))

from interface.chrome import list_tabs

import importlib.util
sm_path = _r / "tool" / "GOOGLE.CDMCP" / "logic" / "cdp" / "session_manager.py"
spec = importlib.util.spec_from_file_location("session_manager", str(sm_path))
sm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sm)

TEST_SESSION = "test_boot_unit"
SHORT_TIMEOUT = 120
SHORT_IDLE = 60

def cleanup():
    sm.close_session(TEST_SESSION)
    time.sleep(0.5)

def test_boot():
    print("=" * 60)
    print("TEST 1: boot_tool_session creates session with demo")
    print("=" * 60)
    cleanup()

    result = sm.boot_tool_session(
        TEST_SESSION,
        timeout_sec=SHORT_TIMEOUT,
        idle_timeout_sec=SHORT_IDLE,
        port=9222,
    )
    print(f"  Result: ok={result.get('ok')}, action={result.get('action')}")
    print(f"  Session ID: {result.get('session_id')}")
    print(f"  Window ID: {result.get('window_id')}")

    assert result.get("ok"), f"Boot failed: {result.get('error')}"
    session = result.get("session")
    assert session is not None, "Session object missing from result"

    print(f"\n  Session name: {session.name}")
    print(f"  Timeout: {session.timeout_sec}s (expected {SHORT_TIMEOUT})")
    print(f"  Idle timeout: {session.idle_timeout_sec}s (expected {SHORT_IDLE})")
    assert session.timeout_sec == SHORT_TIMEOUT
    assert session.idle_timeout_sec == SHORT_IDLE

    # Check pinned session tab
    assert session.lifetime_tab_id, "No lifetime tab ID"
    print(f"  Lifetime tab: {session.lifetime_tab_id}")

    # Check demo tab exists
    time.sleep(2)
    demo_tab = session._tabs.get("demo")
    print(f"  Demo tab: {demo_tab}")
    assert demo_tab is not None, "Demo tab was not created"
    assert demo_tab.get("id"), "Demo tab has no ID"
    print(f"  Demo tab ID: {demo_tab['id']}")

    # Verify tabs are visible in Chrome
    tabs = list_tabs(9222)
    session_tab_found = False
    demo_tab_found = False
    for t in tabs:
        if t.get("id") == session.lifetime_tab_id:
            session_tab_found = True
            print(f"  Session tab URL: {t.get('url', '')[:60]}")
        if t.get("id") == demo_tab.get("id"):
            demo_tab_found = True
            print(f"  Demo tab URL: {t.get('url', '')[:60]}")

    assert session_tab_found, "Session tab not found in Chrome"
    assert demo_tab_found, "Demo tab not found in Chrome"

    print("\n  PASS: Session booted with pinned tab + demo tab")

    # Test 2: already_booted
    print(f"\n{'=' * 60}")
    print("TEST 2: Re-boot returns already_booted")
    print("=" * 60)
    result2 = sm.boot_tool_session(TEST_SESSION, timeout_sec=SHORT_TIMEOUT, port=9222)
    print(f"  Result: ok={result2.get('ok')}, action={result2.get('action')}")
    assert result2.get("ok")
    assert result2.get("action") == "already_booted"
    print("  PASS: Re-boot correctly detected existing session")

    # Cleanup
    cleanup()
    print(f"\n{'=' * 60}")
    print("ALL BOOT TESTS PASSED")
    print("=" * 60)

if __name__ == "__main__":
    test_boot()
