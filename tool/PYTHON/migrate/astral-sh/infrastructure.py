"""astral-sh: infrastructure migration.

Downloads standalone Python builds from astral-sh/python-build-standalone
and installs them into the PYTHON tool's data/install/ directory.

This is a refactored version of tool/PYTHON/logic/install.py's download logic.
"""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def execute(args=None):
    """Execute infrastructure migration from astral-sh.

    Usage: TOOL --migrate --infrastructure astral-sh [--version X.Y] [--platform macos-arm64] [--limit N]
    """
    root_str = str(_PROJECT_ROOT)
    if root_str in sys.path:
        sys.path.remove(root_str)
    sys.path.insert(0, root_str)

    from tool.PYTHON.logic.install import (
        get_all_assets_from_cache, download_and_verify, INSTALL_DIR
    )
    from tool.PYTHON.logic.scanner import PythonScanner

    args = args or []
    version = None
    platform_filter = None
    limit = 3

    i = 0
    while i < len(args):
        if args[i] == "--version" and i + 1 < len(args):
            version = args[i + 1]
            i += 2
        elif args[i] == "--platform" and i + 1 < len(args):
            platform_filter = args[i + 1]
            i += 2
        elif args[i] == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])
            i += 2
        else:
            i += 1

    PythonScanner(silent=False)
    filtered = get_all_assets_from_cache(
        version_filter=version,
        platform_filter=platform_filter,
    )

    if not filtered:
        print("  No matching assets found.")
        return 1

    def variant_priority(name):
        if "pgo+lto-full" in name: return 0
        if "pgo-full" in name: return 1
        if "install_only" in name: return 2
        if "full" in name and "debug" not in name and "noopt" not in name: return 3
        return 10

    filtered = sorted(filtered, key=lambda x: (x["tag"], x["patch"], -variant_priority(x["name"])), reverse=True)

    seen = set()
    to_download = []
    for a in filtered:
        key = (a["minor"], a["platform"])
        if key not in seen:
            to_download.append(a)
            seen.add(key)

    download_list = to_download[:limit]
    print(f"  Downloading {len(download_list)} Python builds from astral-sh...")

    success = 0
    for a in download_list:
        if download_and_verify(a, INSTALL_DIR):
            success += 1

    print(f"\n  Installed {success}/{len(download_list)} builds.")
    return 0 if success > 0 else 1
