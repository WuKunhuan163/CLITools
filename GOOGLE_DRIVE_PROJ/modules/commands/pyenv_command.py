"""
Google Drive Shell - Pyenv Command Module

This module provides comprehensive Python version management functionality similar to pyenv,
but designed specifically for the Google Drive Shell remote environment.

Key Features:
- Python version installation from source (both remote and local download)
- Version switching with persistent shell state management
- Background installation support for long-running operations
- Automatic verification of installed Python versions
- Integration with remote environment management (@/python directory)
- State persistence across shell sessions
- Support for both global and local version settings

Commands:
- pyenv install <version>: Install Python version from remote source
- pyenv install-local <version>: Download locally and install remotely
- pyenv install-bg <version>: Background installation
- pyenv local <version>: Set local Python version for current shell
- pyenv global <version>: Set global Python version
- pyenv versions: List installed versions
- pyenv version: Show current version
- pyenv uninstall <version>: Remove installed version

Installation Process:
1. Download Python source code (remote or local)
2. Extract and configure build in temporary directory
3. Compile with optimizations
4. Verify installation by running python --version
5. Move to final location only if verification succeeds
6. Update state files and version tracking

Classes:
    PyenvCommand: Main pyenv command handler with comprehensive version management

Dependencies:
    - Remote compilation environment (gcc, make, etc.)
    - Upload/download functionality for source distribution
    - State management for version persistence
    - Background task management for long installations
"""

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
                    "error": "Usage: pyenv --install|--install-bg|--uninstall|--list|--global|--local|--version|--versions [version]"
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
                force = "--force" in args
                return self.pyenv_list(force=force)
            elif action == "--list-available":
                force = "--force" in args
                return self.pyenv_list_available(force=force)
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
                    "error": f"Unknown pyenv command: {action}. Supported commands: --install, --install-bg, --install-local, --uninstall, --list, --global, --local, --version, --versions"
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
        """安装指定Python版本（远端下载模式）
        
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
                    self.pyenv_uninstall(version)
            
            print(f"Installing Python {version}...")
            print(f"Installation method: Remote download")
            print(f"This may take several minutes...")
            
            # 阶段1：远端下载
            success, source_dir, error_msg = self._download_python_remote(version)
            if not success:
                return {"success": False, "error": error_msg}
            
            # 阶段2：统一编译安装
            compile_script = self._compile_and_install_python(version, source_dir, force)
            
            # 执行编译脚本
            result = self.shell.command_executor.execute_remote_script(compile_script)
            
            # 检查命令执行结果
            data = result.get("data", {})
            exit_code = data.get("exit_code", 1)
            
            if result.get("success") and exit_code == 0:
                # 更新状态文件
                self.add_installed_version(version)
                
                final_install_path = f"{self.main_instance.REMOTE_ENV}/python/{version}"
                return {
                    "success": True,
                    "message": f"Python {version} installed successfully",
                    "version": version,
                    "install_path": final_install_path
                }
            else:
                stderr = data.get("stderr", "")
                stdout = data.get("stdout", "")
                error_msg = f"Failed to install Python {version}"
                if stderr:
                    error_msg += f": {stderr}"
                elif stdout:
                    error_msg += f": {stdout}"
                
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            return {"success": False, "error": f"Error installing Python {version}: {str(e)}"}
    
    def _check_version_and_prepare_install(self, version, force=False):
        """验证版本并准备安装（处理已安装的情况）
        
        Args:
            version: Python版本号
            force: 是否强制覆盖已安装的版本
            
        Returns:
            dict: {"success": bool, "error": str} 如果失败；None 如果成功继续
        """
        if not self.validate_version(version):
            return {
                "success": False, 
                "error": f"Invalid Python version format: '{version}'. Expected format: x.y.z (e.g., 3.9.18)"
            }
        
        # 检查版本是否已安装
        if self.is_version_installed(version):
            if not force:
                return {
                    "success": False,
                    "error": f"Python {version} is already installed. Use --force to reinstall."
                }
            else:
                print(f"Python {version} is already installed. Forcing reinstallation...")
                # 直接使用pyenv_uninstall接口
                self.pyenv_uninstall(version)
        
        return None  # 成功，继续安装
    
    def _generate_install_script(self, version, temp_install_path, final_install_path, 
                                   source_preparation_script="", work_dir=None):
        """生成Python编译安装的bash脚本模板
        
        Args:
            version: Python版本号
            temp_install_path: 临时安装路径（用于编译安装）
            final_install_path: 最终安装路径（验证通过后移动到这里）
            source_preparation_script: 可选的源码准备脚本（下载或解压）
            work_dir: 工作目录（如果需要切换到特定目录）
            
        Returns:
            str: 完整的bash安装脚本
        """
        # 根据是否提供work_dir生成切换目录的命令
        cd_command = f'cd "{work_dir}"\n' if work_dir else ""
        
        return f'''
# 创建临时安装目录
mkdir -p "{temp_install_path}"

{cd_command}{source_preparation_script}

# 解压源码
echo "Extracting source code..."
tar -xzf Python-{version}.tgz
cd Python-{version}

# 配置编译选项 - 安装到临时目录（不使用优化以避免编译问题）
echo "Configuring Python {version}..."
./configure --prefix="{temp_install_path}" --with-ensurepip=install

if [ $? -ne 0 ]; then
    echo "Failed to configure Python {version}"
    rm -rf "{temp_install_path}"
    exit 1
fi

# 编译（使用多核加速）
echo "Compiling Python {version}..."
make -j$(nproc)

if [ $? -ne 0 ]; then
    echo "Failed to compile Python {version}"
    rm -rf "{temp_install_path}"
    exit 1
fi

# 安装到临时目录
echo "Installing Python {version} to temporary location..."
make install

if [ $? -ne 0 ]; then
    echo "Failed to install Python {version}"
    rm -rf "{temp_install_path}"
    exit 1
fi

# 设置执行权限
echo "Setting executable permissions..."
chmod -R 755 "{temp_install_path}/bin/"

# 验证安装 - 检查可执行文件并验证版本
echo "Verifying Python {version} installation..."
if [ -f "{temp_install_path}/bin/python3" ]; then
    # 测试Python可执行文件
    ACTUAL_VERSION=$("{temp_install_path}/bin/python3" --version 2>&1)
    echo "Installed version: $ACTUAL_VERSION"
    
    # 检查版本是否匹配
    if echo "$ACTUAL_VERSION" | grep -q "{version}"; then
        echo "Version verification successful"
        
        # 测试Python执行
        echo "Running test script..."
        {temp_install_path}/bin/python3 -c "import sys; print(f'Python {{{{sys.version}}}} is working correctly!')"
        
        if [ $? -eq 0 ]; then
            echo "✓ Python executable test passed"
            
            # 测试pip
            {temp_install_path}/bin/pip3 --version
            if [ $? -eq 0 ]; then
                echo "✓ pip is working correctly"
            fi
            
            # 移除旧版本（如果存在）
            if [ -d "{final_install_path}" ]; then
                echo "Removing existing version..."
                rm -rf "{final_install_path}"
            fi
            
            # 移动到最终位置
            echo "Moving to final location..."
            mv "{temp_install_path}" "{final_install_path}"
            
            echo "Python {version} installed successfully!"
            echo "Location: {final_install_path}"
            "{final_install_path}/bin/python3" --version
            exit 0
        else
            echo "✗ Python executable test failed"
            rm -rf "{temp_install_path}"
            exit 1
        fi
    else
        echo "Version verification failed: expected {version}, got $ACTUAL_VERSION"
        rm -rf "{temp_install_path}"
        exit 1
    fi
else
    echo "Installation verification failed: python3 executable not found"
    rm -rf "{temp_install_path}"
    exit 1
fi
'''

    def pyenv_install_bg(self, version, force=False):
        """在后台安装指定Python版本（直接在远程下载源码）
        
        Args:
            version: Python版本号
            force: 是否强制覆盖已安装的版本
        """
        # 验证版本并准备安装
        check_result = self._check_version_and_prepare_install(version, force)
        if check_result is not None:
            return check_result
        
        try:
            # 生成临时安装目录的hash名称
            import hashlib
            import time
            temp_hash = hashlib.md5(f"{version}_{int(time.time())}".encode()).hexdigest()[:8]
            temp_install_path = f"{self.main_instance.REMOTE_ENV}/python/.tmp_install_{temp_hash}"
            final_install_path = f"{self.main_instance.REMOTE_ENV}/python/{version}"
            
            # 生成源码准备脚本（下载源码）- 使用@/tmp作为临时下载目录
            build_dir = f"{self.main_instance.REMOTE_ENV}/tmp/python_download_{version}_{temp_hash}"
            source_prep = f'''
# 设置临时构建目录（@/tmp）
BUILD_DIR="{build_dir}"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# 下载Python源码（开放式显示进度）
echo "Downloading Python {version} source code..."
wget https://www.python.org/ftp/python/{version}/Python-{version}.tgz

if [ $? -ne 0 ]; then
    echo "Failed to download Python {version}"
    rm -rf "{temp_install_path}"
    cd /
    rm -rf "$BUILD_DIR"
    exit 1
fi
'''
            
            # 生成完整的安装脚本
            install_script = self._generate_install_script(
                version=version,
                temp_install_path=temp_install_path,
                final_install_path=final_install_path,
                source_preparation_script=source_prep
            )
            
            # 添加构建目录清理
            install_script += f'\n# 清理构建目录\ncd /\nrm -rf "{build_dir}"\n'
            
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
        # 验证版本并准备安装
        check_result = self._check_version_and_prepare_install(version, force)
        if check_result is not None:
            return check_result
        
        try:
            import tempfile
            import os
            import subprocess
            from pathlib import Path
            
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
                    # 尝试使用wget（开放式显示进度）
                    download_cmd = f"wget -O '{tarball_path}' '{download_url}'"
                    result = subprocess.run(download_cmd, shell=True, capture_output=False, text=True)
                    
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
                # 使用绝对路径避免在测试环境中的路径嵌套问题
                remote_tmp_path = f"{self.shell.REMOTE_ENV}/python_install_{version}"
                
                # 创建远程目录
                mkdir_result = self.shell.cmd_mkdir(remote_tmp_path, recursive=True)
                if not mkdir_result.get("success"):
                    import traceback
                    call_stack = ''.join(traceback.format_stack()[-3:])
                    return {
                        "success": False,
                        "error": f"Failed to create remote directory: {mkdir_result.get('error', f'Directory creation failed without specific error message. Call stack: {call_stack}')}"
                    }
                
                # 上传tar.gz文件到@路径 - 移除force=True以启用大文件检测
                from ..commands.upload_command import UploadCommand
                upload_cmd = UploadCommand(self.shell)
                upload_result = upload_cmd.cmd_upload([tarball_path], target_path=remote_tmp_path)
                
                if not upload_result.get("success"):
                    import traceback
                    call_stack = ''.join(traceback.format_stack()[-3:])
                    return {
                        "success": False,
                        "error": f"Failed to upload source code: {upload_result.get('error', f'Source code upload failed without specific error message. Call stack: {call_stack}')}"
                    }
                
                # 构建远程tarball路径
                tarball_filename = os.path.basename(tarball_path)
                remote_tarball_path = f"{remote_tmp_path}/{tarball_filename}"
                print(f"✓ Uploaded to {remote_tarball_path}")
                
                print(f"Step 3/4: Extracting and compiling (this may take 10-20 minutes)...")
                
                # 生成临时安装目录的hash名称
                import hashlib
                import time
                temp_hash = hashlib.md5(f"local_{version}_{int(time.time())}".encode()).hexdigest()[:8]
                temp_install_path = f"{self.shell.REMOTE_ENV}/python/.tmp_install_local_{temp_hash}"
                final_install_path = f"{self.shell.REMOTE_ENV}/python/{version}"
                work_dir = f"{self.shell.REMOTE_ENV}/python_install_{version}"
                
                # 生成完整的安装脚本（源码已经上传，无需下载）
                install_script = self._generate_install_script(
                    version=version,
                    temp_install_path=temp_install_path,
                    final_install_path=final_install_path,
                    source_preparation_script="",  # 源码已上传，无需准备
                    work_dir=work_dir
                )
                
                # 添加清理临时文件的命令
                install_script += f'''
# 清理临时文件
cd "{work_dir}"
cd ..
rm -rf "{work_dir}"
echo "Installation complete. Clean up done."
echo "Python {version} is now available at: {final_install_path}/bin/python3"
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
        
        # 构建卸载路径 - 转换为绝对路径
        python_base_path = self.get_python_base_path()
        absolute_python_base_path = python_base_path.replace("@", self.shell.REMOTE_ENV)
        install_path = f"{absolute_python_base_path}/{version}"
        
        print(f"Uninstalling Python {version}...")
        
        # 构建远程卸载命令 - 在远程环境中先更新状态文件，再删除目录
        state_file = f"{absolute_python_base_path}/python_states.json"
        
        uninstall_command = f'''
# 先更新状态文件，移除版本记录
if [ -f "{state_file}" ]; then
    # 使用Python来更新JSON状态文件
    python3 -c "
import json
import os
try:
    with open('{state_file}', 'r') as f:
        states = json.load(f)
    
    # 移除版本记录
    if 'installed_versions' in states and '{version}' in states['installed_versions']:
        states['installed_versions'].remove('{version}')
        print('Removed {version} from installed versions list')
    
    # 重置所有使用该版本的shell
    for shell_id in list(states.get('shell_versions', {{}}).keys()):
        if states['shell_versions'][shell_id] == '{version}':
            states['shell_versions'][shell_id] = 'system'
            print(f'Reset shell {{shell_id}} from {version} to system')
    
    # 如果全局版本是该版本，重置为system
    if states.get('global_version') == '{version}':
        states['global_version'] = 'system'
        print('Reset global version from {version} to system')
    
    # 写回文件
    with open('{state_file}', 'w') as f:
        json.dump(states, f, indent=2)
    
    print('Python states updated successfully')
except Exception as e:
    print(f'Warning: Could not update states file: {{e}}')
"
fi

# 然后删除安装目录
if [ -d "{install_path}" ]; then
    rm -rf "{install_path}"
    echo "Python {version} uninstalled successfully"
else
    echo "Python {version} directory not found (already removed)"
fi
echo "Python {version} uninstall completed"
'''
        
        # 执行远程卸载命令
        result = self.shell.execute_command_interface("bash", ["-c", uninstall_command])
        
        # 检查命令执行结果 - exit_code在data字段中
        data = result.get("data", {})
        exit_code = data.get("exit_code", 1)
        
        if result.get("success") and exit_code == 0:
            # 状态文件更新已在远程命令中完成，不需要本地更新
            return {
                "success": True,
                "message": f"Python {version} uninstalled successfully",
                "version": version
            }
        else:
            # 直接抛出异常，不包装错误
            import traceback
            call_stack = ''.join(traceback.format_stack()[-3:])  # 获取最近3层调用栈
            error_msg = result.get('error', f'Python uninstall failed without specific error message. Call stack: {call_stack}. \n\nResult: {result}. \n\nFull command: \n{uninstall_command}')
            raise RuntimeError(f"Failed to uninstall Python {version}: {error_msg}")
            
    
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
                print(f"Warning: Failed to list REMOTE_ENV: {remote_env_files.get('error', 'Directory listing failed without specific error message')}")
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
                print(f"Warning: Failed to list python directory: {python_files_result.get('error', 'Python directory listing failed without specific error message')}")
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
                    
                    # 获取当前shell ID
                    current_shell = self.shell.get_current_shell()
                    shell_id = current_shell.get("id", "default_shell") if current_shell else "default_shell"
                    local_key = f'shell_{shell_id}'
                    
                    # 确定当前版本和来源（优先级：local > global > None）
                    if local_key in states:
                        current_version = states[local_key]
                        version_source = f'local shell {shell_id}'
                    elif 'global' in states:
                        current_version = states['global']
                        version_source = 'global'
                        
                except (json.JSONDecodeError, Exception):
                    pass  # 状态文件解析失败，使用默认值
            
            return installed_versions, current_version, version_source
                
        except Exception as e:
            print(f"Warning: Error in unified version query: {e}")
            return [], None, "system"
    
    def pyenv_list_available(self, force=False):
        """列出可下载的Python版本（--list-available的实现，支持--force强制更新）"""
        return {
            "success": False,
            "error": "pyenv --list-available is not implemented yet. Please manually specify the Python version you want to install."
        }
    
    def pyenv_list(self, force=False):
        """列出可下载的Python版本"""
        try:
            if force:
                # 强制更新缓存
                print("Forcing cache update...")
                update_result = self.pyenv_update_cache()
                if not update_result.get("success"):
                    return update_result
            
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
            # 直接使用统一的版本获取方法，避免远程命令
            installed_versions, current_version, version_source = self.get_versions_and_current_unified()
            
            if current_version and current_version != "system":
                print(f"Current Python version: {current_version} ({version_source})")
                return {
                    "success": True,
                    "version": current_version,
                    "source": version_source
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
            installed_versions, current_version, version_source = self.get_versions_and_current_unified()
            return installed_versions if installed_versions else []
                
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
            # 通过特殊命令接口读取状态文件，避免弹出窗口
            import json
            state_file = self.get_python_state_file_path()
            
            # 使用特殊命令接口读取文件
            from .text_command import TextCommand
            text_cmd = TextCommand(self.shell)
            result = text_cmd.cmd_cat(state_file)
            
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
        # 获取当前shell以便进行路径扩展
        current_shell = self.shell.get_current_shell()
        
        # 扩展@路径为实际的REMOTE_ENV路径
        python_base_path = self.shell.path_resolver.resolve_remote_absolute_path("@/python", current_shell)
        state_file = self.shell.path_resolver.resolve_remote_absolute_path("@/python/python_states.json", current_shell)
            
        # 构建更新状态的远程命令
        update_command = f'''
# 确保目录存在
mkdir -p "{python_base_path}"

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
        
        # 检查命令是否成功执行 - 简化逻辑
        success = result.get("success", False)
        
        # 获取exit_code，优先从data字段获取
        exit_code = -1
        if 'data' in result and isinstance(result['data'], dict):
            exit_code = result['data'].get('exit_code', -1)
        else:
            exit_code = result.get("exit_code", -1)
        
        if not success or exit_code != 0:
            error_msg = result.get('error', 'Command execution failed')
            raise Exception(error_msg)
    
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
        
        print(f"Testing {total_count} Python versions concurrently (3 workers)...")
        print(f"Each test: download → configure → compile → test execution")
        print(f"This may take 30-60 minutes depending on version count...")
        
        # 使用线程池并发验证（3个worker，每个独立测试）
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
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
        
        # 🧪 TEMPORARY: 只测试Python 3.9系列（用于验证worker机制）
        for patch in range(0, 6):  # 3.9.0 到 3.9.5 (测试6个版本)
            candidates.append(f"3.9.{patch}")
        
        return candidates
        
        # === 以下是完整版本列表（暂时注释） ===
        
        # Python 3.6 系列
        for patch in range(0, 16):  # 3.6.0 到 3.6.15
            candidates.append(f"3.6.{patch}")
        
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
        """验证Python版本是否可用（实际下载并测试编译和执行）"""
        import subprocess
        import sys
        import os
        import tempfile
        import shutil
        
        # 创建临时目录进行测试
        temp_dir = tempfile.mkdtemp(prefix=f'python_verify_{version}_', dir=os.path.expanduser('~/tmp'))
        
        try:
            download_url = f"https://www.python.org/ftp/python/{version}/Python-{version}.tgz"
            
            # 1. 下载源码（带超时）
            download_result = subprocess.run(
                ['wget', '-q', '-O', f'{temp_dir}/Python-{version}.tgz', download_url],
                capture_output=True,
                text=True,
                timeout=60
            )
            if download_result.returncode != 0:
                return "download_failed"
            
            # 2. 解压
            extract_result = subprocess.run(
                ['tar', '-xzf', f'{temp_dir}/Python-{version}.tgz', '-C', temp_dir],
                capture_output=True,
                text=True,
                timeout=30
            )
            if extract_result.returncode != 0:
                return "extract_failed"
            
            source_dir = f'{temp_dir}/Python-{version}'
            install_dir = f'{temp_dir}/install'
            
            # 3. 配置（简单配置，不启用优化）
            configure_result = subprocess.run(
                ['./configure', f'--prefix={install_dir}'],
                cwd=source_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            if configure_result.returncode != 0:
                return "configure_failed"
            
            # 4. 编译（使用2核心，限制时间）
            make_result = subprocess.run(
                ['make', '-j2'],
                cwd=source_dir,
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )
            # 允许编译有警告，但检查segfault
            if 'Segmentation fault' in make_result.stderr:
                return "compile_segfault"
            if make_result.returncode != 0 and 'pybuilddir.txt' not in make_result.stderr:
                return "compile_failed"
            
            # 5. 安装
            install_result = subprocess.run(
                ['make', 'install'],
                cwd=source_dir,
                capture_output=True,
                text=True,
                timeout=180
            )
            # 安装可能因hard link失败但实际成功
            
            # 6. 查找Python可执行文件
            python_exe = None
            bin_dir = f'{install_dir}/bin'
            if os.path.exists(bin_dir):
                for fname in os.listdir(bin_dir):
                    if fname.startswith('python3.') and not fname.endswith('.1'):
                        python_exe = f'{bin_dir}/{fname}'
                        break
                if not python_exe and os.path.exists(f'{bin_dir}/python3'):
                    python_exe = f'{bin_dir}/python3'
            
            if not python_exe or not os.path.exists(python_exe):
                return "executable_not_found"
            
            # 7. 测试执行：输出版本号
            version_result = subprocess.run(
                [python_exe, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if version_result.returncode != 0:
                return "version_check_failed"
            
            # 8. 测试执行：运行简单代码
            code_result = subprocess.run(
                [python_exe, '-c', 'import sys; print(sys.version_info.major)'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if code_result.returncode != 0:
                return "code_execution_failed"
            
            # 所有测试通过
            return "verified"
            
        except subprocess.TimeoutExpired:
            return "timeout"
        except Exception as e:
            return f"error_{str(e)[:20]}"
        finally:
            # 清理临时目录
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
    
    def add_installed_version(self, version):
        """添加已安装版本到状态文件"""
        try:
            import json
            installed_versions = self.get_installed_versions()
            if version not in installed_versions:
                installed_versions.append(version)
            
            self.update_python_state("installed_versions", json.dumps(sorted(installed_versions)))
            
        except Exception as e:
            print(f"Warning: Failed to update installed versions: {e}")
    
    def remove_installed_version(self, version):
        """从状态文件移除已安装版本"""
        try:
            import json
            installed_versions = self.get_installed_versions()
            if version in installed_versions:
                installed_versions.remove(version)
            
            self.update_python_state("installed_versions", json.dumps(sorted(installed_versions)))
            
        except Exception as e:
            print(f"Warning: Failed to update installed versions: {e}")
    
    def _compile_and_install_python(self, version, source_dir, force=False):
        """统一的Python编译安装流程
        
        Args:
            version: Python版本号
            source_dir: 源码所在目录（@/tmp/python_download_{version}）
            force: 是否强制覆盖已安装版本
            
        Returns:
            str: bash脚本内容（用于execute_shell_command或execute_background_command）
        """
        import hashlib
        import time
        
        # 生成临时安装目录的hash名称
        temp_hash = hashlib.md5(f"{version}_{int(time.time())}".encode()).hexdigest()[:8]
        temp_install_path = f"{self.main_instance.REMOTE_ENV}/tmp/.tmp_install_{temp_hash}"
        final_install_path = f"{self.main_instance.REMOTE_ENV}/python/{version}"
        
        # 构建统一的编译安装脚本
        script = f'''
# ============================================================
# Python {version} 编译安装脚本（统一流程）
# ============================================================

# 源码目录
SOURCE_DIR="{source_dir}"

# 临时安装目录
TEMP_INSTALL="{temp_install_path}"
FINAL_INSTALL="{final_install_path}"

echo "[$(date +%H:%M:%S)] Starting Python {version} compilation and installation"
echo "[$(date +%H:%M:%S)] Source directory: $SOURCE_DIR"

# 检查源码目录是否存在
if [ ! -d "$SOURCE_DIR" ]; then
    echo "[$(date +%H:%M:%S)] ERROR: Source directory does not exist: $SOURCE_DIR"
    exit 1
fi

# 创建临时安装目录
echo "[$(date +%H:%M:%S)] Creating temporary install directory..."
mkdir -p "$TEMP_INSTALL"

# 进入源码目录
cd "$SOURCE_DIR"

# 查找解压后的Python源码目录
if [ -d "Python-{version}" ]; then
    cd "Python-{version}"
    echo "[$(date +%H:%M:%S)] Found extracted source: Python-{version}/"
elif [ -f "Python-{version}.tgz" ]; then
    echo "[$(date +%H:%M:%S)] Extracting source archive..."
    tar -xzf "Python-{version}.tgz"
    if [ $? -ne 0 ]; then
        echo "[$(date +%H:%M:%S)] ERROR: Failed to extract source archive"
        rm -rf "$TEMP_INSTALL"
        exit 1
    fi
    cd "Python-{version}"
    echo "[$(date +%H:%M:%S)] Source extracted successfully"
else
    echo "[$(date +%H:%M:%S)] ERROR: Source archive not found"
    rm -rf "$TEMP_INSTALL"
    exit 1
fi

# Configure
echo "[$(date +%H:%M:%S)] Configuring Python {version}..."
echo "[$(date +%H:%M:%S)] Prefix: $TEMP_INSTALL"
./configure --prefix="$TEMP_INSTALL" --enable-optimizations --with-ensurepip=install

if [ $? -ne 0 ]; then
    echo "[$(date +%H:%M:%S)] ERROR: Configure failed"
    rm -rf "$TEMP_INSTALL"
    exit 1
fi
echo "[$(date +%H:%M:%S)] Configure completed successfully"

# Compile
echo "[$(date +%H:%M:%S)] Compiling Python {version} (this may take 5-10 minutes)..."
make -j$(nproc)

if [ $? -ne 0 ]; then
    echo "[$(date +%H:%M:%S)] ERROR: Compilation failed"
    rm -rf "$TEMP_INSTALL"
    exit 1
fi
echo "[$(date +%H:%M:%S)] Compilation completed successfully"

# Install
echo "[$(date +%H:%M:%S)] Installing Python {version}..."
make install

if [ $? -ne 0 ]; then
    echo "[$(date +%H:%M:%S)] ERROR: Installation failed"
    rm -rf "$TEMP_INSTALL"
    exit 1
fi
echo "[$(date +%H:%M:%S)] Installation to temp directory completed"

# Verify installation
echo "[$(date +%H:%M:%S)] Verifying installation..."
if [ -f "$TEMP_INSTALL/bin/python3" ]; then
    ACTUAL_VERSION=$("$TEMP_INSTALL/bin/python3" --version 2>&1)
    echo "[$(date +%H:%M:%S)] Installed version: $ACTUAL_VERSION"
    
    # Check if version matches
    if echo "$ACTUAL_VERSION" | grep -q "{version}"; then
        echo "[$(date +%H:%M:%S)] Version verification successful"
        
        # Remove old version if exists
        if [ -d "$FINAL_INSTALL" ]; then
            echo "[$(date +%H:%M:%S)] Removing existing version..."
            rm -rf "$FINAL_INSTALL"
        fi
        
        # Move to final location
        echo "[$(date +%H:%M:%S)] Moving to final location: $FINAL_INSTALL"
        mv "$TEMP_INSTALL" "$FINAL_INSTALL"
        
        echo "[$(date +%H:%M:%S)] Python {version} installed successfully"
        echo "[$(date +%H:%M:%S)] Location: $FINAL_INSTALL"
        "$FINAL_INSTALL/bin/python3" --version
    else
        echo "[$(date +%H:%M:%S)] ERROR: Version verification failed"
        echo "[$(date +%H:%M:%S)] Expected {version}, got $ACTUAL_VERSION"
        rm -rf "$TEMP_INSTALL"
        exit 1
    fi
else
    echo "[$(date +%H:%M:%S)] ERROR: python3 executable not found"
    rm -rf "$TEMP_INSTALL"
    exit 1
fi

# Clean up source directory (optional)
echo "[$(date +%H:%M:%S)] Cleaning up source directory..."
rm -rf "$SOURCE_DIR"

echo "[$(date +%H:%M:%S)] All done!"
'''
        return script
    
    def _download_python_remote(self, version):
        """远端下载Python源码到统一目录
        
        Args:
            version: Python版本号
            
        Returns:
            tuple: (success: bool, source_dir: str, error_msg: str)
        """
        download_dir = f"{self.main_instance.REMOTE_ENV}/tmp/python_download_{version}"
        
        # 构建远端下载脚本
        download_script = f'''
# ============================================================
# Python {version} 远端下载脚本
# ============================================================

DOWNLOAD_DIR="{download_dir}"

echo "[$(date +%H:%M:%S)] Starting remote download of Python {version}"

# 清理旧的下载目录
if [ -d "$DOWNLOAD_DIR" ]; then
    echo "[$(date +%H:%M:%S)] Removing old download directory..."
    rm -rf "$DOWNLOAD_DIR"
fi

# 创建下载目录
echo "[$(date +%H:%M:%S)] Creating download directory: $DOWNLOAD_DIR"
mkdir -p "$DOWNLOAD_DIR"
cd "$DOWNLOAD_DIR"

# 下载Python源码
echo "[$(date +%H:%M:%S)] Downloading Python {version} from python.org..."
wget -q --show-progress https://www.python.org/ftp/python/{version}/Python-{version}.tgz

if [ $? -ne 0 ]; then
    echo "[$(date +%H:%M:%S)] ERROR: Failed to download Python {version}"
    rm -rf "$DOWNLOAD_DIR"
    exit 1
fi

echo "[$(date +%H:%M:%S)] Download completed: Python-{version}.tgz"
ls -lh "Python-{version}.tgz"

echo "[$(date +%H:%M:%S)] Remote download successful!"
echo "[$(date +%H:%M:%S)] Source location: $DOWNLOAD_DIR"
'''
        
        # 执行下载脚本
        result = self.shell.execute_shell_command(download_script, command_identifier=None)
        
        if result != 0:
            return False, None, f"Failed to download Python {version} on remote"
        
        return True, download_dir, ""
    
    def _download_python_local(self, version):
        """本地下载Python源码并上传到统一目录
        
        Args:
            version: Python版本号
            
        Returns:
            tuple: (success: bool, source_dir: str, error_msg: str)
        """
        import tempfile
        import subprocess
        import os
        import shutil
        
        download_dir = f"{self.main_instance.REMOTE_ENV}/tmp/python_download_{version}"
        
        print(f"Step 1/3: Downloading Python {version} source code locally...")
        
        # 创建本地临时目录
        local_temp_dir = tempfile.mkdtemp(prefix=f"python_{version}_")
        
        try:
            # 本地下载
            download_url = f"https://www.python.org/ftp/python/{version}/Python-{version}.tgz"
            local_tgz = os.path.join(local_temp_dir, f"Python-{version}.tgz")
            
            result = subprocess.run(
                ["wget", "-q", "--show-progress", "-O", local_tgz, download_url],
                timeout=600
            )
            
            if result.returncode != 0:
                shutil.rmtree(local_temp_dir, ignore_errors=True)
                return False, None, f"Failed to download Python {version} locally"
            
            file_size = os.path.getsize(local_tgz) / 1024 / 1024
            print(f"Downloaded: {file_size:.1f} MB")
            
            print(f"Step 2/3: Uploading to remote: {download_dir}...")
            
            # 创建远程目录
            mkdir_result = self.shell.cmd_mkdir(download_dir, recursive=True)
            if not mkdir_result.get("success"):
                shutil.rmtree(local_temp_dir, ignore_errors=True)
                return False, None, f"Failed to create remote directory: {download_dir}"
            
            # 上传源码包
            upload_result = self.shell.cmd_upload(
                local_path=local_tgz,
                remote_path=download_dir,
                is_folder=False,
                command_identifier=None
            )
            
            if upload_result != 0:
                shutil.rmtree(local_temp_dir, ignore_errors=True)
                return False, None, f"Failed to upload source code to {download_dir}"
            
            print(f"Upload completed!")
            
            # 清理本地临时文件
            shutil.rmtree(local_temp_dir, ignore_errors=True)
            
            return True, download_dir, ""
            
        except Exception as e:
            shutil.rmtree(local_temp_dir, ignore_errors=True)
            return False, None, f"Error during local download: {str(e)}"

