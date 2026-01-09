"""
Google Drive Shell - Command Executor Module

This module provides the core command execution functionality for the Google Drive Shell system.
It handles remote command execution, debug information capture, and result processing.

Key Features:
- Unified command execution interface for all remote operations
- Debug information capture and management
- Thread-safe execution with proper error handling
- Integration with remote shell management
- Support for both synchronous and background command execution
- Comprehensive logging and debugging capabilities

Classes:
    DebugCapture: Thread-safe debug information capture system
    CommandExecutor: Main command execution engine

Command Flow:
1. Command validation and preprocessing
2. Remote shell preparation and state management
3. Command execution via remote interface
4. Result processing and error handling
5. Debug information capture and storage

Dependencies:
    - Remote shell management for execution context
    - Window management for remote command display
    - Error handling and validation systems
    - Threading support for concurrent operations

Migrated from: remote_commands.py (refactored for better modularity)
"""
from typing import List
import threading
import json
import os
from .connection_check import create_connection_check_instance


def regularize_newlines(text):
    """
    如果text以连续至少两个\\n结尾，去掉一个\\n。
    例如：
    - "error\\n\\n" -> "error\\n"
    - "error\\n\\n\\n\\n" -> "error\\n\\n\\n"
    - "error\\n" -> "error\\n" (不变)
    """
    if text.endswith('\n\n'):
        return text[:-1]  # 去掉最后一个\\n
    elif not text.endswith('\n'):
        return text + '\n'
    return text

