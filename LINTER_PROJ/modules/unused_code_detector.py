"""
Unused Code Detector Module
Analyzes Python code for unused functions, classes, variables, and imports
"""

import os
import ast
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

class CodeAnalyzer(ast.NodeVisitor):
    """AST visitor for analyzing code definitions and usages"""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.definitions = {
            'functions': {},
            'classes': {},
            'variables': {},
            'imports': {},
        }
        self.usages = {
            'functions': set(),
            'classes': set(),
            'variables': set(),
            'imports': set(),
        }
        self.current_scope = []
        self.private_names = set()
        
        # For local variable tracking: {scope_name: {var_name: lineno}}
        self.local_vars_by_scope = {}
        # Track which local vars are used: {scope_name: {var_name}}
        self.local_vars_used_by_scope = {}
        
        # Track variable types for simple type inference
        # {var_name: class_name}
        self.variable_types = {}
        
        # Track class methods for matching attribute calls
        # {class_name: [method_names]}
        self.class_methods = {}
        
    def visit_FunctionDef(self, node):
        """Visit function definition"""
        func_name = node.name
        full_name = '.'.join(self.current_scope + [func_name])
        self.definitions['functions'][full_name] = node.lineno
        
        if func_name.startswith('_'):
            self.private_names.add(full_name)
        
        # Check decorators
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                # Simple decorator like @abstractmethod
                self.usages['functions'].add(decorator.id)
                self.usages['imports'].add(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                # Decorator like @abc.abstractmethod
                if isinstance(decorator.value, ast.Name):
                    self.usages['imports'].add(decorator.value.id)
        
        # Check type annotations in parameters and return type
        for arg in node.args.args:
            if arg.annotation:
                self._visit_annotation(arg.annotation)
        
        # Check return type annotation
        if node.returns:
            self._visit_annotation(node.returns)
        
        # Enter function scope
        self.current_scope.append(func_name)
        scope_name = '.'.join(self.current_scope)
        self.local_vars_by_scope[scope_name] = {}
        self.local_vars_used_by_scope[scope_name] = set()
        
        # Visit function body
        for stmt in node.body:
            self.visit(stmt)
        
        # Exit scope
        self.current_scope.pop()
    
    def _visit_annotation(self, annotation):
        """Visit type annotation and mark used names"""
        if isinstance(annotation, ast.Name):
            # Simple type like List, Optional, int, str
            self.usages['imports'].add(annotation.id)
            self.usages['classes'].add(annotation.id)
        elif isinstance(annotation, ast.Subscript):
            # Generic type like List[str], Optional[Dict]
            if isinstance(annotation.value, ast.Name):
                self.usages['imports'].add(annotation.value.id)
            # Recursively visit the subscript
            if hasattr(annotation, 'slice'):
                if isinstance(annotation.slice, ast.Name):
                    self.usages['imports'].add(annotation.slice.id)
                elif isinstance(annotation.slice, ast.Tuple):
                    for elt in annotation.slice.elts:
                        if isinstance(elt, ast.Name):
                            self.usages['imports'].add(elt.id)
        elif isinstance(annotation, ast.Attribute):
            # Type like typing.List
            if isinstance(annotation.value, ast.Name):
                self.usages['imports'].add(annotation.value.id)
        
    def visit_AsyncFunctionDef(self, node):
        """Visit async function definition"""
        self.visit_FunctionDef(node)
        
    def visit_ClassDef(self, node):
        """Visit class definition"""
        class_name = node.name
        full_name = '.'.join(self.current_scope + [class_name])
        self.definitions['classes'][full_name] = node.lineno
        
        if class_name.startswith('_'):
            self.private_names.add(full_name)
        
        # Check decorators
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                self.usages['functions'].add(decorator.id)
                self.usages['imports'].add(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                if isinstance(decorator.value, ast.Name):
                    self.usages['imports'].add(decorator.value.id)
        
        # Check base classes
        for base in node.bases:
            if isinstance(base, ast.Name):
                self.usages['classes'].add(base.id)
                self.usages['imports'].add(base.id)
            elif isinstance(base, ast.Attribute):
                if isinstance(base.value, ast.Name):
                    self.usages['imports'].add(base.value.id)
        
        self.current_scope.append(class_name)
        for stmt in node.body:
            self.visit(stmt)
        self.current_scope.pop()
        
    def visit_Assign(self, node):
        """Visit assignment statement"""
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                
                if self.current_scope:
                    # Local variable in function/class
                    scope_name = '.'.join(self.current_scope)
                    if scope_name in self.local_vars_by_scope:
                        self.local_vars_by_scope[scope_name][var_name] = node.lineno
                else:
                    # Module-level variable
                    full_name = var_name
                    self.definitions['variables'][full_name] = node.lineno
                    
                    if var_name.startswith('_'):
                        self.private_names.add(full_name)
        
        self.generic_visit(node)
    
    def visit_Nonlocal(self, node):
        """Visit nonlocal statement"""
        # Mark nonlocal variables as used in their enclosing scope
        if self.current_scope and len(self.current_scope) > 1:
            # Find the enclosing scope (parent function)
            parent_scope = '.'.join(self.current_scope[:-1])
            current_scope_name = '.'.join(self.current_scope)
            
            for name in node.names:
                # Mark the variable as used in the parent scope
                if parent_scope in self.local_vars_used_by_scope:
                    self.local_vars_used_by_scope[parent_scope].add(name)
                else:
                    self.local_vars_used_by_scope[parent_scope] = {name}
                
                # Also mark as used in current scope for any future references
                if current_scope_name in self.local_vars_used_by_scope:
                    self.local_vars_used_by_scope[current_scope_name].add(name)
                else:
                    self.local_vars_used_by_scope[current_scope_name] = {name}
        
    def visit_Import(self, node):
        """Visit import statement"""
        for alias in node.names:
            import_name = alias.asname if alias.asname else alias.name
            self.definitions['imports'][import_name] = node.lineno
            
    def visit_ImportFrom(self, node):
        """Visit from...import statement"""
        for alias in node.names:
            if alias.name == '*':
                continue
            import_name = alias.asname if alias.asname else alias.name
            self.definitions['imports'][import_name] = node.lineno
            
    def visit_Attribute(self, node):
        """Visit attribute access (e.g., self.method, obj.attr, module.Class)"""
        # IMPORTANT: Visit children first to handle nested attributes
        self.generic_visit(node)
        
        # Then mark attribute as used
        if isinstance(node.ctx, ast.Load):
            attr_name = node.attr
            
            # Check if this is self.method_name
            if isinstance(node.value, ast.Name) and node.value.id == 'self':
                # Mark method as used - get class name from scope
                if self.current_scope:
                    # current_scope = ['ClassName', 'method_name', ...]
                    # First element is usually the class name
                    class_name = self.current_scope[0]
                    full_name = f"{class_name}.{attr_name}"
                    self.usages['functions'].add(full_name)
                
                # Also mark without class prefix (for simpler matching)
                self.usages['functions'].add(attr_name)
            
            # Check if this is obj.method where obj is a known variable/import
            elif isinstance(node.value, ast.Name):
                obj_name = node.value.id
                # When accessing module.attribute or obj.method, mark both as used
                self.usages['functions'].add(attr_name)
                self.usages['variables'].add(attr_name)
                self.usages['variables'].add(obj_name)
                self.usages['classes'].add(obj_name)
                self.usages['imports'].add(obj_name)
            
            # Handle nested attributes like self.api.method or module.submodule.Class
            elif isinstance(node.value, ast.Attribute):
                # Mark the final attribute as used (e.g., 'method' in self.api.method)
                self.usages['functions'].add(attr_name)
                self.usages['variables'].add(attr_name)
                
                # Walk back to find the root name
                current = node.value
                while isinstance(current, ast.Attribute):
                    # Also mark intermediate attributes (e.g., 'api' in self.api.method)
                    self.usages['variables'].add(current.attr)
                    self.usages['functions'].add(current.attr)
                    current = current.value
                
                # Mark the root (e.g., 'self' in self.api.method, or module name)
                if isinstance(current, ast.Name):
                    self.usages['imports'].add(current.id)
                    self.usages['variables'].add(current.id)
    
    def visit_Name(self, node):
        """Visit name usage"""
        if isinstance(node.ctx, ast.Load):
            name = node.id
            
            # Check if it's a local variable in current scope
            if self.current_scope:
                scope_name = '.'.join(self.current_scope)
                if scope_name in self.local_vars_by_scope:
                    if name in self.local_vars_by_scope[scope_name]:
                        # Mark this local var as used
                        self.local_vars_used_by_scope[scope_name].add(name)
                        # Still check global definitions too
            
            # Check global definitions
            if name in self.definitions['functions']:
                self.usages['functions'].add(name)
            if name in self.definitions['classes']:
                self.usages['classes'].add(name)
            if name in self.definitions['variables']:
                self.usages['variables'].add(name)
            if name in self.definitions['imports']:
                self.usages['imports'].add(name)
        
        self.generic_visit(node)
        
    def visit_Call(self, node):
        """Visit function call"""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            self.usages['functions'].add(func_name)
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                self.usages['variables'].add(node.func.value.id)
                self.usages['classes'].add(node.func.value.id)
        
        self.generic_visit(node)
        
    def visit_For(self, node):
        """Visit for loop - mark iterable as used"""
        # Mark the iterable as used
        if isinstance(node.iter, ast.Name):
            self.usages['variables'].add(node.iter.id)
        
        self.generic_visit(node)
    
    def visit_With(self, node):
        """Visit with statement"""
        # Mark context manager variables as used
        for item in node.items:
            if item.context_expr:
                self.visit(item.context_expr)
            if item.optional_vars:
                self.visit(item.optional_vars)
        
        # Visit the body
        for stmt in node.body:
            self.visit(stmt)
    
    def visit_AsyncWith(self, node):
        """Visit async with statement"""
        self.visit_With(node)
    
    # NOTE: visit_Attribute is defined above at line 181


class UnusedCodeDetector:
    """Detects unused code in Python files"""
    
    def __init__(self, target_path: str, verbose: bool = False):
        self.target_path = Path(target_path)
        self.verbose = verbose
        self.all_definitions = defaultdict(lambda: defaultdict(dict))
        self.all_usages = defaultdict(set)
        self.file_analyzers = {}
        self.errors = []
        
    def scan_python_files(self) -> List[Path]:
        """Scan target path for Python files"""
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
        
        if self.verbose:
            print(f"Found {len(python_files)} Python files")
        
        return python_files
    
    def analyze_file(self, filepath: Path) -> CodeAnalyzer:
        """Analyze single Python file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            tree = ast.parse(source_code, filename=str(filepath))
            analyzer = CodeAnalyzer(str(filepath))
            analyzer.visit(tree)
            
            # Extract unused local variables
            analyzer.unused_local_vars = []
            for scope_name, var_dict in analyzer.local_vars_by_scope.items():
                used_vars = analyzer.local_vars_used_by_scope.get(scope_name, set())
                for var_name, lineno in var_dict.items():
                    if var_name not in used_vars:
                        # Unused local variable
                        is_private = var_name.startswith('_')
                        full_name = f"{scope_name}.{var_name}"
                        analyzer.unused_local_vars.append((lineno, full_name, is_private))
            
            return analyzer
        except SyntaxError as e:
            self.errors.append(f"Syntax error in {filepath}: {e}")
            return None
        except Exception as e:
            self.errors.append(f"Analysis error in {filepath}: {e}")
            return None
    
    def collect_all_definitions_and_usages(self, python_files: List[Path]):
        """Collect definitions and usages from all files"""
        for i, filepath in enumerate(python_files, 1):
            if self.verbose:
                print(f"[{i}/{len(python_files)}] Analyzing: {filepath.name}")
                
            analyzer = self.analyze_file(filepath)
            if analyzer is None:
                continue
                
            self.file_analyzers[str(filepath)] = analyzer
            
            for def_type in ['functions', 'classes', 'variables', 'imports']:
                for name, lineno in analyzer.definitions[def_type].items():
                    # For imports, keep full name (e.g., concurrent.futures)
                    # For others, use simple name (e.g., MyClass from MyClass.method)
                    key_name = name if def_type == 'imports' else name.split('.')[-1]
                    if key_name not in self.all_definitions[def_type]:
                        self.all_definitions[def_type][key_name] = []
                    self.all_definitions[def_type][key_name].append((str(filepath), lineno, name))
            
            for usage_type in ['functions', 'classes', 'variables', 'imports']:
                self.all_usages[usage_type].update(analyzer.usages[usage_type])
            
            # Collect unused local variables
            if hasattr(analyzer, 'unused_local_vars'):
                for lineno, full_name, is_private in analyzer.unused_local_vars:
                    # Add to all_definitions for processing in find_unused_code
                    if full_name not in self.all_definitions['variables']:
                        self.all_definitions['variables'][full_name] = []
                    self.all_definitions['variables'][full_name].append((str(filepath), lineno, full_name))
    
    def find_unused_code(self) -> Dict[str, List[Tuple[str, int, str, bool]]]:
        """Find unused code"""
        unused = {
            'functions': [],
            'classes': [],
            'variables': [],
            'imports': [],
        }
        
        special_methods = {
            '__init__', '__str__', '__repr__', '__eq__', '__hash__',
            '__len__', '__getitem__', '__setitem__', '__delitem__',
            '__iter__', '__next__', '__enter__', '__exit__',
            '__call__', '__new__', '__del__', '__bool__',
            '__add__', '__sub__', '__mul__', '__div__', '__mod__',
            '__lt__', '__le__', '__gt__', '__ge__', '__ne__',
            'main',
        }
        
        export_patterns = {'__all__', '__version__', '__author__', '__email__'}
        
        for def_type in ['functions', 'classes', 'variables', 'imports']:
            for name, locations in self.all_definitions[def_type].items():
                if name in special_methods or name in export_patterns:
                    continue
                
                if name == '__name__':
                    continue
                
                is_used = False
                
                # Direct usage check - check simple name
                if name in self.all_usages[def_type]:
                    is_used = True
                
                # For functions/methods: also check if full name (ClassName.method_name) is used
                if def_type == 'functions' and not is_used:
                    # Check each location's full_name
                    for filepath, lineno, full_name in locations:
                        # Check if full_name is in usages
                        if full_name in self.all_usages[def_type]:
                            is_used = True
                            break
                        # Check if any part of the full_name matches
                        # E.g., for "GoogleDriveShell.cmd_cd", check if "cmd_cd" is used
                        simple_name = full_name.split('.')[-1]
                        if simple_name in self.all_usages[def_type]:
                            is_used = True
                            break
                
                # Special handling for module imports with dots (e.g., concurrent.futures)
                # If the module is "concurrent.futures", check if "concurrent" is used
                if def_type == 'imports' and '.' in name:
                    root_name = name.split('.')[0]
                    if root_name in self.all_usages['imports']:
                        is_used = True
                
                if not is_used:
                    for filepath, lineno, full_name in locations:
                        is_private = name.startswith('_')
                        unused[def_type].append((filepath, lineno, full_name, is_private))
        
        # Sort results by file then by name
        for def_type in unused:
            unused[def_type].sort(key=lambda x: (x[0], x[2]))
        
        return unused
    
    def run(self) -> Dict:
        """Run analysis and return results"""
        python_files = self.scan_python_files()
        
        if not python_files:
            return {
                "success": False,
                "message": "No Python files found",
                "total_files": 0,
                "total_unused": 0,
                "unused": {},
                "errors": []
            }
        
        self.collect_all_definitions_and_usages(python_files)
        unused = self.find_unused_code()
        
        total_unused = sum(len(items) for items in unused.values())
        
        # Convert to hierarchical format: {file: {line: "error message"}}
        hierarchical_unused = {}
        for def_type, items in unused.items():
            hierarchical_unused[def_type] = {}
            for filepath, lineno, name, is_private in items:
                if filepath not in hierarchical_unused[def_type]:
                    hierarchical_unused[def_type][filepath] = {}
                
                # Format message based on type
                type_names = {
                    'functions': '函数',
                    'classes': '类',
                    'variables': '变量',
                    'imports': '导入'
                }
                marker = " [私有]" if is_private else ""
                message = f"{name} {type_names[def_type]}未被使用{marker}"
                hierarchical_unused[def_type][filepath][lineno] = message
        
        return {
            "success": True,
            "message": f"Analyzed {len(python_files)} files, found {total_unused} unused items",
            "total_files": len(python_files),
            "total_unused": total_unused,
            "unused": hierarchical_unused,
            "errors": self.errors
        }

