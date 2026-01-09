"""
Import Checker Module
Validates Python imports and detects missing/unused imports
"""

import ast
import importlib
import sys
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict


class ImportChecker:
    """Checks for import issues in Python code"""
    
    def __init__(self, target_path: str, verbose: bool = False):
        self.target_path = Path(target_path)
        self.verbose = verbose
        self.issues = defaultdict(list)
        
    def check_file(self, filepath: Path) -> Dict:
        """Check imports in a single file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Collect imports
            imported = set()
            import_lines = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.asname if alias.asname else alias.name
                        imported.add(name)
                        import_lines[name] = node.lineno
                elif isinstance(node, ast.ImportFrom):
                    if node.names[0].name == '*':
                        imported.add('*')
                    else:
                        for alias in node.names:
                            name = alias.asname if alias.asname else alias.name
                            imported.add(name)
                            import_lines[name] = node.lineno
            
            # Collect local definitions
            defined = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    defined.add(node.name)
                elif isinstance(node, ast.ClassDef):
                    defined.add(node.name)
            
            # Collect used names
            used = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    used.add(node.id)
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        used.add(node.func.id)
            
            # Check for unused imports
            unused_imports = []
            for imp in imported:
                if imp != '*' and imp not in used and imp not in defined:
                    unused_imports.append({
                        'name': imp,
                        'line': import_lines.get(imp, 0)
                    })
            
            # Check for missing imports
            import builtins as builtins_module
            builtins = set(dir(builtins_module))
            missing_imports = []
            
            for name in used:
                if (name not in imported and
                    name not in defined and
                    name not in builtins and
                    '*' not in imported):
                    missing_imports.append(name)
            
            return {
                'file': str(filepath),
                'unused_imports': unused_imports,
                'missing_imports': missing_imports,
                'total_imports': len(imported)
            }
            
        except Exception as e:
            return {
                'file': str(filepath),
                'error': str(e),
                'unused_imports': [],
                'missing_imports': [],
                'total_imports': 0
            }
    
    def run(self) -> Dict:
        """Run import checking"""
        python_files = []
        
        if self.target_path.is_file():
            if self.target_path.suffix == '.py':
                python_files.append(self.target_path)
        else:
            for root, dirs, files in os.walk(self.target_path):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                for file in files:
                    if file.endswith('.py'):
                        python_files.append(Path(root) / file)
        
        if not python_files:
            return {
                'success': False,
                'message': 'No Python files found',
                'files_checked': 0,
                'files_with_issues': 0,
                'issues': []
            }
        
        results = []
        files_with_issues = 0
        
        for filepath in python_files:
            if self.verbose:
                print(f"Checking: {filepath.name}")
            
            result = self.check_file(filepath)
            
            if result.get('unused_imports') or result.get('missing_imports'):
                files_with_issues += 1
                results.append(result)
        
        return {
            'success': True,
            'message': f'Checked {len(python_files)} files, found issues in {files_with_issues}',
            'files_checked': len(python_files),
            'files_with_issues': files_with_issues,
            'issues': results
        }


import os


