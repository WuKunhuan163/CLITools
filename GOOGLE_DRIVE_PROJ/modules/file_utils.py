#!/usr/bin/env python3
"""
Google Drive Shell - File Utils Module
从google_drive_shell.py重构而来的file_utils模块
"""

import os
import sys
import json
import time
import hashlib
import warnings
import subprocess
import shutil
import zipfile
import tempfile
from pathlib import Path
import platform
import psutil
from typing import Dict
try:
    from ..google_drive_api import GoogleDriveService
except ImportError:
    from GOOGLE_DRIVE_PROJ.google_drive_api import GoogleDriveService

def get_multiline_input_safe(prompt, single_line=False):
    """
    安全的多行输入函数，支持Ctrl+D结束输入
    
    Args:
        prompt (str): 输入提示
        single_line (bool): 是否只接受单行输入
        
    Returns:
        str: 用户输入的内容，如果用户取消则返回None
    """
    try:
        # 配置readline以支持中文字符
        import readline
        try:
            readline.set_startup_hook(None)
            readline.clear_history()
            
            # 设置编辑模式为emacs（支持更好的中文编辑）
            readline.parse_and_bind("set editing-mode emacs")
            # 启用UTF-8支持
            readline.parse_and_bind("set input-meta on")
            readline.parse_and_bind("set output-meta on")
            readline.parse_and_bind("set convert-meta off")
            # 启用中文字符显示
            readline.parse_and_bind("set print-completions-horizontally off")
            readline.parse_and_bind("set skip-completed-text on")
            # 确保正确处理宽字符
            readline.parse_and_bind("set enable-bracketed-paste on")
        except Exception:
            pass  # 如果配置失败，继续使用默认设置
        
        print(prompt, end="", flush=True)
        
        if single_line:
            # 单行输入
            try:
                return input()
            except EOFError:
                return None
        else:
            # 多行输入，直到Ctrl+D
            lines = []
            print(f"(多行输入，按 Ctrl+D 结束):")
            try:
                while True:
                    line = input()
                    lines.append(line)
            except EOFError:
                # Ctrl+D被按下，结束输入
                pass
            
            return '\n'.join(lines) if lines else None
            
    except KeyboardInterrupt:
        # Ctrl+C被按下
        print(f"\n输入已取消")
        return None
    except Exception as e:
        print(f"\n输入错误: {e}")
        return None

