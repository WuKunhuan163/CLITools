"""
Command Executor Module
从 remote_commands.py 重构而来
"""

import time
from typing import List
import threading
from pathlib import Path

class DebugCapture:
    """Debug信息捕获和存储系统"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._debug_buffer = []
                    cls._instance._is_capturing = False
        return cls._instance
    
    def start_capture(self):
        """开始捕获debug信息"""
        self._is_capturing = True
        self._debug_buffer.clear()
    
    def stop_capture(self):
        """停止捕获debug信息"""
        self._is_capturing = False
    
    def add_debug(self, message):
        """添加debug信息到缓存"""
        if self._is_capturing:
            self._debug_buffer.append(message)
    
    def get_debug_info(self):
        """获取捕获的debug信息"""
        return '\n'.join(self._debug_buffer)
    
debug_capture = DebugCapture()

def debug_print(*args, **kwargs):
    """统一的debug输出函数，捕获时只存储，不捕获时正常输出"""
    # 构建消息字符串
    message = ' '.join(str(arg) for arg in args)
    
    # 如果正在捕获，添加到缓存
    if debug_capture._is_capturing:
        debug_capture.add_debug(message)
    else:
        # 正常输出
        print(message, **kwargs)

class CommandExecutor:
    """重构后的command_executor功能"""

    def __init__(self, drive_service=None, main_instance=None):
        self.drive_service = drive_service
        self.main_instance = main_instance
        self.SPECIAL_COMMANDS = {
            'ls', 'cd', 'pwd', 'mkdir', 'mv', 'cat', 'grep', 
            'upload', 'download', 'edit', 'read', 'find', 'help', 'exit', 'quit', 'venv'
        }

    def execute_command(self, user_command, result_filename=None, current_shell=None, skip_quote_escaping=False):
        """
        统一的命令执行接口 - 支持任何用户命令，自动生成JSON结果
        
        Args:
            user_command (str): 用户要执行的完整命令
            result_filename (str, optional): 指定的结果文件名
            current_shell (dict, optional): 当前shell信息
            skip_quote_escaping (bool, optional): 跳过引号转义处理，用于已经处理过的命令
            
        Returns:
            dict: 执行结果
        """
        # 处理__QUOTED_COMMAND__标记
        if user_command.startswith("__QUOTED_COMMAND__"):
            user_command = user_command[len("__QUOTED_COMMAND__"):]
        
        # 使用统一的JSON生成接口（包含语法检查）
        try:
            remote_command, actual_result_filename = self.main_instance.command_generator.generate_command(
                user_command, result_filename, current_shell, skip_quote_escaping
            )
        except Exception as e:
            # 如果是语法错误，直接返回错误，不弹出窗口
            if "syntax errors" in str(e).lower():
                print(f"Error: Bash syntax error detected:")
                print(f"   {str(e)}")
                print(f"   Please fix the syntax error in your command and try again.")
                return {
                    "success": False,
                    "action": "syntax_error",
                    "data": {
                        "error": str(e),
                        "source": "syntax_check"
                    }
                }
            else:
                # 其他错误继续抛出
                raise
        
        # 显示远程窗口
        title = f"GDS Unified Command: {user_command[:50]}..."
        window_result = self.show_remote_command_window(
            title=title,
            command_text=remote_command
        )
        
        # Debug: 保存原始输出到文件（用于调试）
        try:
            import os
            # 使用统一路径常量
            try:
                from .path_constants import get_data_dir
                debug_dir = str(get_data_dir())
                debug_file = str(get_data_dir() / "raw_gds_output.txt")
            except ImportError:
                debug_dir = "~/.local/bin/GOOGLE_DRIVE_DATA"
                debug_file = os.path.join(debug_dir, "raw_gds_output.txt")
            os.makedirs(debug_dir, exist_ok=True)
            
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write("=" * 50 + "\n")
                f.write("COMMAND:\n")
                f.write(f"{user_command}\n\n")
                
                f.write("=" * 50 + "\n")
                f.write("RESULT:\n")
                f.write(f"{window_result}\n\n")
                
                # 这里先写占位符，后续会在结果处理时更新
                f.write("=" * 50 + "\n")
                f.write("RAW_OUTPUT:\n")
                f.write("(Will be updated after command execution)\n\n")
                
                f.write("=" * 50 + "\n")
                f.write("OUTPUT:\n")
                f.write("(Will be updated after command execution)\n\n")
                
                f.write("=" * 50 + "\n")
                f.write("RAW_ERROR:\n")
                f.write("(Will be updated after command execution)\n\n")
                
                f.write("=" * 50 + "\n")
                f.write("ERROR:\n")
                f.write("(Will be updated after command execution)\n\n")
                
                f.write("=" * 50 + "\n")
                f.write("REMOTE_COMMAND:\n")
                f.write(f"{remote_command}\n")
        except Exception as debug_e:
            pass  # 忽略debug输出错误
        
        # 处理窗口结果
        if window_result["action"] == "success":
            # 用户点击了执行完成，现在开始显示进度指示器，等待并读取结果
            from .progress_manager import start_progress_buffering, stop_progress_buffering
            
            # 启动进度指示器（让用户看到）
            start_progress_buffering("⏳ Waiting for result ...")
            
            try:
                result_file_path = f"{self.main_instance.REMOTE_ROOT}/tmp/{actual_result_filename}"
                result = self.main_instance.result_processor.wait_and_read_result_file(actual_result_filename)
            finally:
                # 停止进度指示器
                stop_progress_buffering()
            
            if result.get("success", False):
                data = result.get("data", {})
                return {
                    "success": True,
                    "action": "success",
                    "data": data,
                    "source": "unified_command"
                }
            else:
                return {
                    "success": False,
                    "action": "execution_failed",
                    "data": {
                        "error": result.get("error", "Command execution failed"),
                        "source": "unified_command"
                    }
                }
                
        elif window_result["action"] == "direct_feedback":
            # 用户选择直接反馈，使用direct_feedback_interface
            print()  # 换行
            feedback_result = self.direct_feedback_interface(remote_command, actual_result_filename)
            return feedback_result
            
        elif window_result["action"] == "copy":
            return {
                "success": True,
                "action": "copy",
                "data": {
                    "message": "Command copied to clipboard",
                    "source": "unified_command"
                }
            }
            
        else:  # timeout, cancel, failure, error
            import traceback
            error_details = {
                "success": False,
                "action": window_result["action"],
                "error": window_result.get("error", "Operation cancelled or failed"),
                "traceback": traceback.format_stack()
            }
            return error_details



    def update_debug_output_with_progress(self, file_result, raw_progress_output, raw_progress_error):
        """更新debug文件的输出部分，包含真正的原始输出"""
        try:
            import os
            # 使用统一路径常量
            try:
                from .path_constants import get_data_dir
                debug_file = str(get_data_dir() / "raw_gds_output.txt")
            except ImportError:
                debug_file = "~/.local/bin/GOOGLE_DRIVE_DATA/raw_gds_output.txt"
            
            if not os.path.exists(debug_file):
                return
                
            # 读取现有内容
            with open(debug_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 获取结果数据
            if file_result.get("success") and "data" in file_result:
                data = file_result["data"]
                remote_stdout = data.get("stdout", "")
                remote_stderr = data.get("stderr", "")
                
                # 合并进度输出和远程输出作为真正的原始输出
                combined_raw_output = raw_progress_output + remote_stdout
                combined_raw_error = raw_progress_error + remote_stderr
                
                # 处理输出（模拟_process_terminal_erase的逻辑）
                processed_output = self.process_terminal_escape_sequences(combined_raw_output) if combined_raw_output else ""
                processed_error = self.process_terminal_escape_sequences(combined_raw_error) if combined_raw_error else ""
                
                # 替换占位符
                content = content.replace(
                    "=" * 50 + "\nRAW_OUTPUT:\n(Will be updated after command execution)\n\n",
                    "=" * 50 + f"\nRAW_OUTPUT:\n{repr(combined_raw_output)}\n\n"
                )
                content = content.replace(
                    "=" * 50 + "\nOUTPUT:\n(Will be updated after command execution)\n\n",
                    "=" * 50 + f"\nOUTPUT:\n{processed_output}\n\n"
                )
                content = content.replace(
                    "=" * 50 + "\nRAW_ERROR:\n(Will be updated after command execution)\n\n",
                    "=" * 50 + f"\nRAW_ERROR:\n{repr(combined_raw_error)}\n\n"
                )
                content = content.replace(
                    "=" * 50 + "\nERROR:\n(Will be updated after command execution)\n\n",
                    "=" * 50 + f"\nERROR:\n{processed_error}\n\n"
                )
            else:
                # 命令失败的情况
                error_msg = file_result.get("error", "Unknown error")
                content = content.replace(
                    "=" * 50 + "\nRAW_OUTPUT:\n(Will be updated after command execution)\n\n",
                    "=" * 50 + f"\nRAW_OUTPUT:\n{repr(raw_progress_output)}\n\n"
                )
                content = content.replace(
                    "=" * 50 + "\nOUTPUT:\n(Will be updated after command execution)\n\n",
                    "=" * 50 + f"\nOUTPUT:\n{self.process_terminal_escape_sequences(raw_progress_output)}\n\n"
                )
                content = content.replace(
                    "=" * 50 + "\nRAW_ERROR:\n(Will be updated after command execution)\n\n",
                    "=" * 50 + f"\nRAW_ERROR:\n{repr(raw_progress_error + error_msg)}\n\n"
                )
                content = content.replace(
                    "=" * 50 + "\nERROR:\n(Will be updated after command execution)\n\n",
                    "=" * 50 + f"\nERROR:\n{self.process_terminal_escape_sequences(raw_progress_error) + error_msg}\n\n"
                )
            
            # 写回文件
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(content)
                
        except Exception as e:
            pass  # 忽略debug更新错误
    

    def execute_command_interface(self, cmd, args, _skip_queue_management=False, _original_user_command=None):
        """
        统一远端命令执行接口 - 处理除特殊命令外的所有命令

        Args:
            cmd (str): 命令名称
            args (list): 命令参数
            _skip_queue_management (bool): 是否跳过队列管理（避免双重管理）

        Returns:
            dict: 执行结果，包含stdout、stderr、path等字段
        """
        # 检查是否为特殊命令，如果是则不应该到这里
        if cmd in self.SPECIAL_COMMANDS:
            return {"success": False, "error": f"Special command '{cmd}' should not use remote execution"}
        cleaned_args = args

        # 调试日志已禁用
        # 导入正确的远程窗口队列管理器并生成唯一的窗口ID
        import time

        # 设置时间戳基准点（如果还没有设置的话）
        if not hasattr(self, '_debug_start_time'):
            self._debug_start_time = time.time()
        
        if cleaned_args:
            import shlex
            if cmd.startswith("__QUOTED_COMMAND__"):
                user_command = f"{cmd} {' '.join(str(arg) for arg in cleaned_args)}"
            else:
                user_command = f"{cmd} {' '.join(shlex.quote(str(arg)) for arg in cleaned_args)}"
        else:
            user_command = cmd
            
        current_shell = self.main_instance.get_current_shell()
        result = self.execute_command(
            user_command=user_command,
            current_shell=current_shell
        )
        return result


    def execute_special_command(self, name: str, args: List[str], **kwargs) -> int:
        """
        Execute a command by name.
        
        Args:
            name: Command name
            args: Command arguments
            **kwargs: Additional keyword arguments
            
        Returns:
            int: Exit code (0 for success, non-zero for failure)
        """
        command = self.main_instance.command_registry.get_command(name)
        if command is None:
            print(f"Error: Unknown command '{name}'")
            return 1
        
        # 直接使用原始参数，不进行 JSON 处理
        if not command.validate_args(args):
            return 1
        return command.execute(name, args, **kwargs)


    def show_remote_command_window(self, title, command_text, timeout_seconds=3600, test_mode=False, is_priority=False):
        if hasattr(self, '_no_direct_feedback') and self._no_direct_feedback:
            test_mode = True

        if hasattr(self, '_is_priority') and self._is_priority:
            is_priority = True
            self._is_priority = False

        """
        新架构：统一窗口管理，避免多线程竞态问题
        """
        # 添加挂载检查到命令文本
        mount_check_header = f'''# 首先检查挂载是否成功
MOUNT_CHECK_FAILED=0
python3 -c "
import os
import sys
try:
    mount_hash = '{getattr(self.main_instance, "MOUNT_HASH", "")}'
    if mount_hash:
        fingerprint_file = \\\"{self.main_instance.REMOTE_ROOT}/tmp/.gds_mount_fingerprint_\\\" + mount_hash
        if os.path.exists(fingerprint_file):
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        sys.exit(1)
except Exception:
    sys.exit(1)
"
if [ $? -ne 0 ]; then
    clear && echo "Error: 当前session的GDS无法访问Google Drive文件结构。请使用GOOGLE_DRIVE --remount指令重新挂载，然后执行GDS的其他命令"
    MOUNT_CHECK_FAILED=1
fi

if [ $MOUNT_CHECK_FAILED -eq 0 ]; then
'''
        # 将挂载检查添加到命令文本前面，并在最后添加fi
        enhanced_command_text = mount_check_header + command_text + "\nfi"
        
        from .window_manager import get_window_manager
        
        # 获取窗口管理器并请求窗口
        window_manager = get_window_manager()
        
        # 获取当前命令的hash（如果存在）
        current_hash = getattr(self, '_current_cmd_hash', None)
        
        result = window_manager.request_window(title, enhanced_command_text, timeout_seconds, command_hash=current_hash, no_direct_feedback=test_mode, is_priority=is_priority)
        return result


    def fix_json(self, json_str: str) -> str:
        """
        Intelligently fix JSON by adding missing quotes and using eval.
        
        Args:
            json_str: JSON string that may have missing quotes
            
        Returns:
            str: Fixed JSON string
        """
        import re
        import ast
        import json
        
        # Strategy: First try to parse as-is, then fix if needed
        fixed_str = json_str
        
        # First, try to parse the JSON as-is
        try:
            parsed = ast.literal_eval(fixed_str)
            result = json.dumps(parsed)
            return result
        except Exception:
            pass
        
        # Pattern 1: Fix string replacement [[text1, text2]] -> [["text1", "text2"]]
        # Avoid matching triple nested arrays like [[[2, 2], text]]
        string_pattern = r'(?<!\[)\[\[([^"\[\]]+?),\s*([^"\[\]]+?)\]\](?!\])'
        def fix_string_replacement(match):
            text1 = match.group(1).strip()
            text2 = match.group(2).strip()
            return f'[["{text1}", "{text2}"]]'
        if re.search(string_pattern, fixed_str):
            fixed_str = re.sub(string_pattern, fix_string_replacement, fixed_str)
        
        # Pattern 2: Fix line replacement [[[numbers], text]] -> [[[numbers], "text"]]
        # Match unquoted text after the number array (including special characters and spaces)
        line_pattern = r'(\[\[\[[0-9, ]+\],\s*)([^"\[\]]+?)(\]\])'
        def fix_line_replacement(match):
            prefix = match.group(1)
            text = match.group(2).strip()
            suffix = match.group(3)
            return f'{prefix}"{text}"{suffix}'
        if re.search(line_pattern, fixed_str):
            fixed_str = re.sub(line_pattern, fix_line_replacement, fixed_str)
        
        # Now try to parse with ast.literal_eval
        parsed = ast.literal_eval(fixed_str)
        result = json.dumps(parsed)
        return result
            
    def direct_feedback(self, remote_command, debug_info=None):
        """
        直接反馈功能 - 粘贴远端命令和用户反馈，用=分割
        使用统一的_get_multiline_user_input方法
        """
        debug_print(f"进入direct_feedback方法")

        # 先输出debug信息（如果有的话）
        if debug_info:
            print(f"Debug information:")
            print(debug_info)
            print(f"=" * 20)  # 20个等号分割线

        # 然后粘贴生成的远端指令
        print(f"Generated remote command:")
        print(remote_command)
        print(f"=" * 20)  # 50个等号分割线

        print(f"Please provide command execution result (multi-line input, press Ctrl+D to finish):")
        print()

        # 使用统一的多行输入方法
        full_output = self._get_multiline_user_input()

        # 简单解析输出：如果包含错误关键词，放到stderr，否则放到stdout
        error_keywords = ['error', 'Error', 'ERROR', 'exception', 'Exception', 'EXCEPTION', 
                            'traceback', 'Traceback', 'TRACEBACK', 'failed', 'Failed', 'FAILED']

        # 检查是否包含错误信息
        has_error = any(keyword in full_output for keyword in error_keywords)
        if has_error:
            stdout_content = ""
            stderr_content = full_output
            exit_code = 1  # 有错误时默认退出码为1
        else:
            stdout_content = full_output
            stderr_content = ""
            exit_code = 0 

        # 构建反馈结果
        feedback_result = {
            "success": exit_code == 0,
            "action": "direct_feedback",
            "data": {
                "working_dir": "user_provided",
                "timestamp": "user_provided", 
                "exit_code": exit_code,
                "stdout": stdout_content,
                "stderr": stderr_content,
                "source": "direct_feedback"
            }
        }
        return feedback_result


    def direct_feedback_interface(self, remote_command, result_filename=None, debug_info=None):
        """
        增强的直接反馈功能 - 在收集用户反馈后，尝试等待并获取实际的执行结果

        Args:
            remote_command (str): 远端命令内容
            result_filename (str): 结果文件名（如果有的话）
            debug_info (str): debug信息，仅在直接反馈时输出

        Returns:
            dict: 包含直接反馈和实际结果的综合结果
        """
        feedback_result = self.direct_feedback(remote_command, debug_info)

        # 添加分隔符
        print(f"=" * 20)

        # 如果提供了result_filename，尝试等待并读取实际的执行结果
        if result_filename:
            try:
                # 等待并读取结果文件
                actual_result = self.wait_and_read_result_file(result_filename)

                if actual_result.get("success", False):
                    actual_data = actual_result.get("data", {})
                    actual_stdout = actual_data.get("stdout", "").strip()
                    actual_stderr = actual_data.get("stderr", "").strip()

                    # 不打印actual_stdout，因为用户的直接反馈已经包含了输出
                    # 只在有stderr时打印stderr
                    if actual_stderr:
                        import sys
                        print(actual_stderr, file=sys.stderr)

                    # 返回实际的执行结果，但保留用户反馈信息
                    return {
                        "success": actual_result.get("success", False),
                        "action": "direct_feedback_interface",
                        "data": actual_data,
                        "user_feedback": feedback_result.get("data", {}),
                        "source": "direct_feedback_interface"
                    }
                else:
                    error_msg = actual_result.get("error", "Failed to get actual result")
                    print(f"Could not get actual execution result: {error_msg}")

            except Exception as e:
                print(f"Error waiting for actual result: {e}")

        # 如果没有result_filename或获取实际结果失败，返回用户反馈结果
        return feedback_result


    def process_terminal_escape_sequences(self, text):
        """处理终端转义序列，模拟用户看到的输出"""
        if not text:
            return ""
        
        # 模拟终端处理转义序列
        lines = text.split('\n')
        processed_lines = []
        
        for line in lines:
            # 处理回车符 \r
            if '\r' in line:
                parts = line.split('\r')
                # 回车符会回到行首，所以只保留最后一部分
                line = parts[-1]
            
            # 处理退格符 \b
            while '\b' in line:
                # 找到\b的位置
                pos = line.find('\b')
                if pos > 0:
                    # 删除\b前面的一个字符和\b本身
                    line = line[:pos-1] + line[pos+1:]
                else:
                    # 如果\b在开头，只删除\b
                    line = line[1:]
            
            # 处理ANSI转义序列（颜色代码等）
            # 简单匹配 \033[...m 或 \x1b[...m
            import re
            line = re.sub(r'\033\[[0-9;]*m', '', line)  # ESC[...m
            line = re.sub(r'\x1b\[[0-9;]*m', '', line)  # ESC[...m (十六进制)
            line = re.sub(r'\033\[[0-9;]*[A-Za-z]', '', line)  # ESC[...字母
            line = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', line)  # ESC[...字母
            
            # 处理光标移动等其他转义序列
            line = re.sub(r'\033\[[0-9]+;[0-9]+[Hf]', '', line)  # 光标位置
            line = re.sub(r'\x1b\[[0-9]+;[0-9]+[Hf]', '', line)
            line = re.sub(r'\033\[[0-9]*[ABCDEFGJKST]', '', line)  # 各种光标移动
            line = re.sub(r'\x1b\[[0-9]*[ABCDEFGJKST]', '', line)
            
            # 处理清屏序列
            line = re.sub(r'\033\[2J', '', line)
            line = re.sub(r'\x1b\[2J', '', line)
            line = re.sub(r'\033\[H', '', line)
            line = re.sub(r'\x1b\[H', '', line)
            line = re.sub(r'\033\[K', '', line)  # 清除到行尾
            line = re.sub(r'\x1b\[K', '', line)
            
            # 处理响铃符
            line = line.replace('\a', '')
            line = line.replace('\x07', '')
            
            # 处理制表符
            line = line.replace('\t', '    ')  # 制表符转换为4个空格
            
            processed_lines.append(line)
        
        return '\n'.join(processed_lines)

    def _get_multiline_user_input(self):
        """
        获取用户的多行输入，支持Ctrl+D结束
        使用与USERINPUT完全相同的信号超时输入逻辑
        
        Returns:
            str: 用户输入的多行内容
        """
        lines = []
        timeout_seconds = 180  # 3分钟超时，和USERINPUT一致
        
        # 定义超时异常
        class TimeoutException(Exception):
            pass
        
        def timeout_handler(signum, frame):
            raise TimeoutException("Input timeout")
        
        # 使用信号方式进行超时控制，完全复制USERINPUT逻辑
        import signal
        import readline
        
        original_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)
        
        try:
            while True:
                try:
                    line = input()
                    lines.append(line)
                except EOFError:
                    # Ctrl+D结束输入
                    break
        except TimeoutException:
            print("\nInput timeout after 180 seconds")
        finally:
            # 恢复信号处理器
            signal.alarm(0)
            signal.signal(signal.SIGALRM, original_handler)
        
        return '\n'.join(lines)
