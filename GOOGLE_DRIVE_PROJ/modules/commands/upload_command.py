"""
Google Drive Shell - Upload Command Module

This module handles all file and folder upload operations to Google Drive.
It provides comprehensive upload functionality with support for both small and large files,
automatic file type detection, and intelligent handling of mixed upload scenarios.

Key Features:
- Small file upload via LOCAL_EQUIVALENT synchronization
- Large file upload via manual drag-and-drop interface
- Mixed upload scenarios with unified file movement
- Automatic file size detection and routing
- Progress tracking and user feedback
- Tkinter-based interactive windows for large file uploads
- Comprehensive error handling and retry mechanisms
- Support for folder uploads with structure preservation

Classes:
    UploadCommand: Main upload command handler with support for various upload scenarios

Upload Flow:
1. File analysis and size-based routing (small vs large files)
2. Small files: Upload to LOCAL_EQUIVALENT → Sync → Move to target
3. Large files: Manual upload to DRIVE_EQUIVALENT → Sync → Move to target
4. Mixed uploads: Parallel processing with unified final move operation

Dependencies:
    - Google Drive Desktop for file synchronization
    - Tkinter for large file upload interface
    - Path resolution and validation systems
    - Progress management and user feedback systems
"""

import os
import tempfile
import zipfile
from pathlib import Path
from ..command_executor import debug_capture, debug_print
from .base_command import BaseCommand
from ..system_utils import ensure_google_drive_desktop_running


