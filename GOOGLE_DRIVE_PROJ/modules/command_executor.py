"""
Command Executor Module
从 remote_commands.py 重构而来
"""
from typing import List
import threading

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

def write_debug_output(command=None, result=None, raw_output=None, output=None, 
                       raw_error=None, error=None, remote_command=None, full_command=None,
                       return_code=None):
    """
    统一的debug输出接口
    
    Args:
        command: 用户命令
        result: 窗口结果字典
        raw_output: 原始stdout
        output: 处理后的stdout
        raw_error: 原始stderr
        error: 处理后的stderr
        remote_command: 远端命令
        full_command: 完整命令（含参数）
        return_code: 返回码
    """
    from .path_constants import get_data_dir
    debug_file = str(get_data_dir() / "raw_gds_output.txt")
    
    with open(debug_file, 'w', encoding='utf-8') as f:
        # 命令
        f.write("=" * 50 + "\n")
        f.write("COMMAND:\n")
        f.write(f"{command if command is not None else '(not provided)'}\n\n")
        
        # 完整命令
        if full_command is not None:
            f.write("=" * 50 + "\n")
            f.write("FULL_COMMAND:\n")
            f.write(f"{full_command}\n\n")
        
        # 结果
        if result is not None:
            f.write("=" * 50 + "\n")
            f.write("RESULT:\n")
            f.write(f"{result}\n\n")
        
        # 返回码
        if return_code is not None:
            f.write("=" * 50 + "\n")
            f.write("RETURN_CODE:\n")
            f.write(f"{return_code}\n\n")
        
        # 原始输出
        f.write("=" * 50 + "\n")
        f.write("RAW_OUTPUT:\n")
        if raw_output is not None:
            f.write(f"{repr(raw_output)}\n\n")
        else:
            f.write("(not provided)\n\n")
        
        # 处理后的输出
        f.write("=" * 50 + "\n")
        f.write("OUTPUT:\n")
        if output is not None:
            f.write(f"{output}\n\n")
        else:
            f.write("(not provided)\n\n")
        
        # 原始错误
        f.write("=" * 50 + "\n")
        f.write("RAW_ERROR:\n")
        if raw_error is not None:
            f.write(f"{repr(raw_error)}\n\n")
        else:
            f.write("(not provided)\n\n")
        
        # 处理后的错误
        f.write("=" * 50 + "\n")
        f.write("ERROR:\n")
        if error is not None:
            f.write(f"{error}\n\n")
        else:
            f.write("(not provided)\n\n")
        
        # 远端命令
        if remote_command is not None:
            f.write("=" * 50 + "\n")
            f.write("REMOTE_COMMAND:\n")
            f.write(f"{remote_command}\n") # 忽略debug输出错误

