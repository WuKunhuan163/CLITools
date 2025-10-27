"""
File Validator Module
从 remote_commands.py 重构而来
"""

class FileValidator:
    """重构后的file_validator功能"""

    def __init__(self, drive_service=None, main_instance=None):
        self.drive_service = drive_service
        self.main_instance = main_instance

    def _verify_upload_with_progress(self, expected_files, target_path, current_shell):
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
            from .progress_manager import validate_creation
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

    def _check_remote_file_exists(self, file_path):
        """
        检查远端文件是否存在（绝对路径）

        Args:
            file_path (str): 绝对路径的文件路径（如~/tmp/filename.json）

        Returns:
            dict: 检查结果
        """
        try:
            # 解析路径
            if "/" in file_path:
                dir_path, filename = file_path.rsplit("/", 1)
            else:
                dir_path = "~"
                filename = file_path

            # 列出目录内容
            ls_result = self.main_instance.cmd_ls(dir_path)

            if not ls_result.get("success"):
                return {"exists": False, "error": f"Cannot access directory: {dir_path}"}

            # 检查文件和文件夹是否在列表中
            files = ls_result.get("files", [])
            folders = ls_result.get("folders", [])
            all_items = files + folders

            # 检查文件或文件夹是否存在
            file_exists = any(f.get("name") == filename for f in all_items)

            return {"exists": file_exists}

        except Exception as e:
            return {"exists": False, "error": f"Check file existence failed: {str(e)}"}
