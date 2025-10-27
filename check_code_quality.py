#!/usr/bin/env python3
"""
代码质量检查工具
- 检查未使用的导入
- 检查未定义的函数调用
- 检查未使用的变量定义
"""

import os
import ast
from pathlib import Path
from collections import defaultdict
import re

class CodeQualityChecker:
    def __init__(self, project_dir):
        self.project_dir = project_dir
        self.issues = defaultdict(list)
        
    def check_file(self, file_path):
        """检查单个文件的代码质量"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content, filename=file_path)
            
            # 收集导入
            imports = self._collect_imports(tree)
            # 收集定义的函数和类
            definitions = self._collect_definitions(tree, content)
            # 收集使用的名称
            usages = self._collect_usages(tree, content)
            
            # 检查未使用的导入
            unused_imports = []
            for imp_name, imp_info in imports.items():
                if imp_name not in usages and not imp_name.startswith('_'):
                    # 排除一些特殊情况
                    if imp_name not in ['typing', 'Optional', 'List', 'Dict', 'Any']:
                        unused_imports.append({
                            'type': 'unused_import',
                            'line': imp_info['line'],
                            'name': imp_name,
                            'statement': imp_info['statement']
                        })
            
            # 检查可能未定义的调用
            undefined_calls = []
            for usage in usages:
                # 如果使用的名称不在导入和定义中，可能是未定义的
                if usage not in imports and usage not in definitions:
                    # 排除一些内置名称和特殊情况
                    if not self._is_builtin_or_special(usage):
                        undefined_calls.append({
                            'type': 'possibly_undefined',
                            'name': usage
                        })
            
            return {
                'imports': imports,
                'definitions': definitions,
                'usages': usages,
                'unused_imports': unused_imports,
                'undefined_calls': undefined_calls
            }
        
        except SyntaxError as e:
            return {
                'error': f"Syntax error: {e}",
                'line': e.lineno
            }
        except Exception as e:
            return {
                'error': f"Error: {e}"
            }
    
    def _collect_imports(self, tree):
        """收集所有导入"""
        imports = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name.split('.')[0]
                    imports[name] = {
                        'line': node.lineno,
                        'statement': f"import {alias.name}",
                        'type': 'import'
                    }
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports[name] = {
                        'line': node.lineno,
                        'statement': f"from {module} import {alias.name}",
                        'type': 'from_import'
                    }
        return imports
    
    def _collect_definitions(self, tree, content):
        """收集所有函数和类定义"""
        definitions = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                definitions[node.name] = {
                    'line': node.lineno,
                    'type': 'function'
                }
            elif isinstance(node, ast.ClassDef):
                definitions[node.name] = {
                    'line': node.lineno,
                    'type': 'class'
                }
        return definitions
    
    def _collect_usages(self, tree, content):
        """收集所有名称使用"""
        usages = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                usages.add(node.id)
            elif isinstance(node, ast.Attribute):
                # 对于 obj.attr，收集 obj
                if isinstance(node.value, ast.Name):
                    usages.add(node.value.id)
        return usages
    
    def _is_builtin_or_special(self, name):
        """检查是否是内置名称或特殊名称"""
        builtins = {
            # Python内置函数
            'print', 'len', 'range', 'str', 'int', 'float', 'list', 'dict',
            'set', 'tuple', 'bool', 'type', 'isinstance', 'issubclass',
            'open', 'input', 'sum', 'min', 'max', 'abs', 'all', 'any',
            'enumerate', 'zip', 'map', 'filter', 'sorted', 'reversed',
            # 常见模块和标准库
            'os', 'sys', 'time', 'json', 'Path', 're', 'subprocess',
            # Python关键字和特殊名称
            'self', 'cls', 'super', 'None', 'True', 'False',
            # 异常类
            'Exception', 'ValueError', 'TypeError', 'KeyError',
            'IndexError', 'AttributeError', 'ImportError',
            # typing相关
            'Optional', 'List', 'Dict', 'Any', 'Union', 'Tuple'
        }
        return name in builtins or name.startswith('_')
    
    def check_project(self):
        """检查整个项目"""
        results = {}
        py_files = []
        
        # 收集所有Python文件
        for root, dirs, files in os.walk(self.project_dir):
            # 跳过特定目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for file in files:
                if file.endswith('.py') and 'backup' not in file.lower():
                    file_path = os.path.join(root, file)
                    py_files.append(file_path)
        
        print(f"🔍 扫描 {len(py_files)} 个Python文件...\n")
        
        # 检查每个文件
        files_with_issues = 0
        total_issues = 0
        
        for file_path in sorted(py_files):
            relative_path = os.path.relpath(file_path, self.project_dir)
            result = self.check_file(file_path)
            
            if 'error' in result:
                print(f"❌ {relative_path}")
                print(f"   错误: {result['error']}")
                continue
            
            has_issues = False
            file_issues = []
            
            # 未使用的导入
            if result['unused_imports']:
                has_issues = True
                for issue in result['unused_imports']:
                    file_issues.append(f"  ⚠️  未使用的导入 (line {issue['line']}): {issue['statement']}")
                    total_issues += 1
            
            # 可能未定义的调用（只显示前5个）
            if result['undefined_calls']:
                # 过滤掉常见的误报
                filtered_calls = [c for c in result['undefined_calls'] 
                                 if c['name'] not in ['f', 'e', 'x', 'i', 'j', 'k', 'v', 'args', 'kwargs']]
                if filtered_calls[:5]:  # 只显示前5个
                    has_issues = True
                    for issue in filtered_calls[:5]:
                        file_issues.append(f"  💡 可能未定义: {issue['name']}")
                        total_issues += 1
            
            if has_issues:
                files_with_issues += 1
                print(f"\n📄 {relative_path}")
                for issue_msg in file_issues:
                    print(issue_msg)
            
            results[relative_path] = result
        
        print(f"\n" + "=" * 80)
        print(f"📊 检查完成")
        print(f"   文件总数: {len(py_files)}")
        print(f"   有问题的文件: {files_with_issues}")
        print(f"   问题总数: {total_issues}")
        print("=" * 80)
        
        return results

def main():
    project_dir = 'GOOGLE_DRIVE_PROJ'
    
    print("🔍 代码质量检查工具")
    print("=" * 80)
    print(f"项目目录: {project_dir}\n")
    
    checker = CodeQualityChecker(project_dir)
    results = checker.check_project()
    
    # 生成报告文件
    report_path = 'code_quality_report.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("代码质量检查报告\n")
        f.write("=" * 80 + "\n\n")
        
        for file_path, result in sorted(results.items()):
            if 'error' in result:
                f.write(f"{file_path}: ERROR - {result['error']}\n")
                continue
            
            if result['unused_imports'] or result['undefined_calls']:
                f.write(f"\n{file_path}\n")
                f.write("-" * 80 + "\n")
                
                for issue in result['unused_imports']:
                    f.write(f"  [未使用导入] Line {issue['line']}: {issue['statement']}\n")
                
                for issue in result['undefined_calls'][:10]:
                    f.write(f"  [可能未定义] {issue['name']}\n")
    
    print(f"\n📝 详细报告已保存到: {report_path}")

if __name__ == '__main__':
    main()