def process_terminal_erase(stdout):
        """
        模拟终端输出处理，正确处理擦除字符和所有终端转义序列
        
        Args:
            stdout: GDS命令的标准输出
            
        Returns:
            str: 清理后的输出
        """
        import re
        
        def process(text):
            """
            处理终端转义序列，模拟真实终端行为
            """
            if text is None:
                return ''
            if not text:
                return text
            
            result = text
            
            # 1. 移除ANSI颜色代码和其他控制序列（除了\r、\b和\x1b[K）
            # 匹配模式：\033[...m 或 \x1b[...m 以及其他光标移动序列，但保留\x1b[K
            # 先移除颜色代码（以m结尾的）
            result = re.sub(r'\x1b\[[0-9;]*m', '', result)
            result = re.sub(r'\033\[[0-9;]*m', '', result)
            # 移除其他光标移动序列，但排除K（清除到行尾）
            result = re.sub(r'\x1b\[[0-9;]*[A-JL-Za-jl-z]', '', result)
            result = re.sub(r'\033\[[0-9;]*[A-JL-Za-jl-z]', '', result)
            
            # 2. 移除响铃符
            result = result.replace('\a', '')
            result = result.replace('\x07', '')
            
            # 4. 处理退格符 \b
            # 从左到右处理退格符
            while '\b' in result:
                pos = result.find('\b')
                if pos > 0:
                    # 删除前一个字符和退格符本身
                    result = result[:pos-1] + result[pos+1:]
                else:
                    # 开头的退格符直接删除
                    result = result[1:]
            
            # 5. 反向处理：从后往前寻找擦除序列
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
                if erase_pattern == '\n\x1b[K':
                    # 对于\n\x1b[K序列，擦除从换行符开始到下一个换行符（或结尾）的所有内容
                    # 这包括换行符本身和后面的内容，直到下一行开始
                    next_newline = result.find('\n', last_erase_pos + len(erase_pattern))
                    if next_newline == -1:
                        # 没有下一个换行符，擦除到结尾
                        result = result[:last_erase_pos]
                    else:
                        # 有下一个换行符，擦除到下一个换行符（不包括下一个换行符）
                        result = result[:last_erase_pos] + result[next_newline:]
                else:
                    # 对于\r\x1b[K序列，使用原来的逻辑
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
        
        if stdout is None:
            return ''
        
        cleaned_stdout = stdout
        if cleaned_stdout:
            cleaned_stdout = process(cleaned_stdout)
            cleaned_stdout = re.sub(r'\n+', '\n', cleaned_stdout)
            cleaned_stdout = cleaned_stdout.strip()
        
        return cleaned_stdout


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
                       return_code=None, append=False):
    """
    统一的debug输出接口 - JSON格式实时查看指令执行
    
    Args:
        command: 用户命令
        result: 窗口结果字典
        raw_output: 原始stdout (应包含⏳indicator)
        output: 处理后的stdout (应与"输出:"字段一致)
        raw_error: 原始stderr
        error: 处理后的stderr (应与"错误:"字段一致)
        remote_command: 远端命令
        full_command: 完整命令（含参数）
        return_code: 返回码
        append: 是否追加模式（用于实时更新）
    """
    import json
    from .path_constants import get_data_dir
    from datetime import datetime
    
    debug_file = str(get_data_dir() / "raw_gds_output.json")
    
    # 构建debug数据
    debug_data = {
        "timestamp": datetime.now().isoformat(),
        "command": command,
        "result": result,
        "return_code": return_code,
        "raw_output": raw_output,
        "output": output,
        "raw_error": raw_error,
        "error": error,
        "remote_command": remote_command,
        "full_command": full_command,
        "analysis": {
            "raw_contains_indicator": '⏳' in (raw_output or ''),
            "output_contains_indicator": '⏳' in (output or ''),
            "indicator_removal_success": '⏳' not in (output or '') if raw_output and '⏳' in raw_output else None
        }
    }
    
    if append:
        # 追加模式：读取现有数据，添加新条目
        try:
            with open(debug_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            if not isinstance(existing_data, list):
                existing_data = [existing_data]
        except (FileNotFoundError, json.JSONDecodeError):
            existing_data = []
        
        existing_data.append(debug_data)
        
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
    else:
        # 覆盖模式：写入单个条目
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump(debug_data, f, indent=2, ensure_ascii=False)

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

    def ensure_tmp_id_cached(self):
        """确保~/tmp的ID已被解析和缓存"""
        try:
            # 检查是否已有~/tmp的缓存ID
            tmp_logical_path = "~/tmp"
            cached_id = self.get_cached_path_id(tmp_logical_path)
            
            if cached_id:
                # 已有缓存，无需重新解析
                return cached_id
            
            # 没有缓存，需要解析~/tmp的ID
            resolved_id = self.resolve_tmp_folder_id()
            
            if resolved_id:
                # 将解析的ID添加到缓存
                self.cache_path_id(tmp_logical_path, resolved_id)
                return resolved_id
            else:
                # 解析失败，但不影响命令执行
                return None
                
        except Exception as e:
            # 解析失败不应该影响命令执行
            print(f"Warning: Failed to resolve ~/tmp ID: {e}")
            return None
    
    def get_cached_path_id(self, logical_path):
        """从缓存中获取路径ID"""
        try:
            from .path_constants import PathConstants
            path_constants = PathConstants()
            config_path = str(path_constants.GDS_PATH_IDS_FILE)
            
            if not os.path.exists(config_path):
                return None
                
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            return config.get("path_ids", {}).get(logical_path)
        except Exception:
            return None
    
    def cache_path_id(self, logical_path, folder_id):
        """将路径ID添加到缓存"""
        try:
            import json
            import os
            import time
            from .path_constants import PathConstants
            
            path_constants = PathConstants()
            config_path = str(path_constants.GDS_PATH_IDS_FILE)
            
            # 加载现有配置
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
            else:
                config = {"path_ids": {}, "last_updated": None}
            
            # 添加新的路径ID
            config["path_ids"][logical_path] = folder_id
            config["last_updated"] = time.time()
            
            # 保存配置
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
        except Exception as e:
            print(f"Warning: Failed to cache path ID: {e}")
    
    def resolve_tmp_folder_id(self):
        """解析~/tmp文件夹的Google Drive ID"""
        try:
            if not self.main_instance.drive_service:
                return None
            
            # 获取REMOTE_ROOT文件夹ID
            root_folder_id = getattr(self.main_instance, 'REMOTE_ROOT_FOLDER_ID', None)
            if not root_folder_id:
                return None
            
            # 在REMOTE_ROOT中查找tmp文件夹
            result = self.main_instance.drive_service.list_files(
                folder_id=root_folder_id, 
                max_results=100
            )
            
            if not result.get('success') or not result.get('files'):
                return None
            
            # 查找名为'tmp'的文件夹
            for item in result['files']:
                if (item.get('name') == 'tmp' and 
                    item.get('mimeType') == 'application/vnd.google-apps.folder'):
                    return item['id']
            
            return None
            
        except Exception as e:
            print(f"Warning: Failed to resolve tmp folder ID: {e}")
            return None
    
    def should_add_connection_check(self, estimated_duration_seconds=None):
        """
        Determine if Connection Check should be added to the current command
        
        Args:
            estimated_duration_seconds (float, optional): Estimated command duration
            
        Returns:
            bool: True if Connection Check should be added
        """
        try:
            # Load or initialize counter
            counter_info = self.get_execution_counter()
            
            # Get frequency settings (configurable for testing vs production)
            window_threshold = self.get_template_window_threshold()
            duration_threshold = self._get_template_duration_threshold()
            
            # Check condition 1: Every X remote windows (trigger on Xth window, not X+1th)
            if counter_info['count'] >= (window_threshold - 1):
                self.reset_execution_counter()
                return True
            
            # Check condition 2: Commands taking >T seconds
            if estimated_duration_seconds and estimated_duration_seconds > duration_threshold:
                self.reset_execution_counter()
                return True
            
            # Increment counter for next time
            self.increment_execution_counter()
            return False
            
        except Exception as e:
            print(f"Warning: Failed to check Connection Check condition: {e}")
            return False
    
    def get_execution_counter(self):
        """Get current execution counter from persistent storage"""
        try:
            from .path_constants import PathConstants
            path_constants = PathConstants()
            counter_file = path_constants.GOOGLE_DRIVE_DATA_DIR / "connection_check_counter.json"
            
            if counter_file.exists():
                with open(counter_file, 'r') as f:
                    return json.load(f)
            else:
                return {"count": 0, "last_reset": None}
        except Exception:
            return {"count": 0, "last_reset": None}
    
    def increment_execution_counter(self):
        """Increment the execution counter"""
        try:
            import time
            from .path_constants import PathConstants
            
            path_constants = PathConstants()
            counter_file = path_constants.GOOGLE_DRIVE_DATA_DIR / "connection_check_counter.json"
            
            counter_info = self.get_execution_counter()
            counter_info['count'] += 1
            counter_info['last_updated'] = time.time()
            
            os.makedirs(counter_file.parent, exist_ok=True)
            with open(counter_file, 'w') as f:
                json.dump(counter_info, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to increment execution counter: {e}")
    
    def reset_execution_counter(self):
        """Reset the execution counter to 0"""
        try:
            import time
            from .path_constants import PathConstants
            
            path_constants = PathConstants()
            counter_file = path_constants.GOOGLE_DRIVE_DATA_DIR / "connection_check_counter.json"
            
            counter_info = {"count": 0, "last_reset": time.time()}
            
            os.makedirs(counter_file.parent, exist_ok=True)
            with open(counter_file, 'w') as f:
                json.dump(counter_info, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to reset execution counter: {e}")
    
    def get_template_window_threshold(self):
        """Get window threshold for Connection Check (configurable for testing vs production)"""
        from .path_constants import PathConstants
        path_constants = PathConstants()
        config_file = path_constants.GOOGLE_DRIVE_DATA_DIR / "connection_check_config.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
            return config.get("window_threshold", 50)  # Default for testing
        else:
            return 50  # Default for testing (user can change to 50 for production)
    
    def _get_template_duration_threshold(self):
        """Get duration threshold for Connection Check (configurable for testing vs production)"""
        from .path_constants import PathConstants
        path_constants = PathConstants()
        config_file = path_constants.GOOGLE_DRIVE_DATA_DIR / "connection_check_config.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
            return config.get("duration_threshold", 20)
        else:
            return 20  # Default for testing (user can change to 20 for production)
    
    def should_wait_for_remount(self):
        """Check if we should wait for remount before executing commands"""
        import json
        from .path_constants import PathConstants
        path_constants = PathConstants()
        flag_file = path_constants.GOOGLE_DRIVE_DATA_DIR / "remount_required.flag"
        
        if flag_file.exists():
            try:
                with open(flag_file, 'r') as f:
                    flag_data = json.load(f)
                reason = flag_data.get('reason', 'Unknown reason')
                set_at = flag_data.get('set_at', 'Unknown time')
                self._log_remount_trigger(reason, set_at)
            except Exception:
                self._log_remount_trigger("Flag file exists but unreadable", "Unknown")
            return True
        
        return False
    
    
    def _set_remount_required_flag(self, reason="Unknown error detected in previous command execution"):
        """Set flag indicating remount is required before next command"""
        try:
            import time
            import json
            import os
            from .path_constants import PathConstants
            
            path_constants = PathConstants()
            flag_file = path_constants.GOOGLE_DRIVE_DATA_DIR / "remount_required.flag"
            
            flag_data = {
                "created": time.time(),
                "reason": reason,
                "set_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            os.makedirs(flag_file.parent, exist_ok=True)
            with open(flag_file, 'w') as f:
                json.dump(flag_data, f, indent=2)
                
        except Exception as e:
            print(f"Warning: Failed to set remount required flag: {e}")
    
    def _clear_remount_required_flag(self):
        """Clear the remount required flag (called after successful remount)"""
        try:
            from .path_constants import PathConstants
            path_constants = PathConstants()
            flag_file = path_constants.GOOGLE_DRIVE_DATA_DIR / "remount_required.flag"
            
            if flag_file.exists():
                flag_file.unlink()
        except Exception as e:
            print(f"Warning: Failed to clear remount required flag: {e}")
    
    
    def _log_remount_call(self, trigger_function, reason):
        """记录remount调用的上下文信息"""
        try:
            import json
            import traceback
            import inspect
            from datetime import datetime
            from pathlib import Path
            
            # 获取调用栈信息
            call_stack = traceback.format_stack()[:-1]  # 排除当前方法
            
            # 获取直接调用者信息
            caller_frame = inspect.currentframe().f_back  # 获取调用者信息
            caller_info = {
                "function": caller_frame.f_code.co_name,
                "filename": caller_frame.f_code.co_filename.split('/')[-1],
                "line_number": caller_frame.f_lineno
            }
            
            # 获取调用链（最近的5层）
            call_chain = []
            frame = caller_frame
            for i in range(5):
                if frame is None:
                    break
                call_chain.append({
                    "function": frame.f_code.co_name,
                    "filename": frame.f_code.co_filename.split('/')[-1],
                    "line_number": frame.f_lineno
                })
                frame = frame.f_back
            
            # 创建log记录
            log_record = {
                "timestamp": datetime.now().isoformat(),
                "trigger_function": trigger_function,
                "reason": reason,
                "caller_info": caller_info,
                "call_chain": call_chain,
                "call_stack_summary": [line.strip() for line in call_stack[-3:]],
                "source": "CommandExecutor"
            }
            
            # 保存到临时变量，等待结果后一起写入
            self._pending_remount_log = log_record
            
        except Exception as e:
            pass  # 静默处理log错误，不影响主流程
    
    def _log_remount_result(self, returncode, stdout, stderr):
        """记录remount结果"""
        try:
            from pathlib import Path
            import json
            
            if not hasattr(self, '_pending_remount_log'):
                return
            
            # 添加结果信息
            self._pending_remount_log.update({
                "remount_returncode": returncode,
                "remount_output": stdout[:500] if stdout else None,
                "remount_error": stderr[:500] if stderr else None,
                "remount_success": returncode == 0
            })
            
            # 写入log文件
            log_file = Path.home() / ".local/bin/GOOGLE_DRIVE_DATA/auto_remount_log.json"
            log_file.parent.mkdir(exist_ok=True)
            
            # 读取现有log
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    existing_logs = json.load(f)
                if not isinstance(existing_logs, list):
                    existing_logs = [existing_logs]
            except (FileNotFoundError, json.JSONDecodeError):
                existing_logs = []
            
            # 添加新记录
            existing_logs.append(self._pending_remount_log)
            
            # 写入文件
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(existing_logs, f, indent=2, ensure_ascii=False)
            
            # 清理临时变量
            delattr(self, '_pending_remount_log')
            
        except Exception as e:
            pass  # 静默处理log错误，不影响主流程
    
    def _wait_for_remount_completion(self):
        """等待remount完成（如果需要的话）"""
        try:
            from .remount_lock_manager import get_remount_lock_manager
            
            lock_manager = get_remount_lock_manager()
            
            # 使用锁管理器等待remount完成（无超时限制）
            lock_manager.wait_for_remount_completion(max_wait_seconds=None)
                
        except Exception as e:
            # 静默处理等待错误，不影响命令执行
            pass
    
    def _log_remount_trigger(self, reason, set_at):
        """记录remount触发信息到log文件"""
        try:
            from pathlib import Path
            import json
            from datetime import datetime
            
            # 写入log文件
            log_file = Path.home() / ".local/bin/GOOGLE_DRIVE_DATA/auto_remount_log.json"
            log_file.parent.mkdir(exist_ok=True)
            
            # 创建触发记录
            trigger_record = {
                "timestamp": datetime.now().isoformat(),
                "event_type": "remount_triggered",
                "reason": reason,
                "flag_set_at": set_at,
                "source": "CommandExecutor.should_wait_for_remount"
            }
            
            # 读取现有log
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    existing_logs = json.load(f)
                if not isinstance(existing_logs, list):
                    existing_logs = [existing_logs]
            except (FileNotFoundError, json.JSONDecodeError):
                existing_logs = []
            
            # 添加新记录
            existing_logs.append(trigger_record)
            
            # 写入文件
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(existing_logs, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            pass  # 静默处理log错误，不影响主流程
    
    def add_connection_check_to_command(self, remote_command, result_filename, cmd_hash=None):
        """
        Add Connection Check to the end of a remote command
        
        Args:
            remote_command (str): Original remote command
            result_filename (str): Expected result filename
            cmd_hash (str, optional): Command hash to display in Connection Check
            
        Returns:
            str: Command with Connection Check appended
        """
        try:
            # Get cached tmp ID
            tmp_id = self.get_cached_path_id("~/tmp")
            if not tmp_id:
                return remote_command
            
            # Create Connection Check instance
            connection_check = create_connection_check_instance(self.main_instance)
            
            # Generate Connection Check code
            template_code = connection_check.generate_template(
                result_filename=result_filename,
                tmp_folder_id=tmp_id,
                interval_seconds=1,
                command_hash=cmd_hash
            )
            
            if not template_code:
                # If template generation failed, return original command
                return remote_command
            
            # Append Connection Check to the command
            enhanced_command = f"{remote_command}\n\n{template_code}"
            
            return enhanced_command
            
        except Exception as e:
            print(f"Warning: Failed to add Connection Check: {e}")
            return remote_command

    def execute_command(self, remote_command, result_filename, cmd_hash, raw_command=None, capture_result=True):
        """
        执行远程命令接口 - 只负责执行已生成的远程命令

        Args:
            remote_command (str): 已生成的远程命令脚本
            result_filename (str): 结果文件名
            cmd_hash (str): 命令hash
            raw_command (str, optional): 原始用户命令（用于debug输出）
            capture_result (bool): 是否捕获并下载结果JSON文件（默认True）

        Returns:
            dict: 执行结果
        """
        try:
            # 确保~/tmp的ID已被解析和缓存
            self.ensure_tmp_id_cached()
            
            # 检查是否需要添加Connection Check
            if self.should_add_connection_check():
                remote_command = self.add_connection_check_to_command(remote_command, result_filename, cmd_hash)
            
            # 显示远程窗口
            window_result = self.show_remote_command_window(cmd=remote_command, cmd_hash=cmd_hash, user_command=raw_command)
            
            # 处理窗口结果
            if window_result["action"] == "success":
                # 如果不需要捕获结果，点击"执行完成"后直接返回，不等待结果JSON
                if not capture_result:
                    return {
                    "success": True,
                    "action": "success",
                    "data": {
                        "message": "Command executed without result capture",
                        "source": "unified_command",
                        "capture_result": False
                    },
                    "source": "unified_command"
                }
            
                # 否则等待并读取结果文件
                from .progress_manager import start_progress_buffering, stop_progress_buffering
                start_progress_buffering("⏳ Waiting for result ...")
                try:
                    result = self.main_instance.result_processor.wait_and_read_result_file(result_filename)
                finally:
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
                    # 尝试从多个位置获取错误信息
                    error_msg = result.get("error", "")
                    if not error_msg:
                        # 尝试从data.error获取
                        data = result.get('data', {})
                        error_msg = data.get('error', '')
                    
                    return {
                        "success": False,
                        "action": "execution_failed",
                        "data": {
                            "error": error_msg,
                            "source": "unified_command"
                        },
                        "error": error_msg  # 保持顶级error字段，确保google_drive_shell.py能获取到
                    }
                    
            elif window_result["action"] == "direct_feedback":
                print()  # 换行
                # 如果不捕获结果，不传递result_filename（避免等待结果文件）
                filename_to_pass = None if not capture_result else result_filename
                return self.direct_feedback_interface(remote_command, filename_to_pass)
                
            elif window_result["action"] == "copy":
                return {
                    "success": True,
                    "action": "copy",
                    "data": {
                        "message": "Command copied to clipboard",
                        "source": "unified_command"
                    }
                }
            
            # 处理interrupted和window_closed情况
            if window_result["action"] == "interrupted":
                return {
                    "success": False,
                    "error": "Command interrupted by user (Ctrl+C)",
                    "interrupted": True
                }
            
            if window_result["action"] == "window_closed":
                return {
                    "success": False,
                    "error": "Window closed by user",
                    "interrupted": True
                }
            
            # 对于其他情况（timeout, cancel, failure, error），直接返回原始结果
            # 让上层处理错误并显示完整traceback
            return window_result
        
        except KeyboardInterrupt:
            return {
                "success": False,
                "error": "Command interrupted by user (Ctrl+C)",
                "interrupted": True
            }

    def execute_command_interface(self, cmd, args=None, _skip_queue_management=False, original_user_command=None, capture_result=True):
        """
        统一远端命令执行接口 - 处理除特殊命令外的所有命令

        Args:
            cmd (str): 命令名称或完整命令字符串
            args (list, optional): 命令参数。如果为None，cmd被视为完整命令字符串
            _skip_queue_management (bool): 是否跳过队列管理（避免双重管理）
            original_user_command (str, optional): 原始用户命令，用于保持hash一致性
            capture_result (bool): 是否捕获并下载结果JSON文件（默认True）

        Returns:
            dict: 执行结果，包含stdout、stderr、path等字段
        """
        # 检查是否需要remount（基于flag文件）
        should_wait = self.should_wait_for_remount()
        if should_wait: 
            try:
                from .window_manager import get_window_manager
                window_manager = get_window_manager()
                window_manager.check_and_handle_remount()
            except Exception as e:
                return {"success": False, "error": f"Remount required but failed: {e}"}
        
        # 调试代码已移除
        # 特殊命令保护已移除 - 现在有raw command功能，允许所有命令通过窗口执行
        
        # 如果args为None，说明cmd已经是完整命令字符串
        if args is None:
            cleaned_args = []
        else:
            cleaned_args = args

        # 调试日志已禁用
        # 导入正确的远程窗口队列管理器并生成唯一的窗口ID
        import time

        # 设置时间戳基准点（如果还没有设置的话）
        if not hasattr(self, '_debug_start_time'):
            self._debug_start_time = time.time()

        # 如果提供了原始用户命令，优先使用它（用于保持hash一致性）
        if original_user_command:
            cmd = original_user_command
        elif args is None:
            # args为None时，cmd已经是完整命令字符串，直接使用
            pass
        elif cleaned_args:
            import shlex
            cmd = f"{cmd} {' '.join(shlex.quote(str(arg)) for arg in cleaned_args)}"
        else:
            cmd = cmd
            
        current_shell = self.main_instance.get_current_shell()
        remote_command, result_filename, cmd_hash = self.main_instance.command_generator.generate_command(cmd, None, current_shell, capture_result=capture_result)

        # 执行远程命令
        result = self.execute_command(
            remote_command=remote_command,
            result_filename=result_filename,
            cmd_hash=cmd_hash,
            raw_command=cmd,
            capture_result=capture_result
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
        # 检查是否需要remount（基于flag文件）
        should_wait = self.should_wait_for_remount()
        
        if should_wait:
            # 需要remount，触发窗口管理器处理
            try:
                from .window_manager import get_window_manager
                window_manager = get_window_manager()
                window_manager.check_and_handle_remount()
            except Exception as e:
                print(f"Error: Remount required but failed: {e}")
                return 1
        
        # 在执行特殊命令前检查是否需要等待remount完成
        self._wait_for_remount_completion()
        
        command = self.main_instance.command_registry.get_command(name)
        if command is None:
            print(f"Error: Unknown command '{name}'")
            return 1
        
        # 直接使用原始参数，不进行 JSON 处理
        if not command.validate_args(args):
            return 1
        return command.execute(name, args, **kwargs)


    def show_remote_command_window(self, cmd, timeout_seconds=3600, test_mode=False, is_priority=False, cmd_hash=None, user_command=None):
        # 调试窗口弹出次数
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
        # 确保tmp目录存在（如果整个~/tmp被删除，需要重新创建）
        tmp_dir = \\\"{self.main_instance.REMOTE_ROOT}/tmp\\\"
        os.makedirs(tmp_dir, exist_ok=True)
        
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
        enhanced_cmd = mount_check_header + cmd + "\nfi"
        from .window_manager import get_window_manager
        
        # 获取窗口管理器并请求窗口
        window_manager = get_window_manager()
        
        # 使用传入的cmd_hash
        result = window_manager.request_window(enhanced_cmd, cmd_hash, timeout_seconds, no_direct_feedback=test_mode, is_priority=is_priority, user_command=user_command)
        return result
                
    def direct_feedback(self, remote_command, debug_info=None):
        """
        直接反馈功能 - 粘贴远端命令和用户反馈，用=分割
        使用统一的get_multiline_user_input方法
        """
        # 先输出debug信息（如果有的话）
        if debug_info:
            print(f"Debug information:")
            print(debug_info)
            print(f"=" * 20)  # 20个等号分割线

        # 然后粘贴生成的远端指令
        print(f"Generated remote command:")
        print(remote_command)
        print(f"=" * 20)  # 50个等号分割线

        # 使用PYTHON_PROJ/python3 subprocess调用USERINPUT，避免系统Python的tkinter问题
        try:
            import re
            import subprocess
            import pathlib
            
            # 从remote_command中提取实际的用户命令
            user_command_match = re.search(r'bash << \'USER_COMMAND_EOF\' > "\$OUTPUT_FILE" 2> "\$ERROR_FILE"\n(.*?)\nUSER_COMMAND_EOF', remote_command, re.DOTALL)
            if user_command_match:
                clean_context = user_command_match.group(1).strip()
            else:
                clean_context = "GDS command"
            
            # 动态构造路径
            current_file_dir = pathlib.Path(__file__).parent.parent  # 从modules/command_executor.py回到GOOGLE_DRIVE_PROJ
            base_dir = current_file_dir.parent  # 回到包含GOOGLE_DRIVE.py的目录
            project_name = base_dir.name
            title = f"{project_name} - Agent Mode [GDS: {clean_context}]"
            python_exec = str(base_dir / 'PYTHON_PROJ' / 'python3')
            userinput_path = str(base_dir / 'USERINPUT.py')
            
            # 构造命令参数
            cmd_args = [python_exec, userinput_path, '--timeout', '180']
            if title and 'GDS:' in title:
                # 提取GDS命令作为ID
                gds_cmd = title.split('[GDS: ')[-1].rstrip(']')
                # 简化ID，移除特殊字符
                gds_cmd_safe = gds_cmd.replace("'", '').replace('"', '')
                cmd_args.extend(['--id', f'GDS: {gds_cmd_safe}'])
            
            # 运行USERINPUT
            result = subprocess.run(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=200
            )
            
            if result.returncode == 0 and result.stdout:
                full_output = result.stdout.strip()
            else:
                full_output = f"USERINPUT subprocess failed: returncode={result.returncode}, stderr={result.stderr}"
            print(f"[DEBUG] get_user_input_tkinter returned: {repr(full_output)}")
            print(f"[DEBUG] Return type: {type(full_output)}")
            
            # 确保返回字符串
            if full_output is None:
                full_output = ""
            
            # 移除末尾的提示信息（如果存在）
            if "任务完成后，执行终端命令" in full_output:
                full_output = full_output.split("任务完成后，执行终端命令")[0].strip()
                
        except Exception as e:
            print(f"USERINPUT interface failed: {e}")
            full_output = f"Error: Unable to get user input via USERINPUT interface: {e}"

        # 检查是否成功获取到输出
        if full_output is None:
            return {
                "cmd": "direct_feedback_failed",
                "stdout": "",
                "stderr": "Failed to get user input via USERINPUT interface",
                "exit_code": 1,
                "source": "direct_feedback_error"
            }

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
        # 先输出debug信息（如果有的话）
        if debug_info:
            print(f"Debug information:")
            print(debug_info)
            print(f"=" * 20)  # 20个等号分割线

        # 然后粘贴生成的远端指令
        print(f"Generated remote command:")
        print(remote_command)
        print(f"=" * 20)  # 50个等号分割线

        # 使用PYTHON_PROJ/python3 subprocess调用USERINPUT，避免系统Python的tkinter问题
        try:
            import re
            import subprocess
            import pathlib
            
            # 从remote_command中提取实际的用户命令
            user_command_match = re.search(r'bash << \'USER_COMMAND_EOF\' > "\$OUTPUT_FILE" 2> "\$ERROR_FILE"\n(.*?)\nUSER_COMMAND_EOF', remote_command, re.DOTALL)
            if user_command_match:
                clean_context = user_command_match.group(1).strip()
            else:
                clean_context = "GDS command"
            
            # 动态构造路径
            current_file_dir = pathlib.Path(__file__).parent.parent  # 从modules/command_executor.py回到GOOGLE_DRIVE_PROJ
            base_dir = current_file_dir.parent  # 回到包含GOOGLE_DRIVE.py的目录
            project_name = base_dir.name
            title = f"{project_name} - Agent Mode [GDS: {clean_context}]"
            python_exec = str(base_dir / 'PYTHON_PROJ' / 'python3')
            userinput_path = str(base_dir / 'USERINPUT.py')
            
            # 构造命令参数
            cmd_args = [python_exec, userinput_path, '--timeout', '180']
            if title and 'GDS:' in title:
                # 提取GDS命令作为ID
                gds_cmd = title.split('[GDS: ')[-1].rstrip(']')
                # 简化ID，移除特殊字符
                gds_cmd_safe = gds_cmd.replace("'", '').replace('"', '')
                cmd_args.extend(['--id', f'GDS: {gds_cmd_safe}'])
            
            # 运行USERINPUT
            result = subprocess.run(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=200
            )
            
            if result.returncode == 0 and result.stdout:
                full_output = result.stdout.strip()
            else:
                full_output = f"USERINPUT subprocess failed: returncode={result.returncode}, stderr={result.stderr}"
            
            # 确保返回字符串
            if full_output is None:
                full_output = ""
            
            # 移除末尾的提示信息（如果存在）
            if "任务完成后，执行终端命令" in full_output:
                full_output = full_output.split("任务完成后，执行终端命令")[0].strip()
            
            # 显示用户反馈
            print(f"User feedback: {full_output}")
            
            # 处理用户输入，构造direct feedback结果
            error_keywords = ['error', 'Error', 'ERROR', 'exception', 'Exception', 'EXCEPTION', 
                             'traceback', 'Traceback', 'TRACEBACK', 'failed', 'Failed', 'FAILED']
            
            has_error = any(keyword in full_output for keyword in error_keywords)
            
            if has_error:
                stdout_content = ""
                stderr_content = full_output
                exit_code = 1
            else:
                stdout_content = full_output
                stderr_content = ""
                exit_code = 0

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
            
        except Exception as e:
            print(f"Failed to get user feedback: {e}")
            feedback_result = {
                "success": False,
                "action": "direct_feedback",
                "data": {
                    "working_dir": "error",
                    "timestamp": "error", 
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": f"Failed to get user input: {e}",
                    "source": "direct_feedback"
                }
            }

        # 添加分隔符
        print()
        print(f"=" * 20)

        # 如果提供了result_filename，尝试等待并读取实际的执行结果
        if result_filename:
            try:
                # 开始进度显示
                from .progress_manager import start_progress_buffering, stop_progress_buffering
                start_progress_buffering("⏳ Waiting for result ...")
                try:
                    # 等待并读取结果文件
                    actual_result = self.main_instance.result_processor.wait_and_read_result_file(result_filename)
                finally:
                    # 确保停止进度显示
                    stop_progress_buffering()

                if actual_result.get("success", False):
                    actual_data = actual_result.get("data", {})
                    actual_stderr = actual_data.get("stderr", "").strip()

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
                    print(f"Could not get actual execution result. ")

            except Exception as e:
                print(f"Error waiting for actual result: {e}")

        return {
            "success": True,
            "action": "direct_feedback_no_result",
            "data": {},
            "source": "direct_feedback_interface_no_capture"
        }

    def get_multiline_user_input(self, prompt, is_single_line=False, timeout_seconds=180, prompt_same_line=False, command_context=None):
        """
        获取用户的多行输入 - 直接使用USERINPUT tkinter GUI接口
        
        Args:
            prompt (str): 输入提示
            is_single_line (bool): 是否单行输入（保留兼容性，实际不使用）
            timeout_seconds (int): 超时时间（秒），默认180秒
            prompt_same_line (bool): 是否在同一行显示提示符（保留兼容性，实际不使用）
            command_context (str): 命令上下文，用作USERINPUT的ID
            
        Returns:
            str: 用户输入的多行内容
        """
        
        print(f"[DEBUG] get_multiline_user_input called!")
        print(f"[DEBUG] prompt: {prompt}")
        print(f"[DEBUG] command_context length: {len(command_context) if command_context else 0}")
        
        try:
            import sys
            import os
            import pathlib
            
            print(f"[DEBUG] Starting USERINPUT integration...")
            
            # 动态获取项目根目录
            project_root = pathlib.Path(__file__).parent.parent.parent.absolute()
            userinput_dir = str(project_root)
            if userinput_dir not in sys.path:
                sys.path.insert(0, userinput_dir)
            
            print(f"[DEBUG] Importing USERINPUT module...")
            # 导入USERINPUT模块
            import importlib.util
            userinput_py = project_root / "USERINPUT.py"
            spec = importlib.util.spec_from_file_location("userinput_module", str(userinput_py))
            userinput_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(userinput_module)
            
            print(f"[DEBUG] USERINPUT module imported successfully")
            
            # 构造窗口标题
            title = None
            if command_context:
                # 清理命令上下文，只保留主要部分
                clean_context = command_context.replace('GDS ', '').strip()
                if len(clean_context) > 50:
                    clean_context = clean_context[:47] + "..."
                # 获取项目名并添加自定义ID
                project_name, _, _ = userinput_module.get_project_name()
                title = f"{project_name} - Agent Mode [{clean_context}]"
                
            print(f"[DEBUG] Window title: {title}")
            
            # 显示提示信息（在USERINPUT窗口之外）
            if prompt and not prompt_same_line:
                print(prompt)
            
            print(f"[DEBUG] About to call get_user_input_tkinter...")
            # 直接调用get_user_input_tkinter函数
            user_input = userinput_module.get_user_input_tkinter(
                title=title,
                timeout=timeout_seconds,
                max_retries=3
            )
            
            print(f"[DEBUG] get_user_input_tkinter returned: {user_input}")
            print(f"[DEBUG] user_input type: {type(user_input)}")
            print(f"[DEBUG] user_input length: {len(user_input) if user_input else 0}")
            
            if user_input:
                # 移除末尾的提示信息（如果存在）
                if "任务完成后，执行终端命令" in user_input:
                    user_input = user_input.split("任务完成后，执行终端命令")[0].strip()
                print(f"[DEBUG] Returning cleaned user input: {len(user_input)} chars")
                return user_input
            else:
                print(f"[DEBUG] No user input received, returning empty string")
                return ""
                
        except Exception as e:
            print(f"[DEBUG] Exception in USERINPUT interface: {e}")
            import traceback
            traceback.print_exc()
            # 如果USERINPUT接口失败，返回错误信息
            return f"Error: Unable to get user input via USERINPUT interface: {e}"
