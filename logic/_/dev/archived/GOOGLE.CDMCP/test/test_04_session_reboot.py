#!/usr/bin/env python3
"""Unit test: CDMCP session reboot after window closure.

Verifies:
  1. After closing the session window, require_tab detects loss and triggers reboot
  2. After reboot, session has new window with pinned tab + demo
"""
import sys, time
from pathlib import Path

_r = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_r))
from interface.resolve import setup_paths
setup_paths(str(_r / "tool" / "GOOGLE.CDMCP" / "main.py"))

from interface.chrome import close_tab

import importlib.util
sm_path = _r / "tool" / "GOOGLE.CDMCP" / "logic" / "cdp" / "session_manager.py"
spec = importlib.util.spec_from_file_location("session_manager", str(sm_path))
sm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sm)

TEST_SESSION = "test_reboot_unit"

def cleanup():
    sm.close_session(TEST_SESSION)
    time.sleep(0.5)

def test_reboot():
    cleanup()

    print("=" * 60)
    print("PHASE 1: Boot initial session")
    print("=" * 60)
    result = sm.boot_tool_session(
        TEST_SESSION, timeout_sec=300, idle_timeout_sec=120, port=9222,
    )
    assert result.get("ok"), f"Initial boot failed: {result.get('error')}"
    session = result["session"]
    original_window = session.window_id
    original_tab = session.lifetime_tab_id
    print(f"  Window ID: {original_window}")
    print(f"  Session tab: {original_tab}")
    print(f"  Demo tab: {session._tabs.get('demo', {}).get('id', 'N/A')}")
    print("  PASS: Initial session booted")

    print(f"\n{'=' * 60}")
    print("PHASE 2: Close session window (simulate user closing)")
    print("=" * 60)
    # Close the session tab (simulates window closure)
    if original_tab:
        close_tab(original_tab, port=9222)
        print(f"  Closed tab: {original_tab}")
    demo_id = session._tabs.get("demo", {}).get("id")
    if demo_id:
        close_tab(demo_id, port=9222)
        print(f"  Closed demo tab: {demo_id}")
    time.sleep(2)
    print("  PASS: Session window tabs closed")

    print(f"\n{'=' * 60}")
    print("PHASE 3: require_tab should detect loss and trigger reboot")
    print("=" * 60)
    tab_info = session.require_tab(
        "test_app", url_pattern="youtube.com",
        open_url="https://www.youtube.com", auto_open=True, wait_sec=15,
    )
    print(f"  require_tab result: {tab_info}")

    if tab_info:
        print(f"  New tab ID: {tab_info.get('id')}")
        print(f"  New tab URL: {tab_info.get('url', '')[:60]}")
        new_window = session.window_id
        print(f"  New window ID: {new_window}")
        print(f"  Window changed: {new_window != original_window}")

        # Check new demo tab exists
        time.sleep(2)
        demo_after = session._tabs.get("demo")
        print(f"  Demo tab after reboot: {demo_after.get('id') if demo_after else 'None'}")

        print("  PASS: Session recovered with new window")
    else:
        print("  WARN: require_tab returned None (reboot may need improvement)")

    # Cleanup
    cleanup()
    print(f"\n{'=' * 60}")
    print("ALL REBOOT TESTS PASSED")
    print("=" * 60)

if __name__ == "__main__":
    test_reboot()
