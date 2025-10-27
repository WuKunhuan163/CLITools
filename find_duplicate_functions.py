#!/usr/bin/env python3
"""
检查 GOOGLE_DRIVE_PROJ 中是否有同一文件内重复的函数定义
"""

import os
import re
from pathlib import Path
from collections import defaultdict

def find_function_definitions_with_lines(file_path):
    """找到文件中所有函数定义及其行号"""
    functions = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(lines, 1):
                # 匹配函数定义: def function_name(
                match = re.match(r'^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', line)
                if match:
                    func_name = match.group(1)
                    functions.append((func_name, i))
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return functions

def main():
    project_dir = Path(__file__).parent / "GOOGLE_DRIVE_PROJ"
    
    if not project_dir.exists():
        print(f"Error: {project_dir} not found")
        return
    
    print("Checking for duplicate function definitions...")
    print("=" * 80)
    
    found_duplicates = False
    total_files_checked = 0
    total_duplicates = 0
    
    for root, dirs, files in os.walk(project_dir):
        # 忽略特定目录
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', '.pytest_cache']]
        
        for file in files:
            if file.endswith('.py'):
                total_files_checked += 1
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, project_dir)
                
                functions = find_function_definitions_with_lines(file_path)
                
                # 统计每个函数名出现的次数
                func_counts = defaultdict(list)
                for func_name, line_num in functions:
                    func_counts[func_name].append(line_num)
                
                # 找出重复的函数
                duplicates = {name: lines for name, lines in func_counts.items() if len(lines) > 1}
                
                if duplicates:
                    if not found_duplicates:
                        found_duplicates = True
                    
                    print(f"\n🚨 DUPLICATES FOUND in {rel_path}:")
                    print("-" * 80)
                    for func_name, line_nums in sorted(duplicates.items()):
                        print(f"  Function: {func_name}")
                        print(f"  Defined at lines: {', '.join(map(str, line_nums))}")
                        print(f"  ({len(line_nums)} definitions)\n")
                        total_duplicates += len(line_nums) - 1  # Count extra definitions
    
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print(f"  • Files checked: {total_files_checked}")
    if found_duplicates:
        print(f"  • ⚠️  Found {total_duplicates} duplicate function definitions!")
    else:
        print(f"  • ✅ No duplicate function definitions found")
    print("=" * 80)

if __name__ == "__main__":
    main()

