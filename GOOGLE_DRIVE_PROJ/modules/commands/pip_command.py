from .base_command import BaseCommand

class PipCommand(BaseCommand):
    """
    Pip package management and scanning
    Merged from pip_operations.py
    """
    
    @property
    def command_name(self):
        return "pip"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行pip命令"""
        if not args:
            print("Error: pip command needs arguments")
            return 1
        
        # 直接调用cmd_pip方法
        result = self.cmd_pip(*args)
        if result.get("success"):
            message = result.get("message", "")
            if message.strip():
                print(message)
            return 0
        else:
            error_msg = result.get("error", "Pip operation failed")
            print(error_msg)
            return 1
    
    def cmd_pip(self, *args, **kwargs):
        """执行pip命令（增强版 - 自动处理虚拟环境、包状态显示）"""
        try:
            if not args:
                return {"success": False, "error": "pip命令需要参数"}
            
            # 构建pip命令
            pip_args = list(args)
            pip_command = " ".join(pip_args)
            
            # 获取当前激活的虚拟环境
            current_shell = self.shell.get_current_shell()
            shell_id = current_shell.get("id", "default_shell") if current_shell else "default_shell"
            
            # 检查是否有激活的虚拟环境
            from .venv_command import VenvCommand
            venv_cmd = VenvCommand(self.shell)
            from ..venv_manager import VenvApiManager
            api_manager = VenvApiManager(self.shell.drive_service, self.shell)
            result = api_manager.read_venv_states()
            all_states = result.get('data', {}) if result.get('success') else {}
            current_venv = None
            env_path = None
            if shell_id in all_states and all_states[shell_id].get("current_venv"):
                current_venv = all_states[shell_id]["current_venv"]
                env_path = f"{venv_cmd.get_venv_base_path()}/{current_venv}"
            
            # 特殊处理不同的pip命令
            if pip_args[0] == "--show-deps":
                # 直接处理 --show-deps，委托给dependency_analysis
                current_packages = self.get_packages_from_json(current_venv) if current_venv else {}
                # 这里需要调用DepsCommand，暂时先返回错误
                return {"success": False, "error": "Please use 'GDS deps' command for dependency analysis"}
            
            # 检测当前环境中的包（用于显示[√]标记）
            current_packages = self.detect_current_environment_packages(current_venv)
            
            if pip_args[0] == "install":
                return self.handle_pip_install(pip_args[1:], current_venv, env_path, current_packages)
            elif pip_args[0] == "uninstall":
                return self.handle_pip_uninstall(pip_args[1:], current_venv, env_path, current_packages)
            elif pip_args[0] == "list":
                return self.handle_pip_list(pip_args[1:], current_venv, env_path, current_packages)
            elif pip_args[0] == "show":
                return self.handle_pip_show(pip_args[1:], current_venv, env_path, current_packages)
            else:
                # 其他pip命令，使用增强版执行器
                target_info = f"in {current_venv}" if current_venv else "in system environment"
                return self.execute_pip_command(pip_command, current_venv, target_info)
                
        except Exception as e:
            return {"success": False, "error": f"pip命令执行失败: {str(e)}"}

    def handle_pip_install(self, packages_args, current_venv, env_path, current_packages):
        """处理pip install命令"""
        try:
            if not packages_args:
                return {"success": False, "error": "pip install需要指定包名"}
            
            if '--show-deps' in packages_args:
                return {"success": False, "error": "Please use 'GDS deps' command for dependency analysis instead of 'pip install --show-deps'"}
            
            # 解析选项
            force_install = '--force' in packages_args
            packages_to_install = [pkg for pkg in packages_args if not pkg.startswith('--')]

            if not force_install:
                all_installed = True
                for package in packages_to_install:
                    pkg_name = package.split('==')[0].split('>=')[0].split('<=')[0].split('>')[0].split('<')[0].split('!=')[0]
                    if pkg_name not in current_packages:
                        all_installed = False
                        break
                
                if all_installed:
                    return {
                        "success": True,
                        "message": "All target packages are already installed.",
                        "installed_packages": packages_to_install
                    }
            
            # 标准安装流程
            install_command = f"install {' '.join(packages_to_install)}"
            target_info = f"in {current_venv}" if current_venv else "in system environment"
            return self.execute_pip_command(install_command, current_venv, target_info)
            
        except Exception as e:
            return {"success": False, "error": f"处理pip install时出错: {str(e)}"}

    def handle_pip_list(self, list_args, current_venv, env_path, current_packages):
        """处理pip list命令 - 显示增强的包列表信息"""
        try:
            # 检查是否有--refresh-list选项
            force_refresh = "--refresh-list" in list_args
            if force_refresh:
                list_args = [arg for arg in list_args if arg != "--refresh-list"]
                if current_venv:
                    current_packages = self.get_packages_from_json(current_venv, force_refresh=True)
            print(f"Total {len(current_packages)} packages")
            
            if current_packages:
                for pkg_name, version in sorted(current_packages.items()):
                    print(f"  {pkg_name} == {version}")
            
            # 如果有额外的list参数，执行原始pip list命令
            if list_args:
                list_command = f"list {' '.join(list_args)}"
                target_info = f"in {current_venv}" if current_venv else "in system environment"
                return self.execute_pip_command(list_command, current_venv, target_info)
            
            return {
                "success": True,
                "packages": current_packages,
                "environment": current_venv or "system"
            }
            
        except Exception as e:
            return {"success": False, "error": f"处理pip list时出错: {str(e)}"}

    def handle_pip_uninstall(self, uninstall_args, current_venv, env_path, current_packages):
        """处理pip uninstall命令"""
        try:
            if not uninstall_args:
                return {"success": False, "error": "pip uninstall需要指定包名"}
            
            uninstall_command = f"uninstall -y {' '.join(uninstall_args)}"
            target_info = f"in {current_venv}" if current_venv else "in system environment"
            print(f"Uninstalling packages: {', '.join(uninstall_args)}")
            return self.execute_pip_command(uninstall_command, current_venv, target_info)
            
        except Exception as e:
            return {"success": False, "error": f"处理pip uninstall时出错: {str(e)}"}

    def handle_pip_show(self, show_args, current_venv, env_path, current_packages):
        """处理pip show命令 - 显示包的详细信息"""
        try:
            if not show_args:
                return {"success": False, "error": "pip show需要指定包名"}
            
            show_command = f"show {' '.join(show_args)}"
            target_info = f"in {current_venv}" if current_venv else "in system environment"
            return self.execute_pip_command(show_command, current_venv, target_info)
            
        except Exception as e:
            return {"success": False, "error": f"处理pip show时出错: {str(e)}"}


    def get_packages_from_json(self, venv_name, force_refresh=False):
        """Get packages from JSON with directory scanning fallback"""
        try:
            # 如果强制刷新或JSON中没有数据，进行目录扫描
            if force_refresh:
                print(f"Refreshing package list from directory scan...")
                scanned_packages = self.scan_environment_directory(venv_name)
                if scanned_packages:
                    # 更新JSON文件
                    self.remote_update_json_packages(venv_name, scanned_packages, action="replace")
                    return scanned_packages
            
            # 获取JSON中的包信息
            from ..venv_manager import VenvApiManager
            api_manager = VenvApiManager(self.shell.drive_service, self.shell)
            result = api_manager.read_venv_states()
            all_states = result.get('data', {}) if result.get('success') else {}
            packages_from_json = {}
            
            if all_states and 'environments' in all_states and venv_name in all_states['environments']:
                env_data = all_states['environments'][venv_name]
                packages_from_json = env_data.get('packages', {})
            
            # 如果JSON中没有包信息，进行目录扫描
            if not packages_from_json:
                scanned_packages = self.scan_environment_directory(venv_name)
                if scanned_packages:
                    # 更新JSON文件
                    self.remote_update_json_packages(venv_name, scanned_packages, action="replace")
                    return scanned_packages
            
            return packages_from_json
        except Exception as e:
            return {}

    def scan_environment_directory(self, env_name):
        """Scan virtual environment directory for installed packages"""
        try:
            from .venv_command import VenvCommand
            venv_cmd = VenvCommand(self.shell)
            env_path = f"{venv_cmd.get_venv_base_path()}/{env_name}"
            
            # 构建扫描命令
            scan_command = f"""
