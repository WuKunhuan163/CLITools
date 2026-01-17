#!/usr/bin/env python3
"""
统一的错误处理和traceback系统

提供增强的异常捕获和错误报告功能，
能够捕获最底层的错误并提供详细的调试信息。
"""

import traceback
import sys, json
import os, re, inspect
from typing import Optional, Dict, Any, List
from datetime import datetime


class EnhancedErrorHandler:
    """增强的错误处理器"""
    
    def __init__(self, debug_mode: bool = True):
        self.debug_mode = debug_mode
    
    @staticmethod
    def convert_ls_error_to_command_format(ls_result, command_name):
        """Convert ls error format to specific command format for bash alignment
        
        Args:
            ls_result (dict): Result from ls command with error
            command_name (str): Name of the command that called ls (e.g., 'cd', 'touch')
            
        Returns:
            dict: Modified result with command-specific error format
        """
        if not ls_result.get('success'):
            ls_error = ls_result.get('error', '')
            if ls_error.startswith('ls:'):
                # Extract the path from the ls error message
                # Format: "ls: path: No such file or directory"
                match = re.search(r"ls: ([^:]+): (.+)", ls_error)
                if match:
                    path = match.group(1)
                    error_msg = match.group(2)
                    # Format like bash: "command: no such file or directory: path"
                    command_error = f"{command_name}: {error_msg.lower()}: {path}"
                    ls_result['error'] = command_error
                else:
                    # Fallback to simple replacement
                    command_error = ls_error.replace('ls:', f'{command_name}:', 1)
                    ls_result['error'] = command_error
        return ls_result
    
    def setup_error_logging(self):
        """设置错误日志"""
        try:
            from .path_constants import get_data_dir
            log_dir = get_data_dir()
            self.error_log_file = log_dir / "error_log.txt"
        except Exception:
            # 如果设置失败，使用None
            self.error_log_file = None
    
    def capture_exception(self, 
            context: str = "Unknown", 
            exception: Optional[Exception] = None,
            additional_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        捕获并分析异常，返回详细的错误信息
        
        Args:
            context: 错误发生的上下文描述
            exception: 要分析的异常对象，如果为None则获取当前异常
            additional_info: 额外的调试信息
            
        Returns:
            Dict: 包含详细错误信息的字典
        """
        try:
            # 获取异常信息
            if exception is None:
                exc_type, exc_value, exc_traceback = sys.exc_info()
            else:
                exc_type = type(exception)
                exc_value = exception
                exc_traceback = exception.__traceback__
            
            if exc_type is None:
                return {
                    "success": False,
                    "error": "No exception to capture",
                    "context": context
                }
            
            # 构建详细的错误信息
            error_info = {
                "success": False,
                "context": context,
                "exception_type": exc_type.__name__,
                "exception_message": str(exc_value),
                "traceback_summary": self.get_traceback_summary(exc_traceback),
                "full_traceback": self.get_full_traceback(exc_traceback),
                "root_cause": self.find_root_cause(exc_traceback),
                "stack_frames": self.analyze_stack_frames(exc_traceback),
                "timestamp": self.get_timestamp()
            }
            
            # 添加额外信息
            if additional_info:
                error_info["additional_info"] = additional_info
            
            # 记录到日志
            self.log_error(error_info)
            
            # 如果是调试模式，打印详细信息
            if self.debug_mode:
                self.print_debug_info(error_info)
            
            return error_info
            
        except Exception as capture_error:
            # 异常捕获本身出错，返回基本信息
            return {
                "success": False,
                "error": f"Error capturing exception: {capture_error}",
                "context": context,
                "original_exception": str(exception) if exception else "Unknown"
            }
    
    def get_traceback_summary(self, tb) -> List[str]:
        """获取traceback摘要"""
        try:
            return traceback.format_tb(tb, limit=10)
        except Exception:
            return ["Failed to get traceback summary"]
    
    def get_full_traceback(self, tb) -> str:
        """获取完整的traceback"""
        try:
            return ''.join(traceback.format_tb(tb))
        except Exception:
            return "Failed to get full traceback"
    
    def find_root_cause(self, tb) -> Dict[str, Any]:
        """找到根本原因（最底层的异常）"""
        try:
            frames = []
            current_tb = tb
            
            while current_tb is not None:
                frame = current_tb.tb_frame
                frames.append({
                    "filename": frame.f_code.co_filename,
                    "function": frame.f_code.co_name,
                    "line_number": current_tb.tb_lineno,
                    "local_vars": self.safeget_locals(frame),
                    "code_context": self.get_code_context(frame.f_code.co_filename, current_tb.tb_lineno)
                })
                current_tb = current_tb.tb_next
            
            # 最后一个frame通常是根本原因
            if frames:
                root_frame = frames[-1]
                return {
                    "location": f"{root_frame['filename']}:{root_frame['line_number']}",
                    "function": root_frame['function'],
                    "code_context": root_frame['code_context'],
                    "local_variables": root_frame['local_vars']
                }
            
            return {"error": "No frames found"}
            
        except Exception as e:
            return {"error": f"Failed to find root cause: {e}"}
    
    def analyze_stack_frames(self, tb) -> List[Dict[str, Any]]:
        """分析所有栈帧，包括完整的调用栈"""
        frames = []
            
        # 首先获取完整的调用栈（从当前位置到顶层）
        current_stack = inspect.stack()
        
        # 过滤掉错误处理相关的栈帧，只保留用户代码的调用栈
        filtered_stack = []
        for frame_info in current_stack:
            filename = frame_info.filename
            function_name = frame_info.function
            
            # 跳过错误处理系统本身的栈帧
            if (function_name in ['capture_exception', 'analyze_stack_frames', 'print_debug_info', 
                                'capture_and_report_error'] or 
                'error_handler.py' in filename):
                continue
            
            filtered_stack.append({
                "filename": os.path.basename(filename),
                "full_path": filename,
                "function": function_name,
                "line_number": frame_info.lineno,
                "is_user_code": self.is_user_code(filename),
                "source": "current_stack"
            })
        
        # 反转栈帧顺序，使其从顶层到底层
        filtered_stack.reverse()
        
        # 然后添加异常traceback中的栈帧
        current_tb = tb
        while current_tb is not None:
            frame = current_tb.tb_frame
            frame_info = {
                "filename": os.path.basename(frame.f_code.co_filename),
                "full_path": frame.f_code.co_filename,
                "function": frame.f_code.co_name,
                "line_number": current_tb.tb_lineno,
                "is_user_code": self.is_user_code(frame.f_code.co_filename),
                "source": "exception_traceback"
            }
            
            # 只为用户代码添加详细信息
            if frame_info["is_user_code"]:
                frame_info["code_context"] = self.get_code_context(
                    frame.f_code.co_filename, current_tb.tb_lineno
                )
                frame_info["local_vars"] = self.safeget_locals(frame)
            
            frames.append(frame_info)
            current_tb = current_tb.tb_next
        
        # 合并调用栈和异常traceback，去重
        all_frames = filtered_stack + frames
        
        # 去重：如果同一个函数在同一行出现多次，只保留一个
        unique_frames = []
        seen = set()
        for frame in all_frames:
            key = (frame["full_path"], frame["line_number"], frame["function"])
            if key not in seen:
                seen.add(key)
                unique_frames.append(frame)
        
        return unique_frames
    
    def safeget_locals(self, frame) -> Dict[str, str]:
        """安全地获取局部变量"""
        try:
            locals_dict = {}
            for key, value in frame.f_locals.items():
                try:
                    # 只保留简单类型的变量，避免复杂对象
                    if isinstance(value, (str, int, float, bool, type(None))):
                        locals_dict[key] = str(value)
                    elif isinstance(value, (list, tuple, dict)):
                        # 限制集合类型的长度
                        str_value = str(value)
                        if len(str_value) > 200:
                            locals_dict[key] = str_value[:200] + "..."
                        else:
                            locals_dict[key] = str_value
                    else:
                        locals_dict[key] = f"<{type(value).__name__}>"
                except Exception:
                    locals_dict[key] = "<unable to represent>"
            
            return locals_dict
            
        except Exception:
            return {"error": "Failed to get local variables"}
    
    def get_code_context(self, filename: str, line_number: int, context_lines: int = 3) -> Dict[str, Any]:
        """获取代码上下文"""
        try:
            if not os.path.exists(filename):
                return {"error": "File not found"}
            
            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            start_line = max(0, line_number - context_lines - 1)
            end_line = min(len(lines), line_number + context_lines)
            
            context = {}
            for i in range(start_line, end_line):
                line_num = i + 1
                is_error_line = line_num == line_number
                context[line_num] = {
                    "code": lines[i].rstrip(),
                    "is_error_line": is_error_line
                }
            
            return context
            
        except Exception as e:
            return {"error": f"Failed to get code context: {e}"}
    
    def is_user_code(self, filename: str) -> bool:
        """判断是否为用户代码"""
        try:
            # 检查是否在项目目录中
            project_indicators = [
                "GOOGLE_DRIVE_PROJ",
                "GOOGLE_DRIVE_DATA", 
                "_UNITTEST",
                "/.local/bin/",
                "GOOGLE_DRIVE.py"  # 包含顶层入口文件
            ]
            
            # 排除系统库和Python标准库
            system_excludes = [
                "/usr/lib/python",
                "/usr/local/lib/python",
                "site-packages",
                "<frozen",
                "<built-in",
                "threading.py",
                "subprocess.py"
            ]
            
            # 如果是系统代码，返回False
            if any(exclude in filename for exclude in system_excludes):
                return False
            
            # 如果是项目代码，返回True
            return any(indicator in filename for indicator in project_indicators)
            
        except Exception:
            return False
    
    def get_timestamp(self) -> str:
        """获取时间戳"""
        try:
            return datetime.datetime.now().isoformat()
        except Exception:
            return "Unknown"
    
    def log_error(self, error_info: Dict[str, Any]):
        """记录错误到日志文件"""
        if not hasattr(self, 'error_log_file') or not self.error_log_file:
            return
        
        try:
            with open(self.error_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(error_info, indent=2, ensure_ascii=False))
                f.write("\n" + "="*80 + "\n")
        except Exception:
            pass  # 忽略日志记录错误
    
    def print_debug_info(self, error_info: Dict[str, Any]):
        """打印调试信息"""
        try:
            print(f"Error Report - {error_info['context']}")
            print(f"{error_info['exception_type']}: {error_info['exception_message']}")
            
            if "root_cause" in error_info and "location" in error_info["root_cause"]:
                root = error_info["root_cause"]
                print(f"Root Cause: {root['location']} in {root['function']}()")
                
                if "code_context" in root and isinstance(root["code_context"], dict):
                    print("Code Context:")
                    for line_num, line_info in root["code_context"].items():
                        marker = ">>> " if line_info["is_error_line"] else "    "
                        print(f"{marker}{line_num}: {line_info['code']}")
            
            # 显示完整的调用栈
            all_frames = error_info.get("stack_frames", [])
            if all_frames:
                print("\nComplete Call Stack:")
                for i, frame in enumerate(all_frames, 1):
                    print(f"  {i:2d}. {frame['filename']}:{frame['line_number']} in {frame['function']}()")
                    
                    # 如果是用户代码且有代码上下文，显示关键行
                    if frame.get("is_user_code") and "code_context" in frame:
                        context = frame["code_context"]
                        if isinstance(context, dict):
                            # 只显示错误行
                            for line_num, line_info in context.items():
                                if line_info.get("is_error_line"):
                                    code_line = line_info["code"].strip()
                                    if code_line:  # 只显示非空行
                                        print(f"      >>> {code_line}")
                                    break
            
            # # 额外显示简化的用户代码栈（向后兼容）
            # user_frames = [f for f in all_frames if f.get("is_user_code")]
            # if user_frames:
            #     print("\nUser Code Stack:")
            #     for frame in user_frames:
            #         print(f"  {frame['filename']}:{frame['line_number']} in {frame['function']}()")
            
        except Exception:
            print(f"\nError in {error_info.get('context', 'Unknown')}: {error_info.get('exception_message', 'Unknown error')}")


# 全局错误处理器实例
error_handler = EnhancedErrorHandler()


def capture_and_report_error(context: str = "Unknown", 
                           exception: Optional[Exception] = None,
                           additional_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    便捷函数：捕获并报告错误
    
    Args:
        context: 错误上下文
        exception: 异常对象
        additional_info: 额外信息
        
    Returns:
        Dict: 错误信息
    """
    return error_handler.capture_exception(context, exception, additional_info)

if __name__ == '__main__':
    def test_function():
        x = "test"
        return x.nonexistent_method()
    try:
        test_function()
    except Exception as e:
        error_info = capture_and_report_error("Test Error", e)
        print("\nError captured successfully!")
