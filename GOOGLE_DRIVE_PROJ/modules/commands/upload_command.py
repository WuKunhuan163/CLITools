"""
Upload operations commands
从file_core.py迁移而来
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
        # 检查是否是 upload_folder 命令
        if cmd == 'upload_folder':
            return self.execute_upload_folder(args)
        
        # 解析参数: upload [--target-dir TARGET] [--force] <files...>
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
                # 剩余的参数都是源文件
                source_files.append(args[i])
                i += 1
        
        if not source_files:
            print("Error: No source files specified")
            return 1
        
        # 调用cmd_upload
        result = self.cmd_upload(source_files, target_path=target_path, force=force)
        
        if result.get("success"):
            return 0
        else:
            error_msg = result.get("error", "Upload failed")
            print(error_msg)
            return 1
    
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
        
        # 调用cmd_upload_folder
        result = self.cmd_upload_folder(folder_path, target_path=target_path, keep_zip=keep_zip, force=force)
        
        if result.get("success"):
            return 0
        else:
            error_msg = result.get("error", "Folder upload failed")
            print(error_msg)
            return 1
    
    def check_large_files(self, source_files):
        """检查大文件并分离处理（大于1G的文件）"""
        normal_files = []
        large_files = []
        
        for file_path in source_files:
            try:
                file_size = os.path.getsize(file_path)
                # 1G = 1024 * 1024 * 1024 bytes
                if file_size > 1024 * 1024 * 1024:
                    large_files.append({
                        "path": file_path,
                        "size": file_size,
                        "name": os.path.basename(file_path)
                    })
                else:
                    normal_files.append(file_path)
            except OSError:
                # 文件不存在或无法访问，加入normal_files让后续处理报错
                normal_files.append(file_path)
        
        return normal_files, large_files
    
    def handle_large_files(self, large_files, target_path, current_shell):
        """处理大文件上传"""
        print(f"\nDetected {len(large_files)} large files (>1GB):")
        for file_info in large_files:
            size_gb = file_info["size"] / (1024 * 1024 * 1024)
            print(f"  - {file_info['name']} ({size_gb:.1f} GB)")
        
        print(f"\nLarge files need to be manually uploaded to Google Drive:")
        print(f"  1. Open Google Drive web version")
        print(f"  2. Manually drag and drop these large files")
        print(f"  3. Wait for upload to complete")
        
        return {"success": True, "message": "Large files detected, manual upload required"}
    
    
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
            # 使用进度管理器显示上传进度
            from ..progress_manager import start_progress_buffering
            start_progress_buffering("⏳ Waiting for upload ...")
            progress_started = True
            debug_capture.start_capture()
            
            # 延迟启动debug信息捕获，让重命名信息能够显示
            debug_print(f"cmd_upload called with source_files={source_files}, target_path='{target_path}', force={force}")
            
            # 0. 检查Google Drive Desktop是否运行
            if not ensure_google_drive_desktop_running():
                if progress_started:
                    from ..progress_manager import stop_progress_buffering
                    stop_progress_buffering()
                return {"success": False, "error": "用户取消上传操作"}
            
            # 1. 验证输入参数
            if not source_files:
                if progress_started:
                    from ..progress_manager import stop_progress_buffering
                    stop_progress_buffering()
                return {"success": False, "error": "请指定要上传的文件"}
            
            if isinstance(source_files, str):
                source_files = [source_files]
            
            # 2. 获取当前 shell (需要提前获取，因为大文件处理也需要)
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell, please create or switch to a shell"}
            
            # 1.5. 检查大文件并分离处理
            normal_files, large_files = self.check_large_files(source_files)
            
            # 处理大文件
            if large_files:
                large_file_result = self.handle_large_files(large_files, target_path, current_shell)
                if not large_file_result["success"]:
                    return large_file_result
            
            # 如果没有正常大小的文件需要处理，但有大文件，需要等待手动上传完成
            if not normal_files:
                if large_files:
                    # 等待大文件手动上传完成
                    large_file_names = [Path(f["path"]).name for f in large_files]
                    start_progress_buffering(f"⏳ Waiting for large files manual upload ...")
                    
                    # 创建虚拟file_moves用于计算超时时间
                    virtual_file_moves = [{"new_path": f["path"]} for f in large_files]
                    sync_result = self.main_instance.sync_manager.wait_for_file_sync(large_file_names, virtual_file_moves)
                    
                    if sync_result["success"]:
                        return {
                            "success": True,
                            "message": f"\nLarge files manual upload completed: {len(large_files)} files",
                            "large_files_handled": True,
                            "sync_time": sync_result.get("sync_time", 0)
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Manual upload failed: {sync_result.get('error', 'Unknown error')}",
                            "large_files_handled": True
                        }
                else:
                    return {"success": False, "error": "Cannot find valid files"}
            
            # 继续处理正常大小的文件
            source_files = normal_files
            
            # 3. 解析目标路径（使用absolute path接口 + drive id接口）
            debug_print(f"Before resolve - target_path='{target_path}'")
            debug_print(f"current_shell={current_shell}")
            # 先获取逻辑路径
            target_display_path = self.main_instance.path_resolver.resolve_remote_absolute_path(target_path, current_shell, return_logical=True)
            # 再获取drive ID
            target_folder_id, _ = self.main_instance.path_resolver.resolve_drive_id(target_path, current_shell)
            debug_print(f"After resolve - target_folder_id='{target_folder_id}', target_display_path='{target_display_path}'")
            if target_folder_id is None and self.drive_service:
                target_folder_id = None  # 标记为需要创建
                target_display_path = target_path
            elif not self.drive_service:
                print(f"Warning: Google Drive API service not initialized, using mock mode")
            
            # 3.5. 检查目标文件是否已存在，避免冲突（除非使用--force）
            if not force:
                conflict_check_result = self.check_remote_file_conflicts(source_files, target_path)
                if not conflict_check_result["success"]:
                    return conflict_check_result
            
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
                move_result = self.main_instance.sync_manager.move_to_local_equivalent(source_file)
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
                    failed_moves.append({
                        "file": source_file,
                        "error": move_result.get("error", "Unknown error")
                    })
                    print(f"\n✗ {move_result['error']}")
            
            if not file_moves:
                return {
                    "success": False,
                    "error": "All file moves failed",
                    "failed_moves": failed_moves
                }
            
            # 6. 等待文件同步到 DRIVE_EQUIVALENT
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
                print(f"Warning: File sync check failed: {sync_result.get('error', 'Unknown error')}")
                print(f"Upload may have succeeded, please manually verify files have been uploaded")
                print(f"You can retry upload if needed")
                
                # 返回失败结果，让用户决定是否重试
                return {
                    "success": False,
                    "error": f"Upload sync verification failed: {sync_result.get('error', 'Unknown error')}",
                    "file_moves": file_moves,
                    "sync_time": sync_result.get("sync_time", 0),
                    "suggestion": "Files may have been uploaded successfully. Please check manually and retry if needed."
                }
            else:
                # 优先使用 base_sync_time，如果不存在则使用 sync_time，都不存在时使用0
                base_time = (sync_result.get("base_sync_time") if "base_sync_time" in sync_result else sync_result.get("sync_time", 0))
                sync_result["sync_time"] = base_time
            
            # 7. 静默验证文件同步状态
            self.verify_files_available(file_moves)
            
            # 8. 静默生成远端命令
            debug_print(f"Before generate_mv_commands - file_moves={file_moves}")
            debug_print(f"Before generate_mv_commands - target_path='{target_path}'")
            remote_command = self.main_instance.remote_commands.generate_mv_commands(file_moves, target_path, folder_upload_info)
            debug_print(f"After generate_mv_commands - remote_command preview: {remote_command[:200]}...")
            
            # 7.5. 远端目录创建已经集成到generate_mv_commands中，无需额外处理
            
            # 8. 使用统一的远端命令执行接口
            execution_result = self.main_instance.execute_command_interface("bash", ["-c", remote_command])
            
            # 如果执行失败，直接返回错误
            if not execution_result["success"]:
                # 明确处理错误信息的获取
                if "error" in execution_result:
                    error = execution_result["error"]
                elif "data" in execution_result and isinstance(execution_result["data"], dict):
                    error = execution_result["data"].get("error", "Unknown error")
                else:
                    error = "Unknown error"
                
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
            else:
                # 普通文件上传：使用ls-based验证
                expected_for_verification = [fm.get("original_filename", fm["filename"]) for fm in file_moves]

                # 使用带进度的验证机制
                verify_result = self.verify_upload_with_progress(
                    expected_for_verification, 
                    target_path, 
                    current_shell
                )

                debug_capture.start_capture()
                debug_print(f"Verification completed: {verify_result}")
            
            # 9. 上传和远端命令执行完成后，清理LOCAL_EQUIVALENT中的文件
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
                "message": f"Upload completed: {len(verify_result.get('found_files', []))}/{len(file_moves)} files" if verify_result["success"] else f" ✗\n⚠️ Partially uploaded: {len(verify_result.get('found_files', []))}/{len(file_moves)} files",
                "api_available": self.drive_service is not None
            }
            
            # Add debug information for all uploads to diagnose verification issues
            used_direct_feedback = verify_result.get("source") == "direct_feedback"
            upload_failed = not verify_result["success"]
            
            # Always show debug information to diagnose verification problems
            if used_direct_feedback:
                debug_print(f"User used direct feedback, showing debug information:")
            elif upload_failed:
                debug_print(f"Upload failed, showing debug information:")
            else:
                debug_print(f"Upload completed, showing verification debug information:")
            
            debug_print(f"verify_result={verify_result}")
            debug_print(f"sync_result={sync_result}")
            debug_print(f"target_folder_id='{target_folder_id}'")
            debug_print(f"target_display_path='{target_display_path}'")
            
            # 停止debug信息捕获
            debug_capture.stop_capture()
            
            # Always print debug capture buffer
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
        检查大文件（>1GB）并提供手动上传方案
        
        Args:
            source_files (list): 源文件路径列表
            
        Returns:
            tuple: (normal_files, large_files) - 正常文件和大文件列表
        """
        normal_files = []
        large_files = []
        GB_SIZE = 1024 * 1024 * 1024  # 1GB in bytes
        
        for file_path in source_files:
            expanded_path = self.main_instance.path_resolver.expand_path(file_path)
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
                # 停止progress显示并确保清除，然后输出错误信息
                from ..progress_manager import stop_progress_buffering, is_progress_active
                if is_progress_active():
                    stop_progress_buffering()
                    print()
                print(f"File does not exist: {file_path}")
        
        return normal_files, large_files

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
                            target_folder_id, _ = self.main_instance.resolve_drive_id(target_path, current_shell)
                        
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
                    input("按Enter键继续...")  # 等待用户确认
                    
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
            
            # 定义验证函数
            def validate_all_files():
                validation_result = self.main_instance.validation.verify_upload_success_by_ls(
                    expected_files=expected_files,
                    target_path=target_path,
                    current_shell=current_shell
                )
                found_count = len(validation_result.get("found_files", []))
                return found_count == len(expected_files)
            
            # 直接使用统一的验证接口，它会正确处理进度显示的切换
            from ..progress_manager import validate_creation
            result = validate_creation(validate_all_files, file_display, 60, "upload")
            
            # 转换返回格式
            all_found = result["success"]
            if all_found:
                found_files = expected_files
                missing_files = []
            else:
                # 如果验证失败，需要重新检查哪些文件缺失
                final_validation = self.main_instance.validation.verify_upload_success_by_ls(
                    expected_files=expected_files,
                    target_path=target_path,
                    current_shell=current_shell
                )
                found_files = final_validation.get("found_files", [])
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

