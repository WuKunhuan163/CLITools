#!/usr/bin/env python3
"""
Google Drive - Shell Commands Module
从GOOGLE_DRIVE.py重构而来的shell_commands模块
"""

import os
import sys
import json
import webbrowser
import hashlib
import subprocess
import time
import uuid
import warnings
from pathlib import Path
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')
from dotenv import load_dotenv
load_dotenv()

# GoogleDriveShell will be imported when needed to avoid circular import

# 导入需要的函数
try:
    HOME_URL = "https://drive.google.com/drive/my-drive"  # 直接定义常量
except ImportError:
    HOME_URL = "https://drive.google.com/drive/u/0/my-drive"

# 使用统一的shell管理系统
def get_current_shell():
    """获取当前shell，使用统一的GoogleDriveShell实例"""
    try:
        # 动态导入避免循环导入
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from google_drive_shell import GoogleDriveShell
        
        shell = GoogleDriveShell()
        return shell.get_current_shell()
    except Exception as e:
        print(f"Failed to get current shell: {e}")
        return None

# 导入Google Drive Shell管理类 - 注释掉避免循环导入
# try:
#     from google_drive_shell import GoogleDriveShell
# except ImportError as e:
#     print(f"Failed to import Google Drive Shell: {e}")
#     GoogleDriveShell = None

# 添加缺失的工具函数
def is_run_environment(command_identifier=None):
    """Check if running in RUN environment by checking environment variables"""
    if command_identifier:
        return os.environ.get(f'RUN_IDENTIFIER_{command_identifier}') == 'True'
    return False

def write_to_json_output(data, command_identifier=None):
    """将结果写入到指定的 JSON 输出文件中"""
    if not is_run_environment(command_identifier):
        return False
    
    # Get the specific output file for this command identifier
    if command_identifier:
        output_file = os.environ.get(f'RUN_DATA_FILE_{command_identifier}')
    else:
        output_file = os.environ.get('RUN_DATA_FILE')
    
    if not output_file:
        return False
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"写入JSON输出文件失败: {e}")
        return False

# 全局常量
from .path_constants import path_constants
HOME_URL = path_constants.HOME_URL
HOME_FOLDER_ID = path_constants.get_folder_id("HOME_FOLDER_ID")
REMOTE_ROOT_FOLDER_ID = path_constants.get_folder_id("REMOTE_ROOT_FOLDER_ID")

def shell_pwd(command_identifier=None):
    """显示当前远程逻辑地址"""
    try:
        current_shell = get_current_shell()
        
        if not current_shell:
            error_msg = "No active remote shell, please create or switch to a shell"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        current_path = current_shell.get("current_path", "~")
        
        result_data = {
            "success": True,
            "current_path": current_path,
            "shell_id": current_shell["id"],
            "shell_name": current_shell["name"],
            "home_url": HOME_URL
        }
        
        if is_run_environment(command_identifier):
            write_to_json_output(result_data, command_identifier)
        else:
            print(current_path)
        
        return 0
        
    except Exception as e:
        error_msg = f"Error getting current path: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def split_pipe_command(shell_cmd):
    """
    正确分割管道命令，考虑引号内的管道符号
    
    Args:
        shell_cmd (str): 要分割的shell命令
        
    Returns:
        list: 分割后的命令部分
    """
    parts = []
    current_part = ""
    in_single_quote = False
    in_double_quote = False
    i = 0
    
    while i < len(shell_cmd):
        char = shell_cmd[i]
        
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            current_part += char
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            current_part += char
        elif char == '|' and not in_single_quote and not in_double_quote:
            # 这是一个管道符号（不管前后是否有空格）
            parts.append(current_part.strip())
            current_part = ""
            # 跳过管道符号后的空格（如果有的话）
            if i + 1 < len(shell_cmd) and shell_cmd[i + 1] == ' ':
                i += 1
        else:
            current_part += char
        
        i += 1
    
    if current_part.strip():
        parts.append(current_part.strip())
    
    return parts

