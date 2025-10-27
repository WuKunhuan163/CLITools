#!/usr/bin/env python3
"""
查找可能的委托调用模式
找到那些只被调用1次，且调用位置紧跟在定义之后的函数
"""

import os
import re
import ast
from pathlib import Path
from collections import defaultdict

def get_function_definitions(file_path):
    """获取文件中所有函数定义及其位置"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content, filename=file_path)
        
        functions = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions[node.name] = {
                    'line': node.lineno,
                    'end_line': node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
                    'is_method': False
                }
        
        # 检测方法（在类中的函数）
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if item.name in functions:
                            functions[item.name]['is_method'] = True
        
        return functions
    except Exception as e:
        return {}

def find_function_calls(file_path, target_function):
    """在文件中查找特定函数的所有调用位置"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        call_locations = []
        # 匹配函数调用：function_name(
        # 也匹配 self.function_name( 和 obj.function_name(
        pattern = rf'\b{re.escape(target_function)}\s*\('
        
        for i, line in enumerate(lines, 1):
            # 跳过注释
            if line.strip().startswith('#'):
                continue
            
            if re.search(pattern, line):
                # 排除函数定义行
                if not (line.strip().startswith('def ') or line.strip().startswith('async def ')):
                    call_locations.append(i)
        
        return call_locations
    except Exception as e:
        return []

def analyze_delegate_patterns(project_dir):
    """分析项目中的委托调用模式"""
    project_path = Path(project_dir)
    
    # 收集所有Python文件
    py_files = []
    for root, dirs, files in os.walk(project_path):
        # 跳过__pycache__等目录
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for file in files:
            if file.endswith('.py'):
                py_files.append(os.path.join(root, file))
    
    delegate_candidates = []
    
    for file_path in py_files:
        # 跳过备份文件
        if 'backup' in file_path.lower():
            continue
        
        relative_path = os.path.relpath(file_path, project_dir)
        functions = get_function_definitions(file_path)
        
        for func_name, func_info in functions.items():
            # 查找调用位置
            call_locations = find_function_calls(file_path, func_name)
            
            # 过滤：只保留调用1次的函数
            if len(call_locations) == 1:
                call_line = call_locations[0]
                def_end_line = func_info['end_line']
                
                # 检查调用是否在定义之后不远处（比如在20行内）
                distance = call_line - def_end_line
                
                if 0 < distance <= 20:
                    # 读取调用行的内容
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            call_line_content = lines[call_line - 1].strip() if call_line <= len(lines) else ""
                    except:
                        call_line_content = ""
                    
                    delegate_candidates.append({
                        'file': relative_path,
                        'function': func_name,
                        'def_line': func_info['line'],
                        'def_end_line': def_end_line,
                        'call_line': call_line,
                        'distance': distance,
                        'call_content': call_line_content,
                        'is_method': func_info['is_method']
                    })
    
    return delegate_candidates

def main():
    project_dir = 'GOOGLE_DRIVE_PROJ'
    
    print("🔍 查找潜在的委托调用模式")
    print("=" * 80)
    print(f"项目目录: {project_dir}")
    print(f"查找条件: 函数只被调用1次，且调用在定义后20行内\n")
    
    candidates = analyze_delegate_patterns(project_dir)
    
    if not candidates:
        print("✅ 未发现明显的委托调用模式")
        return
    
    # 按文件分组
    by_file = defaultdict(list)
    for candidate in candidates:
        by_file[candidate['file']].append(candidate)
    
    print(f"📊 发现 {len(candidates)} 个潜在的委托调用\n")
    
    for file_path in sorted(by_file.keys()):
        items = by_file[file_path]
        print(f"\n📄 {file_path} ({len(items)} 个)")
        print("-" * 80)
        
        for item in sorted(items, key=lambda x: x['def_line']):
            func_type = "方法" if item['is_method'] else "函数"
            print(f"\n  {func_type}: {item['function']}")
            print(f"    定义: 第 {item['def_line']}-{item['def_end_line']} 行")
            print(f"    调用: 第 {item['call_line']} 行 (距离: {item['distance']} 行)")
            print(f"    内容: {item['call_content'][:80]}")
            
            # 检测是否是self.调用（典型的委托模式）
            if 'self.' in item['call_content'] or 'return ' in item['call_content']:
                print(f"    🚨 可能是委托调用！")
    
    # 生成报告文件
    report_path = 'delegate_calls_report.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("委托调用分析报告\n")
        f.write("=" * 80 + "\n\n")
        
        for file_path in sorted(by_file.keys()):
            items = by_file[file_path]
            f.write(f"\n{file_path} ({len(items)} 个)\n")
            f.write("-" * 80 + "\n")
            
            for item in sorted(items, key=lambda x: x['def_line']):
                f.write(f"\n{item['function']}\n")
                f.write(f"  定义: {item['def_line']}-{item['def_end_line']}\n")
                f.write(f"  调用: {item['call_line']} (距离 {item['distance']})\n")
                f.write(f"  {item['call_content']}\n")
    
    print(f"\n\n📝 详细报告已保存到: {report_path}")

if __name__ == '__main__':
    main()

