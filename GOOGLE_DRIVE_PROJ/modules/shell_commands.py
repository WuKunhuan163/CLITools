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
    from .remote_commands import HOME_URL
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
# 使用统一路径常量
try:
    from .path_constants import path_constants
    HOME_URL = path_constants.HOME_URL
    HOME_FOLDER_ID = path_constants.get_folder_id("HOME_FOLDER_ID")
    REMOTE_ROOT_FOLDER_ID = path_constants.get_folder_id("REMOTE_ROOT_FOLDER_ID")
except ImportError:
    # 回退到硬编码值
    HOME_URL = "https://drive.google.com/drive/u/0/my-drive"
    HOME_FOLDER_ID = "root"
    REMOTE_ROOT_FOLDER_ID = "1LSndouoVj8pkoyi-yTYnC4Uv03I77T8f"



def _shell_ls_fallback(path, command_identifier, current_shell):
    """Fallback ls implementation using the old method"""
    try:
        # 确定要列出的文件夹ID
        if path is None or path == ".":
            # 列出当前目录
            target_folder_id = current_shell.get("current_folder_id", REMOTE_ROOT_FOLDER_ID)
            display_path = current_shell.get("current_path", "~")
        elif path == "~":
            # 列出根目录
            target_folder_id = REMOTE_ROOT_FOLDER_ID
            display_path = "~"
        else:
            # 实现基本路径解析，支持文件路径
            try:
                # 首先尝试作为目录解析
                target_folder_id, display_path = resolve_path(path, current_shell)
                
                if not target_folder_id:
                    # 如果作为目录解析失败，尝试作为文件路径解析
                    file_info = resolve_file_path(path, current_shell)
                    if file_info:
                        # 这是一个文件路径，直接显示文件信息
                        if file_info['mimeType'] == 'application/vnd.google-apps.folder':
                            print(f"{file_info['name']}/")
                        else:
                            print(f"{file_info['name']}")
                        
                        if is_run_environment(command_identifier):
                            write_to_json_output({
                                "success": True,
                                "path": path,
                                "files": [file_info] if file_info['mimeType'] != 'application/vnd.google-apps.folder' else [],
                                "folders": [file_info] if file_info['mimeType'] == 'application/vnd.google-apps.folder' else [],
                                "count": 1
                            }, command_identifier)
                        return 0
                    else:
                        error_msg = f"Path not found: {path}"
                        if is_run_environment(command_identifier):
                            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
                        else:
                            print(error_msg)
                        return 1
            except Exception as e:
                error_msg = f"Path resolution failed: {path} ({e})"
                if is_run_environment(command_identifier):
                    write_to_json_output({"success": False, "error": error_msg}, command_identifier)
                else:
                    print(error_msg)
                return 1
        
        # 使用API列出文件
        import sys
        api_service_path = Path(__file__).parent.parent / "google_drive_api.py"
        sys.path.insert(0, str(api_service_path.parent))
        from google_drive_api import GoogleDriveService #type: ignore
        
        # 创建服务实例
        drive_service = GoogleDriveService()
        
        # 列出文件
        result = drive_service.list_files(folder_id=target_folder_id, max_results=None)
        
        if result['success']:
            files = result['files']
            
            if is_run_environment(command_identifier):
                # RUN环境下返回JSON
                write_to_json_output({
                    "success": True,
                    "path": display_path,
                    "folder_id": target_folder_id,
                    "files": files,
                    "count": len(files)
                }, command_identifier)
            else:
                # 直接执行时显示bash风格的列表
                if not files:
                    # 目录为空时不显示任何内容，就像bash一样
                    pass
                else:
                    # 按名称排序，文件夹优先
                    folders = sorted([f for f in files if f['mimeType'] == 'application/vnd.google-apps.folder'], 
                                   key=lambda x: x['name'].lower())
                    other_files = sorted([f for f in files if f['mimeType'] != 'application/vnd.google-apps.folder'], 
                                       key=lambda x: x['name'].lower())
                    
                    # 合并列表，文件夹在前
                    all_items = folders + other_files
                    
                    # 简单的列表格式，类似bash ls
                    for item in all_items:
                        name = item['name']
                        if item['mimeType'] == 'application/vnd.google-apps.folder':
                            # 文件夹用不同颜色或标记（这里用简单文本）
                            print(f"{name}/")
                        else:
                            print(name)
            
            return 0
        else:
            error_msg = f"Failed to list files: {result['error']}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"Error executing ls command: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

# resolve_path函数已移动到path_resolver.py中
# 旧的使用resolve_path的函数应该被重构或删除