def handle_pipe_commands(shell_cmd, command_identifier=None):
    """处理用|连接的pipe命令 - 修复版本：直接在远程执行整个pipe命令"""
    try:
        # 解析pipe命令：支持 | 操作符，但要正确处理引号
        pipe_parts = split_pipe_command(shell_cmd)
        if len(pipe_parts) < 2:
            # 不是pipe命令，返回特殊值表示需要其他处理
            return None
        
        # 获取GoogleDriveShell实例来执行命令
        try:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from google_drive_shell import GoogleDriveShell
            
            shell = GoogleDriveShell()
        except Exception as e:
            error_msg = f"Failed to get GoogleDriveShell instance: {e}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1

        # 修复：直接将整个pipe命令作为远程命令执行，而不是本地模拟
        # 这样可以确保pipe操作在远程shell中正确执行
        try:
            # 获取当前shell信息
            current_shell = shell.get_current_shell()
            if not current_shell:
                error_msg = "No active shell found for pipe command execution"
                if is_run_environment(command_identifier):
                    write_to_json_output({"success": False, "error": error_msg}, command_identifier)
                else:
                    print(error_msg)
                return 1
            
            # 使用远程命令执行接口直接执行整个pipe命令
            result = shell.execute_command_interface("bash", ["-c", shell_cmd])
            
            if isinstance(result, dict):
                # 显示输出 - 处理嵌套的数据结构
                if result.get("success") and "data" in result:
                    # 新的嵌套结构
                    data = result["data"]
                    stdout = data.get("stdout", "")
                    stderr = data.get("stderr", "")
                    exit_code = data.get("exit_code", 0)
                else:
                    # 旧的平坦结构
                    stdout = result.get("stdout", "")
                    stderr = result.get("stderr", "")
                    exit_code = result.get("exit_code", 0)
                
                if stdout:
                    if not is_run_environment(command_identifier):
                        print(stdout, end="")
                    elif is_run_environment(command_identifier):
                        # 在RUN环境下，将输出写入JSON
                        write_to_json_output({
                            "success": True,
                            "stdout": stdout,
                            "stderr": stderr,
                            "exit_code": exit_code
                        }, command_identifier)
                        return exit_code
                        
                if stderr:
                    if not is_run_environment(command_identifier):
                        import sys
                        print(stderr, end="", file=sys.stderr)
                        
                return exit_code
            else: 
                return result if isinstance(result, int) else 0
                
        except Exception as e:
            error_msg = f"Error executing pipe command remotely: {e}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
    except Exception as e:
        error_msg = f"Error executing pipe commands: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(f"{error_msg}")
        return 1

