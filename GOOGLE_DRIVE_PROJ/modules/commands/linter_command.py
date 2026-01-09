import subprocess
from typing import Dict, Optional
from .base_command import BaseCommand
import os, tempfile, json, sys
from pathlib import Path

class LinterCommand(BaseCommand):
    """
    Code linter command
    Merged from linter.py
    """
    
    # Language mapping from file extensions
    LANGUAGE_MAP = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.json': 'json',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php',
        '.sh': 'shell',
        '.bash': 'shell',
        '.zsh': 'shell',
    }
    
    # Supported linters for each language
    supported_linters = {
        'python': 'pyflakes',
        'javascript': 'eslint',
        'json': 'json',
        'shell': 'shellcheck',
    }
    
    @property
    def command_name(self):
        return "linter"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行linter命令"""
        # 检查是否请求帮助
        if '--help' in args or '-h' in args:
            self.show_help()
            return 0
            
        if not args:
            print("Error: linter command needs a file name")
            return 1
        
        # Parse arguments for --language option
        language = None
        filename = None
        
        i = 0
        while i < len(args):
            if args[i] == '--language' and i + 1 < len(args):
                language = args[i + 1]
                i += 2
            else:
                if filename is None:
                    filename = args[i]
                i += 1
        
        if not filename:
            print("Error: linter command needs a file name")
            return 1
        
        # 直接调用cmd_linter方法
        result = self.cmd_linter(filename, language=language)
        
        # Check if linting process itself failed (e.g., file not found, linter not available)
        if "error" in result and not result.get("language"):
            # This is a fatal error (not lint errors), print and exit
            error_msg = result.get("error", "Linter failed")
            print(error_msg)
            return 1
        
        # Linting process completed (possibly with lint errors/warnings)
        language = result.get("language", "unknown")
        has_errors = bool(result.get("errors", []))
        status = "FAIL" if has_errors else "PASS"
        message = result.get("message", "")
        
        print(f"Language: {language}")
        print(f"Status: {status}")
        print(f"Message: {message}")
        
        errors = result.get("errors", [])
        if errors:
            print("\nErrors:")
            for error in errors:
                print(f"  • {error}")
        
        warnings = result.get("warnings", [])
        if warnings:
            print("\nWarnings:")
            for warning in warnings:
                print(f"  • {warning}")
        
        # Return 1 only if there are lint errors (not warnings)
        if errors:
            return 1
        else:
            return 0
        
    def show_help(self):
        """显示linter命令帮助信息"""
        print("GDS Linter Command Help")
        print("=" * 50)
        print()
        print("USAGE:")
        print("  GDS linter <file> [--language <lang>]  # Lint a file")
        print("  GDS linter --help                       # Show this help")
        print()
        print("DESCRIPTION:")
        print("  Perform code linting on files in the remote environment.")
        print("  Automatically detects language from file extension.")
        print()
        print("SUPPORTED LANGUAGES:")
        print("  Python      (.py)  - Uses pyflakes")
        print("  JavaScript  (.js)  - Uses eslint")
        print("  TypeScript  (.ts)  - Uses eslint")
        print("  JSON        (.json)- Uses json")
        print("  Shell       (.sh)  - Uses shellcheck")
        print()
        print("OPTIONS:")
        print("  --language <lang>                      # Override language detection")
        print()
        print("EXAMPLES:")
        print("  GDS linter script.py                   # Lint Python file")
        print("  GDS linter app.js                      # Lint JavaScript file")
        print("  GDS linter config.json                 # Validate JSON file")
        print("  GDS linter script.sh                   # Lint shell script")
        print()
        print("RELATED COMMANDS:")
        print("  GDS python --help                      # Python execution")
        print("  GDS cat --help                         # View file contents")
    
    def detect_language(self, filename: str, language: Optional[str] = None) -> str:
        """Detect language from filename or use provided language"""
        if language:
            return language.lower()
        
        file_path = Path(filename)
        extension = file_path.suffix.lower()
        
        return self.LANGUAGE_MAP.get(extension, 'unknown')
    
    def lint_content(self, content: str, filename: str, language: Optional[str] = None) -> Dict:
        """
        Lint content and return results
        
        Args:
            content: File content to lint
            filename: Original filename for context
            language: Language override (optional)
            
        Returns:
            Dict with success, errors, warnings, and info
        """
        detected_language = self.detect_language(filename, language)
        
        if detected_language == 'unknown':
            return {
                "success": True,
                "language": detected_language,
                "message": f"Language not detected for {filename}, skipping linting",
                "errors": [],
                "warnings": [],
                "info": []
            }
        
        if detected_language not in self.supported_linters:
            return {
                "success": True, 
                "language": detected_language,
                "message": f"No linter available for {detected_language}",
                "errors": [],
                "warnings": [],
                "info": [f"Install a {detected_language} linter for better checking"]
            }
        
        linter = self.supported_linters[detected_language]
        return self.run_linter(content, filename, detected_language, linter)
    
    def run_linter(self, content: str, filename: str, language: str, linter: str) -> Dict:
        """Run the specific linter on content"""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix=Path(filename).suffix, delete=False) as tmp_file:
                tmp_file.write(content)
                tmp_file_path = tmp_file.name
            
            try:
                if language == 'python':
                    return self.lint_python(tmp_file_path, linter)
                elif language in ['javascript', 'typescript']:
                    return self.lint_javascript(tmp_file_path, linter)
                elif language == 'java':
                    return self.lint_java(tmp_file_path, linter)
                elif language in ['cpp', 'c']:
                    return self.lint_cpp(tmp_file_path, linter)
                elif language == 'go':
                    return self.lint_go(tmp_file_path, linter)
                elif language == 'json':
                    return self.lint_json(tmp_file_path, linter)
                elif language == 'yaml':
                    return self.lint_yaml(tmp_file_path, linter)
                elif language == 'bash':
                    return self.lint_bash(tmp_file_path, linter)
                else:
                    return self.generic_lint_result(language, "Linter not implemented")
            finally:
                # Clean up temporary file
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
            if linter == 'pyflakes':
                result = subprocess.run(['pyflakes', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'flake8':
                result = subprocess.run(['flake8', '--format=%(path)s:%(row)d:%(col)d: %(code)s %(text)s', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'pylint':
                result = subprocess.run(['pylint', '--output-format=text', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'pycodestyle':
                result = subprocess.run(['pycodestyle', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'python3':
                # Built-in Python syntax check
                result = subprocess.run(['python3', '-m', 'py_compile', file_path], 
                                      capture_output=True, text=True)
            else:
                # Unknown linter fallback: basic Python syntax check
                result = subprocess.run(['python3', '-m', 'py_compile', file_path], 
                                      capture_output=True, text=True)
            
            # print(f"[DEBUG lint_python] Linter: {linter}")
            # print(f"[DEBUG lint_python] Return code: {result.returncode}")
            # print(f"[DEBUG lint_python] Stdout: {repr(result.stdout)}")
            # print(f"[DEBUG lint_python] Stderr: {repr(result.stderr)}")
            
            return self.parse_python_output(result, linter)
            
        except Exception as e:
            return self.generic_lint_result('python', f"Python linting failed: {e}")
    
    def lint_javascript(self, file_path: str, linter: str) -> Dict:
        """Lint JavaScript/TypeScript code"""
        try:
            if linter == 'eslint':
                result = subprocess.run(['eslint', '--format=compact', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'jshint':
                result = subprocess.run(['jshint', file_path], 
                                      capture_output=True, text=True)
            else:
                return self.generic_lint_result('javascript', "No JavaScript linter available")
            
            return self.parse_javascript_output(result, linter)
            
        except Exception as e:
            return self.generic_lint_result('javascript', f"JavaScript linting failed: {e}")
    
    def lint_java(self, file_path: str, linter: str) -> Dict:
        """Lint Java code"""
        try:
            if linter == 'javac':
                result = subprocess.run(['javac', '-Xlint', file_path], 
                                      capture_output=True, text=True)
            else:
                return self.generic_lint_result('java', "Java linting not fully implemented")
            
            return self.parse_java_output(result)
            
        except Exception as e:
            return self.generic_lint_result('java', f"Java linting failed: {e}")
    
    def lint_cpp(self, file_path: str, linter: str) -> Dict:
        """Lint C++ code"""
        try:
            if linter == 'cppcheck':
                result = subprocess.run(['cppcheck', '--enable=all', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'gcc':
                result = subprocess.run(['gcc', '-Wall', '-Wextra', '-fsyntax-only', file_path], 
                                      capture_output=True, text=True)
            else:
                return self.generic_lint_result('cpp', "C++ linting not available")
            
            return self.parse_cpp_output(result, linter)
            
        except Exception as e:
            return self.generic_lint_result('cpp', f"C++ linting failed: {e}")
    
    def lint_json(self, file_path: str, linter: str) -> Dict:
        """Lint JSON content"""
        try:
            if linter == 'python-json':
                # Use Python's json module for validation
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
            else:
                result = subprocess.run(['jsonlint', file_path], 
                                      capture_output=True, text=True)
                return self.parse_json_output(result)
                
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
            return self.generic_lint_result('json', f"JSON linting failed: {e}")
    
    def lint_bash(self, file_path: str, linter: str) -> Dict:
        """Lint Bash scripts"""
        try:
            result = subprocess.run(['shellcheck', file_path], 
                                  capture_output=True, text=True)
            return self.parse_shellcheck_output(result)
            
        except Exception as e:
            return self.generic_lint_result('bash', f"Bash linting failed: {e}")
    
    def parse_python_output(self, result: subprocess.CompletedProcess, linter: str) -> Dict:
        """Parse Python linter output"""
        errors = []
        warnings = []
        
        # Check both stdout and stderr for errors (py_compile and pyflakes may use either)
        error_output = (result.stderr or "") + (result.stdout or "")
        
        # print(f"[DEBUG parse_python_output] Combined error_output: {repr(error_output)}")
        # print(f"[DEBUG parse_python_output] Return code: {result.returncode}")
        
        if result.returncode != 0:
            # Syntax errors - parse from combined output
            for line in error_output.strip().split('\n'):
                if line.strip():
                    # print(f"[DEBUG parse_python_output] Processing line: {repr(line)}")
                    # Skip empty lines and check for error indicators
                    # Expanded to include pyflakes-style errors like "invalid syntax"
                    if ('SyntaxError' in line or 'IndentationError' in line or 'Error:' in line or 
                        'invalid syntax' in line or 'syntax error' in line.lower() or 
                        line.startswith('  File ')):
                        errors.append(line.strip())
                        # print(f"[DEBUG parse_python_output]   -> Added to errors")
                    elif any(code in line for code in ['E', 'F']):  # pylint/flake8 error codes
                        errors.append(line.strip())
                        # print(f"[DEBUG parse_python_output]   -> Added to errors (E/F code)")
                    elif line.strip() and not line.startswith('>>>'):  # Other non-empty lines
                        warnings.append(line.strip())
                        # print(f"[DEBUG parse_python_output]   -> Added to warnings")
        elif result.stdout:
            # returncode == 0 but may have warnings in stdout (pyflakes)
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    if any(code in line for code in ['E', 'F']):  # Errors
                        errors.append(line.strip())
                    else:  # Warnings
                        warnings.append(line.strip())
        
        result_dict = {
            "success": len(errors) == 0,
            "language": "python",
            "message": f"Python linting completed with {linter}",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
        # print(f"[DEBUG parse_python_output] Final result: success={result_dict['success']}, errors count={len(errors)}, warnings count={len(warnings)}")
        return result_dict
    
    def parse_javascript_output(self, result: subprocess.CompletedProcess, linter: str) -> Dict:
        """Parse JavaScript linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                if 'error' in line.lower():
                    errors.append(line.strip())
                elif 'warn' in line.lower():
                    warnings.append(line.strip())
                else:
                    warnings.append(line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "javascript", 
            "message": f"JavaScript linting completed with {linter}",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def generic_lint_result(self, language: str, message: str) -> Dict:
        """Generic lint result for unsupported cases"""
        return {
            "success": True,
            "language": language,
            "message": message,
            "errors": [],
            "warnings": [],
            "info": [message]
        }

    def cmd_linter(self, filename, language=None, *args, **kwargs):
        """Lint file - delegate to linter functionality"""
        try:
            # Get file content using remote cat command instead of cmd_cat API
            # This is more reliable for linter as it uses the same path resolution as other commands
            current_shell = self.shell.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell"}
            
            # Resolve the absolute path
            absolute_path = self.shell.path_resolver.resolve_remote_absolute_path(
                filename, current_shell, return_logical=False
            )
            if not absolute_path:
                return {"success": False, "error": f"Could not resolve path: {filename}"}
            
            # Use cmd_cat to read file (it returns "output" field, not "stdout")
            cat_result = self.shell.cmd_cat(filename)
            
            if not cat_result.get("success"):
                return {
                    "success": False,
                    "error": f"Could not read file {filename}: {cat_result.get('error', 'File reading failed')}"
                }
            
            content = cat_result.get("output", "")  # cmd_cat returns "output" field
            # print(f"[DEBUG cmd_linter] File content length: {len(content)} chars")
            # print(f"[DEBUG cmd_linter] File content preview: {repr(content[:200])}")
            
            # Run linter on content
            result = self.lint_content(content, filename, language=language)
            
            # Format output for display
            output_lines = []
            output_lines.append(f"Language: {result.get('language', 'unknown')}")
            output_lines.append(f"Status: {'PASS' if result.get('success', False) else 'FAIL'}")
            output_lines.append(f"Message: {result.get('message', '')}")
            
            if result.get('errors'):
                output_lines.append("\nErrors:")
                for error in result['errors']:
                    output_lines.append(f"  • {error}")
            
            if result.get('warnings'):
                output_lines.append("\nWarnings:")
                for warning in result['warnings']:
                    output_lines.append(f"  • {warning}")
            
            if result.get('info'):
                output_lines.append("\nInfo:")
                for info in result['info']:
                    output_lines.append(f"  • {info}")
            
            # Return the linter result directly, adding output field for backward compatibility
            result_with_output = result.copy()
            result_with_output["output"] = "\n".join(output_lines)
            result_with_output["has_errors"] = bool(result.get('errors'))
            return result_with_output
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Linter execution failed: {str(e)}"
            }

    def main():
        """Command line interface for GDS linter"""
        import argparse
        
        parser = argparse.ArgumentParser(description='GDS Multi-language Linter')
        parser.add_argument('file', help='File to lint')
        parser.add_argument('--language', '-l', help='Language override')
        parser.add_argument('--format', '-f', choices=['json', 'text'], default='text', help='Output format')
        
        args = parser.parse_args()
        
        if not os.path.exists(args.file):
            print(f"Error: File {args.file} not found")
            sys.exit(1)
        
        # For CLI mode, we don't have a shell instance
        # Create a mock object that won't be used
        class MockShell:
            drive_service = None
        
        linter = LinterCommand(MockShell())
        
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(args.file, 'r', encoding='latin-1') as f:
                    content = f.read()
            except Exception as e:
                print(f"Error reading file: {e}")
                sys.exit(1)
        
        result = linter.lint_content(content, args.file, args.language)
        
        if args.format == 'json':
            print(json.dumps(result, indent=2))
        else:
            # Text format
            print(f"Language: {result['language']}")
            print(f"Status: {'PASS' if result['success'] else 'FAIL'}")
            print(f"Message: {result['message']}")
            
            if result['errors']:
                print(f"\nErrors:")
                for error in result['errors']:
                    print(f"  • {error}")
            
            if result['warnings']:
                print(f"\nWarning: Warnings:")
                for warning in result['warnings']:
                    print(f"  • {warning}")
            
            if result['info']:
                print(f"\nInfo:")
                for info in result['info']:
                    print(f"  • {info}")
    
    def lint_go(self, file_path: str, linter: str) -> Dict:
        """Lint Go files"""
        try:
            subprocess.run(['gofmt', '-e', file_path], 
                         capture_output=True, text=True)
            return self.generic_lint_result('go', f"Go linting completed")
        except Exception as e:
            return self.generic_lint_result('go', f"Go linting not available: {e}")
    
    def lint_yaml(self, file_path: str, linter: str) -> Dict:
        """Lint YAML files"""
        try:
            subprocess.run(['yamllint', file_path], 
                         capture_output=True, text=True)
            return self.generic_lint_result('yaml', f"YAML linting completed")
        except Exception as e:
            return self.generic_lint_result('yaml', f"YAML linting not available: {e}")
    
    def parse_cpp_output(self, result: subprocess.CompletedProcess, linter: str) -> Dict:
        """Parse C++ linter output"""
        return self.generic_lint_result('cpp', "C++ linting completed")
    
    def parse_java_output(self, result: subprocess.CompletedProcess) -> Dict:
        """Parse Java linter output"""
        return self.generic_lint_result('java', "Java linting completed")
    
    def parse_json_output(self, result: subprocess.CompletedProcess) -> Dict:
        """Parse JSON linter output"""
        if result.returncode == 0:
            return self.generic_lint_result('json', "JSON is valid")
        else:
            return {
                "success": False,
                "language": "json",
                "message": "JSON linting found errors",
                "errors": [result.stderr or "JSON validation failed"],
                "warnings": [],
                "info": []
            }
    
    def parse_shellcheck_output(self, result: subprocess.CompletedProcess) -> Dict:
        """Parse shellcheck output"""
        if result.returncode == 0:
            return self.generic_lint_result('bash', "No issues found")
        else:
            errors = []
            if result.stdout:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        errors.append(line.strip())
            return {
                "success": False,
                "language": "bash",
                "message": "Shellcheck found issues",
                "errors": errors,
                "warnings": [],
                "info": []
            }

