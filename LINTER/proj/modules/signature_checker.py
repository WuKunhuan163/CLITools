"""
Function Signature Checker Module
Validates function call signatures against their definitions
"""

import ast
import os
from pathlib import Path
from typing import Dict, List
from collections import defaultdict


class SignatureChecker:
    """Checks function call signatures"""
    
    def __init__(self, target_path: str, verbose: bool = False):
        self.target_path = Path(target_path)
        self.verbose = verbose
        self.function_defs = defaultdict(list)
        self.issues = []
        
    def collect_definitions(self, filepath: Path):
        """Collect function definitions with parameter info"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_name = node.name
                    args = node.args
                    
                    total_params = len(args.args)
                    defaults_count = len(args.defaults)
                    min_args = total_params - defaults_count
                    max_args = total_params
                    
                    param_names = [arg.arg for arg in args.args]
                    has_self = total_params > 0 and param_names[0] == 'self'
                    has_varargs = args.vararg is not None
                    has_kwargs = args.kwarg is not None
                    kwonly_args = [arg.arg for arg in args.kwonlyargs]
                    
                    self.function_defs[func_name].append({
                        'file': str(filepath),
                        'line': node.lineno,
                        'min_args': min_args,
                        'max_args': max_args,
                        'param_names': param_names,
                        'kwonly_args': kwonly_args,
                        'has_self': has_self,
                        'has_varargs': has_varargs,
                        'has_kwargs': has_kwargs
                    })
        except Exception:
            pass
    
    def check_calls(self, filepath: Path):
        """Check function calls in a file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = None
                    is_method_call = False
                    
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr
                        is_method_call = True
                    
                    if not func_name:
                        continue
                    
                    # Skip builtins
                    builtins = ['print', 'len', 'str', 'int', 'float', 'bool', 'list', 'dict', 
                               'set', 'tuple', 'range', 'enumerate', 'zip', 'map', 'filter',
                               'sorted', 'isinstance', 'hasattr', 'getattr', 'setattr', 'open',
                               'input', 'format', 'type', 'super', 'property']
                    
                    if func_name in builtins:
                        continue
                    
                    # Skip common methods
                    if is_method_call:
                        common_methods = ['get', 'pop', 'update', 'append', 'extend', 'keys',
                                        'values', 'items', 'split', 'join', 'strip', 'replace',
                                        'format', 'startswith', 'endswith', 'find', 'index',
                                        'count', 'lower', 'upper']
                        if func_name in common_methods:
                            continue
                    
                    pos_args_count = len(node.args)
                    keyword_args = {kw.arg: kw.value for kw in node.keywords if kw.arg}
                    
                    if func_name in self.function_defs:
                        self._check_single_call(
                            filepath, node.lineno, func_name, is_method_call,
                            pos_args_count, keyword_args
                        )
        except Exception:
            pass
    
    def _check_single_call(self, filepath, lineno, func_name, is_method_call, 
                          pos_args_count, keyword_args):
        """Check a single function call against definitions"""
        defs = self.function_defs[func_name]
        
        signature_match = False
        
        for defn in defs:
            min_args = defn['min_args']
            max_args = defn['max_args']
            param_names = defn['param_names']
            has_self = defn['has_self']
            has_varargs = defn['has_varargs']
            has_kwargs = defn['has_kwargs']
            
            # Adjust for self in method calls
            if is_method_call and has_self:
                min_args = max(0, min_args - 1)
                max_args = max(0, max_args - 1)
                param_names = param_names[1:] if param_names else []
            
            # Accept any arguments if varargs or kwargs
            if has_varargs or has_kwargs:
                signature_match = True
                break
            
            # Check positional arguments
            if pos_args_count < min_args:
                # Check if provided via kwargs
                required_params = param_names[:min_args]
                provided_via_kwargs = sum(1 for p in required_params[pos_args_count:] 
                                        if p in keyword_args)
                
                if pos_args_count + provided_via_kwargs >= min_args:
                    signature_match = True
                    break
            elif pos_args_count <= max_args:
                # Check kwargs are valid
                invalid_kwargs = [kw for kw in keyword_args 
                                if kw not in param_names and kw not in defn['kwonly_args']]
                
                if not invalid_kwargs:
                    signature_match = True
                    break
        
        if not signature_match:
            self.issues.append({
                'file': str(filepath),
                'line': lineno,
                'function': func_name,
                'provided_args': pos_args_count,
                'provided_kwargs': list(keyword_args.keys()),
                'is_method_call': is_method_call,
                'expected_min': defs[0]['min_args'],
                'expected_max': defs[0]['max_args']
            })
    
    def run(self) -> Dict:
        """Run signature checking"""
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
                'functions_checked': 0,
                'issues_found': 0,
                'issues': []
            }
        
        # Collect definitions
        if self.verbose:
            print(f"Collecting definitions from {len(python_files)} files...")
        
        for filepath in python_files:
            self.collect_definitions(filepath)
        
        # Check calls
        if self.verbose:
            print(f"Checking function calls...")
        
        for filepath in python_files:
            self.check_calls(filepath)
        
        return {
            'success': True,
            'message': f'Checked {len(self.function_defs)} functions, found {len(self.issues)} signature issues',
            'functions_checked': len(self.function_defs),
            'issues_found': len(self.issues),
            'issues': self.issues
        }


