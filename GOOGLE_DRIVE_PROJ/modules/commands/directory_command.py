"""
Directory operations commands (mkdir)
从file_core.py迁移而来
"""

import time


class DirectoryCommand:
    """目录操作命令"""
    
    def __init__(self, main_instance):
        self.main_instance = main_instance
        self.drive_service = main_instance.drive_service
    
    def cmd_mkdir(self, target_path, recursive=False):
        """
        通过远端命令创建目录的接口（使用统一接口）
        
        Args:
            target_path (str): 目标路径
            recursive (bool): 是否递归创建
            
        Returns:
            dict: 创建结果
        """
        try:
            # 获取当前shell以解析相对路径
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell"}
            
            # 解析绝对路径
            absolute_path = self.main_instance.resolve_remote_absolute_path(target_path, current_shell)
            if not absolute_path:
                return {"success": False, "error": f"Cannot resolve path: {target_path}"}
            
            # 生成远端mkdir命令，添加清屏和成功/失败提示（总是使用-p确保父目录存在）
            remote_command = f'mkdir -p "{absolute_path}"'
            try:
                execution_result = self.main_instance.execute_command_interface("bash", ["-c", remote_command])
            except Exception: 
                import traceback
                traceback.print_exc()
                raise
            
            if execution_result.get("success"):
                data = execution_result.get("data", {})
                exit_code = data.get("exit_code", execution_result.get("exit_code", -1))
                if exit_code == 0: 
                    verification_result = self.main_instance.verify_creation_with_ls(target_path, current_shell, creation_type="dir")
                    if verification_result["success"]: 
                        return {
                            "success": True,
                            "path": target_path,
                            "absolute_path": absolute_path,
                            "remote_command": remote_command,
                            "message": "", 
                            "verification": verification_result
                        }
                    else:
                        # 验证失败
                        return {
                            "success": False,
                            "error": f"Directory creation may have failed, verification timeout: {target_path}",
                            "verification": verification_result,
                            "remote_command": remote_command
                        }
                else:
                    stderr = data.get("stderr", execution_result.get("stderr", ""))
                    return {
                        "success": False,
                        "error": f"mkdir command failed with exit code {exit_code}: {stderr}",
                        "remote_command": remote_command
                    }
            else:
                # 使用增强的错误处理系统来处理执行失败
                error_msg = execution_result.get('error', 'Command execution failed')
                print(f"mkdir command execution failed: {error_msg}")
                
                # 如果有详细的错误信息，显示它
                if 'debug_info' in execution_result:
                    print("Detailed error information available in debug_info")
                else:
                    # 显示基本的调用栈信息
                    import traceback
                    print("\nCall stack (most recent call last):")
                    stack_lines = traceback.format_stack()
                    # 只显示最后几个相关的调用
                    for line in stack_lines[-3:]:
                        clean_line = line.strip().replace('\n', ' ')
                        print(f"  {clean_line}")
                
                return {
                    "success": False,
                    "error": f"mkdir command execution failed: {error_msg}",
                    "remote_command": remote_command,
                    "debug_info": execution_result.get('debug_info')
                }
                
        except Exception as e:
            # 使用增强的错误处理系统
            try:
                from ..error_handler import capture_and_report_error
                error_info = capture_and_report_error(
                    context="cmd_mkdir", 
                    exception=e,
                    additional_info={
                        "target_path": locals().get("target_path", "unknown"),
                        "absolute_path": locals().get("absolute_path", "unknown"),
                        "remote_command": locals().get("remote_command", "unknown")
                    }
                )
                return {"success": False, "error": f"Execute mkdir command failed: {e}", "debug_info": error_info}
            except ImportError:
                # 回退到原来的方法
                import traceback
                print(f"\nException in cmd_mkdir: {e}")
                print("Full exception traceback:")
                traceback.print_exc()
                return {"success": False, "error": f"Execute mkdir command failed: {e}"}

