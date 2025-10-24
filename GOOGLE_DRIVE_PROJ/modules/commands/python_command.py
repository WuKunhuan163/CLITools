"""
Python command handler for GDS.
"""

from typing import List
from .base_command import BaseCommand


class PythonCommand(BaseCommand):
    """Handler for python commands."""
    
    @property
    def command_name(self) -> str:
        return "python"
    
    def execute(self, cmd: str, args: List[str], **kwargs) -> int:
        """Execute python command."""
        # print(f"DEBUG in PythonCommand: MATCHED PYTHON BRANCH! Processing python with args: {args}")
        
        if not args:
            self.print_error("python command needs a file name or code")
            return 1
            
        if args[0] == '-c':
            # 执行Python代码
            if len(args) < 2:
                self.print_error("python -c needs code")
                return 1
            # 过滤掉命令行选项参数，只保留Python代码
            code_args = []
            for arg in args[1:]:
                if not arg.startswith('--'):
                    code_args.append(arg)
            
            # 统一处理已经在execute_shell_command中完成
            code = ' '.join(code_args)
            
            # print(f"DEBUG in PythonCommand: Executing Python code: '{code}'")
            
            # 不要移除Python代码的引号，因为shlex.split已经正确处理了shell引号
            # Python代码中的引号是语法的一部分，不应该被移除
            result = self.shell.cmd_python_code(code)
        else:
            # 执行Python文件
            filename = args[0]
            # 传递额外的命令行参数
            python_args = args[1:] if len(args) > 1 else []
            # print(f"DEBUG in PythonCommand: Executing Python file: '{filename}' with args: {python_args}")
            result = self.shell.cmd_python(filename=filename, python_args=python_args)
        # print(f"DEBUG in PythonCommand: Python execution result: {result}")
        
        if result.get("success", False):
            # 显示输出
            stdout = result.get("stdout", "")
            stderr = result.get("stderr", "")
            
            if stdout:
                print(stdout, end="", flush=True)
            if stderr:
                import sys
                print(stderr, end="", file=sys.stderr, flush=True)
            
            # 返回Python脚本的实际退出码（可能是非零）
            return_code = result.get("return_code", result.get("returncode", 0))
            return return_code
        else:
            # 显示错误信息
            error_msg = result.get("error", "Python command execution failed")
            self.print_error(error_msg)
            # 也显示stderr（如果有）
            stderr = result.get("stderr", "")
            if stderr:
                import sys
                print(stderr, end="", file=sys.stderr)
            return 1