class UploadCommand(BaseCommand):
    """上传命令"""
    
    @property
    def command_name(self):
        return "upload"
    
    def __init__(self, main_instance):
        super().__init__(main_instance)
        self.main_instance = main_instance
        self.drive_service = main_instance.drive_service
    
    def execute(self, cmd, args, **kwargs):
        """执行上传命令（BaseCommand要求的方法）"""
        # 检查是否请求帮助
        if args and (args[0] == '--help' or args[0] == '-h'):
            if cmd == 'upload_folder':
                self.show_upload_folder_help()
            else:
                self.show_upload_help()
            return 0
        
        # 检查是否是 upload_folder 命令
        if cmd == 'upload_folder':
            return self.execute_upload_folder(args)
        
        # 解析参数: upload [--target-dir TARGET] [--force] <files...>
        # 或者：upload [--force] <source> <target> （类似cp命令的语法）
        target_path = "."
        force = False
        source_files = []
        
        i = 0
        while i < len(args):
            if args[i] == '--target-dir':
                if i + 1 < len(args):
                    target_path = args[i + 1]
                    i += 2
                else:
                    print("Error: --target-dir option requires a directory path")
                    return 1
            elif args[i] == '--force':
                force = True
                i += 1
            else:
                # 剩余的参数都是源文件或目标路径
                source_files.append(args[i])
                i += 1
        
        if not source_files:
            print("Error: No source files specified")
            return 1
        
        # 检测是否使用了 cp 风格的语法：如果没有指定 --target-dir 且有多个参数，
        # 最后一个参数可能是目标路径
        if target_path == "." and len(source_files) >= 2:
            # 检查最后一个参数是否看起来像目标路径
            last_arg = source_files[-1]
            # 如果最后一个参数包含斜杠或以 ~ 开头，可能是路径
            # 但还需要检查它是否是实际存在的本地文件
            import os
            if ('/' in last_arg or last_arg.startswith('~')) and not os.path.exists(os.path.expanduser(last_arg)):
                # 最后一个参数看起来像路径且不是本地文件，将其视为目标路径
                target_path = last_arg
                source_files = source_files[:-1]
                print(f"[DEBUG] 检测到cp风格语法: source_files={source_files}, target_path={target_path}")
        
        # Translate remote path format back to local path format
        # source_files are local paths, but general argument processing
        # may have converted them to remote format (e.g., /content/drive/MyDrive/REMOTE_ROOT/...)
        print(f"[DEBUG upload] 原始source_files: {source_files}")
        from ..command_generator import CommandGenerator
        corrected_source_files = [CommandGenerator.translate_remote_to_local(file_path) for file_path in source_files]
        print(f"[DEBUG upload] 转换后corrected_source_files: {corrected_source_files}")
        
        # 调用cmd_upload
        result = self.cmd_upload(corrected_source_files, target_path=target_path, force=force)
        
        if result.get("success"):
            return 0
        else:
            error_msg = result.get("error", "Upload failed")
            print(error_msg)
            return 1
    
    def show_upload_help(self):
        """显示upload命令的帮助信息"""
        help_text = """
GDS Upload Command - Upload files to Google Drive

Usage:
    GDS upload [OPTIONS] <file1> [file2 ...]
    GDS upload --help

Arguments:
    <files>          One or more local files to upload

Options:
    --target-dir <dir>    Target directory in Google Drive (default: current directory)
    --force               Force overwrite if file already exists
    --help, -h            Show this help message

Examples:
    # Upload a single file to current directory
    GDS upload myfile.txt

    # Upload multiple files
    GDS upload file1.txt file2.txt file3.txt

    # Upload to a specific directory
    GDS upload --target-dir ~/documents myfile.txt

    # Force overwrite existing files
    GDS upload --force myfile.txt

    # Upload to a specific directory with force
    GDS upload --target-dir ~/documents --force myfile.txt

Notes:
    - Large files (>100MB) will trigger a confirmation prompt
    - Files are uploaded to the remote Google Drive environment
    - Use 'upload-folder' command to upload entire directories
"""
        print(help_text)
    
    def show_upload_folder_help(self):
        """显示upload-folder命令的帮助信息"""
        help_text = """
GDS Upload-Folder Command - Upload entire directories to Google Drive

Usage:
    GDS upload-folder [OPTIONS] <folder>
    GDS upload-folder --help

Arguments:
    <folder>         Local folder to upload

Options:
    --target-dir <dir>    Target directory in Google Drive (default: current directory)
    --keep-zip            Keep the temporary zip file after upload
    --force               Force overwrite if folder already exists
    --help, -h            Show this help message

Examples:
    # Upload a folder to current directory
    GDS upload-folder my_folder

    # Upload to a specific directory
    GDS upload-folder --target-dir ~/documents my_folder

    # Keep the zip file after upload
    GDS upload-folder --keep-zip my_folder

    # Force overwrite existing folder
    GDS upload-folder --force my_folder

Notes:
    - The folder is automatically zipped before upload
    - The zip file is extracted on the remote side
    - Use --keep-zip to preserve the temporary zip file
    - Large folders may take time to zip and upload
"""
        print(help_text)
    
    def execute_upload_folder(self, args):
        """执行upload_folder命令"""
        # 解析参数: upload_folder [--target-dir TARGET] [--keep-zip] [--force] <folder>
        target_path = "."
        keep_zip = False
        force = False
        folder_path = None
        
        i = 0
        while i < len(args):
            if args[i] == '--target-dir':
                if i + 1 < len(args):
                    target_path = args[i + 1]
                    i += 2
                else:
                    print("Error: --target-dir option requires a directory path")
                    return 1
            elif args[i] == '--keep-zip':
                keep_zip = True
                i += 1
            elif args[i] == '--force':
                force = True
                i += 1
            else:
                folder_path = args[i]
                i += 1
        
        if not folder_path:
            print("Error: No folder path specified")
            return 1
        
        # Translate remote path format back to local path format
        # folder_path is a local path, but general argument processing
        # may have converted it to remote format (e.g., /content/drive/MyDrive/REMOTE_ROOT/...)
        from ..command_generator import CommandGenerator
        folder_path = CommandGenerator.translate_remote_to_local(folder_path)
        
        # 调用cmd_upload_folder
        result = self.cmd_upload_folder(folder_path, target_path=target_path, keep_zip=keep_zip, force=force)
        
        if result.get("success"):
            return 0
        else:
            error_msg = result.get("error", "Folder upload failed")
            print(error_msg)
            return 1
    
    
    
    def check_remote_file_conflicts(self, source_files, target_path):
        """检查远程文件是否已存在（用于非force模式）"""
        try:
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell"}
            
            conflicts = []
            
            # 获取目标目录中的文件列表
            ls_result = self.main_instance.cmd_ls(target_path, detailed=False, recursive=False)
            if not ls_result.get("success"):
                # 如果无法列出文件（可能是目录不存在），则认为没有冲突
                return {"success": True, "conflicts": []}
            
            # 获取远程文件名列表
            remote_files = set()
            if ls_result.get("files"):
                for file_info in ls_result["files"]:
                    remote_files.add(file_info["name"])
            
            # 检查每个源文件是否在远程已存在
            for source_file in source_files:
                if not os.path.exists(source_file):
                    continue
                
                filename = os.path.basename(source_file)
                if filename in remote_files:
                    conflicts.append({
                        "local_file": source_file,
                        "remote_file": filename,
                        "reason": "File already exists in remote directory"
                    })
            
            if conflicts:
                conflict_files = [c["remote_file"] for c in conflicts]
                return {
                    "success": False,
                    "conflicts": conflicts,
                    "error": f"\nFile exists: {', '.join(conflict_files)}. Use --force to override."
                }
            
            return {"success": True, "conflicts": []}
            
        except Exception as e:
            # 如果检查过程出错，允许继续上传（保守处理）
            debug_print(f"Remote file conflict check failed: {e}")
            return {"success": True, "conflicts": []}
    
    def cmd_upload_folder(self, folder_path, target_path=".", keep_zip=False, force=False):
        """
        上传文件夹到Google Drive
        
        流程：打包 -> 上传zip文件（作为普通文件）
        
        Args:
            folder_path (str): 要上传的文件夹路径
            target_path (str): 目标路径（相对于当前shell路径）
            keep_zip (bool): 是否保留本地zip文件（远端总是保留zip文件）
            force (bool): 是否强制覆盖现有文件
            
        Returns:
            dict: 上传结果
        """
        try:
            folder_name = Path(folder_path).name
            
            # 使用统一的进度显示系统
            from ..progress_manager import start_progress_buffering, add_success_mark, clear_progress
            start_progress_buffering(f"Packing {folder_name} ...")
            
            # 步骤1: 打包文件夹
            zip_result = self.zip_folder(folder_path)
            if not zip_result["success"]:
                clear_progress()
                return {"success": False, "error": f"打包失败: {zip_result['error']}"}
            else: 
                add_success_mark()
                clear_progress()
            
            zip_path = zip_result["zip_path"]
            zip_filename = Path(zip_path).name
            
            try:
                # 步骤2: 上传zip文件并自动解压
                # 传递文件夹上传的特殊参数
                upload_result = self.cmd_upload([zip_path], target_path, force=force, 
                                              folder_upload_info={
                                                  "is_folder_upload": True,
                                                  "zip_filename": zip_filename,
                                                  "keep_zip": keep_zip
                                              })
                if not upload_result["success"]:
                    return {"success": False, "error": f"上传失败: {upload_result['error']}"}
                
                # 成功完成 - 不需要额外的输出，cmd_upload已经处理了进度显示
                return {
                    "success": True,
                    "message": f"Uploaded folder: {folder_name}",
                    "original_folder": folder_path,
                    "zip_uploaded": zip_filename,
                    "zip_kept": keep_zip,
                    "target_path": target_path,
                    "zip_size": zip_result.get("zip_size", 0),
                    "method": "zip_upload_and_extract",
                    "upload_details": upload_result
                }
                
            finally:
                # 根据keep_zip参数决定是否清理本地临时zip文件
                if not keep_zip:
                    try:
                        if Path(zip_path).exists():
                            Path(zip_path).unlink()
                    except Exception as e:
                        print(f"Warning: Failed to clean up temporary file: {e}")
                else:
                    print(f"Saved local zip file: {zip_path}")
                    
        except Exception as e:
            # 如果出错，也要清理临时文件
            try:
                if 'zip_path' in locals() and Path(zip_path).exists():
                    Path(zip_path).unlink()
            except:
                pass
            return {"success": False, "error": f"Folder upload process failed: {e}"}
    
    def cmd_upload(self, source_files, target_path=".", force=False, folder_upload_info=None, remove_local=False):
        """
        GDS UPLOAD 命令实现
        
        Args:
            source_files (list): 要上传的源文件路径列表
            target_path (str): 目标路径（相对于当前 shell 路径）
            force (bool): 是否强制覆盖现有文件
            
        Returns:
            dict: 上传结果
        """
        progress_started = False
        try:
            # 1. 验证输入参数
            if not source_files:
                return {"success": False, "error": "请指定要上传的文件"}
            
            if isinstance(source_files, str):
                source_files = [source_files]
            
            # 2. 获取当前 shell (需要提前获取)
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell, please create or switch to a shell"}
            
            # 3. 提前检查大文件（在显示进度之前）
            normal_files, large_files = self.check_large_files(source_files)
            
            # 如果有混合文件（既有小文件又有大文件），优化处理顺序
            if normal_files and large_files:
                print(f"Mixed upload detected: {len(normal_files)} small files + {len(large_files)} large files")
                
                # 先处理小文件，移动到LOCAL_EQUIVALENT开始同步
                source_files = normal_files  # 设置为只处理小文件
                # 大文件将在小文件处理完成后处理
            elif large_files and not normal_files:
                # 只有大文件的情况，直接处理
                large_file_result = self.handle_large_files(large_files, target_path, current_shell)
                if not large_file_result["success"]:
                    return large_file_result
            
            # 如果只有大文件没有小文件，处理大文件并返回
            if not normal_files and large_files:
                # 大文件已经通过handle_large_files提示用户手动拖入DRIVE_EQUIVALENT
                # 现在需要等待同步并移动到目标位置
                
                print(f"\nWaiting for manually uploaded files to be synchronized...")
                from ..progress_manager import start_progress_buffering
                start_progress_buffering("⏳ Waiting for large files sync ...")
                
                large_file_names = [Path(f["path"]).name for f in large_files]
                
                # 创建虚拟file_moves用于计算超时时间
                virtual_file_moves = [{"new_path": f["path"]} for f in large_files]
                sync_result = self.main_instance.sync_manager.wait_for_file_sync(large_file_names, virtual_file_moves)
                
                if not sync_result["success"]:
                    import traceback
                    call_stack = ''.join(traceback.format_stack()[-3:])
                    return {
                        "success": False,
                        "error": f"Large files sync failed: {sync_result.get('error', f'Sync operation failed without specific error message. Call stack: {call_stack}')}",
                        "large_files_handled": True
                    }
                
                # 同步成功后，执行mv命令移动到目标位置
                target_display_path = self.main_instance.path_resolver.resolve_remote_absolute_path(target_path, current_shell, return_logical=True)
                
                print(f"Move manually uploaded files to the destination: {target_display_path}")
                
                # Use the same mv command generation logic as small files
                large_file_moves = []
                for filename in large_file_names:
                    large_file_moves.append({
                        "filename": filename,
                        "original_filename": filename,
                        "renamed": False,
                        "target_path": target_path
                    })
                
                # Generate mv commands using the same logic as small files
                mv_command = self.main_instance.remote_commands.generate_mv_commands(large_file_moves, target_path)
                
                # Execute the mv command
                if mv_command.strip():
                    mv_result = self.main_instance.execute_command_interface("bash", ["-c", mv_command])
                else:
                    # No mv needed
                    mv_result = {"success": True}
                
                if mv_result.get("success"):
                    print(f"✓ Files moved successfully to {target_display_path}")
                    return {
                        "success": True,
                        "message": f"\n✓ Large files uploaded and moved: {len(large_files)} files",
                        "large_files_handled": True
                    }
                else:
                    import traceback
                    call_stack = ''.join(traceback.format_stack()[-3:])
                    return {
                        "success": False,
                        "error": f"Failed to move large files: {mv_result.get('error', f'Move operation failed without specific error message. Call stack: {call_stack}')}",
                        "large_files_handled": True
                    }
            elif not normal_files and not large_files:
                return {"success": False, "error": "No files to upload"}
            
            # 继续处理正常大小的文件
            source_files = normal_files
            
            # 4. 检查Google Drive Desktop是否运行（在开始进度显示之前）
            if not ensure_google_drive_desktop_running():
                return {"success": False, "error": "用户取消上传操作"}
            
            # 4.5. 检查目标文件是否已存在，避免冲突（除非使用--force）
            # 重要：在显示进度指示器之前检查冲突
            if not force:
                conflict_check_result = self.check_remote_file_conflicts(source_files, target_path)
                if not conflict_check_result["success"]:
                    return conflict_check_result
            
            # 5. 开始进度显示（在Google Drive Desktop检查和冲突检查之后）
            from ..progress_manager import start_progress_buffering
            start_progress_buffering("⏳ Waiting for upload ...")
            progress_started = True
            debug_capture.start_capture()
            debug_print(f"cmd_upload called with source_files={source_files}, target_path='{target_path}', force={force}")
            
            # 6. 解析目标路径（使用absolute path接口 + drive id接口）
            debug_print(f"Before resolve - target_path='{target_path}'")
            debug_print(f"current_shell={current_shell}")
            # 先获取逻辑路径
            target_display_path = self.main_instance.path_resolver.resolve_remote_absolute_path(target_path, current_shell, return_logical=True)
            # 再获取drive ID
            target_folder_id, _ = self.main_instance.resolve_drive_id(target_path, current_shell)
            debug_print(f"After resolve - target_folder_id='{target_folder_id}', target_display_path='{target_display_path}'")
            if target_folder_id is None and self.drive_service:
                target_folder_id = None  # 标记为需要创建
                target_display_path = target_path
            elif not self.drive_service:
                print(f"Warning: Google Drive API service not initialized, using mock mode")
            
            # 4. 检查是否有文件夹，提示正确语法
            for source_file in source_files:
                if Path(source_file).is_dir():
                    print(f"\nError: '{source_file}' is a directory")
                    print(f"To upload folders, use: GDS upload_folder {source_file}")
                    print(f"   Options: --keep-zip to preserve local zip file")
                    return {"success": False, "error": f""}
            
            # 5. 移动文件到 LOCAL_EQUIVALENT
            file_moves = []
            failed_moves = []
            
            for source_file in source_files:
                debug_print(f"Processing file: {source_file}")
                move_result = self.main_instance.sync_manager.move_to_local_equivalent(source_file, target_path)
                debug_print(f"Move result: {move_result}")
                
                if move_result["success"]:
                    file_moves.append({
                        "original_path": move_result["original_path"],
                        "filename": move_result["filename"],
                        "original_filename": move_result["original_filename"],
                        "new_path": move_result["new_path"],
                        "renamed": move_result["renamed"]
                    })
                    
                    # 记录重命名信息到debug（不显示给用户）
                    if move_result["renamed"]:
                        debug_print(f"File renamed: {move_result['original_filename']} -> {move_result['filename']}")
                    else:
                        debug_print(f"File processed without renaming: {move_result['filename']}")
                else:
                    import traceback
                    call_stack = ''.join(traceback.format_stack()[-3:])
                    error_msg = move_result.get("error", "")
                    if not error_msg:
                        error_msg = f"Unknown error. Call stack: {call_stack}"
                    
                    failed_moves.append({
                        "file": source_file,
                        "error": error_msg
                    })
                    print(f"\n✗ {move_result['error']}")
            
            if not file_moves:
                return {
                    "success": False,
                    "error": "All file moves failed",
                    "failed_moves": failed_moves
                }
            
            # 6. 如果是混合上传，在小文件开始同步时启动大文件处理
            if large_files:
                print(f"\nSmall files are now syncing. Please start uploading large files...")
                large_file_result = self.handle_large_files(large_files, target_path, current_shell)
                if not large_file_result["success"]:
                    print(f"Large file setup failed: {large_file_result.get('error', 'Large file processing failed without specific error message')}")
                    print(f"Continuing with small files only...")
                    large_files = []  # Clear large files to avoid processing later
            
            # 7. 停止上传进度显示，开始同步等待
            if progress_started:
                from ..progress_manager import stop_progress_buffering
                stop_progress_buffering()
                progress_started = False
            
            # 8. 等待文件同步到 DRIVE_EQUIVALENT
            # 对于同步检测，使用重命名后的文件名（在DRIVE_EQUIVALENT中的实际文件名）
            expected_filenames = [fm["filename"] for fm in file_moves]
            
            sync_result = self.main_instance.sync_manager.wait_for_file_sync(expected_filenames, file_moves)
            
            if sync_result.get("cancelled"):
                # 用户取消了同步等待
                return {
                    "success": False,
                    "cancelled": True,
                    "error": "Upload cancelled by user during file sync",
                    "file_moves": file_moves,
                    "sync_time": sync_result.get("sync_time", 0)
                }
            elif not sync_result["success"]:
                # 同步检测失败，但继续执行
                print(f"Warning: File sync check failed: {sync_result.get('error', 'Sync verification failed without specific error message')}")
                print(f"Upload may have succeeded, please manually verify files have been uploaded")
                print(f"You can retry upload if needed")
                
                # 返回失败结果，让用户决定是否重试
                return {
                    "success": False,
                    "error": f"Upload sync verification failed: {sync_result.get('error', 'Sync verification failed without specific error message')}",
                    "file_moves": file_moves,
                    "sync_time": sync_result.get("sync_time", 0),
                    "suggestion": "Files may have been uploaded successfully. Please check manually and retry if needed."
                }
            else:
                # 优先使用 base_sync_time，如果不存在则使用 sync_time，都不存在时使用0
                base_time = (sync_result.get("base_sync_time") if "base_sync_time" in sync_result else sync_result.get("sync_time", 0))
                sync_result["sync_time"] = base_time
            
            # 9. 静默验证文件同步状态
            self.verify_files_available(file_moves)
            
            # 10. 静默生成远端移动命令
            debug_print(f"Before generate_mv_commands - file_moves={file_moves}")
            debug_print(f"Before generate_mv_commands - target_path='{target_path}'")
            remote_command = self.main_instance.remote_commands.generate_mv_commands(file_moves, target_path, folder_upload_info, force=force)
            # 在长时间运行的操作中减少调试输出
            if len(remote_command) > 500:
                debug_print(f"After generate_mv_commands - remote_command length: {len(remote_command)} chars")
            else:
                debug_print(f"After generate_mv_commands - remote_command preview: {remote_command[:200]}...")
            
            # 11. 如果有大文件，延迟小文件mv命令执行；否则立即执行
            if large_files:
                # 混合上传：延迟小文件mv命令，等大文件处理完成后统一执行
                debug_print(f"Mixed upload: delaying small file mv command until large files are processed")
                execution_result = {"success": True}  # 暂时标记为成功，实际mv在后面统一执行
            else:
                # 纯小文件上传：立即执行mv命令
                execution_result = self.main_instance.execute_command_interface("bash", ["-c", remote_command])
            
            # 如果执行失败，直接返回错误
            if not execution_result.get("success", False):
                # 明确处理错误信息的获取 - 错误可能在顶层或data层
                error = execution_result.get("error", "")
                if not error and "data" in execution_result:
                    error = execution_result["data"].get("error", "")
                if not error:
                    error = "Command execution failed without specific error message"
                
                import traceback
                call_stack = ''.join(traceback.format_stack()[-3:])  # 获取最近3层调用栈
                error = f"Upload error: {error}. Call stack: {call_stack}"
                
                return {
                    "success": False,
                    "error": error,
                    "remote_command": remote_command,
                    "execution_result": execution_result
                }
            
            if folder_upload_info and folder_upload_info.get("is_folder_upload", False):
                # 文件夹上传：跳过文件验证，信任远程命令执行结果
                debug_print(f"Folder upload detected, skipping file verification")
                verify_result = {
                    "success": True,
                    "found_files": [],
                    "missing_files": [],
                    "total_expected": len(expected_filenames),
                    "total_found": 0,
                    "skip_verification": True
                }
            elif large_files:
                # 混合上传：跳过小文件验证，因为mv命令还没有执行
                debug_print(f"Mixed upload detected, skipping small file verification until all files are moved")
                verify_result = {
                    "success": True,
                    "found_files": [fm.get("original_filename", fm["filename"]) for fm in file_moves],
                    "missing_files": [],
                    "total_expected": len(expected_filenames),
                    "total_found": len(file_moves),
                    "skip_verification": True
                }
            else:
                # 纯小文件上传：使用ls-based验证
                expected_for_verification = [fm.get("original_filename", fm["filename"]) for fm in file_moves]
                
                # 使用带进度的验证机制
                verify_result = self.verify_upload_with_progress(
                    expected_for_verification, 
                    target_path, 
                    current_shell
                )

                debug_capture.start_capture()
                debug_print(f"Verification completed: {verify_result}")
            
            # 12. 准备结果对象
            result = {
                "success": verify_result["success"],
                "uploaded_files": verify_result.get("found_files", []),
                "failed_files": verify_result.get("missing_files", []) + [fm["file"] for fm in failed_moves],
                "target_path": target_display_path,
                "target_folder_id": target_folder_id,
                "total_attempted": len(file_moves) + len(failed_moves),
                "total_succeeded": len(verify_result.get("found_files", [])),
                "remote_command": remote_command,
                "file_moves": file_moves,
                "failed_moves": failed_moves,
                "sync_time": sync_result.get("sync_time", 0),
                "message": f"Upload completed: {len(verify_result.get('found_files', []))}/{len(file_moves)} files" if verify_result["success"] else f" ✗\nPartially uploaded: {len(verify_result.get('found_files', []))}/{len(file_moves)} files",
                "api_available": self.drive_service is not None
            }
            
            # 13. 处理混合上传中的大文件（如果有的话）
            if verify_result["success"] and large_files:
                print(f"\nSmall files uploaded successfully. ")
                print(f"Waiting for manually uploaded large files. ")
                
                from ..progress_manager import start_progress_buffering
                start_progress_buffering("⏳ Waiting for large files sync ...")
                
                large_file_names = [Path(f["path"]).name for f in large_files]
                
                # 创建虚拟file_moves用于计算超时时间
                virtual_file_moves = [{"new_path": f["path"]} for f in large_files]
                large_sync_result = self.main_instance.sync_manager.wait_for_file_sync(large_file_names, virtual_file_moves)
                
                if not large_sync_result["success"]:
                    print(f"Warning: Large files sync failed: {large_sync_result.get('error', 'Large file sync failed without specific error message')}")
                    print(f"Small files were uploaded successfully, but large files may need manual verification")
                else:
                    # 同步成功后，合并执行小文件和大文件的mv命令
                    print(f"Moving all files (small + large) to destination: {target_display_path}")
                    
                    # 生成大文件的mv命令
                    large_file_moves = []
                    for filename in large_file_names:
                        large_file_moves.append({
                            "filename": filename,
                            "original_filename": filename,
                            "renamed": False,
                            "target_path": target_path
                        })
                    # 使用统一的文件移动方法（小文件还在LOCAL_EQUIVALENT，大文件在DRIVE_EQUIVALENT）
                    debug_print(f"DEBUG: Using unified file move for small + large files")
                    
                    # 使用统一的文件移动方法处理所有文件
                    unified_mv_result = self.unified_file_move(file_moves, large_file_moves, target_path, folder_upload_info)
                    if unified_mv_result.get("success"):
                        result["uploaded_files"].extend(large_file_names)
                        result["total_succeeded"] += len(large_files)
                        result["message"] = f"Mixed upload completed: {len(file_moves)} small + {len(large_files)} large files"
                    else:
                        print(f"Warning: Failed to move files: {unified_mv_result.get('error', 'File move operation failed without specific error message')}")
                        print(f"Some files may still be in their temporary locations and need manual moving")
            
            # 14. 上传和远端命令执行完成后，清理LOCAL_EQUIVALENT中的文件
            if verify_result["success"]:
                self.main_instance.cache_manager.cleanup_local_equivalent_files(file_moves)
                
                # 添加删除记录到缓存（记录原始文件名和临时文件名的使用）
                for file_info in file_moves:
                    original_filename = file_info["original_filename"]
                    temp_filename = file_info["filename"]
                    
                    # 记录原始文件名的使用
                    self.main_instance.cache_manager.add_deletion_record(original_filename)
                    debug_print(f"Added deletion record for original: {original_filename}")
                    
                    # 如果文件被重命名，也记录临时文件名的使用
                    if file_info["renamed"] and temp_filename != original_filename:
                        self.main_instance.cache_manager.add_deletion_record(temp_filename)
                        debug_print(f"Added deletion record for temp: {temp_filename}")
                
                # 如果指定了 --remove-local 选项，删除本地源文件
                if remove_local:
                    removed_files = []
                    failed_removals = []
                    for source_file in source_files:
                        try:
                            if os.path.exists(source_file):
                                os.unlink(source_file)
                                removed_files.append(source_file)
                        except Exception as e:
                            failed_removals.append({"file": source_file, "error": str(e)})
            
            # Add debug information only for failed uploads or when user used direct feedback
            used_direct_feedback = verify_result.get("source") == "direct_feedback"
            upload_failed = not verify_result["success"]
            
            # Only show debug information for failures or direct feedback scenarios
            if used_direct_feedback:
                debug_print(f"User used direct feedback, showing debug information:")
                debug_print(f"verify_result={verify_result}")
                debug_print(f"sync_result={sync_result}")
                debug_print(f"target_folder_id='{target_folder_id}'")
                debug_print(f"target_display_path='{target_display_path}'")
            elif upload_failed:
                debug_print(f"Upload failed, showing debug information:")
            debug_print(f"verify_result={verify_result}")
            debug_print(f"sync_result={sync_result}")
            debug_print(f"target_folder_id='{target_folder_id}'")
            debug_print(f"target_display_path='{target_display_path}'")
            
            # 停止debug信息捕获
            debug_capture.stop_capture()
            
            # Only print debug capture buffer for failures or direct feedback
            if used_direct_feedback or upload_failed:
                captured_debug = debug_capture.get_debug_info()
                if captured_debug:
                    debug_print(f"Captured debug output:")
                    debug_print(captured_debug)
            
            # 添加本地文件删除信息
            if remove_local and verify_result["success"]:
                result["removed_local_files"] = removed_files
                result["failed_local_removals"] = failed_removals
                if removed_files:
                    result["message"] += f" (removed {len(removed_files)} local files)"
                if failed_removals:
                    result["message"] += f" (failed to remove {len(failed_removals)} local files)"
            
            # 停止debug信息捕获
            # 注意：不在这里清除进度显示，让调用方的result_print统一处理
            debug_capture.stop_capture()
            return result
            
        except Exception as e:
            # 停止debug信息捕获和进度显示
            debug_capture.stop_capture()
            if progress_started:
                from ..progress_manager import clear_progress, is_progress_active
                if is_progress_active():
                    clear_progress()
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Upload error: {str(e)}"
            }


    def zip_folder(self, folder_path, zip_path=None):
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
        检查大文件（>10MB）并提供手动上传方案
        
        Args:
            source_files (list): 源文件路径列表
            
        Returns:
            tuple: (normal_files, large_files) - 正常文件和大文件列表
        """
        from ..config_loader import get_large_file_threshold_mb
        normal_files = []
        large_files = []
        threshold_mb = get_large_file_threshold_mb()
        threshold_bytes = threshold_mb * 1024 * 1024
        
        for file_path in source_files:
            expanded_path = self.main_instance.path_resolver.expand_path(file_path)
            if os.path.exists(expanded_path):
                file_size = os.path.getsize(expanded_path)
                if file_size > threshold_bytes:
                    large_files.append({
                        "path": expanded_path,
                        "original_path": file_path,
                        "size_mb": file_size / (1024 * 1024),
                        "size": file_size
                    })
                else:
                    normal_files.append(expanded_path)
            else:
                # 停止progress显示并确保清除，然后输出错误信息
                from ..progress_manager import stop_progress_buffering, is_progress_active
                if is_progress_active():
                    stop_progress_buffering()
                    print()
                print(f"File does not exist: {file_path}")
        
        return normal_files, large_files

    def handle_large_files(self, large_files, target_path=".", current_shell=None):
        """处理大文件的手动上传 - 打开DRIVE_EQUIVALENT让用户拖入"""
        from ..config_loader import get_large_file_threshold_mb
        import tempfile
        import shutil
        import platform
        
        try:
            if not large_files:
                return {"success": True, "message": "没有大文件需要手动处理"}
            
            threshold_mb = get_large_file_threshold_mb()
            print(f"\n检测到 {len(large_files)} 个大文件（>{threshold_mb}MB），需要手动上传:")
            for file_info in large_files:
                print(f"  - {Path(file_info['original_path']).name} ({file_info['size_mb']:.1f} MB)")
            
            
            
            temp_upload_dir = Path(tempfile.mkdtemp(prefix="GDS_MANUAL_UPLOAD_"))
            # 不使用resolve()以避免macOS上的"T"文件夹问题
            
            try:
                # 将大文件复制或链接到临时文件夹
                for file_info in large_files:
                    src_path = Path(file_info["path"])
                    dst_path = temp_upload_dir / src_path.name
                    
                    # 对于大文件，优先使用文件复制以便用户直观看到实际文件
                    try:
                        shutil.copy2(src_path, dst_path)
                    except Exception as e:
                        # 如果复制失败（空间不足等），尝试硬链接
                        try:
                            os.link(src_path, dst_path)
                        except:
                            # 最后尝试符号链接
                            dst_path.symlink_to(src_path.absolute())
                
                # 创建README文件
                readme_path = temp_upload_dir / "上传说明_README.txt"
                drive_eq_path = self.main_instance.DRIVE_EQUIVALENT
                readme_content = f"""GDS 大文件手动上传说明
{'='*60}