class CommandExecutor:
    """重构后的command_executor功能"""

    def __init__(self, drive_service=None, main_instance=None):
        self.drive_service = drive_service
        self.main_instance = main_instance
        self.SPECIAL_COMMANDS = {
            'ls', 'cd', 'pwd', 'mkdir', 'mv', 'cat', 'grep', 
            'upload', 'download', 'edit', 'read', 'find', 'help', 'exit', 'quit', 'venv'
        }

    def process_terminal_erase(self, stdout):
        """
        模拟终端输出处理，正确处理擦除字符
        基于实际观察到的模式：\r\x1b[K会擦除当前行
        
        Args:
            stdout: GDS命令的标准输出
            
        Returns:
            tuple: (cleaned_stdout)
        """
        import re
        def process(text):
            """
            处理终端转义序列，模拟真实终端行为
            使用反向处理：从后往前寻找擦除符号，从擦除符号位置向左擦除
            """
            if not text:
                return text
            
            result = text
            
            # 反向处理：从后往前寻找擦除序列
            while True:
                # 寻找最后一个\r\x1b[K序列
                last_r_erase_pos = result.rfind('\r\x1b[K')
                # 寻找最后一个\n\x1b[K序列
                last_n_erase_pos = result.rfind('\n\x1b[K')
                
                # 选择最后出现的擦除序列
                if last_r_erase_pos == -1 and last_n_erase_pos == -1:
                    # 没有找到擦除序列，处理完成
                    break
                
                # 确定使用哪个擦除序列（选择位置更靠后的）
                if last_r_erase_pos > last_n_erase_pos:
                    last_erase_pos = last_r_erase_pos
                    erase_pattern = '\r\x1b[K'
                else:
                    last_erase_pos = last_n_erase_pos
                    erase_pattern = '\n\x1b[K'
                
                # 找到擦除序列，需要擦除当前行
                # 从擦除序列位置向左找到行的开始位置
                line_start = result.rfind('\n', 0, last_erase_pos)
                if line_start == -1:
                    # 没有找到换行符，说明要擦除从开头到擦除序列的所有内容
                    line_start = 0
                else:
                    # 找到了换行符，保留换行符，从换行符后开始擦除
                    line_start += 1
                
                # 擦除从line_start到擦除序列结束的内容
                erase_end = last_erase_pos + len(erase_pattern)
                result = result[:line_start] + result[erase_end:]
            
            # 处理单独的\r（回车符）
            while True:
                last_cr_pos = result.rfind('\r')
                if last_cr_pos == -1:
                    break
                
                # 检查这个\r是否已经是\r\x1b[K的一部分（应该已经被处理了）
                if (last_cr_pos + 3 < len(result) and 
                    result[last_cr_pos:last_cr_pos+4] == '\r\x1b[K'):
                    # 这是\r\x1b[K序列的一部分，应该已经被处理了，跳过
                    # 这种情况不应该发生，但为了安全起见
                    break
                
                # 单独的\r：光标回到行首，后续字符会覆盖当前行
                line_start = result.rfind('\n', 0, last_cr_pos)
                if line_start == -1:
                    line_start = 0
                else:
                    line_start += 1
                
                # 移除\r，保留后续内容（如果有的话）
                result = result[:line_start] + result[last_cr_pos+1:]
            
            # 处理单独的\x1b[K序列
            while True:
                last_k_pos = result.rfind('\x1b[K')
                if last_k_pos == -1:
                    break
                
                # 检查这个\x1b[K前面是否有\r
                if (last_k_pos >= 1 and result[last_k_pos-1] == '\r'):
                    # 这是\r\x1b[K的一部分，应该已经被处理了
                    break
                
                # 单独的\x1b[K：擦除从光标到行尾
                # 需要擦除当前行的内容
                # 从\x1b[K位置向左找到行的开始位置
                line_start = result.rfind('\n', 0, last_k_pos)
                if line_start == -1:
                    # 没有找到换行符，擦除从开头到\x1b[K的所有内容
                    result = result[last_k_pos+3:]
                else:
                    # 找到了换行符，保留换行符，擦除从换行符后到\x1b[K的内容
                    result = result[:line_start+1] + result[last_k_pos+3:]
            
            return result
        
        cleaned_stdout = stdout
        if cleaned_stdout:
            cleaned_stdout = process(cleaned_stdout)
            cleaned_stdout = re.sub(r'\n+', '\n', cleaned_stdout)
            cleaned_stdout = cleaned_stdout.strip()
            if cleaned_stdout:
                cleaned_stdout += '\n'
        
        return cleaned_stdout

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
        import time
        
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
        
        write_debug_output(
            command=user_command,
            result=window_result,
            raw_output="(Will be updated after command execution)",
            raw_error="(Will be updated after command execution)",
            remote_command=remote_command
        )
        
        # 处理窗口结果
        if window_result["action"] == "success":
            # 用户点击了执行完成，现在开始显示进度指示器，等待并读取结果
            from .progress_manager import start_progress_buffering, stop_progress_buffering
            
            # 启动进度指示器（让用户看到）
            start_progress_buffering("⏳ Waiting for result ...")
            
            try:
                result = self.main_instance.result_processor.wait_and_read_result_file(actual_result_filename)
            finally:
                # 停止进度指示器
                stop_progress_buffering()
            
            # 更新debug文件，记录实际的执行结果
            if result.get("success", False):
                data = result.get("data", {})
                write_debug_output(
                    command=user_command,
                    result=result,
                    raw_output=data.get("stdout", ""),
                    output=data.get("stdout", ""),
                    raw_error=data.get("stderr", ""),
                    error=data.get("stderr", ""),
                    remote_command=remote_command,
                    return_code=data.get("exit_code", -1)
                )
            
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
        
        # 如果提供了原始用户命令，优先使用它（用于保持hash一致性）
        if _original_user_command:
            user_command = _original_user_command
        elif cleaned_args:
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
