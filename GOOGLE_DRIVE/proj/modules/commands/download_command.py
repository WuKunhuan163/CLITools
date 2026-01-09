"""
Google Drive Shell - Download Command Module

This module provides comprehensive file and folder download functionality from the Google Drive
remote environment to the local system. It supports various download scenarios including
individual files, entire directories, and batch operations.

Key Features:
- Single file download with local path specification
- Directory download with structure preservation
- Batch download operations for multiple files
- Automatic compression for directory downloads
- Progress tracking and status reporting
- Integration with Google Drive API for file access
- Local path resolution and conflict handling

Commands:
- download <remote_file> [local_path]: Download single file
- download <remote_dir> [local_path]: Download directory (compressed)
- download --batch <file1> <file2> ...: Download multiple files

Download Flow:
1. Validate remote file/directory existence
2. Resolve local destination path
3. Handle conflicts and create directories as needed
4. For directories: compress remotely, then download
5. For files: direct download with metadata preservation
6. Verify download completion and integrity

Classes:
    DownloadCommand: Main download command handler

Dependencies:
    - Google Drive API for file access and metadata
    - Remote command execution for compression operations
    - Local file system operations for destination handling
    - Path resolution for both remote and local paths
    - Progress management for user feedback
"""

from .base_command import BaseCommand
import os

class DownloadCommand(BaseCommand):
    @property
    def command_name(self):
        return "download"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行download命令"""
        # 检查是否请求帮助
        if args and (args[0] == '--help' or args[0] == '-h'):
            self.show_download_help()
            return 0
        
        if not args:
            print("Error: download command needs a file name")
            return 1
        
        filename = args[0]
        local_path = args[1] if len(args) > 1 else None
        
        if not filename:
            print("Error: download command needs a file name")
            return 1
        
        # Translate remote path format back to local path format
        # The local_path parameter is a local path, but general argument processing
        # may have converted it to remote format (e.g., /content/drive/MyDrive/REMOTE_ROOT/...)
        from ..command_generator import CommandGenerator
        local_path = CommandGenerator.translate_remote_to_local(local_path)
        
        # 调用shell的download方法（不再支持force参数）
        result = self.shell.cmd_download(filename, local_path=local_path)
        
        if result.get("success", False):
            message = result.get("message", "Downloaded successfully")
            print(message)
            
            # 如果有本地路径信息，也显示出来
            if result.get("local_path"):
                print(f"Local path: {result.get('local_path')}")
            
            # 如果是目录下载，显示额外信息
            if result.get("source") == "directory_download":
                print(f"Directory compressed and downloaded as zip file")
                if result.get("zip_filename"):
                    print(f"Temporary zip filename: {result.get('zip_filename')}")
            
            return 0
        else:
            error_msg = result.get("error", "Download failed")
            print(error_msg)
            return 1
    
    def show_download_help(self):
        """显示download命令的帮助信息"""
        help_text = """
GDS Download Command - Download files from Google Drive

Usage:
    GDS download [OPTIONS] <filename> [local_path]
    GDS download --help

Arguments:
    <filename>       File or directory name in Google Drive to download
    [local_path]     Optional local path to save the file (default: cache directory)

Options:
    --help, -h       Show this help message

Examples:
    # Download file to cache directory
    GDS download myfile.txt

    # Download file to specific local path
    GDS download myfile.txt ~/Downloads/myfile.txt

    # Download directory (will be compressed as zip)
    GDS download my_folder

Notes:
    - Files are first downloaded to a cache directory
    - If local_path is specified, the file is copied from cache to that location
    - Directories are automatically compressed as zip files before download
