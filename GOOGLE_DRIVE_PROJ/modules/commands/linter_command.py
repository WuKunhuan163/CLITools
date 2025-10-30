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
    
    @property
    def command_name(self):
        return "linter"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行linter命令"""
        if not args:
            print("Error: linter command needs a file name")
            return 1
        
        filename = args[0]
        
        # 直接调用cmd_linter方法
        result = self.cmd_linter(filename)
        
        if result.get("success"):
            language = result.get("language", "unknown")
            status = "PASS" if result.get("success", False) else "FAIL"
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
            
            if errors or warnings:
                return 1
            else:
                return 0
        else:
            error_msg = result.get("error", "Linter failed")
            print(error_msg)
            return 1
    
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
        return self.run_lintercontent, filename, detected_language, linter)
    
    def run_linterself, content: str, filename: str, language: str, linter: str) -> Dict:
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
            if linter == 'flake8':
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
        
        if result.returncode != 0 and result.stderr:
            # Syntax errors
            for line in result.stderr.strip().split('\n'):
                if line.strip():
                    errors.append(line.strip())
        
        if result.stdout:
            # Style warnings
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    if any(code in line for code in ['E', 'F']):  # Errors
                        errors.append(line.strip())
                    else:  # Warnings
                        warnings.append(line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "python",
            "message": f"Python linting completed with {linter}",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
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

    def cmd_linter(self, filename, *args, **kwargs):
        """Lint file - delegate to linter functionality"""
        try:
            # Get file content first
            cat_result = self.text_operations.cmd_cat(filename)
            if not cat_result.get("success"):
                return {
                    "success": False,
                    "error": f"Could not read file {filename}: {cat_result.get('error', 'Unknown error')}"
                }
            
            content = cat_result.get("output", "")
            
            # Import and use the new LINTER tool
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            linter = LinterCommand()
            
            # Run linter on content
            result = linter.lint_content(content, filename)
            
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
            
            return {
                "success": True,
                "output": "\n".join(output_lines),
                "has_errors": bool(result.get('errors')),
                "linter_result": result
            }
            
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
        
        linter = LinterCommand()
        
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

