from .base_command import BaseCommand

class PyenvCommand(BaseCommand):
    """
    Pyenv management command
    """
    
    @property
    def command_name(self):
        return "pyenv"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行pyenv命令"""
        # 检查是否请求帮助
        if '--help' in args or '-h' in args:
            self.show_help()
            return 0
            
        if not args:
            print("Error: pyenv command needs arguments")
            return 1
        
        # 直接调用cmd_pyenv方法
        result = self.cmd_pyenv(*args)
        
        if result.get("success"):
            stdout = result.get("stdout", "")
            if stdout:
                print(stdout)
            return 0
        else:
            error_msg = result.get("error", "Pyenv operation failed")
            print(error_msg)
            return 1
    
    def show_help(self):
        """显示pyenv命令帮助信息"""
        print("GDS Python Version Management (pyenv) Help")
        print("=" * 50)
        print()
        print("USAGE:")
        print("  GDS pyenv --install <version> [--force]      # Install Python version")
        print("  GDS pyenv --install-bg <version> [--force]   # Install in background")
        print("  GDS pyenv --install-local <version> [--force]# Download locally then install")
        print("  GDS pyenv --uninstall <version>              # Uninstall Python version")
        print("  GDS pyenv --list                    # List installed versions")
        print("  GDS pyenv --list-available          # List available versions for installation")
        print("  GDS pyenv --global <version>        # Set global default Python version")
        print("  GDS pyenv --local <version>         # Set local Python version for current shell")
        print("  GDS pyenv --version                 # Show current Python version")
        print("  GDS pyenv --versions                # Show all installed versions")
        print("  GDS pyenv --update-cache            # Update available versions cache")
        print("  GDS pyenv --help                    # Show this help")
        print()
        print("DESCRIPTION:")
        print("  Manage multiple Python versions in the remote environment.")
        print("  Allows installation, switching, and management of different Python versions.")
        print()
        print("EXAMPLES:")
        print("  GDS pyenv --install 3.9.18               # Install Python 3.9.18 (remote download)")
        print("  GDS pyenv --install-local 3.10.13        # Download locally, then install (FASTER!)")
        print("  GDS pyenv --install 3.9.18 --force       # Force reinstall existing version")
        print("  GDS pyenv --install-bg 3.10.13           # Install in background")
        print("  GDS pyenv --global 3.9.18           # Set 3.9.18 as global default")
        print("  GDS pyenv --local 3.10.13           # Use 3.10.13 in current shell")
        print("  GDS pyenv --versions                 # List all installed versions")
        print("  GDS pyenv --list-available          # See available versions")
        print()
        print("BACKGROUND TASKS:")
        print("  Use --install-bg for long installations. Track progress with:")
        print("  GDS --bg --status <task_id>          # Check installation status")
        print("  GDS --bg --log <task_id>             # View installation log")
        print()
        print("RELATED COMMANDS:")
        print("  GDS python --help                   # Python execution")
        print("  GDS pip --help                      # Package management")
        print("  GDS venv --help                     # Virtual environment management")
    
    def cmd_pyenv(self, *args):
        """
        Python版本管理命令
        
        支持的子命令：
        - --install <version>: 安装指定Python版本
        - --uninstall <version>: 卸载指定Python版本
        - --list: 列出所有已安装的Python版本
        - --list-available: 列出可下载的Python版本
        - --global <version>: 设置全局默认Python版本
        - --local <version>: 设置当前shell的Python版本
        - --version: 显示当前使用的Python版本
        - --versions: 显示所有已安装版本及当前版本标记
        
        Args:
            *args: 命令参数
            
        Returns:
            dict: 操作结果
        """
        try:
            if not args:
                return {
                    "success": False,
                    "error": "Usage: pyenv --install|--install-bg|--uninstall|--list|--list-available|--global|--local|--version|--versions [version]"
                }
            
            action = args[0]
            version = args[1] if len(args) > 1 else None
            force = "--force" in args
            
            if action == "--install":
                if not version:
                    return {"success": False, "error": "Please specify a Python version to install"}
                return self.pyenv_install(version, force=force)
            elif action == "--install-bg":
                if not version:
                    return {"success": False, "error": "Please specify a Python version to install in background"}
                return self.pyenv_install_bg(version, force=force)
            elif action == "--install-local":
                if not version:
                    return {"success": False, "error": "Please specify a Python version to install from local download"}
                return self.pyenv_install_local(version, force=force)
            elif action == "--uninstall":
                if not version:
                    return {"success": False, "error": "Please specify a Python version to uninstall"}
                return self.pyenv_uninstall(version)
            elif action == "--list":
                return {
                    "success": False,
                    "error": "pyenv: no such command `list'. Use 'pyenv --versions' to list installed versions."
                }
            elif action == "--list-available":
                return self.pyenv_list_available()
            elif action == "--update-cache":
                return self.pyenv_update_cache()
            elif action == "--global":
                if not version:
                    return self.pyenv_global_get()
                return self.pyenv_global_set(version)
            elif action == "--local":
                if not version:
                    return self.pyenv_local_get()
                return self.pyenv_local_set(version)
            elif action == "--version":
                return self.pyenv_version()
            elif action == "--versions":
                return self.getpyenv_versions()
            else:
                return {
                    "success": False,
                    "error": f"Unknown pyenv command: {action}. Supported commands: --install, --install-bg, --uninstall, --list-available, --update-cache, --global, --local, --version, --versions"
                }
                
        except Exception as e:
            return {"success": False, "error": f"pyenv命令执行失败: {str(e)}"}
    
    def get_python_base_path(self):
        """获取Python版本基础路径
        
        使用@路径前缀来代表REMOTE_ENV
        """
        return "@/python"
    
    def get_python_state_file_path(self):
        """获取Python版本状态文件路径"""
        return f"{self.get_python_base_path()}/python_states.json"
    
    def pyenv_install(self, version, force=False):
        """安装指定Python版本
        
        Args:
            version: Python版本号
            force: 是否强制覆盖已安装的版本
        """
        if not self.validate_version(version):
            return {
                "success": False, 
                "error": f"Invalid Python version format: '{version}'. Expected format: x.y.z (e.g., 3.9.18) or special identifiers like 'system'"
            }
        
        try:
            # 检查版本是否已安装
            if self.is_version_installed(version):
                if not force:
                    return {
                        "success": False,
                        "error": f"Python {version} is already installed. Use --force to reinstall."
                    }
                else:
                    print(f"Python {version} is already installed. Forcing reinstallation...")
                    # 先卸载旧版本
                    uninstall_result = self.pyenv_uninstall(version)
                    if not uninstall_result.get("success"):
                        return {
                            "success": False,
                            "error": f"Failed to uninstall existing version: {uninstall_result.get('error', 'Unknown error')}"
                        }
            
            # 构建安装路径
            install_path_logical = f"{self.get_python_base_path()}/{version}"
            
            # 解析@路径为绝对路径
            current_shell = self.main_instance.get_current_shell()
            install_path = self.main_instance.path_resolver.resolve_remote_absolute_path(install_path_logical, current_shell)


            print(f"\n\n\n{'=' * 100}")
            print(f"DEBUG install_path_logical: {install_path_logical}")
            print(f"DEBUG install_path: {install_path}")
            print(f"{'=' * 100}\n\n\n")
            
            print(f"Installing Python {version}...")
            print(f"Installation path: {install_path}")
            print(f"This may take several minutes...")
            
            # 构建远程安装命令
            # 使用pyenv-like installation method via source compilation
            install_command = f'''
# 创建安装目录
mkdir -p "{install_path}"

# 设置临时构建目录
BUILD_DIR="/tmp/python_build_{version}"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# 下载Python源码
echo "Downloading Python {version} source code..."
wget -q https://www.python.org/ftp/python/{version}/Python-{version}.tgz

if [ $? -ne 0 ]; then
    echo "Failed to download Python {version}"
    exit 1
fi

# 解压源码
tar -xzf Python-{version}.tgz
cd Python-{version}

# 配置编译选项
echo "Configuring Python {version}..."
./configure --prefix="{install_path}" --enable-optimizations --with-ensurepip=install

if [ $? -ne 0 ]; then
    echo "Failed to configure Python {version}"
    exit 1
fi

# 编译和安装
echo "Compiling Python {version}..."
make -j$(nproc)

if [ $? -ne 0 ]; then
    echo "Failed to compile Python {version}"
    exit 1
fi

echo "Installing Python {version}..."
make install

if [ $? -ne 0 ]; then
    echo "Failed to install Python {version}"
    exit 1
fi

# 清理构建目录
cd /
rm -rf "$BUILD_DIR"

# 设置执行权限
echo "Setting executable permissions..."
chmod -R 755 "{install_path}/bin/"

# 验证安装
if [ -f "{install_path}/bin/python3" ]; then
    echo "Python {version} installed successfully"
    echo "Location: {install_path}"
    {install_path}/bin/python3 --version
else
    echo "Installation verification failed"
    exit 1
fi
'''
            
            # 执行远程安装命令
            result = self.shell.command_executor.execute_remote_script(install_command)
            
            if result.get("success") and result.get("exit_code") == 0:
                # 更新状态文件
                self.add_installed_version(version)
                
                return {
                    "success": True,
                    "message": f"Python {version} installed successfully",
                    "version": version,
                    "install_path": install_path
                }
            else:
                stderr = result.get("stderr", "")
                stdout = result.get("stdout", "")
                error_msg = f"Failed to install Python {version}"
                if stderr:
                    error_msg += f": {stderr}"
                elif stdout:
                    error_msg += f": {stdout}"
                
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            return {"success": False, "error": f"Error installing Python {version}: {str(e)}"}
    
    def pyenv_install_bg(self, version, force=False):
        """在后台安装指定Python版本
        
        Args:
            version: Python版本号
            force: 是否强制覆盖已安装的版本
        """
        if not self.validate_version(version):
            return {
                "success": False, 
                "error": f"Invalid Python version format: '{version}'. Expected format: x.y.z (e.g., 3.9.18) or special identifiers like 'system'"
            }
        
        try:
            # 检查版本是否已安装
            if self.is_version_installed(version):
                if not force:
                    return {
                        "success": False,
                        "error": f"Python {version} is already installed. Use --force to reinstall."
                    }
                else:
                    print(f"Python {version} is already installed. Forcing reinstallation...")
                    # 先卸载旧版本
                    uninstall_result = self.pyenv_uninstall(version)
                    if not uninstall_result.get("success"):
                        return {
                            "success": False,
                            "error": f"Failed to uninstall existing version: {uninstall_result.get('error', 'Unknown error')}"
                        }
            
            # 构建安装路径
            install_path = f"{self.get_python_base_path()}/{version}"
            
            # 构建Python安装bash脚本（与pyenv_install相同的脚本）
            install_script = f'''
# 创建安装目录
mkdir -p "{install_path}"

# 设置临时构建目录
BUILD_DIR="/tmp/python_build_{version}"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# 下载Python源码
echo "Downloading Python {version} source code..."
wget -q https://www.python.org/ftp/python/{version}/Python-{version}.tgz

if [ $? -ne 0 ]; then
    echo "Failed to download Python {version}"
    exit 1
fi

# 解压源码
tar -xzf Python-{version}.tgz
cd Python-{version}

# 配置编译选项
echo "Configuring Python {version}..."
./configure --prefix="{install_path}" --enable-optimizations --with-ensurepip=install

if [ $? -ne 0 ]; then
    echo "Failed to configure Python {version}"
    exit 1
fi

# 编译和安装
echo "Compiling Python {version}..."
make -j$(nproc)

if [ $? -ne 0 ]; then
    echo "Failed to compile Python {version}"
    exit 1
fi

echo "Installing Python {version}..."
make install

if [ $? -ne 0 ]; then
    echo "Failed to install Python {version}"
    exit 1
fi

# 清理构建目录
cd /
rm -rf "$BUILD_DIR"

# 设置执行权限
echo "Setting executable permissions..."
chmod -R 755 "{install_path}/bin/"

# 验证安装
if [ -f "{install_path}/bin/python3" ]; then
    echo "Python {version} installed successfully"
    echo "Location: {install_path}"
    {install_path}/bin/python3 --version
    
    # 更新GDS的版本状态文件
    # 调用GDS的pyenv --versions命令来刷新状态（这会自动检测新安装的版本）
    # 这里不需要手动更新，因为安装成功后用户可以手动执行 GDS pyenv --versions
else
    echo "Installation verification failed"
    exit 1
fi
'''
            
            # 使用GDS的后台任务系统执行脚本
            # 调用execute_background_command
            result = self.shell.execute_background_command(install_script, command_identifier=None)
            
            if result == 0:
                # 后台任务启动成功
                return {
                    "success": True,
                    "message": f"Started background installation of Python {version}",
                    "stdout": f"Background task started. Use 'GDS --bg --status' to check progress."
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to start background installation of Python {version}"
                }
                
        except Exception as e:
            return {"success": False, "error": f"Error starting background installation of Python {version}: {str(e)}"}
    
    def pyenv_install_local(self, version, force=False):
        """本地下载Python源码并上传到远程编译安装
        
        Args:
            version: Python版本号
            force: 是否强制覆盖已安装的版本
            
        Returns:
            dict: 操作结果
        """
        if not self.validate_version(version):
            return {
                "success": False, 
                "error": f"Invalid Python version format: '{version}'. Expected format: x.y.z (e.g., 3.9.18)"
            }
        
        try:
            import tempfile
            import os
            import subprocess
            from pathlib import Path
            
            # 检查版本是否已安装
            if self.is_version_installed(version):
                if not force:
                    return {
                        "success": False,
                        "error": f"Python {version} is already installed. Use --force to reinstall."
                    }
                else:
                    print(f"Python {version} is already installed. Forcing reinstallation...")
                    # 先卸载旧版本
                    uninstall_result = self.pyenv_uninstall(version)
                    if not uninstall_result.get("success"):
                        return {
                            "success": False,
                            "error": f"Failed to uninstall existing version: {uninstall_result.get('error', 'Unknown error')}"
                        }
            
            print(f"Starting local download and remote installation of Python {version}...")
            print(f"Step 1/4: Downloading Python {version} source code locally...")
            
            # 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix=f"python_{version}_")
            try:
                # 下载Python源码到本地
                tarball_name = f"Python-{version}.tgz"
                tarball_path = os.path.join(temp_dir, tarball_name)
                download_url = f"https://www.python.org/ftp/python/{version}/{tarball_name}"
                
                # 使用wget或curl下载
                download_cmd = f"curl -L -o '{tarball_path}' '{download_url}'"
                result = subprocess.run(download_cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode != 0:
                    # 尝试使用wget
                    download_cmd = f"wget -q -O '{tarball_path}' '{download_url}'"
                    result = subprocess.run(download_cmd, shell=True, capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        return {
                            "success": False,
                            "error": f"Failed to download Python {version} source code. Please check your internet connection."
                        }
                
                # 验证文件已下载
                if not os.path.exists(tarball_path) or os.path.getsize(tarball_path) == 0:
                    return {
                        "success": False,
                        "error": f"Downloaded file is empty or not found: {tarball_path}"
                    }
                
                file_size_mb = os.path.getsize(tarball_path) / (1024 * 1024)
                print(f"✓ Downloaded {tarball_name} ({file_size_mb:.1f} MB)")
                
                print(f"Step 2/4: Uploading source code to remote REMOTE_ENV...")
                
                # 上传到REMOTE_ENV的临时目录
                remote_tmp_path = f"@/python_install_{version}"
                
                # 创建远程目录
                mkdir_result = self.shell.cmd_mkdir(remote_tmp_path, recursive=True)
                if not mkdir_result.get("success"):
                    return {
                        "success": False,
                        "error": f"Failed to create remote directory: {mkdir_result.get('error', 'Unknown error')}"
                    }
                
                # 上传tar.gz文件到@路径
                from ..commands.upload_command import UploadCommand
                upload_cmd = UploadCommand(self.shell)
                upload_result = upload_cmd.cmd_upload([tarball_path], target_path=remote_tmp_path, force=True)
                
                if not upload_result.get("success"):
                    return {
                        "success": False,
                        "error": f"Failed to upload source code: {upload_result.get('error', 'Unknown error')}"
                    }
                
                print(f"✓ Uploaded to {remote_tarball_path}")
                
                print(f"Step 3/4: Extracting and compiling (this may take 10-20 minutes)...")
                
                # 构建安装路径 (使用REMOTE_ENV)
                install_path = f"{self.shell.REMOTE_ENV}/python/{version}"
                work_dir = f"{self.shell.REMOTE_ENV}/python_install_{version}"
                
                # 构建远程编译安装脚本
                install_script = f'''
# 创建安装目录
mkdir -p "{install_path}"

# 切换到临时目录
cd "{work_dir}"

# 解压源码
echo "Extracting source code..."
tar -xzf Python-{version}.tgz
cd Python-{version}

# 配置编译选项
echo "Configuring Python {version}..."
./configure --prefix="{install_path}" --enable-optimizations --with-ensurepip=install

if [ $? -ne 0 ]; then
    echo "Failed to configure Python {version}"
    exit 1
fi

# 编译（使用多核加速）
echo "Compiling Python {version}..."
make -j$(nproc)

if [ $? -ne 0 ]; then
    echo "Failed to compile Python {version}"
    exit 1
fi

# 安装
echo "Installing Python {version}..."
make install

if [ $? -ne 0 ]; then
    echo "Failed to install Python {version}"
    exit 1
fi

# 添加执行权限
echo "Setting executable permissions..."
chmod +x "{install_path}/bin/python3"
chmod +x "{install_path}/bin/python3.{version.rsplit('.', 1)[0]}"
chmod +x "{install_path}/bin/pip3"

# 验证安装 - 运行简单的Python代码
if [ -x "{install_path}/bin/python3" ]; then
    echo "Python {version} installed successfully!"
    {install_path}/bin/python3 --version
    
    # 测试Python执行
    echo "Running test script..."
    {install_path}/bin/python3 -c "import sys; print(f'Python {{sys.version}} is working correctly!')"
    
    if [ $? -eq 0 ]; then
        echo "✓ Python executable test passed"
        
        # 测试pip
        {install_path}/bin/pip3 --version
        if [ $? -eq 0 ]; then
            echo "✓ pip is working correctly"
        fi
    else
        echo "✗ Python executable test failed"
        exit 1
    fi
    
    # 清理临时文件
    cd ..
    rm -rf Python-{version} Python-{version}.tgz
    
    echo "Installation complete. Clean up done."
    echo "Python {version} is now available at: {install_path}/bin/python3"
    exit 0
else
    echo "Installation verification failed - executable not found"
    exit 1
fi
'''
                
                # 使用后台任务系统执行脚本
                print(f"Step 4/4: Starting background compilation...")
                result_code = self.shell.execute_background_command(install_script, command_identifier=None)
                
                if result_code == 0:
                    print(f"✓ Background compilation started successfully!")
                    print(f"")
                    print(f"The compilation will continue in the background.")
                    print(f"This typically takes 10-20 minutes depending on server performance.")
                    print(f"")
                    print(f"To check installation progress, use the background task commands shown above.")
                    
                    return {
                        "success": True,
                        "message": f"Started local-download installation of Python {version}",
                        "stdout": f"Background compilation started. Use 'GDS --bg --status <task_id>' to check progress."
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to start background compilation"
                    }
                    
            finally:
                # 清理本地临时目录
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                except:
                    pass
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": f"Error in local installation: {str(e)}"}
    
    def pyenv_uninstall(self, version):
        """卸载指定Python版本"""
        if not self.validate_version(version):
            return {"success": False, "error": f"Invalid Python version format: {version}"}
        
        try:
            # 检查版本是否已安装
            if not self.is_version_installed(version):
                return {
                    "success": False,
                    "error": f"Python {version} is not installed"
                }
            
            # 检查是否为当前使用的版本
            current_version = self.get_current_python_version()
            if current_version == version:
                return {
                    "success": False,
                    "error": f"Cannot uninstall Python {version} because it is currently in use. Please switch to another version first."
                }
            
            # 构建卸载路径
            install_path = f"{self.get_python_base_path()}/{version}"
            
            print(f"Uninstalling Python {version}...")
            
            # 构建远程卸载命令
            uninstall_command = f'''
if [ -d "{install_path}" ]; then
    rm -rf "{install_path}"
    echo "Python {version} uninstalled successfully"
else
    echo "Python {version} directory not found"
    exit 1
fi
'''
            
            # 执行远程卸载命令
            result = self.shell.execute_command_interface("bash", ["-c", uninstall_command])
            
            if result.get("success") and result.get("exit_code") == 0:
                # 更新状态文件
                self.remove_installed_version(version)
                
                return {
                    "success": True,
                    "message": f"Python {version} uninstalled successfully",
                    "version": version
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to uninstall Python {version}: {result.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            return {"success": False, "error": f"Error uninstalling Python {version}: {str(e)}"}
    
    def get_versions_and_current_unified(self):
        """使用单个远程命令同时获取已安装版本、当前版本和版本来源信息
        
        优化：通过Google Drive API直接列出目录，避免弹出远程窗口
        """
        try:
            import json
            import re
            
            # 直接使用REMOTE_ENV_FOLDER_ID访问REMOTE_ENV目录
            remote_env_folder_id = self.shell.REMOTE_ENV_FOLDER_ID
            
            if not remote_env_folder_id:
                print("Warning: REMOTE_ENV_FOLDER_ID not found")
                return [], None, "system"
            
            # 首先列出REMOTE_ENV目录，找到python子目录
            remote_env_files = self.shell.drive_service.list_files(folder_id=remote_env_folder_id, max_results=1000)
            
            if not remote_env_files.get("success"):
                print(f"Warning: Failed to list REMOTE_ENV: {remote_env_files.get('error', 'Unknown error')}")
                return [], None, "system"
            
            # 找到python目录的folder_id
            python_folder_id = None
            python_state_file_id = None
            
            for file_info in remote_env_files.get("files", []):
                if file_info.get("name") == "python" and file_info.get("mimeType") == "application/vnd.google-apps.folder":
                    python_folder_id = file_info.get("id")
                    break
            
            if not python_folder_id:
                # python目录不存在，返回空列表
                return [], None, "system"
            
            # 列出python目录的内容
            python_files_result = self.shell.drive_service.list_files(folder_id=python_folder_id, max_results=1000)
            
            if not python_files_result.get("success"):
                print(f"Warning: Failed to list python directory: {python_files_result.get('error', 'Unknown error')}")
                return [], None, "system"
            
            # 提取版本号和状态文件
            installed_versions = []
            for file_info in python_files_result.get("files", []):
                name = file_info.get("name", "")
                is_dir = file_info.get("mimeType") == "application/vnd.google-apps.folder"
                
                # 匹配版本号格式：x.y.z
                if is_dir and re.match(r'^\d+\.\d+\.\d+$', name):
                    installed_versions.append(name)
                    
                # 找到python_states.json文件
                elif name == "python_states.json":
                    python_state_file_id = file_info.get("id")
            
            # 读取状态文件获取当前版本
            current_version = None
            version_source = "system"
            
            if python_state_file_id:
                # 直接通过Google Drive API读取文件内容（无需保存到本地）
                try:
                    import io
                    from googleapiclient.http import MediaIoBaseDownload
                    
                    request = self.shell.drive_service.service.files().get_media(fileId=python_state_file_id)
                    file_content = io.BytesIO()
                    downloader = MediaIoBaseDownload(file_content, request)
                    
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                    
                    # 解析JSON内容
                    content_str = file_content.getvalue().decode('utf-8')
                    states = json.loads(content_str)
                    
                    # 获取当前shell ID（简化）
                    shell_id = 'default_shell'
                    local_key = f'shell_{shell_id}'
                    
                    # 确定当前版本和来源（优先级：local > global > None）
                    if local_key in states:
                        current_version = states[local_key]
                        version_source = f'local (shell {shell_id})'
                    elif 'global' in states:
                        current_version = states['global']
                        version_source = 'global'
                        
                except (json.JSONDecodeError, Exception):
                    pass  # 状态文件解析失败，使用默认值
            
            return installed_versions, current_version, version_source
                
        except Exception as e:
            print(f"Warning: Error in unified version query: {e}")
            return [], None, "system"
    
    def pyenv_list_available(self):
        """列出可下载的Python版本"""
        try:
            # 获取缓存的可用版本列表
            available_versions = self.get_cached_available_versions()
            
            # 只显示验证成功的版本
            verified_versions = [v for v in available_versions if v.get("status") == "verified"]
            
            if not verified_versions:
                print("No verified Python versions available for installation.")
                print("Run with --update-cache to refresh the version list.")
                return {
                    "success": True,
                    "message": "No verified versions available",
                    "versions": []
                }
            
            print("Available Python versions for installation:")
            for version_info in verified_versions:
                version = version_info["version"]
                print(f"  {version}")
            
            print(f"\nShowing {len(verified_versions)} verified versions out of {len(available_versions)} tested.")
            
            return {
                "success": True,
                "message": f"Available Python versions ({len(verified_versions)} verified):",
                "versions": [v["version"] for v in verified_versions],
                "count": len(verified_versions)
            }
            
        except Exception as e:
            return {"success": False, "error": f"Error listing available Python versions: {str(e)}"}
    
    def pyenv_update_cache(self):
        """更新Python版本缓存"""
        try:
            print("Updating Python versions cache...")
            print("This may take several minutes as we test each version...")
            
            # 强制重新生成缓存
            verified_versions = self.py_available_versions()
            
            verified_count = len([v for v in verified_versions if v.get("status") == "verified"])
            total_count = len(verified_versions)
            
            print(f"\nCache update completed!")
            print(f"Tested {total_count} versions, {verified_count} verified as working.")
            
            return {
                "success": True,
                "message": f"Cache updated: {verified_count}/{total_count} versions verified",
                "verified_count": verified_count,
                "total_count": total_count
            }
            
        except Exception as e:
            return {"success": False, "error": f"Error updating cache: {str(e)}"}
    
    def pyenv_global_set(self, version):
        """设置全局默认Python版本"""
        if not self.validate_version(version):
            return {
                "success": False, 
                "error": f"Invalid Python version format: '{version}'. Expected format: x.y.z (e.g., 3.9.18) or special identifiers like 'system'"
            }
        
        # 对于特殊版本（如system），不需要检查是否已安装
        if version not in ["system", "global"] and not self.is_version_installed(version):
            return {"success": False, "error": f"Python {version} is not installed. Use 'pyenv --install {version}' first."}
        
        try:
            # 更新全局Python版本设置
            self.update_python_state("global", version)
            
            print(f"Global Python version set to {version}")
            return {
                "success": True,
                "message": f"Global Python version set to {version}",
                "version": version,
                "scope": "global"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Error setting global Python version: {str(e)}"}
    
    def pyenv_global_get(self):
        """获取全局默认Python版本"""
        try:
            global_version = self.get_python_state("global")
            
            if global_version:
                print(f"Global Python version: {global_version}")
                return {
                    "success": True,
                    "version": global_version,
                    "scope": "global"
                }
            else:
                print("No global Python version set")
                return {
                    "success": True,
                    "version": None,
                    "scope": "global"
                }
                
        except Exception as e:
            return {"success": False, "error": f"Error getting global Python version: {str(e)}"}
    
    def pyenv_local_set(self, version):
        """设置当前shell的Python版本"""
        if not self.validate_version(version):
            return {
                "success": False, 
                "error": f"Invalid Python version format: '{version}'. Expected format: x.y.z (e.g., 3.9.18) or special identifiers like 'system'"
            }
        
        # 对于特殊版本（如system），不需要检查是否已安装
        if version not in ["system", "global"] and not self.is_version_installed(version):
            return {"success": False, "error": f"Python {version} is not installed. Use 'pyenv --install {version}' first."}
        
        try:
            # 获取当前shell ID
            current_shell = self.shell.get_current_shell()
            shell_id = current_shell.get("id", "default") if current_shell else "default"
            
            # 更新shell级别的Python版本设置
            self.update_python_state(f"shell_{shell_id}", version)
            
            print(f"Local Python version set to {version} for shell {shell_id}")
            return {
                "success": True,
                "message": f"Local Python version set to {version}",
                "version": version,
                "scope": "local",
                "shell_id": shell_id
            }
            
        except Exception as e:
            return {"success": False, "error": f"Error setting local Python version: {str(e)}"}
    
    def pyenv_local_get(self):
        """获取当前shell的Python版本"""
        try:
            current_shell = self.shell.get_current_shell()
            shell_id = current_shell.get("id", "default") if current_shell else "default"
            
            local_version = self.get_python_state(f"shell_{shell_id}")
            
            if local_version:
                print(f"Local Python version: {local_version}")
                return {
                    "success": True,
                    "version": local_version,
                    "scope": "local",
                    "shell_id": shell_id
                }
            else:
                print("No local Python version set")
                return {
                    "success": True,
                    "version": None,
                    "scope": "local",
                    "shell_id": shell_id
                }
                
        except Exception as e:
            return {"success": False, "error": f"Error getting local Python version: {str(e)}"}
    
    def pyenv_version(self):
        """显示当前使用的Python版本"""
        try:
            # 一次性读取状态文件，避免多次远程调用
            current_shell = self.shell.get_current_shell()
            shell_id = current_shell.get("id", "default") if current_shell else "default"
            
            # 构建一个命令来一次性获取所有需要的信息
            check_command = f'''
            STATE_FILE="{self.get_python_state_file_path()}"
            if [ -f "$STATE_FILE" ]; then
                python3 -c "
import json
try:
    with open('$STATE_FILE', 'r') as f:
        states = json.load(f)
    
    shell_key = 'shell_{shell_id}'
    local_version = states.get(shell_key, '')
    global_version = states.get('global', '')
    
    if local_version:
        print(f'{{local_version}}|local')
    elif global_version:
        print(f'{{global_version}}|global')
    else:
        print('|system')
except:
    print('|system')
"
            else
                echo "|system"
            fi
            '''
            
            result = self.shell.execute_command_interface("bash", ["-c", check_command])
            
            if result.get("success") and result.get("stdout"):
                version_info = result["stdout"].strip()
                if "|" in version_info:
                    version, source = version_info.split("|", 1)
                    
                    if version and source != "system":
                        if source == "local":
                            source = f"local (shell {shell_id})"
                        print(f"Current Python version: {version} ({source})")
                        return {
                            "success": True,
                            "version": version,
                            "source": source
                        }
            
            # 如果没有配置或出错，返回系统默认
            print("No Python version configured (using system default)")
            return {
                "success": True,
                "version": "system",
                "source": "system"
            }
                
        except Exception as e:
            return {"success": False, "error": f"Error getting current Python version: {str(e)}"}
    
    def getpyenv_versions(self):
        """显示所有已安装版本及当前版本标记"""
        try:
            # 使用单个远程命令同时获取已安装版本、当前版本和版本来源信息
            installed_versions, current_version, version_source = self.get_versions_and_current_unified()
            
            if not installed_versions:
                print("No Python versions installed")
                return {
                    "success": True,
                    "message": "No Python versions installed",
                    "versions": []
                }
            
            print(f"Installed Python versions ({len(installed_versions)} total):")
            for version in sorted(installed_versions):
                if version == current_version:
                    print(f"* {version}")  # 标记当前版本
                else:
                    print(f"  {version}")
            
            # 显示版本来源信息（已从统一命令获取）
            if version_source and current_version:
                print(f"Current: {current_version} ({version_source})")
            
            return {
                "success": True,
                "message": f"Listed {len(installed_versions)} installed Python versions",
                "versions": installed_versions,
                "current_version": current_version,
                "version_source": version_source
            }
            
        except Exception as e:
            return {"success": False, "error": f"Error listing Python versions: {str(e)}"}
    
    # 辅助方法
    def validate_version(self, version):
        """验证Python版本格式"""
        import re
        
        # 特殊版本标识符
        special_versions = ["system", "global"]
        if version in special_versions:
            return True
        
        # 标准版本格式：x.y.z 或 x.y
        pattern = r'^\d+\.\d+(\.\d+)?$'  # 匹配 x.y.z 或 x.y 格式
        return bool(re.match(pattern, version))
    
    def is_version_installed(self, version):
        """检查指定版本是否已安装"""
        try:
            installed_versions = self.get_installed_versions()
            return version in installed_versions
        except:
            return False
    
    def get_installed_versions(self):
        """获取所有已安装的Python版本 - 使用Google Drive API避免远端窗口"""
        try:
            # 使用统一的版本获取方法（通过Google Drive API）
            versions_info = self.get_versions_and_current_unified()
            if versions_info and "installed_versions" in versions_info:
                return versions_info["installed_versions"]
            else:
                return []
                
        except Exception as e:
            print(f"Warning: Error getting installed versions: {e}")
            return []
    
    def get_current_python_version(self):
        """获取当前使用的Python版本"""
        try:
            # 优先级：local > global > system
            current_shell = self.shell.get_current_shell()
            shell_id = current_shell.get("id", "default") if current_shell else "default"
            
            # 检查local版本
            local_version = self.get_python_state(f"shell_{shell_id}")
            if local_version:
                return local_version
            
            # 检查global版本
            global_version = self.get_python_state("global")
            if global_version:
                return global_version
            
            # 返回None表示使用系统默认
            return None
            
        except Exception as e:
            print(f"Warning: Error getting current Python version: {e}")
            return None
    
    def get_python_state(self, key):
        """从状态文件获取Python版本信息"""
        try:
            # 通过远程命令读取状态文件
            import json
            state_file = self.get_python_state_file_path()
            read_command = f'cat "{state_file}" 2>/dev/null || echo "{{}}"'
            result = self.shell.execute_command_interface("bash", ["-c", read_command])
            
            if result.get("success") and result.get("stdout"):
                try:
                    states = json.loads(result["stdout"])
                    return states.get(key)
                except json.JSONDecodeError:
                    return None
            else:
                return None
                
        except Exception as e:
            print(f"Warning: Error reading Python state: {e}")
            return None
    
    def update_python_state(self, key, value):
        """更新状态文件中的Python版本信息"""
        state_file = self.get_python_state_file_path()
            
        # 构建更新状态的远程命令
        update_command = f'''
# 确保目录存在
mkdir -p "{self.get_python_base_path()}"

# 更新状态
python3 -c "
import json
import sys
from datetime import datetime

try:
    with open('{state_file}', 'r') as f:
        states = json.load(f)
except:
    states = {{}}

states['{key}'] = '{value}'
states['{key}_updated_at'] = datetime.now().isoformat()

with open('{state_file}', 'w') as f:
    json.dump(states, f, indent=2, ensure_ascii=False)

print('State updated successfully')
"
'''
            
        result = self.shell.execute_command_interface("bash", ["-c", update_command])
        
        if not (result.get("success") and result.get("exit_code") == 0):
            raise Exception(f"Failed to update Python state: {result.get('error', 'Unknown error')}")
    
    def get_cached_available_versions(self):
        """获取缓存的可用Python版本列表"""
        cache_file = self.get_available_versions_cache_file()
        import json
        import os
        from datetime import datetime, timedelta
        
        # 检查缓存文件是否存在且未过期（7天）
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # 检查缓存是否过期
            cache_time = datetime.fromisoformat(cache_data.get("updated_at", "1970-01-01"))
            if datetime.now() - cache_time < timedelta(days=7):
                return cache_data.get("versions", [])
        
        # 缓存不存在或已过期，生成新的缓存
        return self.py_available_versions()
    
    def get_available_versions_cache_file(self):
        """获取可用版本缓存文件路径"""
        import os
        from ..path_constants import get_data_dir
        cache_dir = str(get_data_dir())
        cache_file = str(get_data_dir() / "python_available_versions.json")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_file
    
    def py_available_versions(self):
        """生成可用Python版本缓存（并发验证）"""
        import json
        from datetime import datetime
        import concurrent.futures
        import threading
        
        print("Updating Python versions cache...")
        
        # 生成更全面的Python版本候选列表
        candidate_versions = self.generate_python_version_candidates()
        verified_versions = []
        completed_count = 0
        total_count = len(candidate_versions)
        
        # 线程安全的进度更新
        progress_lock = threading.Lock()
        
        def verify_version_with_progress(version):
            nonlocal completed_count
            status = self.verify_python_version_availability(version)
            
            with progress_lock:
                completed_count += 1
                print(f"[{completed_count}/{total_count}] Python {version}: {status}")
            
            return {
                "version": version,
                "status": status,
                "tested_at": datetime.now().isoformat()
            }
        
        print(f"Testing {total_count} Python versions concurrently...")
        
        # 使用线程池并发验证（限制并发数避免过载）
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_version = {
                executor.submit(verify_version_with_progress, version): version 
                for version in candidate_versions
            }
            
            for future in concurrent.futures.as_completed(future_to_version):
                try:
                    result = future.result()
                    verified_versions.append(result)
                except Exception as e:
                    version = future_to_version[future]
                    print(f"Error testing {version}: {e}")
                    verified_versions.append({
                        "version": version,
                        "status": "failed",
                        "tested_at": datetime.now().isoformat()
                    })
        
        # 保存缓存
        cache_data = {
            "versions": verified_versions,
            "updated_at": datetime.now().isoformat()
        }
        
        cache_file = self.get_available_versions_cache_file()
        try:
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            print(f"Cache updated: {cache_file}")
        except Exception as e:
            print(f"Warning: Failed to save cache: {e}")
        
        return verified_versions
    
    def generate_python_version_candidates(self):
        """生成Python版本候选列表"""
        candidates = []
        
        # Python 2.x 系列 (常用的后期版本)
        for minor in [6, 7]:
            for patch in range(15, 19):  # 2.6.15-2.6.18, 2.7.15-2.7.18
                candidates.append(f"2.{minor}.{patch}")
        
        # Python 3.0-3.6 系列 (部分版本)
        for minor in range(0, 7):  # 3.0 到 3.6
            for patch in range(0, 3):  # 每个系列测试前几个版本
                candidates.append(f"3.{minor}.{patch}")
        
        # Python 3.7 系列
        for patch in range(0, 18):  # 3.7.0 到 3.7.17
            candidates.append(f"3.7.{patch}")
        
        # Python 3.8 系列 (全面覆盖)
        for patch in range(0, 21):  # 3.8.0 到 3.8.20
            candidates.append(f"3.8.{patch}")
        
        # Python 3.9 系列 (全面覆盖)
        for patch in range(0, 21):  # 3.9.0 到 3.9.20
            candidates.append(f"3.9.{patch}")
        
        # Python 3.10 系列 (全面覆盖)
        for patch in range(0, 16):  # 3.10.0 到 3.10.15
            candidates.append(f"3.10.{patch}")
        
        # Python 3.11 系列 (全面覆盖)
        for patch in range(0, 13):  # 3.11.0 到 3.11.12
            candidates.append(f"3.11.{patch}")
        
        # Python 3.12 系列 (全面覆盖)
        for patch in range(0, 15):  # 3.12.0 到 3.12.14
            candidates.append(f"3.12.{patch}")
        
        # Python 3.13 系列 (全面覆盖)
        for patch in range(0, 10):  # 3.13.0 到 3.13.9
            candidates.append(f"3.13.{patch}")
        
        # Python 3.14-3.20 系列 (未来版本，最多就是下载失败)
        for minor in range(14, 21):  # 3.14 到 3.20
            for patch in range(0, 5):  # 每个系列测试前5个版本
                candidates.append(f"3.{minor}.{patch}")
        
        print(f"Generated {len(candidates)} Python version candidates for testing")
        return candidates
    
    def verify_python_version_availability(self, version):
        """验证Python版本是否可用（使用HTTP HEAD请求检查，不实际下载）"""
        import subprocess
        import sys
        
        try:
            download_urls = []
            
            # 根据操作系统选择合适的URL
            is_windows = sys.platform == 'win32'
            is_macos = sys.platform == 'darwin'
            is_linux = sys.platform.startswith('linux')
            
            # Python 2.x 使用不同的URL模式
            if version.startswith('2.'):
                download_urls = [
                    f"https://www.python.org/ftp/python/{version}/Python-{version}.tgz",
                    f"https://github.com/python/cpython/archive/v{version}.tar.gz"
                ]
            else:
                # Python 3.x - 根据平台选择URL
                if is_windows:
                    download_urls = [
                        f"https://www.python.org/ftp/python/{version}/python-{version}-embed-amd64.zip",
                        f"https://www.python.org/ftp/python/{version}/python-{version}-amd64.exe",
                        f"https://www.python.org/ftp/python/{version}/Python-{version}.tgz",
                    ]
                else:
                    # macOS and Linux - 只使用源码包
                    download_urls = [
                        f"https://www.python.org/ftp/python/{version}/Python-{version}.tgz",
                        f"https://github.com/python/cpython/archive/v{version}.tar.gz"
                    ]
            
            for download_url in download_urls:
                try:
                    # 使用HTTP HEAD请求检查文件是否存在（不实际下载）
                    # 使用curl的--head选项只获取头信息
                    result = subprocess.run(
                        ["curl", "-s", "-I", "-L", "--max-time", "5", download_url],
                        capture_output=True,
                        timeout=10,
                        text=True
                    )
                    
                    if result.returncode == 0:
                        # 检查HTTP响应码
                        output = result.stdout
                        if "HTTP/1.1 200" in output or "HTTP/2 200" in output:
                            # 文件存在且可访问
                            return "verified"
                        elif "HTTP/1.1 302" in output or "HTTP/2 302" in output:
                            # 重定向，也算可用
                            return "verified"
                    
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue
                except Exception:
                    continue
            
            # 所有URL都失败
            return "failed"
            
        except Exception as e:
            return "failed"
    
    def add_installed_version(self, version):
        """添加已安装版本到状态文件"""
        try:
            installed_versions = self.get_installed_versions()
            if version not in installed_versions:
                installed_versions.append(version)
            
            self.update_python_state("installed_versions", json.dumps(sorted(installed_versions)))
            
        except Exception as e:
            print(f"Warning: Failed to update installed versions: {e}")
    
    def remove_installed_version(self, version):
        """从状态文件移除已安装版本"""
        try:
            installed_versions = self.get_installed_versions()
            if version in installed_versions:
                installed_versions.remove(version)
            
            self.update_python_state("installed_versions", json.dumps(sorted(installed_versions)))
            
        except Exception as e:
            print(f"Warning: Failed to update installed versions: {e}")

