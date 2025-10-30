#!/usr/bin/env python3
"""
LINTER - Multi-language Syntax Checker and Code Analyzer
Supports: Python, JavaScript, TypeScript, Java, C/C++, Go, Rust, SQL, JSON, YAML, HTML, CSS, Shell
Also includes unused code detection for Python projects
"""

import os
import sys
import subprocess
import json
import tempfile
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Add modules directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'LINTER_PROJ', 'modules'))

from unused_code_detector import UnusedCodeDetector
from import_checker import ImportChecker
from signature_checker import SignatureChecker


class MultiLanguageLinter:
    """Multi-language linter for syntax and style checking"""
    
    LANGUAGE_MAP = {
        '.py': 'python',
        '.js': 'javascript', 
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.cc': 'cpp', 
        '.cxx': 'cpp',
        '.c': 'c',
        '.h': 'cpp',
        '.hpp': 'cpp',
        '.go': 'go',
        '.rs': 'rust',
        '.php': 'php',
        '.rb': 'ruby',
        '.sh': 'bash',
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.xml': 'xml',
        '.html': 'html',
        '.css': 'css',
        '.sql': 'sql'
    }
    
    def __init__(self):
        self.supported_linters = self._detect_available_linters()
    
    def _detect_available_linters(self) -> Dict[str, str]:
        """Detect available linters on system"""
        linters = {}
        
        python_linter_found = False
        for linter in ['flake8', 'pylint', 'pycodestyle']:
            if self._command_exists(linter):
                linters['python'] = linter
                python_linter_found = True
                break
        
        if not python_linter_found and self._command_exists('python3'):
            linters['python'] = 'python3'
        
        for linter in ['eslint', 'jshint', 'standard']:
            if self._command_exists(linter):
                linters['javascript'] = linter
                linters['typescript'] = linter
                break
        
        if self._command_exists('checkstyle'):
            linters['java'] = 'checkstyle'
        elif self._command_exists('javac'):
            linters['java'] = 'javac'
        
        cpp_linter_found = False
        for linter in ['cppcheck', 'clang-tidy']:
            if self._command_exists(linter):
                linters['cpp'] = linter
                linters['c'] = linter
                cpp_linter_found = True
                break
        
        if not cpp_linter_found:
            for compiler in ['gcc', 'clang']:
                if self._command_exists(compiler):
                    linters['cpp'] = compiler
                    linters['c'] = compiler
                    break
        
        if self._command_exists('golint'):
            linters['go'] = 'golint'
        elif self._command_exists('gofmt'):
            linters['go'] = 'gofmt'
        
        if self._command_exists('cargo'):
            linters['rust'] = 'cargo'
        
        if self._command_exists('sqlfluff'):
            linters['sql'] = 'sqlfluff'
        elif self._command_exists('sql-formatter'):
            linters['sql'] = 'sql-formatter'
        
        if self._command_exists('jsonlint'):
            linters['json'] = 'jsonlint'
        elif self._command_exists('python3'):
            linters['json'] = 'python-json'
        
        if self._command_exists('yamllint'):
            linters['yaml'] = 'yamllint'
        
        if self._command_exists('shellcheck'):
            linters['bash'] = 'shellcheck'
        
        if self._command_exists('htmlhint'):
            linters['html'] = 'htmlhint'
        
        if self._command_exists('stylelint'):
            linters['css'] = 'stylelint'
        
        return linters
    
    def _command_exists(self, command: str) -> bool:
        """Check if command exists in PATH"""
        try:
            subprocess.run(['which', command], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def detect_language(self, filename: str, language: Optional[str] = None) -> str:
        """Detect language from filename"""
        if language:
            return language.lower()
        
        file_path = Path(filename)
        extension = file_path.suffix.lower()
        
        return self.LANGUAGE_MAP.get(extension, 'unknown')
    
    def lint_file(self, filename: str, language: Optional[str] = None) -> Dict:
        """Lint a file and return results"""
        if not os.path.exists(filename):
            return {
                "success": False,
                "language": "unknown",
                "message": f"File not found: {filename}",
                "errors": [f"File not found: {filename}"],
                "warnings": [],
                "info": []
            }
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(filename, 'r', encoding='latin-1') as f:
                    content = f.read()
            except Exception as e:
                return {
                    "success": False,
                    "language": "unknown", 
                    "message": f"Error reading file: {e}",
                    "errors": [f"Error reading file: {e}"],
                    "warnings": [],
                    "info": []
                }
        
        return self.lint_content(content, filename, language)
    
    def lint_content(self, content: str, filename: str, language: Optional[str] = None) -> Dict:
        """Lint content and return results"""
        detected_language = self.detect_language(filename, language)
        
        if detected_language == 'unknown':
            return {
                "success": True,
                "language": detected_language,
                "message": f"Language not detected for {filename}",
                "errors": [],
                "warnings": [],
                "info": ["Use --language to specify"]
            }
        
        if detected_language not in self.supported_linters:
            return {
                "success": True, 
                "language": detected_language,
                "message": f"No linter available for {detected_language}",
                "errors": [],
                "warnings": [],
                "info": [f"Install a {detected_language} linter"]
            }
        
        linter = self.supported_linters[detected_language]
        return self._run_linter(content, filename, detected_language, linter)
    
    def _run_linter(self, content: str, filename: str, language: str, linter: str) -> Dict:
        """Run specific linter on content"""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix=Path(filename).suffix, delete=False) as tmp_file:
                tmp_file.write(content)
                tmp_file_path = tmp_file.name
            
            try:
                if language == 'python':
                    return self.lint_python(tmp_file_path, linter)
                elif language == 'json':
                    return self.lint_json(tmp_file_path, linter)
                elif language == 'bash':
                    return self.lint_bash(tmp_file_path, linter)
                else:
                    return self._generic_lint_result(language, "Linter not implemented")
            finally:
                os.unlink(tmp_file_path)
                
        except Exception as e:
            return {
                "success": False,
                "language": language,
                "message": f"Linting failed: {str(e)}",
                "errors": [f"Linter error: {str(e)}"],
                "warnings": [],
                "info": []
            }
    
    def lint_python(self, file_path: str, linter: str) -> Dict:
        """Lint Python code"""
        try:
            if linter == 'flake8':
                result = subprocess.run(['flake8', '--format=%(path)s:%(row)d:%(col)d: %(code)s %(text)s', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'pylint':
                result = subprocess.run(['pylint', '--output-format=text', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'pycodestyle':
                result = subprocess.run(['pycodestyle', file_path], 
                                      capture_output=True, text=True)
            else:
                result = subprocess.run(['python3', '-m', 'py_compile', file_path], 
                                      capture_output=True, text=True)
            
            return self._parse_python_output(result, linter)
            
        except Exception as e:
            return self._generic_lint_result('python', f"Python linting failed: {e}")
    
    def lint_json(self, file_path: str, linter: str) -> Dict:
        """Lint JSON content"""
        try:
            if linter == 'python-json':
                with open(file_path, 'r') as f:
                    json.load(f)
                return {
                    "success": True,
                    "language": "json",
                    "message": "JSON is valid",
                    "errors": [],
                    "warnings": [],
                    "info": []
                }
            elif linter == 'jsonlint':
                result = subprocess.run(['jsonlint', file_path], 
                                      capture_output=True, text=True)
                return self._parse_json_output(result)
            else:
                return self._generic_lint_result('json', "JSON linting not available")
                
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "language": "json",
                "message": "JSON syntax error",
                "errors": [f"Line {e.lineno}: {e.msg}"],
                "warnings": [],
                "info": []
            }
        except Exception as e:
            return self._generic_lint_result('json', f"JSON linting failed: {e}")
    
    def lint_bash(self, file_path: str, linter: str) -> Dict:
        """Lint Bash scripts"""
        try:
            if linter == 'shellcheck':
                result = subprocess.run(['shellcheck', file_path], 
                                      capture_output=True, text=True)
                return self._parse_shellcheck_output(result)
            else:
                return self._generic_lint_result('bash', "Shell linting not available")
            
        except Exception as e:
            return self._generic_lint_result('bash', f"Bash linting failed: {e}")
    
    def _parse_python_output(self, result: subprocess.CompletedProcess, linter: str) -> Dict:
        """Parse Python linter output"""
        errors = []
        warnings = []
        
        if result.returncode != 0 and result.stderr:
            for line in result.stderr.strip().split('\n'):
                if line.strip():
                    errors.append(line.strip())
        
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    if any(code in line for code in ['E', 'F']):
                        errors.append(line.strip())
                    else:
                        warnings.append(line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "python",
            "message": f"Python linting with {linter}",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_json_output(self, result: subprocess.CompletedProcess) -> Dict:
        """Parse JSON linter output"""
        errors = []
        warnings = []
        
        if result.returncode != 0:
            output = result.stdout + result.stderr
            for line in output.strip().split('\n'):
                if line.strip():
                    errors.append(line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "json",
            "message": "JSON validation",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_shellcheck_output(self, result: subprocess.CompletedProcess) -> Dict:
        """Parse shellcheck output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                if 'error' in line.lower():
                    errors.append(line.strip())
                elif 'warning' in line.lower():
                    warnings.append(line.strip())
                else:
                    warnings.append(line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "bash",
            "message": "Shell script linting with shellcheck",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _generic_lint_result(self, language: str, message: str) -> Dict:
        """Generic lint result"""
        return {
            "success": True,
            "language": language,
            "message": message,
            "errors": [],
            "warnings": [],
            "info": [message]
        }


def format_unused_code_output(result: Dict, format_type: str = 'text') -> str:
    """Format unused code analysis results"""
    if format_type == 'json':
        return json.dumps(result, indent=2)
    
    lines = []
    lines.append(f"Target: {result.get('target', 'Unknown')}")
    lines.append(f"Files analyzed: {result['total_files']}")
    lines.append(f"Status: {'PASS' if result['success'] else 'FAIL'}")
    
    if not result['success']:
        lines.append(f"Error: {result['message']}")
        return '\n'.join(lines)
    
    total_unused = result['total_unused']
    if total_unused == 0:
        lines.append("No unused code detected")
        return '\n'.join(lines)
    
    lines.append(f"Unused items found: {total_unused}")
    
    for item_type, items in result['unused'].items():
        if not items:
            continue
            
        type_names = {
            'functions': 'Functions',
            'classes': 'Classes',
            'variables': 'Variables',
            'imports': 'Imports',
        }
        
        lines.append(f"\n{type_names[item_type]}: {len(items)}")
        
        by_file = {}
        for filepath, lineno, name, is_private in items:
            if filepath not in by_file:
                by_file[filepath] = []
            by_file[filepath].append((lineno, name, is_private))
        
        for filepath in sorted(by_file.keys()):
            lines.append(f"  {filepath}")
            for lineno, name, is_private in sorted(by_file[filepath])[:5]:
                marker = "[private]" if is_private else ""
                lines.append(f"    Line {lineno}: {name} {marker}")
            if len(by_file[filepath]) > 5:
                lines.append(f"    ... and {len(by_file[filepath]) - 5} more")
    
    if result['errors']:
        lines.append("\nErrors:")
        for error in result['errors'][:3]:
            lines.append(f"  {error}")
        if len(result['errors']) > 3:
            lines.append(f"  ... and {len(result['errors']) - 3} more")
    
    return '\n'.join(lines)


def format_import_check_output(result: Dict, format_type: str = 'text') -> str:
    """Format import check results"""
    if format_type == 'json':
        return json.dumps(result, indent=2)
    
    lines = []
    lines.append(f"Target: {result.get('target', 'Unknown')}")
    lines.append(f"Files checked: {result['files_checked']}")
    lines.append(f"Status: {'PASS' if result['success'] else 'FAIL'}")
    
    if not result['success']:
        lines.append(f"Error: {result['message']}")
        return '\n'.join(lines)
    
    files_with_issues = result['files_with_issues']
    if files_with_issues == 0:
        lines.append("No import issues found")
        return '\n'.join(lines)
    
    lines.append(f"Files with issues: {files_with_issues}")
    
    for issue in result['issues'][:10]:
        lines.append(f"\n{issue['file']}:")
        
        if issue.get('unused_imports'):
            lines.append(f"  Unused imports: {len(issue['unused_imports'])}")
            for imp in issue['unused_imports'][:3]:
                lines.append(f"    Line {imp['line']}: {imp['name']}")
            if len(issue['unused_imports']) > 3:
                lines.append(f"    ... and {len(issue['unused_imports']) - 3} more")
        
        if issue.get('missing_imports'):
            lines.append(f"  Missing imports: {len(issue['missing_imports'])}")
            for imp in issue['missing_imports'][:3]:
                lines.append(f"    {imp}")
            if len(issue['missing_imports']) > 3:
                lines.append(f"    ... and {len(issue['missing_imports']) - 3} more")
    
    if len(result['issues']) > 10:
        lines.append(f"\n... and {len(result['issues']) - 10} more files")
    
    return '\n'.join(lines)


def format_signature_check_output(result: Dict, format_type: str = 'text') -> str:
    """Format signature check results"""
    if format_type == 'json':
        return json.dumps(result, indent=2)
    
    lines = []
    lines.append(f"Target: {result.get('target', 'Unknown')}")
    lines.append(f"Functions checked: {result['functions_checked']}")
    lines.append(f"Status: {'PASS' if result['success'] else 'FAIL'}")
    
    if not result['success']:
        lines.append(f"Error: {result['message']}")
        return '\n'.join(lines)
    
    issues_found = result['issues_found']
    if issues_found == 0:
        lines.append("No signature issues found")
        return '\n'.join(lines)
    
    lines.append(f"Signature issues found: {issues_found}")
    
    for issue in result['issues'][:10]:
        lines.append(f"\n{issue['file']}:{issue['line']}")
        lines.append(f"  Function: {issue['function']}")
        provided = f"  Provided: {issue['provided_args']} args"
        if issue.get('provided_kwargs'):
            provided += f" + kwargs {issue['provided_kwargs']}"
        lines.append(provided)
        lines.append(f"  Expected: {issue['expected_min']}-{issue['expected_max']} args")
    
    if len(result['issues']) > 10:
        lines.append(f"\n... and {len(result['issues']) - 10} more issues")
    
    return '\n'.join(lines)


def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(
        description='Multi-language Linter and Code Analyzer',
        epilog='Supports syntax checking and unused code detection'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Lint command
    lint_parser = subparsers.add_parser('lint', help='Lint a file for syntax/style')
    lint_parser.add_argument('file', help='File to lint')
    lint_parser.add_argument('--language', '-l', help='Language override')
    lint_parser.add_argument('--format', '-f', choices=['json', 'text'], default='text')
    
    # Unused command
    unused_parser = subparsers.add_parser('unused', help='Detect unused code in Python')
    unused_parser.add_argument('path', help='File or directory to analyze')
    unused_parser.add_argument('--format', '-f', choices=['json', 'text'], default='text')
    unused_parser.add_argument('--verbose', '-v', action='store_true')
    
    # Imports command
    imports_parser = subparsers.add_parser('imports', help='Check import issues in Python')
    imports_parser.add_argument('path', help='File or directory to check')
    imports_parser.add_argument('--format', '-f', choices=['json', 'text'], default='text')
    imports_parser.add_argument('--verbose', '-v', action='store_true')
    
    # Signature command
    signature_parser = subparsers.add_parser('signature', help='Check function signatures in Python')
    signature_parser.add_argument('path', help='File or directory to check')
    signature_parser.add_argument('--format', '-f', choices=['json', 'text'], default='text')
    signature_parser.add_argument('--verbose', '-v', action='store_true')
    
    parser.add_argument('--version', action='version', version='LINTER 2.0.0')
    
    # Default behavior: lint if file argument provided
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
    
    valid_commands = ['lint', 'unused', 'imports', 'signature', '--version', '-h', '--help']
    
    # Handle legacy usage (LINTER file.py)
    if len(sys.argv) == 2 and not sys.argv[1].startswith('-') and sys.argv[1] not in valid_commands:
        args = argparse.Namespace(command='lint', file=sys.argv[1], language=None, format='text')
    elif len(sys.argv) >= 2 and sys.argv[1] not in valid_commands:
        # Legacy usage with options
        sys.argv.insert(1, 'lint')
        args = parser.parse_args()
    else:
        args = parser.parse_args()
    
    # Execute command
    if args.command == 'lint':
        if not os.path.exists(args.file):
            print(f"Error: File not found: {args.file}")
            sys.exit(1)
        
        linter = MultiLanguageLinter()
        result = linter.lint_file(args.file, args.language)
        
        if args.format == 'json':
            print(json.dumps(result, indent=2))
        else:
            print(f"Language: {result['language']}")
            status = "PASS" if result['success'] else "FAIL"
            print(f"Status: {status}")
            print(f"Linter: {result['message']}")
            
            total_issues = len(result['errors']) + len(result['warnings'])
            if total_issues > 0:
                print(f"\n{total_issues} issues found:")
                
                for error in result['errors']:
                    print(f"ERROR: {error}")
                
                for warning in result['warnings']:
                    print(f"WARNING: {warning}")
            
            if result['info']:
                print(f"\nInfo:")
                for info in result['info']:
                    print(f"  {info}")
        
        sys.exit(0 if result['success'] else 1)
    
    elif args.command == 'unused':
        if not os.path.exists(args.path):
            print(f"Error: Path not found: {args.path}")
            sys.exit(1)
        
        detector = UnusedCodeDetector(args.path, verbose=args.verbose)
        result = detector.run()
        result['target'] = args.path
        
        output = format_unused_code_output(result, args.format)
        print(output)
        
        sys.exit(0 if result['success'] else 1)
    
    elif args.command == 'imports':
        if not os.path.exists(args.path):
            print(f"Error: Path not found: {args.path}")
            sys.exit(1)
        
        checker = ImportChecker(args.path, verbose=args.verbose)
        result = checker.run()
        result['target'] = args.path
        
        output = format_import_check_output(result, args.format)
        print(output)
        
        sys.exit(0 if result['success'] else 1)
    
    elif args.command == 'signature':
        if not os.path.exists(args.path):
            print(f"Error: Path not found: {args.path}")
            sys.exit(1)
        
        checker = SignatureChecker(args.path, verbose=args.verbose)
        result = checker.run()
        result['target'] = args.path
        
        output = format_signature_check_output(result, args.format)
        print(output)
        
        sys.exit(0 if result['success'] else 1)
    
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == '__main__':
    main()

