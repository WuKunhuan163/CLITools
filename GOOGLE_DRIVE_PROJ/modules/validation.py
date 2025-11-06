#!/usr/bin/env python3
"""
Google Drive Shell - Validation Module

This module provides comprehensive validation functionality for the Google Drive Shell system.
It handles validation of files, directories, operations, and system states to ensure data
integrity and proper operation of all shell commands.

Key Features:
- File and directory existence validation
- Operation result validation and verification
- Path validation and accessibility checking
- Google Drive API response validation
- Command execution result validation
- Error message standardization and formatting

Validation Types:
- File operations: Existence, accessibility, permissions
- Directory operations: Structure, navigation, creation
- Command results: Success/failure status, output validation
- API responses: Google Drive API call validation
- Path validation: Logical and absolute path verification

Validation Flow:
1. Receive validation request with parameters
2. Determine appropriate validation method
3. Execute validation checks using relevant APIs
4. Format and standardize validation results
5. Return structured validation response
6. Handle errors and edge cases appropriately

Classes:
    Validation: Main validation engine with comprehensive checking capabilities

Dependencies:
    - Google Drive API for remote file/folder validation
    - File system operations for local validation
    - Path resolution for path validation
    - Error handling for validation failures
    - Result formatting for consistent responses
"""

class Validation:
    """Google Drive Shell Validation"""

    def __init__(self, drive_service, main_instance=None):
        """初始化管理器"""
        self.drive_service = drive_service
        self.main_instance = main_instance

    def create_error_result(self, error_message):
        """
        创建标准的错误返回结果
        
        Args:
            error_message (str): 错误消息
            
        Returns:
            dict: 标准错误结果字典
        """
        return {"success": False, "error": error_message}

    def create_success_result(self, message=None, **kwargs):
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

    def handle_exception(self, e, operation_name, default_message=None):
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
        return self.create_error_result(error_msg)


    def verify_with_ls(self, path, current_shell=None, creation_type="file", max_attempts=12, show_hidden=False):
        """
        通用的创建验证接口，支持目录和文件验证
        
        Args:
            path (str): 要验证的路径
            current_shell (dict): 当前shell信息（用于兼容性，实际未使用）
            creation_type (str): 创建类型，"dir"或"file"
            max_attempts (int): 最大重试次数
            
        Returns:
            dict: 验证结果
        """
        attempt_count = 0
        
        def validate():
            nonlocal attempt_count
            attempt_count += 1
            
            # 使用标准API调用，避免弹出窗口
            ls_result = self.main_instance.cmd_ls(path, detailed=False, recursive=False, show_hidden=show_hidden)
            
            # 如果成功找到文件/目录，返回True
            if ls_result["success"]:
                return True
            
            # 如果达到最大尝试次数，返回None表示失败并退出循环
            if attempt_count >= max_attempts:
                return None
            
            # 否则返回False继续重试
            return False
            
        from .progress_manager import validate_creation, clear_progress, is_progress_active
        if is_progress_active():
            clear_progress()
        
        result = validate_creation(validate, path, max_attempts, creation_type)
        
        # 转换返回格式以保持兼容性
        if result["success"]:
            return {
                "success": True,
                "message": f"Creation verified: {path}",
                "attempts": result["attempts"]
            }
        elif result.get("cancelled", False):
            return {
                "success": False,
                "error": f"Verification of '{path}' cancelled by user (Ctrl+C)",
                "attempts": result["attempts"],
                "cancelled": True
            }
        else:
            return {
                "success": False,
                "error": f"Path '{path}' not found after {max_attempts} verification attempts",
                "attempts": result["attempts"]
            }

