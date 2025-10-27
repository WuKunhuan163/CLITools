#!/usr/bin/env python3
"""
Google Drive Shell - Verification Module
从google_drive_shell.py重构而来的verification模块
"""

class Verification:
    """Google Drive Shell Verification"""

    def __init__(self, drive_service, main_instance=None):
        """初始化管理器"""
        self.drive_service = drive_service
        self.main_instance = main_instance  # 引用主实例以访问其他属性

    def verify_creation_with_ls(self, path, current_shell, creation_type="dir", max_attempts=20):
        """
        通用的创建验证接口，支持目录和文件验证
        
        Args:
            path (str): 要验证的路径
            current_shell (dict): 当前shell信息
            creation_type (str): 创建类型，"dir"或"file"
            max_attempts (int): 最大重试次数
            
        Returns:
            dict: 验证结果
        """
        return self._verify_creation_with_ls(path, current_shell, max_attempts, creation_type="file")
    
    def _verify_creation_with_ls(self, path, current_shell, max_attempts=20, creation_type="file"):
        """使用GDS ls统一验证文件或目录创建"""
        
        try:
            # 定义验证函数
            def validate():
                ls_result = self.main_instance.cmd_ls(path, detailed=False, recursive=False)
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
            
        except Exception as e:
            print(f"Error:")  # 失败标记
            return {
                "success": False,
                "error": f"Verification process error: {e}"
            }
