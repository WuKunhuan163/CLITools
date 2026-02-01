#!/usr/bin/env python3
import sys
import os
import subprocess
import json
import argparse
from pathlib import Path

# Add project root to sys.path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent.parent
sys.path.append(str(project_root))

def main():
    parser = argparse.ArgumentParser(description="Batch migrate Python assets.")
    parser.add_argument("--range", nargs=2, type=int, help="Range of asset indices to migrate (start end, inclusive)")
    parser.add_argument("--ids", nargs="+", type=int, help="Specific asset indices to migrate")
    parser.add_argument("--max-concurrent", type=int, default=3, help="Max parallel migrations")
    parser.add_argument("--force", action="store_true", help="Force migration even if already exists")
    
    args = parser.parse_args()
    
    # 1. Get the latest audit report
    audit_dir = project_root / "tool" / "PYTHON" / "data" / "audit" / "releases"
    reports = sorted(list(audit_dir.glob("report_*.json")), reverse=True)
    
    if not reports:
        print("No audit reports found. Please run 'PYTHON --py-update --list' first.")
        return
    
    with open(reports[0], "r") as f:
        data = json.load(f)
        all_assets = data.get("short", [])
    
    if not all_assets:
        print("No assets found in the latest report.")
        return

    print(f"Found {len(all_assets)} assets in total.")
    
    target_indices = []
    if args.ids:
        target_indices = [i for i in args.ids if 0 <= i < len(all_assets)]
    elif args.range:
        start, end = args.range
        target_indices = list(range(max(0, start), min(len(all_assets), end + 1)))
    else:
        print("Please specify --range or --ids. Indices start from 0.")
        return

    to_migrate = [all_assets[i] for i in target_indices]
    
    if not to_migrate:
        return

    # Instead of running multiple main.py processes, call one main.py with all versions
    # This allows the tool's internal MultiLineManager to handle concurrency correctly.
    tool_main = project_root / "tool" / "PYTHON" / "main.py"
    cmd = [sys.executable, str(tool_main), "--py-update"] + to_migrate + ["--concurrency", str(args.max_concurrent)]
    if args.force:
        cmd.append("--force")
    
    print(f"Preparing to migrate {len(to_migrate)} assets: {', '.join(to_migrate)}")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, cwd=str(project_root))
    except Exception as e:
        print(f"Error during batch migration: {e}")

if __name__ == "__main__":
    main()

