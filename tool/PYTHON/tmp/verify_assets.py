#!/usr/bin/env python3
import sys
import os
import subprocess
import json
from pathlib import Path

# Add project root to sys.path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent.parent
sys.path.append(str(project_root))

def verify_version(version_tag):
    """Verifies a single installed version."""
    install_dir = project_root / "tool" / "PYTHON" / "data" / "install" / version_tag
    json_path = install_dir / "PYTHON.json"
    
    report = {
        "tag": version_tag,
        "json_exists": False,
        "release": "unknown",
        "exec_works": False,
        "version_output": "unknown",
        "error": None
    }
    
    if not install_dir.exists():
        report["error"] = "Install directory missing"
        return report

    # 1. Check PYTHON.json
    if json_path.exists():
        report["json_exists"] = True
        try:
            with open(json_path, "r") as f:
                meta = json.load(f)
                report["release"] = meta.get("release", "missing")
        except Exception as e:
            report["error"] = f"JSON read error: {e}"
    
    # 2. Check executable
    from tool.PYTHON.logic.config import get_executable_path
    exec_path = get_executable_path(version_tag)
    
    if exec_path and exec_path.exists():
        try:
            # Try running it
            # On macOS we might need to handle arm64/x86_64 issues, but usually it works
            result = subprocess.run([str(exec_path), "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                report["exec_works"] = True
                report["version_output"] = result.stdout.strip() or result.stderr.strip()
            else:
                report["error"] = f"Exec failed (code {result.returncode}): {result.stderr.strip()}"
        except Exception as e:
            report["error"] = f"Exec error: {e}"
    else:
        report["error"] = f"Executable missing at {exec_path}"
        
    return report

def main():
    install_root = project_root / "tool" / "PYTHON" / "data" / "install"
    installed_versions = sorted([d.name for d in install_root.iterdir() if d.is_dir()])
    
    if not installed_versions:
        print("No Python versions found in tool/PYTHON/data/install/")
        return

    print(f"Verifying {len(installed_versions)} versions...")
    print(f"{'Version':<30} | {'JSON':<10} | {'Release':<12} | {'Exec':<10} | {'Output'}")
    print("-" * 100)
    
    all_reports = []
    for v in installed_versions:
        report = verify_version(v)
        all_reports.append(report)
        
        json_status = "OK" if report["json_exists"] else "MISSING"
        exec_status = "OK" if report["exec_works"] else "FAIL"
        
        print(f"{v:<30} | {json_status:<10} | {report['release']:<12} | {exec_status:<10} | {report['version_output']}")
        if report["error"] and not report["exec_works"]:
            print(f"  -> Error: {report['error']}")

    # Save validation report
    output_path = project_root / "tool" / "PYTHON" / "data" / "audit" / "validation_report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(all_reports, f, indent=2)
    print(f"\nFull validation report saved to: {output_path}")

if __name__ == "__main__":
    main()