def resolve_relative_path(relative_path, base_folder_id, base_path):
    """解析相对路径"""
    try:
        if not relative_path:
            return base_folder_id, base_path
        
        # 导入API服务
        import sys
        api_service_path = Path(__file__).parent.parent / "google_drive_api.py"
        if not api_service_path.exists():
            return None, None
        
        sys.path.insert(0, str(api_service_path.parent))
        from google_drive_api import GoogleDriveService #type: ignore
        
        drive_service = GoogleDriveService()
        
        # 分割路径
        path_parts = relative_path.split("/")
        current_id = base_folder_id
        current_logical_path = base_path
        
        for part in path_parts:
            if not part:  # 跳过空部分
                continue
            
            # 处理特殊路径组件
            if part == "..":
                # 父目录
                parent_id, parent_path = resolve_parent_directory(current_id, current_logical_path)
                if parent_id is None:
                    return None, None  # 没有父目录
                current_id = parent_id
                current_logical_path = parent_path
                continue
            elif part == ".":
                # 当前目录，跳过
                continue
            
            # 在当前目录中查找这个名称的文件夹
            files_result = drive_service.list_files(folder_id=current_id, max_results=100)
            if not files_result['success']:
                return None, None
            
            # 查找匹配的文件夹
            found_folder = None
            for file in files_result['files']:
                if file['name'] == part and file['mimeType'] == 'application/vnd.google-apps.folder':
                    found_folder = file
                    break
            
            if not found_folder:
                return None, None  # 路径不存在
            
            # 更新当前位置
            current_id = found_folder['id']
            if current_logical_path == "~":
                current_logical_path = f"~/{part}"
            else:
                current_logical_path = f"{current_logical_path}/{part}"
        
        return current_id, current_logical_path
        
    except Exception as e:
        print(f"Error resolving relative path: {e}")
        return None, None

def resolve_file_path(file_path, current_shell):
    """解析文件路径，返回文件信息（如果存在）"""
    try:
        # 分离目录和文件名
        if "/" in file_path:
            dir_path = "/".join(file_path.split("/")[:-1])
            filename = file_path.split("/")[-1]
        else:
            # 相对于当前目录
            dir_path = "."
            filename = file_path
        
        # 解析目录路径
        if dir_path == ".":
            parent_folder_id = current_shell.get("current_folder_id", REMOTE_ROOT_FOLDER_ID)
        else:
            parent_folder_id, _ = resolve_path(dir_path, current_shell)
            if not parent_folder_id:
                return None
        
        # 导入API服务
        import sys
        api_service_path = Path(__file__).parent.parent / "google_drive_api.py"
        if not api_service_path.exists():
            return None
        
        sys.path.insert(0, str(api_service_path.parent))
        from google_drive_api import GoogleDriveService #type: ignore
        
        drive_service = GoogleDriveService()
        
        # 在父目录中查找文件
        result = drive_service.list_files(folder_id=parent_folder_id, max_results=100)
        if not result['success']:
            return None
        
        for file in result['files']:
            if file['name'] == filename:
                return file
        
        return None
        
    except Exception as e:
        print(f"Error resolving file path: {e}")
        return None
        
def resolve_parent_directory(folder_id, current_path):
    """解析父目录"""
    try:
        if current_path == "~":
            return None, None  # 已经在根目录
        
        # 导入API服务
        import sys
        api_service_path = Path(__file__).parent.parent / "google_drive_api.py"
        if not api_service_path.exists():
            return None, None
        
        sys.path.insert(0, str(api_service_path.parent))
        from google_drive_api import GoogleDriveService #type: ignore
        
        drive_service = GoogleDriveService()
        
        # 获取当前文件夹的父目录
        folder_info = drive_service.service.files().get(
            fileId=folder_id,
            fields="parents"
        ).execute()
        
        parents = folder_info.get('parents', [])
        if not parents:
            return None, None
        
        parent_id = parents[0]
        
        # 计算父目录的逻辑路径
        if current_path.count('/') == 1:  # ~/folder -> ~
            parent_path = "~"
        else:
            parent_path = '/'.join(current_path.split('/')[:-1])
        
        return parent_id, parent_path
        
    except Exception as e:
        print(f"Error resolving parent directory: {e}")
        return None, None

