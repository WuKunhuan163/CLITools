"""
Google Drive Shell - Python Command Module

This module provides Python code execution functionality within the Google Drive Shell environment.
It enables running Python scripts and commands on the remote system with proper version management
and integration with the pyenv system.

Key Features:
- Remote Python script execution
- Python version detection and reporting
- Integration with pyenv for version management
- Support for both file execution and inline code
- Proper shell state management for Python environments
- Error handling and output capture

Commands:
- python <script.py>: Execute Python script file
- python -c "code": Execute inline Python code
- python --version: Show current Python version

Execution Flow:
1. Validate Python command and arguments
2. Resolve file paths if executing scripts
3. Prepare remote execution environment
4. Execute Python code/script on remote system
5. Capture and return output/errors

Classes:
    PythonCommand: Main Python command handler

Dependencies:
    - Pyenv system for version management
    - Remote shell management for execution context
    - Path resolution for script file handling
    - Command execution infrastructure
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
        # 检查是否请求帮助
        if '--help' in args or '-h' in args:
            self.show_help()
            return 0
            
        if not args:
            self.print_error("python command needs a file name or code")
            return 1
        
        if args[0] == '--version':
            # 显示配置的Python版本 - 实际在远端执行Python
            result = self.shell.cmd_python_code('import sys; print(f"Python {sys.version.split()[0]}")')
            if result.get("success", False):
                stdout = result.get("stdout", "").strip()
                if stdout:
                    print(stdout)
                return 0
            else:
                import traceback
                call_stack = ''.join(traceback.format_stack()[-3:])
                error_msg = result.get('error', f'Python command execution failed without specific error message. Call stack: {call_stack}')
                print(f"Error getting Python version: {error_msg}")
                return 1
        
        if args[0] == '-c':
            # 执行Python代码
            if len(args) < 2:
                self.print_error("python -c needs code")
                return 1
            code_args = [arg for arg in args[1:] if not arg.startswith('--')]
            code = ' '.join(code_args)
            result = self.shell.cmd_python_code(code)
        else:
            # 执行Python文件
            filename = args[0]
            python_args = args[1:] if len(args) > 1 else []
            result = self.cmd_python(filename=filename, python_args=python_args)
        
        if result.get("success", False):
            stdout = result.get("stdout", "")
            stderr = result.get("stderr", "")
            
            if stdout:
                print(stdout, end="", flush=True)
            if stderr:
                import sys
                print(stderr, end="", file=sys.stderr, flush=True)
            
            # 明确处理return_code，优先使用return_code字段
            return_code = (result.get("return_code") if "return_code" in result 
                         else result.get("returncode", 0))
            return return_code
        else:
            error_msg = result.get("error", "Python command execution failed")
            self.print_error(error_msg)
            stderr = result.get("stderr", "")
            if stderr:
                import sys
                print(stderr, end="", file=sys.stderr)
            return 1

    def show_help(self):
        """显示python命令帮助信息"""
        print("GDS Python Command Help")
        print("=" * 50)
        print()
        print("USAGE:")
        print("  GDS python <file.py> [args...]     # Execute Python file")
        print("  GDS python -c '<code>' [args...]   # Execute Python code")
        print("  GDS python --help                  # Show this help")
        print()
        print("DESCRIPTION:")
        print("  Execute Python scripts or code in the remote environment.")
        print("  Uses the currently active Python version (set by pyenv).")
        print()
        print("EXAMPLES:")
        print("  GDS python script.py               # Run script.py")
        print("  GDS python script.py arg1 arg2     # Run with arguments")
        print("  GDS python -c 'print(\"Hello\")'     # Execute inline code")
        print("  GDS python -c 'import sys; print(sys.version)'")
        print()
        print("RELATED COMMANDS:")
        print("  GDS pyenv --help                   # Python version management")
        print("  GDS pip --help                     # Package management")
        print("  GDS venv --help                    # Virtual environment management")

    def get_python_executable(self):
        """获取当前应该使用的Python可执行文件路径 - 已废弃，Python版本选择在远程进行"""
        return "python3"

    def cmd_python(self, code=None, filename=None, python_args=None, save_output=False):
        """python命令 - 执行Python代码"""
        try:
            if filename:
                # 执行Drive中的Python文件
                return self.execute_python_file(filename, save_output, python_args)
            elif code:
                # 执行直接提供的Python代码
                return self.execute_python_code(code, save_output)
            else:
                return {"success": False, "error": "请提供Python代码或文件名"}
                
        except Exception as e:
            return {"success": False, "error": f"执行Python命令时出错: {e}"}

    def execute_python_code(self, code, save_output=False, filename=None):
        """统一的远程Python执行方法，在一个命令中检查虚拟环境并执行代码"""
        try:
            import base64
            import time
            import random
            
            # 使用base64编码避免所有bash转义问题
            code_bytes = code.encode('utf-8')
            code_base64 = base64.b64encode(code_bytes).decode('ascii')
            
            # 生成唯一的临时文件名
            timestamp = int(time.time())
            random_id = f"{random.randint(1000, 9999):04x}"
            temp_filename = f"python_code_{timestamp}_{random_id}.b64"
            
            # 获取环境文件路径
            # Direct storage in REMOTE_ENV, no .tmp subdirectory needed
            env_file = f"{self.main_instance.REMOTE_ENV}/venv/venv_pythonpath.sh"
            temp_file_path = f"{self.main_instance.REMOTE_ROOT}/tmp/{temp_filename}"
            
            # 获取当前shell ID（在模板外部）
            current_shell = self.main_instance.get_current_shell()
            shell_id = current_shell.get("id", "default") if current_shell else "default"
            
            # 构建统一的远程命令：
            # 1. 确保tmp目录存在
            # 2. 将base64字符串写入临时文件
            # 3. source环境文件
            # 4. 从临时文件读取base64并解码执行
            # 5. 清理临时文件
            # 构建命令，在远程环境中智能选择Python可执行文件
            # 所有的Python版本选择逻辑都在远程执行，避免多次窗口调用
            command = f'''
            mkdir -p {self.main_instance.REMOTE_ROOT}/tmp && \\
            echo "{code_base64}" > "{temp_file_path}" && \\
            source {env_file} 2>/dev/null || true
            
            # 在远程环境中智能选择Python可执行文件
            # 1. 检查是否有pyenv设置的Python版本
            PYTHON_EXEC="python3"  # 默认
            PYTHON_BASE_PATH="{self.main_instance.REMOTE_ENV}/python"
            STATE_FILE="$PYTHON_BASE_PATH/python_states.json"
            
            # 获取当前shell ID
            SHELL_ID="{shell_id}"
            
            # 如果状态文件存在，尝试读取Python版本设置
            if [ -f "$STATE_FILE" ]; then
                # 优先检查local版本
                LOCAL_VERSION=$(python3 -c "
import json, sys
try:
    with open('$STATE_FILE', 'r') as f:
        states = json.load(f)
    print(states.get('shell_${{SHELL_ID}}', ''))
except:
    pass
" 2>/dev/null || echo "")
                
                # 如果没有local版本，检查global版本
                if [ -z "$LOCAL_VERSION" ]; then
                    GLOBAL_VERSION=$(python3 -c "
import json, sys
try:
    with open('$STATE_FILE', 'r') as f:
        states = json.load(f)
    print(states.get('global', ''))
except:
    pass
" 2>/dev/null || echo "")
                    CURRENT_VERSION="$GLOBAL_VERSION"
                else
                    CURRENT_VERSION="$LOCAL_VERSION"
                fi
                
                # 如果找到了版本设置，检查对应的Python是否存在
                if [ -n "$CURRENT_VERSION" ] && [ "$CURRENT_VERSION" != "system" ]; then
                    PYENV_PYTHON="$PYTHON_BASE_PATH/$CURRENT_VERSION/bin/python3"
                    if [ -f "$PYENV_PYTHON" ]; then
                        # 尝试修复权限问题
                        chmod +x "$PYENV_PYTHON" 2>/dev/null || true
                        if [ -x "$PYENV_PYTHON" ]; then
                            PYTHON_EXEC="$PYENV_PYTHON"
                        fi
                    fi
                fi
            fi
            
            # 执行Python代码 (修复版本：避免exec嵌套)
            # 直接从base64文件解码并作为脚本执行，而不是通过exec
            base64 -d "{temp_file_path}" | $PYTHON_EXEC
            PYTHON_EXIT_CODE=$?
            
            # 清理临时文件
            rm -f "{temp_file_path}"
            
            # 返回Python脚本的退出码
            exit $PYTHON_EXIT_CODE
            '''.strip()
            
            # 执行远程命令
            result = self.main_instance.execute_command_interface("bash", ["-c", command])
            
            if result.get("success"):
                data = result.get("data", {})
                # 明确处理数据字段，优先使用data中的值
                return {
                    "success": True,
                    "stdout": data.get("stdout") if "stdout" in data else result.get("stdout", ""),
                    "stderr": data.get("stderr") if "stderr" in data else result.get("stderr", ""),
                    "return_code": data.get("exit_code") if "exit_code" in data else result.get("exit_code", 0),
                    "source": result.get("source", ""),
                    "output_displayed": result.get("output_displayed", False)  # 传递输出显示标记
                }
            else:
                return {
                    "success": False,
                    "error": f"User direct feedback is as above. If there is no feedback, it may indicate the operation is cancelled.",
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", "")
                }
                
        except Exception as e:
            return {"success": False, "error": f"远程Python执行时出错: {e}"}

    def execute_python_file(self, filename, save_output=False, python_args=None):
        """远程执行Python文件"""
        try:
            # 获取环境文件路径
            env_file = f"{self.main_instance.REMOTE_ENV}/venv/venv_pythonpath.sh"
            
            # 构建Python命令，包含文件名和参数
            python_executable = self.get_python_executable()
            python_cmd_parts = [python_executable, filename]
            if python_args:
                python_cmd_parts.extend(python_args)
            python_cmd = ' '.join(python_cmd_parts)
            
            # 构建远程命令：检查并应用虚拟环境，然后执行Python文件
            commands = [
                f"source {env_file} 2>/dev/null || true",
                python_cmd
            ]
            command = " && ".join(commands)
            
            # 执行远程命令
            result = self.main_instance.execute_command_interface("bash", ["-c", command])
            
            if result.get("success"):
                data = result.get("data", {})
                # 明确处理数据字段，优先使用data中的值
                return {
                    "success": True,
                    "stdout": data.get("stdout") if "stdout" in data else result.get("stdout", ""),
                    "stderr": data.get("stderr") if "stderr" in data else result.get("stderr", ""),
                    "return_code": data.get("exit_code") if "exit_code" in data else result.get("exit_code", 0),
                    "output_displayed": result.get("output_displayed", False)  # 传递输出显示标记
                }
            else:
                return {
                    "success": False,
                    "error": f"Remote Python file execution failed: {result.get('error', '')}",
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", "")
                }
                
        except Exception as e:
            return {"success": False, "error": f"远程Python文件执行时出错: {e}"}
