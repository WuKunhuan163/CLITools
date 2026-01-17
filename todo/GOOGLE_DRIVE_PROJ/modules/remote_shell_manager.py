#!/usr/bin/env python3
"""
Google Drive - Remote Shell Manager Module
从GOOGLE_DRIVE.py重构而来的remote_shell_manager模块
"""

import json
import hashlib
import time
import uuid
from pathlib import Path

import warnings
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')
from dotenv import load_dotenv
load_dotenv()

# 全局常量
# 使用统一路径常量
from .path_constants import path_constants
HOME_URL = path_constants.HOME_URL
REMOTE_ROOT_FOLDER_ID = path_constants.get_folder_id("REMOTE_ROOT_FOLDER_ID")

class RemoteShellManager:
    """远程Shell管理器类"""
    
    def __init__(self, drive_service=None, main_instance=None):
        """初始化RemoteShellManager
        
        Args:
            drive_service: Google Drive API服务实例
            main_instance: 主实例引用（通常是GoogleDriveShell实例）
        """
        self.drive_service = drive_service
        self.main_instance = main_instance

    def get_shells_file(self):
        """获取远程shell配置文件路径 - 与GoogleDriveShell保持一致"""
        bin_dir = Path(__file__).parent.parent.parent
        data_dir = bin_dir / "GOOGLE_DRIVE_DATA"
        data_dir.mkdir(exist_ok=True)
        return data_dir / "shells.json"

    def load_shells(self):
        """加载远程shell配置"""
        shells_file = self.get_shells_file()
        if shells_file.exists():
            try:
                with open(shells_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"shells": {}, "active_shell": None}

    def save_shells(self, shells_data):
        """保存远程shell配置"""
        shells_file = self.get_shells_file()
        try:
            with open(shells_file, 'w', encoding='utf-8') as f:
                json.dump(shells_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Warning: Save remote shell config failed: {e}")
            return False

    def generate_shell_id(self):
        """生成shell标识符"""
        timestamp = str(int(time.time()))
        random_uuid = str(uuid.uuid4())
        combined = f"{timestamp}_{random_uuid}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def create_shell(self, name=None, folder_id=None, command_identifier=None):
        """创建远程shell"""
        try:
            # 生成shell ID
            shell_id = self.generate_shell_id()
            
            # 获取当前时间
            created_time = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # 如果没有提供名称，使用默认名称
            if not name:
                name = f"shell_{shell_id[:8]}"
            
            # 改进的shell配置，简化结构并添加虚拟环境支持
            shell_config = {
                "id": shell_id,
                "name": name,
                "current_path": "~",  # 当前逻辑路径
                "current_folder_id": REMOTE_ROOT_FOLDER_ID,  # 当前所在的Google Drive文件夹ID
                "created_time": created_time,
                "last_accessed": created_time,
                "venv_state": {
                    "active_env": None,  # 当前激活的虚拟环境名称
                    "pythonpath": "/env/python"  # 当前PYTHONPATH
                }
            }
            
            # 加载现有shells
            shells_data = self.load_shells()
            
            # 添加新shell
            shells_data["shells"][shell_id] = shell_config
            
            # 如果这是第一个shell，设为活跃shell
            if not shells_data["active_shell"]:
                shells_data["active_shell"] = shell_id
            
            # 保存配置
            if self.save_shells(shells_data):
                success_msg = f"Remote shell created successfully"
                
                print(success_msg)
                print(f"Shell ID: {shell_id}")
                print(f"Shell name: {name}")
                print(f"Folder ID: {folder_id or 'root'}")
                print(f"Created time: {created_time}")
                return 0
            else:
                error_msg = "Error: Save remote shell config failed"
                print(error_msg)
                return 1
        except Exception as e:
            error_msg = f"Error: Create remote shell failed: {e}"
            print(error_msg)
            return 1

    def list_shells(self, command_identifier=None):
        """列出所有远程shell"""
        try:
            shells_data = self.load_shells()
            shells = shells_data["shells"]
            active_shell = shells_data["active_shell"]
            
            if not shells:
                no_shells_msg = "No remote shells found"
                print(no_shells_msg)
                return 0
            
            print(f"Total {len(shells)} shells:")
            for shell_id, shell_config in shells.items():
                is_active = "*" if shell_id == active_shell else " "
                print(f"{is_active} {shell_config['name']} (ID: {shell_id})")
            
            return 0
            
        except Exception as e:
            error_msg = f"Error listing remote shells: {e}"
            print(error_msg)
            return 1

    def terminate_shell(self, shell_id, command_identifier=None):
        """终止指定的远程shell"""
        try:
            shells_data = self.load_shells()
            
            if shell_id not in shells_data["shells"]:
                error_msg = f"Cannot find shell ID: {shell_id}"
                print(error_msg)
                return 1
            
            shell_config = shells_data["shells"][shell_id]
            shell_name = shell_config['name']
            
            # 删除shell
            del shells_data["shells"][shell_id]
            
            # 如果删除的是活跃shell，需要选择新的活跃shell
            if shells_data["active_shell"] == shell_id:
                if shells_data["shells"]:
                    # 选择最新的shell作为活跃shell
                    latest_shell = max(shells_data["shells"].items(), 
                                    key=lambda x: x[1]["last_accessed"])
                    shells_data["active_shell"] = latest_shell[0]
                else:
                    shells_data["active_shell"] = None
            
            # 保存配置
            if self.save_shells(shells_data):
                print(f"Shell ID deleted: {shell_id}")
                return 0
            else:
                error_msg = "Failed to save shell configuration"
                print(error_msg)
                return 1
                
        except Exception as e:
            error_msg = f"Error terminating remote shell: {e}"
            print(error_msg)
            return 1

    def checkout_shell(self, shell_id, command_identifier=None):
        """切换到指定的远程shell"""
        try:
            shells_data = self.load_shells()
            
            if shell_id not in shells_data["shells"]:
                error_msg = f"Cannot find shell ID: {shell_id}"
                print(error_msg)
                return 1
            
            shell_config = shells_data["shells"][shell_id]
            shell_name = shell_config['name']
            
            # 更新活跃shell
            shells_data["active_shell"] = shell_id
            
            # 更新最后访问时间
            from datetime import datetime
            shells_data["shells"][shell_id]["last_accessed"] = datetime.now().isoformat()
            
            # 保存配置
            if self.save_shells(shells_data):
                print(f"Switched to shell: {shell_name} ({shell_id})")
                return 0
            else:
                error_msg = "Failed to save shell configuration"
                print(error_msg)
                return 1
                
        except Exception as e:
            error_msg = f"Error checking out remote shell: {e}"
            print(error_msg)
            return 1

    def exit_shell(self, command_identifier=None):
        """退出当前的远程shell"""
        try:
            current_shell = self.get_current_shell()
            
            if not current_shell:
                error_msg = "Error: No active remote shell"
                print(error_msg)
                return 1
            
            # 清除活跃shell
            shells_data = self.load_shells()
            shells_data["active_shell"] = None
            
            if self.save_shells(shells_data):
                success_msg = f"Exited remote shell: {current_shell['name']}"
                print(success_msg)
                return 0
            else:
                error_msg = "Error: Save shell state failed"
                print(error_msg)
                return 1
                
        except Exception as e:
            error_msg = f"Error: {e}"  # 简化错误消息，让上层error handler处理
            print(error_msg)
            return 1

    def get_current_shell(self):
        """获取当前活跃的shell"""
        shells_data = self.load_shells()
        active_shell_id = shells_data.get("active_shell")
        
        if not active_shell_id or active_shell_id not in shells_data["shells"]:
            return None
        
        return shells_data["shells"][active_shell_id]

    def detect_active_venv(self):
        """使用统一的venv --current接口检测当前激活的虚拟环境"""
        try:
            import sys
            import os
            import subprocess
            
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            
            # 使用统一的venv --current接口
            from pathlib import Path
            result = subprocess.run(
                [sys.executable, str(Path(__file__).parent.parent / "GOOGLE_DRIVE.py"), 
                "--shell", "venv --current"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                output = result.stdout
                # 解析输出中的环境名称
                for line in output.split('\n'):
                    if line.startswith("Current virtual environment:"):
                        env_name = line.split(":")[1].strip()
                        return env_name if env_name != "None" else None
            
            return None
        except Exception:
            return None

    def update_shell_venv_state(self, current_shell, active_env):
        """更新shell状态中的虚拟环境信息"""
        try:
            shells_data = self.load_shells()
            shell_id = current_shell['id']
            
            if shell_id in shells_data["shells"]:
                # 确保venv_state字段存在
                if "venv_state" not in shells_data["shells"][shell_id]:
                    shells_data["shells"][shell_id]["venv_state"] = {}
                
                shells_data["shells"][shell_id]["venv_state"]["active_env"] = active_env
                shells_data["shells"][shell_id]["last_accessed"] = time.strftime("%Y-%m-%d %H:%M:%S")
                
                self.save_shells(shells_data)
        except Exception:
            pass  # 如果更新失败，不影响shell正常运行

    def _initialize_default_path_ids(self):
        """初始化默认的REMOTE_ROOT和REMOTE_ENV路径ID配置"""
        try:
            import json
            import os
            import time
            
            from .path_constants import PathConstants
            path_constants = PathConstants()
            config_path = str(path_constants.GDS_PATH_IDS_FILE)
            
            # 加载或创建配置文件
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
            else:
                config = {"path_ids": {}, "last_updated": None}
            
            # 检查是否需要初始化默认ID
            needs_update = False
            
            # 初始化REMOTE_ROOT的ID（~路径）
            if "~" not in config["path_ids"]:
                from ..google_drive_shell import GoogleDriveShell
                shell = GoogleDriveShell()
                config["path_ids"]["~"] = shell.REMOTE_ROOT_FOLDER_ID
                needs_update = True
                # print(f"Initialized default ~ path ID: {shell.REMOTE_ROOT_FOLDER_ID}")
            
            # 初始化REMOTE_ENV的ID（@路径）
            if "@" not in config["path_ids"]:
                from ..google_drive_shell import GoogleDriveShell
                shell = GoogleDriveShell()
                config["path_ids"]["@"] = shell.REMOTE_ENV_FOLDER_ID
                needs_update = True
                # print(f"Initialized default @ path ID: {shell.REMOTE_ENV_FOLDER_ID}")
            
            # 如果有更新，保存配置文件
            if needs_update:
                config["last_updated"] = time.time()
                with open(config_path, 'w') as f:
                    json.dump(config, f, indent=2)
                # print(f"Default path IDs saved to {config_path}")
                
        except Exception as e:
            # 初始化失败不影响shell正常运行
            print(f"Warning: Failed to initialize default path IDs: {e}")

    def enter_shell_mode(self, command_identifier=None):
        """进入交互式shell模式"""
        try:
            # 初始化默认路径ID配置
            self._initialize_default_path_ids()
            
            current_shell = self.get_current_shell()
            
            if not current_shell:
                # 如果没有活跃shell，创建一个默认的
                print(f"No active remote shell, creating default shell...")
                create_result = self.create_shell("default_shell", None, None)
                if create_result != 0:
                    error_msg = "Error: Failed to create default shell"
                    print(error_msg)
                    return 1
                current_shell = self.get_current_shell()
            
            # 在直接执行模式下，启动交互式shell
            import sys
                
                # 检测是否是管道输入模式，如果是则禁用direct feedback
                is_pipe_mode = not sys.stdin.isatty()
                if is_pipe_mode:
                    # 获取GoogleDriveShell实例来设置no_direct_feedback标志
                    try:
                        from ..google_drive_shell import GoogleDriveShell
                        shell_instance = GoogleDriveShell()
                        if hasattr(shell_instance, 'command_executor'):
                            shell_instance.command_executor._no_direct_feedback = True
                    except:
                        pass  # 如果获取失败，不影响shell运行
                
                print(f"Enter 'help' to view available commands, enter 'exit' to exit")
                
                while True:
                    try:
                        # 获取当前shell状态（可能在循环中被更新）
                        current_shell = self.get_current_shell()
                        
                        # 显示提示符，包括虚拟环境和当前路径
                        current_path = current_shell.get("current_path", "~")
                        
                        # 检查是否有激活的虚拟环境
                        venv_prefix = ""
                        venv_state = current_shell.get("venv_state", {})
                        active_env = venv_state.get("active_env")
                        
                        if not active_env:
                            active_env = self.detect_active_venv()
                            if active_env:
                                self.update_shell_venv_state(current_shell, active_env)
                                current_shell["venv_state"] = {"active_env": active_env}
                        
                        if active_env:
                            venv_prefix = f"({active_env}) "
                        
                        # 简化路径显示：类似bash只显示最后一个部分
                        if current_path == "~":
                            display_path = "~"
                        else:
                            # 显示最后一个路径部分，类似bash的行为
                            path_parts = current_path.split('/')
                            display_path = path_parts[-1] if path_parts[-1] else path_parts[-2]
                        
                        prompt = f"{venv_prefix}GDS:{display_path}$ "
                        # 使用简单的input()来避免复杂性和潜在的循环问题
                        try:
                            user_input = input(prompt).strip()
                        except (EOFError, KeyboardInterrupt):
                            print("\nExit Google Drive Shell")
                            return 0
                        
                        if not user_input:
                            continue
                        
                        # 检测是否从管道读取输入，如果是则回显命令
                        import sys
                        if not sys.stdin.isatty(): 
                            print(f"{user_input}")
                        
                        # 解析命令
                        parts = user_input.split()
                        cmd = parts[0].lower()
                        
                        if cmd == "exit":
                            print("Exit Google Drive Shell")
                            break
                        else: 
                            try:
                                # 使用GoogleDriveShell执行命令
                                from ..google_drive_shell import GoogleDriveShell
                                shell_instance = GoogleDriveShell()
                                
                                # 执行完整的shell命令
                                result_code = shell_instance.execute_shell_command(user_input)
                            except Exception as e:
                                print(f"Error executing command '{cmd}': {e}")
                        
                    except KeyboardInterrupt:
                        break
                    except EOFError:
                        break
                
                return 0
            
        except Exception as e:
            error_msg = f"Error starting shell mode: {e}"
            print(error_msg)
            return 1


    def get_current_folder_id(self, current_shell=None):
        """
        获取当前shell的文件夹ID，如果没有则返回REMOTE_ROOT_FOLDER_ID
        
        Args:
            current_shell (dict, optional): 当前shell信息，如果为None则自动获取
            
        Returns:
            str: 当前文件夹ID
        """
        if current_shell is None:
            current_shell = self.main_instance.get_current_shell()
        
        if current_shell:
            return current_shell.get("current_folder_id", self.main_instance.REMOTE_ROOT_FOLDER_ID)
        else:
            return self.main_instance.REMOTE_ROOT_FOLDER_ID

    def create_default_shell(self):
        """创建默认shell"""
        shell_id = "default_shell"
        shell_name = "default"
        shell_config = {
            "id": shell_id,
            "name": shell_name,
            "current_path": "~", 
            "current_folder_id": self.main_instance.REMOTE_ROOT_FOLDER_ID,  # Google Drive文件夹ID
            "created_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "last_accessed": time.strftime("%Y-%m-%d %H:%M:%S"),
            "venv_state": {
                "active_env": None,  # 当前激活的虚拟环境名称
                "pythonpath": "/env/python"  # 当前PYTHONPATH
            }
        }
        
        # 加载现有shells数据
        shells_data = self.load_shells()
        
        # 添加默认shell
        shells_data["shells"][shell_id] = shell_config
        shells_data["active_shell"] = shell_id
        
        # 保存配置
        self.save_shells(shells_data)
        return shell_config