class FileUtils:
    """Google Drive Shell File Utils"""

    def __init__(self, drive_service, main_instance=None):
        """初始化管理器"""
        self.drive_service = drive_service
        self.main_instance = main_instance
    
  # 引用主实例以访问其他属性

    def _zip_folder(self, folder_path, zip_path=None):
        """
        将文件夹打包成zip文件
        
        Args:
            folder_path (str): 要打包的文件夹路径
            zip_path (str): zip文件保存路径，如果为None则自动生成
            
        Returns:
            dict: 打包结果 {"success": bool, "zip_path": str, "error": str}
        """
        try:
            folder_path = Path(folder_path)
            if not folder_path.exists():
                return {"success": False, "error": f"文件夹不存在: {folder_path}"}
            
            if not folder_path.is_dir():
                return {"success": False, "error": f"路径不是文件夹: {folder_path}"}
            
            # 生成zip文件路径
            if zip_path is None:
                # 在临时目录中创建zip文件
                temp_dir = Path(tempfile.gettempdir())
                zip_filename = f"{folder_path.name}.zip"
                zip_path = temp_dir / zip_filename
            else:
                zip_path = Path(zip_path)
            
            # 创建zip文件
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 遍历文件夹中的所有文件和目录
                files_added = 0
                dirs_added = 0
                
                for file_path in folder_path.rglob('*'):
                    if file_path.is_file():
                        # 计算相对路径，使用文件夹名作为根目录
                        arcname = file_path.relative_to(folder_path.parent)
                        zipf.write(file_path, arcname)
                        files_added += 1
                    elif file_path.is_dir():
                        # 添加空目录到zip文件
                        arcname = file_path.relative_to(folder_path.parent)
                        # 确保目录名以/结尾
                        dir_arcname = str(arcname) + '/'
                        zipf.writestr(dir_arcname, '')
                        dirs_added += 1
                
                # 如果文件夹完全为空，至少添加根目录本身
                if files_added == 0 and dirs_added == 0:
                    root_dir_name = folder_path.name + '/'
                    zipf.writestr(root_dir_name, '')
                    dirs_added = 1
                        
            # 检查zip文件是否创建成功
            if zip_path.exists():
                file_size = zip_path.stat().st_size
                return {
                    "success": True,
                    "zip_path": str(zip_path),
                    "original_folder": str(folder_path),
                    "zip_size": file_size
                }
            else:
                return {"success": False, "error": "zip文件创建失败"}
                
        except Exception as e:
            return {"success": False, "error": f"打包过程出错: {e}"}

    def verify_files_available(self, file_moves):
        """
        验证文件是否在同步目录中可用
        
        Args:
            file_moves (list): 文件移动信息列表
            
        Returns:
            bool: 所有文件都可用返回True，否则返回False
        """
        try:
            import os
            for file_info in file_moves:
                filename = file_info["filename"]
                file_path = os.path.join(self.main_instance.LOCAL_EQUIVALENT, filename)
                if not os.path.exists(file_path):
                    return False
            return True
        except Exception as e:
            return False

    def check_large_files(self, source_files):
        """
        检查大文件（>1GB）并提供手动上传方案
        
        Args:
            source_files (list): 源文件路径列表
            
        Returns:
            tuple: (normal_files, large_files) - 正常文件和大文件列表
        """
        try:
            normal_files = []
            large_files = []
            GB_SIZE = 1024 * 1024 * 1024  # 1GB in bytes
            
            for file_path in source_files:
                expanded_path = self._expand_path(file_path)
                if os.path.exists(expanded_path):
                    file_size = os.path.getsize(expanded_path)
                    if file_size > GB_SIZE:
                        large_files.append({
                            "path": expanded_path,
                            "original_path": file_path,
                            "size_gb": file_size / GB_SIZE
                        })
                    else:
                        normal_files.append(expanded_path)
                else:
                    print(f"File does not exist: {file_path}")
            
            return normal_files, large_files
            
        except Exception as e:
            print(f"检查大文件时出错: {e}")
            return source_files, []

    def handle_large_files(self, large_files, target_path=".", current_shell=None):
        """处理大文件的手动上传，支持逐一跟进"""
        try:
            if not large_files:
                return {"success": True, "message": "没有大文件需要手动处理"}
            
            print(f"\n发现 {len(large_files)} 个大文件（>1GB），将逐一处理:")
            
            successful_uploads = []
            failed_uploads = []
            
            for i, file_info in enumerate(large_files, 1):
                print(f"\n{'='*60}")
                print(f"处理第 {i}/{len(large_files)} 个大文件")
                print(f"文件: {file_info['original_path']} ({file_info['size_gb']:.2f} GB)")
                print(f"{'='*60}")
                
                # 为单个文件创建临时上传目录
                single_upload_dir = Path(os.getcwd()) / f"_MANUAL_UPLOAD_{i}"
                single_upload_dir.mkdir(exist_ok=True)
                
                file_path = Path(file_info["path"])
                link_path = single_upload_dir / file_path.name
                
                # 删除已存在的链接
                if link_path.exists():
                    link_path.unlink()
                
                # 创建符号链接
                try:
                    link_path.symlink_to(file_path)
                    print(f"Prepared file: {file_path.name}")
                except Exception as e:
                    print(f"Error: Create link failed: {file_path.name} - {e}")
                    failed_uploads.append({
                        "file": file_info["original_path"],
                        "error": f"Create link failed: {e}"
                    })
                    continue
                
                # 确定目标文件夹URL
                target_folder_id = None
                target_url = None
                
                if current_shell and self.drive_service:
                    try:
                        # 尝试解析目标路径
                        if target_path == ".":
                            target_folder_id = self.get_current_folder_id(current_shell)
                        else:
                            target_folder_id, _ = self.main_instance.resolve_path(target_path, current_shell)
                        
                        if target_folder_id:
                            target_url = f"https://drive.google.com/drive/folders/{target_folder_id}"
                        else:
                            target_url = f"https://drive.google.com/drive/folders/{self.main_instance.REMOTE_ROOT_FOLDER_ID}"
                    except:
                        target_url = f"https://drive.google.com/drive/folders/{self.main_instance.REMOTE_ROOT_FOLDER_ID}"
                else:
                    target_url = f"https://drive.google.com/drive/folders/{self.main_instance.REMOTE_ROOT_FOLDER_ID}"
                
                # 打开文件夹和目标位置
                try:
                    import subprocess
                    import webbrowser
                    
                    # 打开本地文件夹
                    if platform.system() == "Darwin":  # macOS
                        subprocess.run(["open", str(single_upload_dir)])
                    elif platform.system() == "Windows":
                        os.startfile(str(single_upload_dir))
                    else:  # Linux
                        subprocess.run(["xdg-open", str(single_upload_dir)])
                    
                    # 打开目标Google Drive文件夹（不是DRIVE_EQUIVALENT）
                    webbrowser.open(target_url)
                    
                    print(f"Opened local folder: {single_upload_dir}")
                    print(f"Opened target Google Drive folder")
                    print(f"Please drag the file to the Google Drive target folder")
                    
                except Exception as e:
                    print(f"Warning: Open folder failed: {e}")
                
                # 等待用户确认
                try:
                    print(f"\nPlease complete the file upload and press Enter to continue...")
                    get_multiline_input_safe("按Enter键继续...", single_line=True)  # 等待用户确认
                    
                    # 清理临时目录
                    try:
                        if link_path.exists():
                            link_path.unlink()
                        single_upload_dir.rmdir()
                    except:
                        pass
                    
                    successful_uploads.append({
                        "file": file_info["original_path"],
                        "size_gb": file_info["size_gb"]
                    })
                    
                    print(f"File {i}/{len(large_files)} processed")
                    
                except KeyboardInterrupt:
                    print(f"\nError: User interrupted the large file upload process")
                    # 清理临时目录
                    try:
                        if link_path.exists():
                            link_path.unlink()
                        single_upload_dir.rmdir()
                    except:
                        pass
                    break
                except Exception as e:
                    print(f"Error: Error processing file: {e}")
                    failed_uploads.append({
                        "file": file_info["original_path"],
                        "error": str(e)
                    })
            
            print(f"\n{'='*60}")
            print(f"Large file processing completed:")
            print(f"Successful: {len(successful_uploads)} files")
            print(f"Error: Failed: {len(failed_uploads)} files")
            print(f"{'='*60}")
            
            return {
                "success": len(successful_uploads) > 0,
                "large_files_count": len(large_files),
                "successful_uploads": successful_uploads,
                "failed_uploads": failed_uploads,
                "message": f"Large file processing completed: {len(successful_uploads)}/{len(large_files)} files successful"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Error processing large file: {e}"}
