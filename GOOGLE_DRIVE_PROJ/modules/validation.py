#!/usr/bin/env python3
"""
Google Drive Shell - Validation Module
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
        print(f"DEBUG [verify_with_ls]: 输入path = {path}")
        attempt_count = 0
        
        def validate():
            nonlocal attempt_count
            attempt_count += 1
            
            print(f"DEBUG [validate]: attempt_count={attempt_count}, max_attempts={max_attempts}, path={path}")
            
            # 在最后一次尝试时使用远程bash强制刷新（会弹出窗口）
            if attempt_count >= max_attempts:
                print(f"DEBUG [validate]: 调用cmd_ls_remote, path={path}")
                ls_result = self.main_instance.cmd_ls_remote(path, detailed=False, recursive=False, show_hidden=show_hidden)
            else:
                # 使用标准API调用
                print(f"DEBUG [validate]: 调用cmd_ls, path={path}")
                ls_result = self.main_instance.cmd_ls(path, detailed=False, recursive=False, show_hidden=show_hidden)
            
            return ls_result["success"]
            
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

