#!/usr/bin/env python3
import sys
import os
import subprocess
import json
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to sys.path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent.parent
sys.path.append(str(project_root))

def run_migration(version_tag, force=False):
    """Runs the migration for a single version."""
    # Call the tool's main.py directly
    tool_main = project_root / "tool" / "PYTHON" / "main.py"
    cmd = [sys.executable, str(tool_main), "--py-update", version_tag]
    if force:
        cmd.append("--force")
    
    print(f"Starting migration for {version_tag}...")
    try:
        # Use subprocess.run to allow the TUI progress manager to handle its own output
        # But for batch we might want to capture it or just let it print
        result = subprocess.run(cmd, cwd=str(project_root))
        return result.returncode == 0
    except Exception as e:
        print(f"Error migrating {version_tag}: {e}")
        return False

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
    print(f"Preparing to migrate {len(to_migrate)} assets: {', '.join(to_migrate)}")
    
    if not to_migrate:
        return

    # 2. Run migrations
    results = {}
    with ThreadPoolExecutor(max_workers=args.max_concurrent) as executor:
        future_to_v = {executor.submit(run_migration, v, args.force): v for v in to_migrate}
        for future in as_completed(future_to_v):
            v = future_to_v[future]
            try:
                success = future.result()
                results[v] = "Success" if success else "Failed"
            except Exception as e:
                results[v] = f"Error: {e}"

    print("\n" + "="*40)
    print("Batch Migration Summary:")
    for v, res in results.items():
        print(f"  {v}: {res}")
    print("="*40)

if __name__ == "__main__":
    main()