def handle_multiple_commands(shell_cmd, command_identifier=None, shell_instance=None):
    """处理多个用&&、||或|连接的shell命令 - 使用统一的命令解析接口"""
    try:
        # 首先检查是否包含pipe操作符（带空格或不带空格）
        if ' | ' in shell_cmd or '|' in shell_cmd:
            pipe_result = handle_pipe_commands(shell_cmd, command_identifier)
            if pipe_result is not None:
                return pipe_result
            # 如果handle_pipe_commands返回None，说明不是真正的管道命令，继续处理
        
        # 使用统一的命令解析接口
        import sys
        import os
        current_dir = os.path.dirname(__file__)
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        from command_parser import parse_command
        
        # 解析命令
        parse_result = parse_command(shell_cmd)
        
        if not parse_result['is_compound']:
            # 单个命令，不应该到这里，但为了安全起见
            commands_with_operators = [(shell_cmd.strip(), None)]
        else:
            # 转换为原有格式以保持兼容性
            commands_with_operators = []
            for cmd_info in parse_result['commands']:
                commands_with_operators.append((cmd_info['command'], cmd_info['operator']))
        
        # 获取GoogleDriveShell实例来执行命令
        if shell_instance:
            shell = shell_instance
        else:
            try:
                import sys
                import os
                sys.path.append(os.path.dirname(os.path.dirname(__file__)))
                from google_drive_shell import GoogleDriveShell
                
                shell = GoogleDriveShell()
            except Exception as e:
                error_msg = f"Failed to get GoogleDriveShell instance: {e}"
                if is_run_environment(command_identifier):
                    write_to_json_output({"success": False, "error": error_msg}, command_identifier)
                else:
                    print(error_msg)
                return 1
        
        # 执行命令
        results = []
        last_result = 0
        
        # 检查是否所有命令都可以作为一个复合远程命令执行
        # 这样可以避免目录状态不一致的问题
        can_execute_as_compound = True
        contains_cd = False
        for cmd, operator in commands_with_operators:
            # 如果包含需要本地处理的命令，不能作为复合命令执行
            cmd_parts = cmd.split()
            if cmd_parts and cmd_parts[0] in ['help', 'exit', 'quit', 'shells', 'switch']:
                can_execute_as_compound = False
                break
            # 如果包含cd命令，需要特殊处理以更新shell状态
            if cmd_parts and cmd_parts[0] == 'cd':
                contains_cd = True
        
        if can_execute_as_compound and len(commands_with_operators) > 1 and not contains_cd:
            # 作为复合命令执行，重建原始命令字符串
            rebuilt_cmd = []
            for i, (cmd, operator) in enumerate(commands_with_operators):
                if i > 0 and operator:
                    rebuilt_cmd.append(f" {operator} ")
                rebuilt_cmd.append(cmd)
            compound_cmd = ''.join(rebuilt_cmd)
            
            # 直接使用远程命令执行复合命令，避免递归
            try:
                # 直接调用远程命令执行，绕过shell命令解析
                current_shell = get_current_shell()
                if not current_shell:
                    error_msg = "No active shell found"
                    if is_run_environment(command_identifier):
                        write_to_json_output({"success": False, "error": error_msg}, command_identifier)
                    else:
                        print(error_msg)
                    return 1
                
                # 使用远程命令模块直接执行
                # 传递原始命令以保持hash一致性
                result = shell.execute_command_interface("bash", ["-c", compound_cmd], _original_user_command=shell_cmd)
                if isinstance(result, dict):
                    # 显示输出 - 处理嵌套的数据结构
                    data = result.get("data", {})
                    stdout = data.get("stdout", "") or result.get("stdout", "")
                    stderr = data.get("stderr", "") or result.get("stderr", "")
                    exit_code = data.get("exit_code", result.get("exit_code", 0))
                    
                    if stdout:
                        if not is_run_environment(command_identifier):
                            print(stdout, end="")
                    if stderr:
                        if not is_run_environment(command_identifier):
                            print(stderr, end="", file=sys.stderr)
                    return exit_code
                else:
                    return result if isinstance(result, int) else 0
            except Exception as e:
                error_msg = f"Error executing compound command: {e}"
                if is_run_environment(command_identifier):
                    write_to_json_output({"success": False, "error": error_msg}, command_identifier)
                else:
                    print(error_msg)
                return 1
        
        # 否则，逐个执行命令（原有逻辑）
        for i, (cmd, operator) in enumerate(commands_with_operators):
            if not cmd:
                continue
            
            # 根据操作符决定是否执行当前命令
            should_execute = True
            
            if operator == '&&':
                # && 操作符：只有前一个命令成功才执行
                should_execute = (last_result == 0)
            elif operator == '||':
                # || 操作符：只有前一个命令失败才执行
                should_execute = (last_result != 0)
            
            if should_execute:
                try:
                    result = shell.execute_shell_command(cmd, command_identifier)
                    if isinstance(result, dict):
                        if result.get("success", True):
                            last_result = 0
                        else:
                            last_result = 1
                    elif isinstance(result, int):
                        last_result = result
                    else:
                        # 默认认为失败
                        last_result = 1
                        
                except Exception as e:
                    if not is_run_environment(command_identifier):
                        print(f"Error executing command: {e}")
                    last_result = 1
            else:
                # 跳过命令
                if not is_run_environment(command_identifier):
                    if operator == '&&':
                        print(f"\n- Skipped command {i+1}/{len(commands_with_operators)} (previous command failed): {cmd}")
                    elif operator == '||':
                        print(f"\n- Skipped command {i+1}/{len(commands_with_operators)} (previous command succeeded): {cmd}")
            
            results.append(last_result)
        
        # 返回最后一个命令的结果
        final_result = last_result if results else 0
        return final_result
        
    except Exception as e:
        error_msg = f"Error executing multiple commands: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(f"{error_msg}")
        return 1
