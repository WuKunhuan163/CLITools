#!/usr/bin/env python3
"""
Google Drive Shell - Validation Module
从google_drive_shell.py重构而来的validation模块
"""

class Validation:
    """Google Drive Shell Validation"""

    def __init__(self, drive_service, main_instance=None):
        """初始化管理器"""
        self.drive_service = drive_service
        self.main_instance = main_instance  # 引用主实例以访问其他属性

    def verify_upload_success_by_ls(self, expected_files, target_path, current_shell):
        """
        使用GDS ls机制验证文件是否成功上传
        
        Args:
            expected_files (list): 期望上传的文件名列表
            target_path (str): 目标路径（相对于当前shell）
            current_shell (dict): 当前shell信息
            
        Returns:
            dict: 验证结果
        """
        import time
        from .command_executor import debug_print
        
        try:
            # 启动debug capture以避免验证过程中的输出干扰
            from .command_executor import debug_capture
            debug_capture.start_capture()
            
            debug_print(f"Starting ls-based validation for {len(expected_files)} files")
            debug_print(f"target_path='{target_path}', current_path='{current_shell.get('current_path', '~')}'")
            
            # 使用统一的路径解析接口
            current_path = current_shell.get("current_path", "~")
            # 特殊处理：如果target_path看起来像文件名（不是路径），则在当前目录搜索
            if "/" not in target_path and ("." in target_path or target_path in expected_files):
                search_path = current_path
                debug_print(f"target_path '{target_path}' identified as filename, searching in current directory: {search_path}")
            else:
                # 使用compute_absolute_path处理所有路径情况
                search_path = self.main_instance.path_resolver.compute_absolute_path(current_path, target_path if target_path else ".")
            
            debug_print(f"constructed search_path='{search_path}'")
            
            # 使用ls命令检查目录内容
            ls_result = self.main_instance.file_operations.cmd_ls(path=search_path)
            debug_print(f"ls_result success={ls_result.get('success')}")
            
            if not ls_result.get("success"):
                debug_print(f"ls failed: {ls_result.get('error')}")
                # 停止debug capture
                debug_capture.stop_capture()
                return {
                    "success": False,
                    "error": f"无法访问目标目录 {search_path}: {ls_result.get('error')}",
                    "found_files": [],
                    "missing_files": expected_files,
                    "total_found": 0,
                    "total_expected": len(expected_files)
                }
            
            # 获取目录中的文件列表
            debug_capture.start_capture()
            files_in_dir = ls_result.get("files", [])
            file_names_in_dir = [f.get("name") for f in files_in_dir if f.get("name")]
            debug_print(f"found files in directory: {file_names_in_dir}")
            
            # 检查每个期望的文件是否存在
            found_files = []
            missing_files = []
            
            for expected_file in expected_files:
                if expected_file in file_names_in_dir:
                    found_files.append(expected_file)
                    debug_print(f"Found file: {expected_file}")
                else:
                    missing_files.append(expected_file)
                    debug_print(f"Error: Missing file: {expected_file}")
            
            success = len(found_files) == len(expected_files)
            debug_print(f"Validation result: {len(found_files)}/{len(expected_files)} files found")
            
            # 停止debug capture
            debug_capture.stop_capture()
            
            return {
                "success": success,
                "found_files": found_files,
                "missing_files": missing_files,
                "total_found": len(found_files),
                "total_expected": len(expected_files),
                "search_path": search_path
            }
            
        except Exception as e:
            debug_print(f"Exception in ls-based validation: {e}")
            # 停止debug capture
            debug_capture.stop_capture()
            return {
                "success": False,
                "error": f"验证过程中出错: {e}",
                "found_files": [],
                "missing_files": expected_files,
                "total_found": 0,
                "total_expected": len(expected_files)
            }

    def _create_error_result(self, error_message):
        """
        创建标准的错误返回结果
        
        Args:
            error_message (str): 错误消息
            
        Returns:
            dict: 标准错误结果字典
        """
        return {"success": False, "error": error_message}

    def _create_success_result(self, message=None, **kwargs):
        """
        创建标准的成功返回结果
        
        Args:
            message (str, optional): 成功消息
            **kwargs: 其他要包含的键值对
            
        Returns:
            dict: 标准成功结果字典
        """
        result = {"success": True}
        if message:
            result["message"] = message
        result.update(kwargs)
        return result

    def _handle_exception(self, e, operation_name, default_message=None):
        """
        通用异常处理方法
        
        Args:
            e (Exception): 异常对象
            operation_name (str): 操作名称
            default_message (str, optional): 默认错误消息
            
        Returns:
            dict: 错误结果字典
        """
        if default_message:
            error_msg = f"{default_message}: {str(e)}"
        else:
            error_msg = f"{operation_name}时出错: {str(e)}"
        return self._create_error_result(error_msg)
