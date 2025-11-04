"""
Result Processor Module
从 remote_commands.py 重构而来
"""

class ResultProcessor:
    """重构后的result_processor功能"""

    def __init__(self, drive_service=None, main_instance=None):
        self.drive_service = drive_service
        self.main_instance = main_instance

    def wait_and_read_result_file(self, result_filename, max_attempts=12):
        """
        等待并读取远端结果文件，最多等待12次
        
        Args:
            result_filename (str): 远端结果文件名（在tmp目录中）
            max_attempts (int): 最大尝试次数
        Returns:
            dict: 读取结果
        """
        try:
            import time
            
            # 使用逻辑路径而不是远端绝对路径，因为verify_with_ls会传递给cmd_ls
            logical_file_path = f"~/tmp/{result_filename}"

            # 使用进度缓冲输出等待指示器
            from .progress_manager import start_progress_buffering
            start_progress_buffering("⏳ Waiting for result ...")
            import signal
            import sys
            
            # 设置KeyboardInterrupt标志
            interrupted = False
            
            def signal_handler(signum, frame):
                nonlocal interrupted
                interrupted = True
            
            # 注册信号处理器
            old_handler = signal.signal(signal.SIGINT, signal_handler)
            
            try:
                last_access_error = None  # 记录最后一次访问错误
                
                for i in range(max_attempts):
                    # 在每次循环开始时检查中断标志
                    if interrupted:
                        raise KeyboardInterrupt()
                    
                    # 检查文件是否存在，使用简单的ls检查避免递归
                    ls_result = self.main_instance.cmd_ls(logical_file_path, detailed=False, recursive=False)
                    
                    if ls_result.get("success"):
                        # 文件存在，读取内容
                        file_result = self.read_result_file_via_gds(result_filename)
                        
                        # 直接清除进度显示，不添加√标记（与upload validation保持一致）
                        from .progress_manager import clear_progress
                        clear_progress()
                        
                        # 恢复原来的信号处理器
                        signal.signal(signal.SIGINT, old_handler)
                        
                        return file_result
                    else:
                        # 检查是否是访问错误（Unable to access 或 Unable to find the id for subfolder）
                        error_msg = ls_result.get("error", "")
                        if "Unable to access" in error_msg or "Unable to find the id for subfolder" in error_msg:
                            last_access_error = ls_result
                            # 如果是访问错误，在第8次尝试后才停止重试（给足够时间让Google Drive同步）
                            if i >= 7:  # 8秒后才认为是真正的访问错误
                                # 清除进度显示
                                from .progress_manager import clear_progress
                                clear_progress()
                                # 恢复信号处理器
                                signal.signal(signal.SIGINT, old_handler)
                                # 直接返回访问错误，不再继续重试
                                return {
                                    "success": False,
                                    "error": error_msg,
                                    "access_error": True,
                                    "failed_path": ls_result.get("failed_path"),
                                    "failed_id": ls_result.get("failed_id")
                                }
                    
                    # 文件不存在或其他错误，等待1秒并输出进度点
                    # 使用可中断的等待，每100ms检查一次中断标志
                    for j in range(10):  # 10 * 0.1s = 1s
                        if interrupted:
                            raise KeyboardInterrupt()
                        time.sleep(0.1)
                    
                    from .progress_manager import progress_print
                    progress_print(f".")
                
            except KeyboardInterrupt:
                from .progress_manager import clear_progress
                clear_progress()
                # 恢复原来的信号处理器
                signal.signal(signal.SIGINT, old_handler)
                return {
                    "success": False,
                    "error": "Operation cancelled by Ctrl+C during waiting for result from remote. ",
                    "cancelled": True
                }
            finally:
                # 确保信号处理器总是被恢复
                try:
                    signal.signal(signal.SIGINT, old_handler)
                except:
                    pass
            
            # 超时处理，恢复信号处理器并显示超时信息
            signal.signal(signal.SIGINT, old_handler)
            
            # 清除进度指示器
            from .progress_manager import clear_progress
            clear_progress()
            print()  # 换行
            
            # 如果有记录的访问错误，优先显示
            access_error_msg = last_access_error.get("error", "") if last_access_error else ""
            
            # 显示具体的访问错误
            print(access_error_msg)
            print()  # 空行分隔
            
            # 从错误信息中提取路径信息，访问失败则一定有访问不到的地方，否则报错！
            # 规范化接口返回。
            failed_path = last_access_error.get("failed_path", "")
            if not failed_path:
                raise Exception("Unable to return the failed path from the last access error. ")
                
            print(f"等待结果超时。可能的原因：")
            print(f"  (1) 请使用 'GDS reset id {failed_path} <new_id>' 更新正确的文件夹ID")
            print(f"  (2) Google Drive挂载失效，需要使用 'GOOGLE_DRIVE --remount' 重新挂载")
            print(f"  (3) 网络问题导致命令执行缓慢。请检查网络连接")
            
            # 检查是否在真正的后台模式（更严格的检测）
            import sys
            import os
            is_real_background_mode = (
                os.getenv('PYTEST_CURRENT_TEST') is not None or  # pytest环境
                os.getenv('CI') is not None or  # CI环境
                (not sys.stdin.isatty() and not sys.stdout.isatty())  # 真正的后台：输入输出都被重定向
            )
            
            if is_real_background_mode:
                return {
                    "success": False,
                    "error": f"Result file timeout: {logical_file_path}",
                    "timeout": True,
                    "background_mode": True
                }
            
            # 获取用户手动输入（通过main_instance的command_executor）
            try: 
                user_feedback = self.main_instance.command_executor.get_multiline_user_input(prompt="Please provide feedback (press Ctrl+D when done):")
            except Exception as e: 
                raise Exception(f"获取用户反馈失败: {str(e)}")
            if user_feedback.strip(): 
                return {
                    "success": True,
                    "data": {
                        "cmd": "unknown",
                        "args": [],
                        "working_dir": "unknown", 
                        "timestamp": "unknown",
                        "exit_code": 0,  # 假设成功
                        "stdout": user_feedback,
                        "stderr": "",
                        "source": "user_input",  # 标记来源
                        "note": "用户手动输入的执行结果"
                    }
                }
            else: 
                return {
                    "success": False, 
                    "error": f"等待远端结果文件超时，用户未提供反馈: {logical_file_path}"
                }
            
        except Exception as e: 
            return {
                "success": False,
                "error": f"等待结果文件时出错: {str(e)}"
            }


    def preprocess_json_content(self, content):
        """
        预处理JSON内容以修复常见格式问题
        
        Args:
            content (str): 原始JSON内容
            
        Returns:
            str: 清理后的JSON内容
        """
        try:
            # 移除首尾空白
            content = content.strip()
            
            # 如果内容为空，返回默认JSON
            if not content:
                return '{"exit_code": -1, "stdout": "", "stderr": "empty content"}'
            
            # 简单的JSON修复：确保以{开头，}结尾
            if not content.startswith('{'):
                content = '{' + content
            if not content.endswith('}'):
                content = content + '}'
            
            return content
            
        except Exception as e:
            # 如果预处理失败，返回包装的原始内容
            return f'{{"exit_code": -1, "stdout": "{content}", "stderr": "preprocess failed: {str(e)}"}}'


    def read_result_file_via_gds(self, result_filename):
        """
        使用GDS ls和cat机制读取远端结果文件

        Args:
            result_filename (str): 远端结果文件名（在tmp目录中）

        Returns:
            dict: 读取结果
        """
        try:
            # 远端文件路径（在REMOTE_ROOT/tmp目录中）
            # 需要先cd到根目录，然后访问tmp目录
            remote_file_path = f"~/tmp/{result_filename}"

            # 首先使用简单的ls检查文件是否存在，避免递归
            ls_result = self.main_instance.cmd_ls(remote_file_path, detailed=False, recursive=False)
            if not ls_result.get("success"):
                return {
                    "success": False,
                    "error": f"Remote result file does not exist: {remote_file_path}"
                }

            # 使用cat命令读取文件内容
            cat_result = self.main_instance.cmd_cat(remote_file_path)

            if not cat_result.get("success"):
                return {
                    "success": False,
                    "error": f"Read file content failed: {cat_result.get('error', 'unknown error')}"
                }

            # 获取文件内容
            content = cat_result.get("output", "")

            # 尝试解析JSON
            try:
                import json
                # 预处理JSON内容以修复格式问题
                cleaned_content = self.preprocess_json_content(content)
                result_data = json.loads(cleaned_content)

                return {
                    "success": True,
                    "data": result_data
                }
            except json.JSONDecodeError as e:
                # 如果JSON解析失败，返回原始内容
                return {
                    "success": True,
                    "data": {
                        "exit_code": -1,
                        "stdout": content,
                        "stderr": f"JSON parse failed: {str(e)}",
                        "raw_content": content
                    }
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Read result file failed: {str(e)}"
            }

