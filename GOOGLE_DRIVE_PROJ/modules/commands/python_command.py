"""
Python command handler for GDS
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
        if not args:
            self.print_error("python command needs a file name or code")
            return 1
            
        if args[0] == '-c':
            # 执行Python代码
            if len(args) < 2:
                self.print_error("python -c needs code")
                return 1
            code_args = [arg for arg in args[1:] if not arg.startswith('--')]
            code = ' '.join(code_args)
            result = self.cmd_python_code(code)
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
            
            return_code = result.get("return_code", result.get("returncode", 0))
            return return_code
        else:
            error_msg = result.get("error", "Python command execution failed")
            self.print_error(error_msg)
            stderr = result.get("stderr", "")
            if stderr:
                import sys
                print(stderr, end="", file=sys.stderr)
            return 1
    
    # ============================================================================
    # 请将 GOOGLE_DRIVE_PROJ/modules/python_execution.py 中的所有方法粘贴到下方
    # 从 def cmd_python(self, filename, python_args=None): 开始，一直到文件结尾
    # 注意：将所有 self.main_instance 替换为 self.shell
    #       将所有 self.drive_service 替换为 self.shell.drive_service  
    # ============================================================================

        
    def _get_python_executable(self):
        """获取当前应该使用的Python可执行文件路径 - 已废弃，Python版本选择在远程进行"""
        # 这个方法已经不再使用，Python版本选择逻辑已移到远程命令中
        # 保留这个方法以保持兼容性，但总是返回默认值
        return "python3"

    def cmd_python(self, code=None, filename=None, python_args=None, save_output=False):
        """python命令 - 执行Python代码"""
        try:
            if filename:
                # 执行Drive中的Python文件
                return self._execute_python_file(filename, save_output, python_args)
            elif code:
                # 执行直接提供的Python代码
                return self._execute_python_code(code, save_output)
            else:
                return {"success": False, "error": "请提供Python代码或文件名"}
                
        except Exception as e:
            return {"success": False, "error": f"执行Python命令时出错: {e}"}

    def _execute_python_file(self, filename, save_output=False, python_args=None):
        """执行Google Drive中的Python文件"""
        try:
            # 直接在远端执行Python文件，不需要先读取文件内容
            return self._execute_python_file_remote(filename, save_output, python_args)
            
        except Exception as e:
            return {"success": False, "error": f"执行Python文件时出错: {e}"}
    
    def _execute_python_code(self, code, save_output=False, filename=None):
        """执行Python代码并返回结果"""
        try:
            # 直接尝试远程执行，在远程命令中检查和应用虚拟环境
            return self._execute_python_code_remote_unified(code, save_output, filename)
                
        except Exception as e:
            return {"success": False, "error": f"执行Python代码时出错: {e}"}

    def _execute_python_code_remote_unified(self, code, save_output=False, filename=None):
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
            current_shell = self.main_instance.get_current_shell()
            shell_id = current_shell.get("id", "default") if current_shell else "default"
            # Direct storage in REMOTE_ENV, no .tmp subdirectory needed
            env_file = f"{self.main_instance.REMOTE_ENV}/venv/venv_pythonpath.sh"
            temp_file_path = f"{self.main_instance.REMOTE_ROOT}/tmp/{temp_filename}"
            
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
            
            # 获取当前shell ID (简化版本)
            SHELL_ID="default"
            
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
                return {
                    "success": True,
                    "stdout": data.get("stdout", result.get("stdout", "")),
                    "stderr": data.get("stderr", result.get("stderr", "")),
                    "return_code": data.get("exit_code", result.get("exit_code", 0)),
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

    def _execute_python_file_remote(self, filename, save_output=False, python_args=None):
        """远程执行Python文件"""
        try:
            # 获取环境文件路径
            current_shell = self.main_instance.get_current_shell()
            shell_id = current_shell.get("id", "default") if current_shell else "default"
            # Direct storage in REMOTE_ENV, no .tmp subdirectory needed
            env_file = f"{self.main_instance.REMOTE_ENV}/venv/venv_pythonpath.sh"
            
            # 构建Python命令，包含文件名和参数
            python_executable = self._get_python_executable()
            python_cmd_parts = [python_executable, filename]
            if python_args:
                python_cmd_parts.extend(python_args)
            python_cmd = ' '.join(python_cmd_parts)
            
            # 构建远程命令：检查并应用虚拟环境，然后执行Python文件
            commands = [
                # source环境文件，如果失败则忽略（会使用默认的PYTHONPATH）
                f"source {env_file} 2>/dev/null || true",

                python_cmd
            ]
            command = " && ".join(commands)
            
            # 执行远程命令
            result = self.main_instance.execute_command_interface("bash", ["-c", command])
            
            if result.get("success"):
                data = result.get("data", {})
                return {
                    "success": True,
                    "stdout": data.get("stdout", result.get("stdout", "")),
                    "stderr": data.get("stderr", result.get("stderr", "")),
                    "return_code": data.get("exit_code", result.get("exit_code", 0)),
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
