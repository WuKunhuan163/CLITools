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
        # 检查是否请求帮助
        if '--help' in args or '-h' in args:
            self.show_help()
            return 0
            
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
    
    def show_help(self):
        """显示pip命令帮助信息"""
        print("GDS Pip Command Help")
        print("=" * 50)
        print()
        print("USAGE:")
        print("  GDS pip install <package>          # Install package")
        print("  GDS pip uninstall <package>        # Uninstall package")
        print("  GDS pip list                       # List installed packages")
        print("  GDS pip show <package>             # Show package information")
        print("  GDS pip freeze                     # Output installed packages in requirements format")
        print("  GDS pip --help                     # Show this help")
        print()
        print("DESCRIPTION:")
        print("  Manage Python packages in the remote environment.")
        print("  Automatically handles virtual environments and package states.")
        print()
        print("EXAMPLES:")
        print("  GDS pip install numpy              # Install numpy")
        print("  GDS pip install -r requirements.txt # Install from requirements file")
        print("  GDS pip uninstall numpy            # Uninstall numpy")
        print("  GDS pip list                       # List all packages")
        print("  GDS pip show numpy                 # Show numpy details")
        print("  GDS pip freeze > requirements.txt  # Export requirements")
        print()
        print("RELATED COMMANDS:")
        print("  GDS python --help                  # Python execution")
        print("  GDS pyenv --help                   # Python version management")
        print("  GDS venv --help                    # Virtual environment management")
        print("  GDS deps --help                    # Dependency analysis")
    
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
            
            # 解析--transfer-batch参数
            transfer_batch = 1000  # 默认值
            if '--transfer-batch' in packages_args:
                try:
                    batch_index = packages_args.index('--transfer-batch')
                    if batch_index + 1 < len(packages_args):
                        transfer_batch = int(packages_args[batch_index + 1])
                except (ValueError, IndexError):
                    pass
            
            packages_to_install = [pkg for pkg in packages_args if not pkg.startswith('--') and pkg != str(transfer_batch)]

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
            return self.execute_pip_command(install_command, current_venv, target_info, transfer_batch=transfer_batch)
            
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
        from ..venv_manager import VenvApiManager
        api_manager = VenvApiManager(self.shell.drive_service, self.shell)
        result = api_manager.read_venv_states()
        all_states = result.get('data', {}) if result.get('success') else {}
        if all_states and 'environments' in all_states and venv_name in all_states['environments']:
            env_data = all_states['environments'][venv_name]
            return env_data.get('packages', {})
        else: 
            return {}

    def execute_pip_command(self, pip_command, current_env, target_info, transfer_batch=1000):
        """pip命令执行（install使用tmp-pack-transfer策略）"""
        try:
            # install命令使用tmp-pack-transfer避免GDFUSE问题
            if pip_command.startswith("install") and current_env:
                return self._pip_install_with_transfer(pip_command, current_env, transfer_batch=transfer_batch)
            
            # 其他命令直接执行
            # 构建pip命令
            import time
            pip_success_fingerprint = f"~/tmp/pip_{current_env or 'system'}_{int(time.time())}.success"
            
            pip_target_option = ""
            if current_env:
                env_path = f"{self.shell.REMOTE_ENV}/venv/{current_env}"
                if pip_command.startswith("uninstall"):
                    pip_target_option = f" --target {env_path}"
            
            full_pip_command = f"pip {pip_command}{pip_target_option} && touch {pip_success_fingerprint}"
            
            print(f"Executing: pip {pip_command} {target_info}")
            print("-" * 70)
            
            # 使用raw command模式，不capture输出（实时显示）
            if hasattr(self.shell, 'command_executor'):
                old_raw = getattr(self.shell.command_executor, '_raw_command', False)
                self.shell.command_executor._raw_command = True
                
                result = self.shell.command_executor.execute_command_interface(
                    cmd=full_pip_command,
                    capture_result=False  # 不capture，实时显示
                )
                
                self.shell.command_executor._raw_command = old_raw
            
            # 检查成功指纹是否被创建
            from .pyenv_command import PyenvCommand
            pyenv_cmd = PyenvCommand(self.shell)
            success_check = pyenv_cmd.check_fingerprint_exists(pip_success_fingerprint, max_attempts=3)
            
            # 清理成功指纹
            if success_check and hasattr(self.shell, 'command_executor'):
                old_raw = getattr(self.shell.command_executor, '_raw_command', False)
                self.shell.command_executor._raw_command = True
                self.shell.command_executor.execute_command_interface(
                    cmd=f"rm -f {pip_success_fingerprint}",
                    capture_result=False
                )
                self.shell.command_executor._raw_command = old_raw
            
            if success_check:
                print(f"pip {pip_command} completed successfully")
                if current_env:
                    print(f"Note: Use 'GDS pip list --refresh-list' to refresh package cache.")
            else:
                print(f"pip {pip_command} may have failed (fingerprint not found)")
            
            return {
                "success": success_check,
                "message": f"pip {pip_command} {'completed' if success_check else 'failed'}",
                "environment": current_env or "system"
            }
            
        except Exception as e:
            return {"success": False, "error": f"pip命令执行失败: {str(e)}"}
    
    def _pip_install_with_transfer(self, pip_command, current_env, transfer_batch=1000):
        """pip install使用智能transfer策略（根据文件数选择tar或worker）"""
        try:
            import time
            import hashlib
            
            # 生成临时目录
            timestamp = int(time.time())
            temp_id = hashlib.md5(f"{current_env}_{timestamp}".encode()).hexdigest()[:8]
            temp_install_dir = f"/tmp/pip_install_{temp_id}"
            final_venv_dir = f"{self.shell.REMOTE_ENV}/venv/{current_env}"
            print(f"Installing packages...")
            
            # Step 1: pip install到/tmp（实时显示）
            install_cmd = f"mkdir -p {temp_install_dir} && pip {pip_command} --target {temp_install_dir}"
            if hasattr(self.shell, 'command_executor'):
                old_raw = getattr(self.shell.command_executor, '_raw_command', False)
                self.shell.command_executor._raw_command = True
                
                install_result = self.shell.command_executor.execute_command_interface(
                    cmd=install_cmd,
                    capture_result=False  # 实时显示
                )
                
                self.shell.command_executor._raw_command = old_raw
                
                if not install_result.get("success"):
                    return {"success": False, "error": "pip install to /tmp failed"}
            
            print("-" * 70)
            print(f"Download completed. Counting files...")
            
            # Step 2: 统计文件数（包括子目录）
            count_cmd = f"find {temp_install_dir} -type f | wc -l"
            if hasattr(self.shell, 'command_executor'):
                old_raw = getattr(self.shell.command_executor, '_raw_command', False)
                self.shell.command_executor._raw_command = True
                
                count_result = self.shell.command_executor.execute_command_interface(
                    cmd=count_cmd,
                    capture_result=True  # 需要读取结果
                )
                
                self.shell.command_executor._raw_command = old_raw
                
                file_count = 0
                if count_result.get("success"):
                    count_stdout = count_result.get('stdout', '') or count_result.get('data', {}).get('stdout', '')
                    try:
                        file_count = int(str(count_stdout).strip())
                        print(f"Total files: {file_count} (batch size: {transfer_batch})")
                    except ValueError:
                        print(f"Failed to parse file count, using worker strategy")
                        file_count = transfer_batch + 1  # 强制使用worker
            
            # Step 3: 根据文件数选择transfer策略
            if file_count <= transfer_batch:
                # 小包：简单tar策略（一次性转移所有文件和文件夹）
                print(f"Using simple tar strategy (files <= {transfer_batch})")
                print("Transferring...")
                
                tar_cmd = f"""
cd {temp_install_dir} && \
tar -czf /tmp/pip_packages_{temp_id}.tar.gz . && \
mkdir -p {final_venv_dir} && \
cd {final_venv_dir} && \
tar -xzf /tmp/pip_packages_{temp_id}.tar.gz && \
echo 'Packages transferred successfully' && \
rm -f /tmp/pip_packages_{temp_id}.tar.gz && \
rm -rf {temp_install_dir}
"""
                old_raw = getattr(self.shell.command_executor, '_raw_command', False)
                self.shell.command_executor._raw_command = True
                
                result = self.shell.command_executor.execute_command_interface(
                    cmd=tar_cmd.strip(),
                    capture_result=False
                )
                
                self.shell.command_executor._raw_command = old_raw
                success = result.get("success", False)
            else:
                # 大包：使用GDS extract的worker机制
                print(f"Using worker strategy (files > {transfer_batch})")
                print("Transferring with parallel workers...")
                
                from .extract_command import ExtractCommand
                extract_cmd = ExtractCommand(self.main_instance)
                
                try:
                    transfer_result = extract_cmd.transfer_directory(
                        source_dir=temp_install_dir,
                        target_dir=final_venv_dir,
                        transfer_batch=transfer_batch,
                        quiet=False
                    )
                    success = transfer_result.get("success", False)
                    
                    # 清理temp_install_dir
                    if success:
                        cleanup_cmd = f"rm -rf {temp_install_dir}"
                        old_raw = getattr(self.shell.command_executor, '_raw_command', False)
                        self.shell.command_executor._raw_command = True
                        self.shell.command_executor.execute_command_interface(cmd=cleanup_cmd, capture_result=False)
                        self.shell.command_executor._raw_command = old_raw
                        
                except KeyboardInterrupt:
                    print("\nPip install interrupted by user")
                    raise
                except Exception as e:
                    print(f"✗ Worker transfer failed: {e}")
                    success = False
            
            print("-" * 70)
            if success:
                print(f"pip {pip_command} completed successfully")
                print(f"Note: Use 'GDS pip list --refresh-list' to refresh package cache.")
            else:
                print(f"✗ Transfer failed")
            
            return {
                "success": success,
                "message": f"pip {pip_command} {'completed' if success else 'failed'}",
                "environment": current_env
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": f"pip install with transfer failed: {str(e)}"}