def open_dir(path, command_identifier=None):
    """打开目录 - 相当于创建shell + cd"""
    try:
        current_shell = get_current_shell()
        
        # 如果已经有活跃shell，直接cd
        if current_shell:
            return shell_cd(path, command_identifier)
        
        # 没有活跃shell，先创建一个
        import time
        shell_id = generate_shell_id()
        shell_name = f"shell_{shell_id[:8]}"
        created_time = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # 解析目标路径
        temp_shell = {
            "current_path": "~",
            "current_folder_id": REMOTE_ROOT_FOLDER_ID
        }
        
        target_id, target_path = resolve_path(path, temp_shell)
        if not target_id:
            error_msg = f"Directory not found: {path}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        # 创建shell配置，直接定位到目标目录
        shell_config = {
            "id": shell_id,
            "name": shell_name,
            "folder_id": REMOTE_ROOT_FOLDER_ID,  # 根目录ID
            "current_path": target_path,  # 当前逻辑路径设为目标路径
            "current_folder_id": target_id,  # 当前所在的Google Drive文件夹ID
            "created_time": created_time,
            "last_accessed": created_time,
            "status": "active"
        }
        
        # 保存shell
        shells_data = load_shells()
        shells_data["shells"][shell_id] = shell_config
        shells_data["active_shell"] = shell_id
        
        if save_shells(shells_data):
            success_msg = f"Created shell and opened directory: {target_path}"
            result_data = {
                "success": True,
                "message": success_msg,
                "shell_id": shell_id,
                "shell_name": shell_name,
                "path": target_path,
                "folder_id": target_id
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(result_data, command_identifier)
            else:
                print(success_msg)
                print(f"🆔 Shell ID: {shell_id}")
            return 0
        else:
            error_msg = "Failed to save shell configuration"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"Error executing open-dir command: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

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

def shell_help(command_identifier=None):
    """显示帮助信息"""
    try:
        from .help_system import show_unified_help
        return show_unified_help(context="shell", command_identifier=command_identifier)
    except ImportError:
        try:
            from help_system import show_unified_help
            return show_unified_help(context="shell", command_identifier=command_identifier)
        except ImportError:
            # Fallback to basic help if help_system is not available
            basic_help = """pwd                         - show current directory
ls [path] [--detailed] [-R] - list directory contents (recursive with -R)
mkdir [-p] <dir>             - create directory (recursive with -p)
cd <path>                    - change directory
rm <file>                    - remove file
rm -rf <dir>                 - remove directory recursively
echo <text>                  - display text
cat <file>                   - display file contents
help                         - show available commands
exit                         - exit shell mode"""
            
            if is_run_environment(command_identifier):
                write_to_json_output({"success": True, "help": basic_help}, command_identifier)
            else:
                print(basic_help)
            
            return 0

def _split_pipe_command_with_quotes(shell_cmd):
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
        pipe_parts = _split_pipe_command_with_quotes(shell_cmd)
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

def _execute_pipe_command(cmd, input_text, shell, command_identifier=None):
    """执行pipe命令的具体实现"""
    try:
        cmd_parts = cmd.split()
        if not cmd_parts:
            return 1
            
        cmd_name = cmd_parts[0]
        
        if cmd_name == 'grep':
            # 实现简单的grep功能
            if len(cmd_parts) < 2:
                if not is_run_environment(command_identifier):
                    print(f"grep: missing pattern")
                return 1
            
            pattern = cmd_parts[1]
            lines = input_text.split('\n')
            matched_lines = [line for line in lines if pattern in line]
            
            if not is_run_environment(command_identifier):
                for line in matched_lines:
                    print(line)
            return 0
            
        elif cmd_name == 'head':
            # 实现简单的head功能
            n_lines = 10  # 默认显示10行
            if len(cmd_parts) >= 3 and cmd_parts[1] == '-n':
                try:
                    n_lines = int(cmd_parts[2])
                except ValueError:
                    n_lines = 10
            elif len(cmd_parts) >= 2 and cmd_parts[1].startswith('-'):
                try:
                    n_lines = int(cmd_parts[1][1:])
                except ValueError:
                    n_lines = 10
            
            lines = input_text.split('\n')
            head_lines = lines[:n_lines]
            
            if not is_run_environment(command_identifier):
                for line in head_lines:
                    print(line)
            return 0
            
        elif cmd_name == 'tail':
            # 实现简单的tail功能
            n_lines = 10  # 默认显示10行
            if len(cmd_parts) >= 3 and cmd_parts[1] == '-n':
                try:
                    n_lines = int(cmd_parts[2])
                except ValueError:
                    n_lines = 10
            elif len(cmd_parts) >= 2 and cmd_parts[1].startswith('-'):
                try:
                    n_lines = int(cmd_parts[1][1:])
                except ValueError:
                    n_lines = 10
            
            lines = input_text.split('\n')
            tail_lines = lines[-n_lines:] if len(lines) >= n_lines else lines
            
            if not is_run_environment(command_identifier):
                for line in tail_lines:
                    print(line)
            return 0
            
        elif cmd_name == 'sort':
            # 实现简单的sort功能
            lines = input_text.split('\n')
            sorted_lines = sorted(lines)
            
            if not is_run_environment(command_identifier):
                for line in sorted_lines:
                    print(line)
            return 0
            
        elif cmd_name == 'uniq':
            # 实现简单的uniq功能
            lines = input_text.split('\n')
            unique_lines = []
            for line in lines:
                if not unique_lines or unique_lines[-1] != line:
                    unique_lines.append(line)
            
            if not is_run_environment(command_identifier):
                for line in unique_lines:
                    print(line)
            return 0
        else:
            # 不支持的pipe命令
            if not is_run_environment(command_identifier):
                print(f"Pipe command '{cmd_name}' not supported")
            return 1
            
    except Exception as e:
        if not is_run_environment(command_identifier):
            print(f"Error executing pipe command '{cmd}': {e}")
        return 1

def handle_single_command(shell_cmd, command_identifier=None):
    """处理单个命令"""
    try:
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
        
        return shell.execute_shell_command(shell_cmd, command_identifier)
        
    except Exception as e:
        error_msg = f"Error executing command: {e}"
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
                result = shell.execute_command_interface("bash", ["-c", compound_cmd])
                if isinstance(result, dict):
                    # 显示输出
                    if result.get("stdout"):
                        if not is_run_environment(command_identifier):
                            print(result["stdout"], end="")
                    if result.get("stderr"):
                        if not is_run_environment(command_identifier):
                            print(result["stderr"], end="", file=sys.stderr)
                    return result.get("exit_code", 0)
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

def shell_ls_with_id(folder_id, detailed=False, command_identifier=None):
    """列出指定文件夹ID的文件和文件夹"""
    try:
        # 使用API列出文件
        import sys
        api_service_path = Path(__file__).parent.parent / "google_drive_api.py"
        if not api_service_path.exists():
            error_msg = "API service file not found, please run GOOGLE_DRIVE --console-setup"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        sys.path.insert(0, str(api_service_path.parent))
        from google_drive_api import GoogleDriveService #type: ignore
        
        # 创建服务实例
        drive_service = GoogleDriveService()
        
        # 列出文件
        result = drive_service.list_files(folder_id=folder_id, max_results=None)
        
        if result['success']:
            files = result['files']
            
            if detailed:
                # 详细模式：返回JSON格式
                result_data = {
                    "success": True,
                    "folder_id": folder_id,
                    "files": files,
                    "mode": "detailed"
                }
                
                if is_run_environment(command_identifier):
                    write_to_json_output(result_data, command_identifier)
                else:
                    import json
                    print(json.dumps(result_data, indent=2, ensure_ascii=False))
            else:
                # 简洁模式：bash风格输出
                if is_run_environment(command_identifier):
                    result_data = {
                        "success": True,
                        "folder_id": folder_id,
                        "files": files,
                        "mode": "bash"
                    }
                    write_to_json_output(result_data, command_identifier)
                else:
                    # 分离文件夹和文件
                    folders = [f for f in files if f['mimeType'] == 'application/vnd.google-apps.folder']
                    non_folders = [f for f in files if f['mimeType'] != 'application/vnd.google-apps.folder']
                    
                    all_items = []
                    
                    # 添加目录（带/后缀）
                    for folder in folders:
                        all_items.append(f"{folder['name']}/")
                    
                    # 添加文件
                    for file in non_folders:
                        # 跳过隐藏文件
                        if not file['name'].startswith('.'):
                            all_items.append(file['name'])
                    
                    # 输出
                    if all_items:
                        # 计算终端宽度，默认80字符
                        import shutil
                        try:
                            terminal_width = shutil.get_terminal_size().columns
                        except:
                            terminal_width = 80
                        
                        # 如果文件名很长，使用垂直布局
                        max_item_length = max(len(item) for item in all_items) if all_items else 0
                        
                        if max_item_length > 30 or len(all_items) <= 3:
                            # 长文件名或文件数量少时，每行一个
                            for item in all_items:
                                print(item)
                        else:
                            # 短文件名时，使用列布局
                            col_width = min(max(15, max_item_length + 2), 30)
                            items_per_line = max(1, terminal_width // col_width)
                            
                            # 按行显示
                            for i in range(0, len(all_items), items_per_line):
                                line_items = all_items[i:i + items_per_line]
                                formatted_line = []
                                
                                for item in line_items:
                                    if len(item) <= col_width - 2:
                                        formatted_line.append(f"{item:<{col_width}}")
                                    else:
                                        truncated = f"{item[:col_width-5]}..."
                                        formatted_line.append(f"{truncated:<{col_width}}")
                                
                                print(f"".join(formatted_line).rstrip())
            
            return 0
        else:
            error_msg = f"Failed to list files: {result['error']}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"Error executing ls command: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1