find '{env_path}' -maxdepth 1 -name '*.dist-info' -type d 2>/dev/null | sed 's|.*/||' | head -50 && \\
find '{env_path}' -maxdepth 1 -name '*.egg-info' -type d 2>/dev/null | sed 's|.*/||' | head -50
""".strip()
            
            # 执行远程命令
            result = self.shell.command_executor.execute_command_interface("bash", ["-c", scan_command])
            
            if result.get("success"):
                output = result.get("stdout", "")
                # 解析输出获取包信息
                packages = self.parse_package_scan_output(output)
                return packages
            else:
                return {}
                
        except Exception as e:
            return {}

    def parse_package_scan_output(self, output):
        """Parse package scan output to extract package names and versions"""
        packages = {}
        try:
            lines = output.strip().split('\n')
            for line in lines:
                line = line.strip()
                # 查找 .dist-info 目录
                if line.endswith('.dist-info'):
                    # 格式通常是 package_name-version.dist-info
                    parts = line.replace('.dist-info', '').split('-')
                    if len(parts) >= 2:
                        package_name = '-'.join(parts[:-1])  # 包名可能包含连字符
                        version = parts[-1]
                        packages[package_name] = version
                # 查找 .egg-info 目录
                elif line.endswith('.egg-info'):
                    parts = line.replace('.egg-info', '').split('-')
                    if len(parts) >= 2:
                        package_name = '-'.join(parts[:-1])
                        version = parts[-1]
                        packages[package_name] = version
        except Exception as e:
            pass
        
        return packages

    def remote_update_json_packages(self, env_name, packages, action="add"):
        """Update venv_states.json remotely with new package information"""
        try:
            # 构建Python脚本来更新JSON文件
            packages_json = str(packages).replace("'", '"')  # 转换为JSON格式
            
            python_script = f'''
import json
import os

venv_states_file = f"{self.shell.REMOTE_ENV}/venv/venv_states.json"
env_name = "{env_name}"
new_packages = {packages_json}
action = "{action}"

# 读取现有状态
states = {{}}
if os.path.exists(venv_states_file):
    try:
        with open(venv_states_file, 'r') as f:
            states = json.load(f)
    except:
        states = {{}}

# 确保environments字段存在
if 'environments' not in states:
    states['environments'] = {{}}

# 确保环境存在
if env_name not in states['environments']:
    states['environments'][env_name] = {{"packages": {{}}}}

# 确保packages字段存在
if 'packages' not in states['environments'][env_name]:
    states['environments'][env_name]['packages'] = {{}}

# 更新包信息
if action == "add":
    states['environments'][env_name]['packages'].update(new_packages)
    print(f"Added {{len(new_packages)}} packages to {{env_name}}")
elif action == "remove":
    for pkg in new_packages:
        if pkg in states['environments'][env_name]['packages']:
            del states['environments'][env_name]['packages'][pkg]
    print(f"Removed {{len(new_packages)}} packages from {{env_name}}")
elif action == "replace":
    states['environments'][env_name]['packages'] = new_packages
    print(f"Replaced package list with {{len(new_packages)}} packages for {{env_name}}")

# 写回文件
with open(venv_states_file, 'w') as f:
    json.dump(states, f, indent=2)

print(f"JSON file updated successfully")
'''
            
            return python_script  # 返回脚本，由调用者合并到主命令中
                
        except Exception as e:
            print(f"Error updating JSON remotely: {e}")

    def detect_current_environment_packages(self, venv_name):
        """Detect current environment packages with JSON and directory scanning"""
        try:
            if venv_name:
                # 直接从JSON读取，不进行扫描（避免弹窗）
                from ..venv_manager import VenvApiManager
                api_manager = VenvApiManager(self.shell.drive_service, self.shell)
                result = api_manager.read_venv_states()
                all_states = result.get('data', {}) if result.get('success') else {}
                if all_states and 'environments' in all_states and venv_name in all_states['environments']:
                    env_data = all_states['environments'][venv_name]
                    return env_data.get('packages', {})
                else:
                    # 如果JSON中没有数据，返回空字典（用户可以手动--refresh-list）
                    return {}
            else:
                # 对于系统环境，返回基础包
                return {
                    'pip': '23.0.0',
                    'setuptools': '65.0.0'
                }
        except Exception as e:
            return {}

    def execute_pip_command(self, pip_command, current_env, target_info):
        """强化的pip命令执行，支持错误处理和结果验证"""
        try:
            import time
            import random
            
            # 生成唯一的结果文件名
            timestamp = int(time.time())
            random_id = f"{random.randint(1000, 9999):04x}"
            result_filename = f"pip_result_{timestamp}_{random_id}.json"
            
            # 构建环境设置命令
            pip_target_option = ""
            if current_env:
                env_path = f"{self.shell.REMOTE_ENV}/venv/{current_env}"
                pip_target_option = f" --target {env_path}"
            
            # 使用Python subprocess包装pip执行，确保正确捕获所有输出和错误
            python_script = f'''
import subprocess
import json
import sys
from datetime import datetime

print(f"Starting pip {pip_command}...")
start_time = datetime.now()

# 执行pip命令并捕获所有输出
try:
    pip_cmd_parts = ["pip"] + "{pip_command}".split()
    # 添加虚拟环境目标目录（如果有的话）
    pip_target = "{pip_target_option}"
    if pip_target.strip():
        pip_cmd_parts.extend(pip_target.strip().split())
    
    print(f"Full pip command: {{pip_cmd_parts}}")
    
    # 执行pip命令并捕获输出
    result = subprocess.run(
        pip_cmd_parts,
        capture_output=True,
        text=True
    )
    
    # 显示pip的完整输出
    if result.stdout:
        print(f"STDOUT:")
        print(result.stdout)
    if result.stderr:
        print(f"STDERR:")
        print(result.stderr)
    
    # 检查是否有严重ERROR关键字（排除依赖冲突警告）
    has_error = False
    if result.returncode != 0:
        has_error = "ERROR:" in result.stderr or "ERROR:" in result.stdout
    
    # 计算执行时间
    end_time = datetime.now()
    duration = end_time - start_time
    
    print(f"Pip command completed with exit code: {{result.returncode}}")
    if has_error:
        print(f" Detected ERROR messages in pip output")
    
    # 生成结果JSON
    result_data = {{
        "success": result.returncode == 0 and not has_error,
        "pip_command": "{pip_command}",
        "exit_code": result.returncode,
        "environment": "{current_env or 'system'}",
        "stdout": result.stdout,
        "stderr": result.stderr,
        "has_error": has_error,
        "timestamp": datetime.now().isoformat(),
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": duration.total_seconds()
    }}
    
    with open("{self.shell.REMOTE_ROOT}/tmp/{result_filename}", "w") as f:
        json.dump(result_data, f, indent=2)
    
    # 显示最终状态
    if result.returncode == 0 and not has_error:
        print(f"pip command completed successfully")
        
        # 如果是install/uninstall命令且成功，更新JSON文件
        if ("{pip_command}".startswith("install") or "{pip_command}".startswith("uninstall")) and "{current_env}":
            try:
                import json
                import os
                
                venv_states_file = f"{self.shell.REMOTE_ENV}/venv/venv_states.json"
                env_name = "{current_env}"
                
                if "{pip_command}".startswith("install"):
                    # 解析Successfully installed行获取包信息
                    installed_packages = {{}}
                    for line in result.stdout.split('\\n'):
                        if 'Successfully installed' in line:
                            parts = line.replace('Successfully installed', '').strip().split()
                            for part in parts:
                                if '-' in part:
                                    pkg_parts = part.rsplit('-', 1)
                                    if len(pkg_parts) == 2:
                                        package_name, version = pkg_parts
                                        installed_packages[package_name] = version
                    
                    if installed_packages:
                        # 读取现有状态
                        states = {{}}
                        if os.path.exists(venv_states_file):
                            try:
                                with open(venv_states_file, 'r') as f:
                                    states = json.load(f)
                            except:
                                states = {{}}
                        
                        # 确保结构存在
                        if 'environments' not in states:
                            states['environments'] = {{}}
                        if env_name not in states['environments']:
                            states['environments'][env_name] = {{"packages": {{}}}}
                        if 'packages' not in states['environments'][env_name]:
                            states['environments'][env_name]['packages'] = {{}}
                        
                        # 更新包信息
                        states['environments'][env_name]['packages'].update(installed_packages)
                        
                        # 写回文件
                        with open(venv_states_file, 'w') as f:
                            json.dump(states, f, indent=2)
                        
                        print(f"Updated JSON with {{len(installed_packages)}} newly installed packages")
                        
                elif "{pip_command}".startswith("uninstall"):
                    # 解析Successfully uninstalled行获取包信息
                    uninstalled_packages = []
                    for line in result.stdout.split('\\n'):
                        if 'Successfully uninstalled' in line:
                            parts = line.replace('Successfully uninstalled', '').strip().split()
                            for part in parts:
                                if '-' in part:
                                    pkg_parts = part.rsplit('-', 1)
                                    if len(pkg_parts) == 2:
                                        package_name, version = pkg_parts
                                        uninstalled_packages.append(package_name)
                    
                    if uninstalled_packages:
                        # 读取现有状态
                        states = {{}}
                        if os.path.exists(venv_states_file):
                            try:
                                with open(venv_states_file, 'r') as f:
                                    states = json.load(f)
                            except:
                                states = {{}}
                        
                        # 确保结构存在
                        if 'environments' not in states:
                            states['environments'] = {{}}
                        if env_name not in states['environments']:
                            states['environments'][env_name] = {{"packages": {{}}}}
                        if 'packages' not in states['environments'][env_name]:
                            states['environments'][env_name]['packages'] = {{}}
                        
                        # 移除包信息
                        for pkg in uninstalled_packages:
                            if pkg in states['environments'][env_name]['packages']:
                                del states['environments'][env_name]['packages'][pkg]
                        
                        # 写回文件
                        with open(venv_states_file, 'w') as f:
                            json.dump(states, f, indent=2)
                        
                        print(f"Removed {{len(uninstalled_packages)}} packages from JSON")
            except Exception as e:
                print(f"Warning: Failed to update JSON: {{e}}")
    else:
        print(f"pip command failed (exit_code: {{result.returncode}}, has_error: {{has_error}})")

except Exception as e:
    end_time = datetime.now()
    duration = end_time - start_time
    print(f"Error: Error executing pip command: {{e}}")
    result_data = {{
        "success": False,
        "pip_command": "{pip_command}",
        "exit_code": -1,
        "environment": "{current_env or 'system'}",
        "error": str(e),
        "timestamp": datetime.now().isoformat(),
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": duration.total_seconds()
    }}
    with open("{self.shell.REMOTE_ROOT}/tmp/{result_filename}", "w") as f:
        json.dump(result_data, f, indent=2)
'''
            
            # 构建完整的远程命令
            commands = [
                f'cd "{self.shell.REMOTE_ROOT}"',
                "mkdir -p tmp",
                f'python3 -c "{python_script.replace(chr(92), chr(92)+chr(92)).replace(chr(34), chr(92)+chr(34))}"'
            ]
            
            commands = [cmd for cmd in commands if cmd.strip()]
            full_command = " && ".join(commands)
            
            # 执行远程命令
            result = self.shell.command_executor.execute_command_interface("bash", ["-c", full_command])
            
            if result.get("success"):
                # 显示远程pip的完整输出
                remote_output = result.get("stdout", "")
                if remote_output:
                    print(f"Remote pip output:")
                    print(remote_output)
                
                return {
                    "success": True,
                    "output": remote_output,
                    "environment": current_env or "system"
                }
            else:
                error_output = result.get("stderr", "")
                if error_output:
                    print(f"Remote pip error:")
                    print(error_output)
                
                return {
                    "success": False,
                    "error": result.get("error", f"Pip {pip_command} execution failed"),
                    "stderr": error_output
                }
            
        except Exception as e:
            return {"success": False, "error": f"pip命令执行失败: {str(e)}"}

