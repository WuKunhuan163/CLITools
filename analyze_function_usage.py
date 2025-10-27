#!/usr/bin/env python3
"""
分析 GOOGLE_DRIVE_PROJ 中所有函数的使用频率
找出未使用的或很少使用的函数
"""

import os
import re
from pathlib import Path
from collections import defaultdict

def find_function_definitions(file_path):
    """找到文件中所有函数定义"""
    functions = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # 匹配函数定义: def function_name(
            pattern = r'^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
            for match in re.finditer(pattern, content, re.MULTILINE):
                func_name = match.group(1)
                functions.append(func_name)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return functions

def count_function_calls(directory, func_name):
    """统计函数在整个项目中被调用的次数"""
    count = 0
    # 匹配函数调用: .function_name( 或 function_name(
    patterns = [
        rf'\.{re.escape(func_name)}\s*\(',  # .function_name(
        rf'(?<![a-zA-Z0-9_]){re.escape(func_name)}\s*\(',  # function_name( (不是def或其他标识符的一部分)
    ]
    
    for root, dirs, files in os.walk(directory):
        # 忽略 __pycache__ 和 .git 目录
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', '.pytest_cache']]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        for pattern in patterns:
                            matches = re.findall(pattern, content)
                            count += len(matches)
                except Exception as e:
                    pass
    
    # 减去1，因为函数定义本身也会匹配一次
    return max(0, count - 1)

def main():
    project_dir = Path(__file__).parent / "GOOGLE_DRIVE_PROJ"
    
    if not project_dir.exists():
        print(f"Error: {project_dir} not found")
        return
    
    print("Analyzing GOOGLE_DRIVE_PROJ...")
    print("=" * 80)
    
    # 收集所有函数定义
    all_functions = defaultdict(list)  # {func_name: [file_paths]}
    
    for root, dirs, files in os.walk(project_dir):
        # 忽略特定目录
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', '.pytest_cache']]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, project_dir)
                functions = find_function_definitions(file_path)
                for func in functions:
                    all_functions[func].append(rel_path)
    
    print(f"Found {len(all_functions)} unique function names in {sum(len(v) for v in all_functions.values())} total definitions\n")
    
    # 统计每个函数的调用次数
    function_usage = {}
    
    print("Counting function calls...")
    for i, (func_name, file_paths) in enumerate(all_functions.items(), 1):
        if i % 50 == 0:
            print(f"  Progress: {i}/{len(all_functions)}")
        
        call_count = count_function_calls(project_dir, func_name)
        function_usage[func_name] = {
            'count': call_count,
            'defined_in': file_paths
        }
    
    print("\nAnalysis complete!")
    print("=" * 80)
    
    # 按照调用次数排序
    sorted_functions = sorted(function_usage.items(), key=lambda x: x[1]['count'])
    
    # 输出结果
    print("\n" + "=" * 80)
    print("FUNCTION USAGE REPORT (sorted by call count)")
    print("=" * 80)
    
    # 分类统计
    unused = [(name, info) for name, info in sorted_functions if info['count'] == 0]
    rarely_used = [(name, info) for name, info in sorted_functions if 0 < info['count'] <= 3]
    moderately_used = [(name, info) for name, info in sorted_functions if 3 < info['count'] <= 10]
    frequently_used = [(name, info) for name, info in sorted_functions if info['count'] > 10]
    
    print(f"\n📊 SUMMARY:")
    print(f"  • Unused functions (0 calls): {len(unused)}")
    print(f"  • Rarely used (1-3 calls): {len(rarely_used)}")
    print(f"  • Moderately used (4-10 calls): {len(moderately_used)}")
    print(f"  • Frequently used (>10 calls): {len(frequently_used)}")
    
    # 输出未使用的函数
    if unused:
        print(f"\n🚫 UNUSED FUNCTIONS ({len(unused)}):")
        print("=" * 80)
        for func_name, info in unused:
            print(f"\n  {func_name}")
            for file_path in info['defined_in']:
                print(f"    Defined in: {file_path}")
    
    # 输出很少使用的函数
    if rarely_used:
        print(f"\n⚠️  RARELY USED FUNCTIONS (1-3 calls):")
        print("=" * 80)
        for func_name, info in rarely_used[:30]:  # 只显示前30个
            print(f"\n  {func_name} (called {info['count']} times)")
            for file_path in info['defined_in']:
                print(f"    Defined in: {file_path}")
    
    # 输出完整列表到文件
    output_file = Path(__file__).parent / "function_usage_report.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("COMPLETE FUNCTION USAGE REPORT\n")
        f.write("=" * 80 + "\n\n")
        
        for func_name, info in sorted_functions:
            f.write(f"{func_name}: {info['count']} calls\n")
            for file_path in info['defined_in']:
                f.write(f"  Defined in: {file_path}\n")
            f.write("\n")
    
    print(f"\n✅ Complete report saved to: {output_file}")
    print("\nTop 20 most frequently used functions:")
    print("=" * 80)
    for func_name, info in sorted_functions[-20:]:
        print(f"  {func_name}: {info['count']} calls")

if __name__ == "__main__":
    main()