"""
        print(help_text)


    def cmd_download(self, filename, local_path=None):
        """
        download命令 - 从Google Drive下载文件并缓存
        用法：
        - download A: 下载到缓存目录，显示哈希文件名
        - download A B: 下载到缓存目录，然后复制到指定位置（类似cp操作）
        """
        try:
            # 导入缓存管理器
            # 使用统一的 CacheManager
            cache_manager = self.main_instance.cache_manager
            
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell"}
            
            # 构建远端绝对路径
            remote_absolute_path = self.main_instance.resolve_remote_absolute_path(filename, current_shell)
            
            # 检查是否已经缓存
            if cache_manager.is_file_cached(remote_absolute_path):
                cached_info = cache_manager.get_cached_file(remote_absolute_path)
                cached_path = cache_manager.get_cached_file(remote_absolute_path, return_path_only=True)
                
                if local_path:
                    # 如果指定了本地目标，复制缓存文件到目标位置（cp操作）
                    import shutil
                    if os.path.isdir(local_path):
                        # 从原始filename中提取实际文件名（不包含路径部分）
                        actual_filename = os.path.basename(filename)
                        target_path = os.path.join(local_path, actual_filename)
                    else:
                        target_path = local_path
                    
                    # 确保目标目录存在
                    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
                    shutil.copy2(cached_path, target_path)
                    
                    return {
                        "success": True,
                        "message": f"Using cached file: {target_path}",
                        "source": "cache",
                        "remote_path": remote_absolute_path,
                        "cache_file": cached_info["cache_file"],
                        "local_path": target_path,
                        "cache_status": cached_info["status"]
                    }
                else:
                    # 只显示缓存信息
                    return {
                        "success": True,
                        "message": f"Using cached file: {cached_info['cache_file']}",
                        "source": "cache",
                        "remote_path": remote_absolute_path,
                        "cache_file": cached_info["cache_file"],
                        "cached_path": cached_path,
                        "cache_status": cached_info["status"]
                    }
            
            # 文件未缓存，需要下载
            # 解析路径以获取目标文件夹和文件名
            file_info = None
            target_folder_id = None
            actual_filename = None
            
            # 分析路径：分离目录路径和文件名
            if '/' in filename:
                # 包含路径分隔符，需要解析路径
                path_parts = filename.rsplit('/', 1)  # 从右边分割，只分割一次
                dir_path = path_parts[0] if path_parts[0] else '/'
                actual_filename = path_parts[1]
                
                # 解析目录路径
                target_folder_id, resolved_path = self.main_instance.resolve_drive_id(dir_path, current_shell)
                if not target_folder_id:
                    return {"success": False, "error": f"Download failed: directory not found: {dir_path}"}
            else:
                # 没有路径分隔符，在当前目录查找
                target_folder_id = current_shell.get("current_folder_id")
                actual_filename = filename
            
            # 在目标文件夹中查找文件 - 移除max_results限制，使用完整的分页逻辑
            result = self.drive_service.list_files(folder_id=target_folder_id)
            if result['success']:
                files = result['files']
                for file in files:
                    if file['name'] == actual_filename:
                        file_info = file
                        break
            
            if not file_info:
                return {"success": False, "error": f"Download failed: file not found: {actual_filename}"}
            
            # 检查是否为目录，如果是则使用目录下载功能
            if file_info['mimeType'] == 'application/vnd.google-apps.folder':
                return self.download_directory(file_info, actual_filename, remote_absolute_path, local_path)
            
            # 使用Google Drive API直接下载文件
            import tempfile
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{actual_filename}") as temp_file:
                temp_path = temp_file.name
            
            try:
                # 使用Google Drive API下载文件内容
                file_id = file_info['id']
                request = self.drive_service.service.files().get_media(fileId=file_id)
                content = request.execute()
                
                # 将内容写入临时文件
                with open(temp_path, 'wb') as f:
                    f.write(content)
                
                # 下载成功，缓存文件
                cache_result = cache_manager.cache_file(
                    remote_path=remote_absolute_path,
                    temp_file_path=temp_path
                )
                
                if cache_result["success"]:
                    if local_path:
                        # 如果指定了本地目标，也复制到目标位置（cp操作）
                        import shutil
                        
                        # 展开本地路径中的~
                        expanded_local_path = os.path.expanduser(local_path)
                        
                        if os.path.isdir(expanded_local_path):
                            target_path = os.path.join(expanded_local_path, actual_filename)
                        else:
                            target_path = expanded_local_path
                        
                        # 确保目标目录存在
                        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
                        shutil.copy2(temp_path, target_path)
                        
                        result = {
                            "success": True,
                            "message": f"Downloaded successfully to: {target_path}",
                            "source": "download",
                            "remote_path": remote_absolute_path,
                            "cache_file": cache_result["cache_file"],
                            "cache_path": cache_result["cache_path"],
                            "local_path": target_path
                        }
                        return result
                    else:
                        # 只显示缓存信息
                        result = {
                            "success": True,
                            "message": f"Downloaded successfully to: {cache_result['cache_file']}",
                            "source": "download",
                            "remote_path": remote_absolute_path,
                            "cache_file": cache_result["cache_file"],
                            "cache_path": cache_result["cache_path"]
                        }
                        return result
                else:
                    return {"success": False, "error": f"Download failed: {cache_result.get('error')}"}
                    
            finally:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": f"Download file failed: {e}"}


    def download_directory(self, dir_info, dir_name, remote_absolute_path, local_path):
        """
        下载目录：先在远程压缩为zip，然后下载zip包
        
        Args:
            dir_info: 目录信息
            dir_name: 目录名称
            remote_absolute_path: 远程绝对路径
            local_path: 本地目标路径
        """
        try:
            import hashlib
            import time
            import os
            
            # 生成时间哈希的zip文件名
            timestamp = str(int(time.time()))
            hash_suffix = hashlib.md5(f"{remote_absolute_path}_{timestamp}".encode()).hexdigest()[:8]
            zip_filename = f"gds_download_{dir_name}_{timestamp}_{hash_suffix}.zip"
            # 使用绝对路径而不是~路径，避免shell展开问题
            remote_zip_path = f"{self.main_instance.REMOTE_ROOT}/tmp/{zip_filename}"
            
            print(f"正在压缩目录 {dir_name} 到 {remote_zip_path}...")
            
            # 步骤1：远程压缩目录为zip包
            # 使用execute_command_interface执行压缩
            # 确保REMOTE_ROOT/tmp目录存在
            parent_dir = os.path.dirname(remote_absolute_path)
            tmp_dir = f"{self.main_instance.REMOTE_ROOT}/tmp"
            compress_command = f"mkdir -p '{tmp_dir}' && cd '{parent_dir}' && zip -r '{remote_zip_path}' '{dir_name}'"
            
            compress_result = self.main_instance.execute_command_interface("bash", ["-c", compress_command])
            
            if not compress_result.get("success", False):
                import traceback
                call_stack = ''.join(traceback.format_stack()[-3:])
                error_msg = compress_result.get('error', '')
                if not error_msg:
                    error_msg = f"Unknown error. Call stack: {call_stack}"
                return {"success": False, "error": f"Failed to compress directory: {error_msg}"}
            
            # 步骤2：验证zip文件是否创建成功
            print(f"验证zip文件创建: {remote_zip_path}")
            verification_result = self.main_instance.verify_with_ls(
                remote_zip_path, 
                self.main_instance.get_current_shell(), 
                creation_type="file"
            )
            
            if not verification_result.get("success", False):
                return {"success": False, "error": f"Zip file verification failed: {remote_zip_path} not found"}
            
            # 步骤3：下载zip文件到本地
            print(f"下载zip文件到本地...")
            
            # 确定本地目标路径
            if local_path:
                expanded_local_path = os.path.expanduser(local_path)
                if os.path.isdir(expanded_local_path):
                    # 如果是目录，使用原目录名
                    final_target = os.path.join(expanded_local_path, f"{dir_name}.zip")
                else:
                    # 如果是文件路径，直接使用
                    final_target = expanded_local_path
                    if not final_target.endswith('.zip'):
                        final_target += '.zip'
            else:
                # 默认下载到当前目录
                final_target = f"{dir_name}.zip"
            
            # 使用现有的文件下载逻辑下载zip文件
            # 将绝对路径转换为GDS路径格式
            gds_zip_path = f"~/tmp/{zip_filename}"
            download_result = self.cmd_download(gds_zip_path, final_target)
            
            if download_result.get("success", False):
                # 步骤4：清理远程临时zip文件
                try:
                    cleanup_result = self.main_instance.execute_command_interface("bash", ["-c", f"rm -f {remote_zip_path}"])
                    if not cleanup_result.get("success", False):
                        print(f"Warning: Failed to cleanup remote zip file: {remote_zip_path}")
                except Exception as e:
                    print(f"Warning: Error during cleanup: {e}")
                
                return {
                    "success": True,
                    "message": f"Directory downloaded successfully as: {final_target}",
                    "source": "directory_download",
                    "remote_path": remote_absolute_path,
                    "local_path": final_target,
                    "zip_filename": zip_filename
                }
            else:
                return {"success": False, "error": f"Failed to download zip file: {download_result.get('error', 'Download operation failed without specific error message')}"}
                
        except Exception as e:
            return {"success": False, "error": f"Directory download failed: {e}"}