检测到以下大文件需要手动上传（每个文件 >{threshold_mb}MB）：
"""
                for file_info in large_files:
                    readme_content += f"  - {Path(file_info['original_path']).name} ({file_info['size_mb']:.1f} MB)\n"
                
                readme_content += f"""
上传步骤：
  1. Finder/文件管理器已自动打开本地文件夹 (该README所在的文件夹)
  2. 将该本地文件夹中的所有文件拖放到网页自动打开的远端文件夹中  3. 完成后点击 "✅上传完成" 按键
"""
                
                with open(readme_path, 'w', encoding='utf-8') as f:
                    f.write(readme_content)
                
                # 获取DRIVE_EQUIVALENT的Google Drive URL
                drive_eq_folder_id = self.main_instance.DRIVE_EQUIVALENT_FOLDER_ID
                drive_eq_url = f"https://drive.google.com/drive/folders/{drive_eq_folder_id}"
                print(f"\nTarget remote path: {drive_eq_url}")
                
                import subprocess
                import webbrowser
                
                # 先打开远程文件夹（浏览器）
                try:
                    webbrowser.open(drive_eq_url)
                    print(f"✓ Opened the target remote folder in browser")
                except Exception as e:
                    print(f"Warning: Failed to open browser: {e}")
                    print(f"Please manually visit: {drive_eq_url}")
                
                # 然后打开本地文件夹（这样Navigator会在最顶层）
                print(f"\nLocal temporary folder: {temp_upload_dir}")
                try:
                    if platform.system() == "Darwin":  # macOS
                        # 直接使用原始路径，避免macOS上的"T"文件夹问题
                        subprocess.run(["open", str(temp_upload_dir)])
                    elif platform.system() == "Windows":
                        os.startfile(str(temp_upload_dir))
                    else:  # Linux
                        subprocess.run(["xdg-open", str(temp_upload_dir)])
                    
                    print(f"✓ Opened the local temporary folder")
                except Exception as e:
                    print(f"Warning: Failed to open local temporary folder: {e}")
                
                print(f"\n{'='*60}")
                print(f"Please drag the files from the opened local temporary folder to the target remote folder!")
                
                # 使用tkinter窗口替代终端交互
                upload_result = self.show_large_file_upload_window_subprocess(temp_upload_dir, drive_eq_url)
                if not upload_result:
                    return {"success": False, "error": "User cancelled the large file upload"}
                
                # 清理临时文件夹
                try:
                    shutil.rmtree(temp_upload_dir)
                    print(f"✓ Cleaned up the local temporary folder")
                except Exception as e:
                    print(f"Warning: Failed to clean up the local temporary folder: {e}")
                
            except KeyboardInterrupt:
                # 用户中断，清理临时文件夹
                try:
                    shutil.rmtree(temp_upload_dir)
                except:
                    pass
                raise
            
            return {"success": True, "message": "Large files moved to DRIVE_EQUIVALENT"}
        except KeyboardInterrupt:
            return {"success": False, "error": "User interrupted the large file upload"}
        except Exception as e:
            return {"success": False, "error": f"Handling large files failed: {str(e)}"}

    def verify_upload_with_progress(self, expected_files, target_path, current_shell):
        """
        带进度显示的验证逻辑，类似上传过程
        对每个文件进行最多60次重试，显示⏳和点的进度
        """
        try:
            # 生成文件名列表用于显示
            if len(expected_files) <= 3:
                file_display = ", ".join(expected_files)
            else:
                first_three = ", ".join(expected_files[:3])
                file_display = f"{first_three}, ... ({len(expected_files)} files)"
            
            # 定义验证函数，支持最后一次尝试时使用强制刷新
            attempt_count = 0
            max_attempts = 15
            
            def validate_all_files():
                nonlocal attempt_count
                attempt_count += 1
                
                # 为每个文件使用verify_with_ls进行验证
                found_count = 0
                for expected_file in expected_files:
                    # 构建文件的完整路径
                    if target_path == "." or target_path == "":
                        file_path = expected_file
                    else:
                        # 确保正确处理@路径和~路径
                        # 对于@和~等特殊前缀，需要添加/
                        if target_path in ["@", "~"]:
                            file_path = f"{target_path}/{expected_file}"
                        elif target_path.startswith("@/") or target_path.startswith("~/"):
                            # 目标路径已经包含子路径
                            file_path = f"{target_path}/{expected_file}"
                        else:
                            file_path = f"{target_path}/{expected_file}"
                    
                    # 使用verify_with_ls验证单个文件
                    verify_result = self.main_instance.validation.verify_with_ls(
                        path=file_path,
                        current_shell=current_shell,
                        creation_type="file"
                    )
                    
                    if verify_result.get("success", False):
                        found_count += 1
                
                return found_count == len(expected_files)
            
            # 直接使用统一的验证接口，它会正确处理进度显示的切换
            from ..progress_manager import validate_creation
            result = validate_creation(validate_all_files, file_display, max_attempts, "upload")
            
            # 转换返回格式
            all_found = result["success"]
            if all_found:
                found_files = expected_files
                missing_files = []
            else:
                # 如果验证失败，需要重新检查哪些文件缺失
                found_files = []
                for expected_file in expected_files:
                    # 构建文件的完整路径
                    if target_path == "." or target_path == "":
                        file_path = expected_file
                    else:
                        file_path = f"{target_path}/{expected_file}"
                    
                    # 使用verify_with_ls验证单个文件
                    verify_result = self.main_instance.validation.verify_with_ls(
                        path=file_path,
                        current_shell=current_shell,
                        creation_type="file"
                    )
                    
                    if verify_result.get("success", False):
                        found_files.append(expected_file)
                
                missing_files = [f for f in expected_files if f not in found_files]
            
            return {
                "success": all_found,
                "found_files": found_files,
                "missing_files": missing_files,
                "total_found": len(found_files),
                "total_expected": len(expected_files),
                "search_path": target_path
            }
            
        except Exception as e:
            debug_print(f"Validation error: {e}")
            return {
                "success": False,
                "error": str(e),
                "found_files": [],
                "missing_files": expected_files,
                "total_found": 0,
                "total_expected": len(expected_files)
            }

    def show_large_file_upload_window_subprocess(self, temp_upload_dir, drive_eq_url):
        """
        显示大文件上传的Tkinter窗口（在subprocess中运行以抑制警告）
        基于git历史中的标准窗口模板
        
        Args:
            temp_upload_dir: 临时上传目录路径
            drive_eq_url: Google Drive等效目录URL
            
        Returns:
            bool: True表示用户完成上传，False表示用户取消
        """
        import subprocess
        import base64
        
        # 获取音频文件路径
        from ..path_constants import get_proj_dir
        audio_file_path = str(get_proj_dir() / "tkinter_bell.mp3")
        
        # 创建subprocess脚本 - 基于历史模板的标准窗口设计
        subprocess_script = f'''
import sys
import os
import warnings

# 抑制所有警告和IMK信息
warnings.filterwarnings("ignore")
os.environ["TK_SILENCE_DEPRECATION"] = "1"

try:
    import tkinter as tk
    from tkinter import messagebox
    import subprocess
    
    result = False
    
    root = tk.Tk()
    root.title("Large File Upload")
    root.geometry("500x60")  # 使用标准的500x60尺寸
    root.resizable(False, False)
    root.attributes('-topmost', True)
    
    # 居中窗口
    root.eval('tk::PlaceWindow . center')
    
    # 音频文件路径
    audio_file_path = "{audio_file_path}"
    
    # 定义统一的聚焦函数
    def force_focus():
        try:
            root.focus_force()
            root.lift()
            root.attributes('-topmost', True)
        except:
            pass
    
    # 播放提示音
    def play_notification_sound():
        try:
            if os.path.exists(audio_file_path):
                if sys.platform == "darwin":  # macOS
                    subprocess.run(["afplay", audio_file_path], check=False, capture_output=True)
                elif sys.platform.startswith("linux"):  # Linux
                    subprocess.run(["aplay", audio_file_path], check=False, capture_output=True)
                elif sys.platform == "win32":  # Windows
                    import winsound
                    winsound.PlaySound(audio_file_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except:
            pass
    
    # 打开本地文件夹
    def open_local_folder():
        try:
            # 不使用resolve()以避免macOS上的"T"文件夹问题
            temp_dir_path = "{temp_upload_dir}"
            if sys.platform == "darwin":  # macOS
                # 方案1: 直接使用原始路径（推荐）
                subprocess.run(["open", temp_dir_path])
            elif sys.platform == "win32":  # Windows
                os.startfile(temp_dir_path)
            else:  # Linux
                subprocess.run(["xdg-open", temp_dir_path])
        except Exception as e:
            messagebox.showerror("错误", f"无法打开本地文件夹: {{e}}")
    
    # 打开远程文件夹
    def open_remote_folder():
        try:
            import webbrowser
            webbrowser.open("{drive_eq_url}")
        except Exception as e:
            messagebox.showerror("错误", f"无法打开远程文件夹: {{e}}")
    
    # 上传完成回调
    def upload_completed():
        global result
        result = True
        root.quit()
    
    # 取消上传回调
    def upload_cancelled():
        global result
        result = False
        root.quit()
    
    # 主框架 - 基于历史模板
    main_frame = tk.Frame(root, padx=10, pady=10)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # 按钮框架 - 基于历史模板
    button_frame = tk.Frame(main_frame)
    button_frame.pack(fill=tk.X, expand=True)
    
    # 打开本地文件夹按钮 - 使用历史模板样式
    open_local_btn = tk.Button(
        button_frame, 
        text="📁 本地文件夹", 
        command=open_local_folder,
        font=("Arial", 12),
        bg="#2196F3",
        fg="#666666",
        padx=10,
        pady=5,
        relief=tk.RAISED,
        bd=2
    )
    open_local_btn.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
    
    # 打开远程文件夹按钮 - 使用历史模板样式
    open_remote_btn = tk.Button(
        button_frame, 
        text="🌐 远程文件夹", 
        command=open_remote_folder,
        font=("Arial", 12),
        bg="#FF9800",
        fg="#666666",
        padx=10,
        pady=5,
        relief=tk.RAISED,
        bd=2
    )
    open_remote_btn.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
    
    # 上传完成按钮 - 使用历史模板样式
    complete_btn = tk.Button(
        button_frame, 
        text="✅ 上传完成", 
        command=upload_completed,
        font=("Arial", 12, "bold"),
        bg="#4CAF50",
        fg="#666666",
        padx=10,
        pady=5,
        relief=tk.RAISED,
        bd=2
    )
    complete_btn.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
    
    # 取消按钮 - 使用历史模板样式
    cancel_btn = tk.Button(
        button_frame, 
        text="❌ 取消", 
        command=upload_cancelled,
        font=("Arial", 12),
        bg="#f44336",
        fg="#666666",
        padx=10,
        pady=5,
        relief=tk.RAISED,
        bd=2
    )
    cancel_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    # 设置焦点到完成按钮
    complete_btn.focus_set()
    
    # 播放提示音并获取焦点
    root.after(100, play_notification_sound)
    root.after(200, force_focus)
    
    # 运行窗口
    root.mainloop()
    
    # 返回结果
    sys.exit(0 if result else 2)
    
except Exception as e:
    print(f"Tkinter window error: {{e}}", file=sys.stderr)
    sys.exit(1)
'''
        
        try:
            # 运行subprocess
            process = subprocess.run([
                "/usr/bin/python3", "-c", subprocess_script
            ], capture_output=True, text=True, timeout=300)
            
            # 根据返回码判断结果
            if process.returncode == 0:
                return True  # 用户完成上传
            elif process.returncode == 2:
                return False  # 用户取消
            else:
                print(f"Tkinter window failed with code {process.returncode}")
                return self.show_large_file_upload_window_fallback()
                
        except subprocess.TimeoutExpired:
            print("Tkinter window timeout")
            return self.show_large_file_upload_window_fallback()
        except Exception as e:
            print(f"Subprocess error: {e}")
            return self.show_large_file_upload_window_fallback()
    
    def show_large_file_upload_window_fallback(self):
        """
        大文件上传窗口的终端回退方案
        """
        try:
            print("\n" + "="*60)
            print("请完成以下步骤:")
            print("1. 将本地临时文件夹中的文件拖放到远程Google Drive文件夹")
            print("2. 等待文件上传完成")
            print("3. 按Enter继续...")
            print("="*60)
            
            input("按Enter继续，或Ctrl+C取消...")
            return True
        except KeyboardInterrupt:
            return False

    def unified_file_move(self, small_file_moves, large_file_moves, target_path, folder_upload_info=None):
        """
        统一的文件移动函数（函数D）- 将所有文件移动到目标位置
        
        Args:
            small_file_moves: 小文件移动信息列表
            large_file_moves: 大文件移动信息列表  
            target_path: 目标路径
            folder_upload_info: 文件夹上传信息
            
        Returns:
            dict: 移动结果
        """
        try:
            all_file_moves = []
            
            # 合并小文件移动信息
            if small_file_moves:
                all_file_moves.extend(small_file_moves)
            
            # 合并大文件移动信息
            if large_file_moves:
                all_file_moves.extend(large_file_moves)
            
            if not all_file_moves:
                return {"success": True, "message": "No files to move"}
            
            # 生成统一的mv命令
            combined_mv_command = self.main_instance.remote_commands.generate_mv_commands(all_file_moves, target_path, folder_upload_info)
            debug_print(f"DEBUG: Unified mv command (first 300 chars): {combined_mv_command[:300]}...")
            
            # 执行统一的mv命令
            if combined_mv_command.strip():
                mv_result = self.main_instance.execute_command_interface("bash", ["-c", combined_mv_command])
            else:
                mv_result = {"success": True}
            
            if mv_result.get("success"):
                message = "✓ Files moved successfully"
                
                print(message)
                return {
                    "success": True,
                    "message": message
                }
            else:
                error_msg = mv_result.get("error", "File move operation failed without specific error message")
                print(f"Warning: Failed to move files: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
                
        except Exception as e:
            error_msg = f"Unified file move failed: {str(e)}"
            print(f"Error: {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }

