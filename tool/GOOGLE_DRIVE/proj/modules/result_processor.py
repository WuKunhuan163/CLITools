"""
Result Processor Module
从 remote_commands.py 重构而来
"""

class ResultProcessor:
    """重构后的result_processor功能"""

    def __init__(self, drive_service=None, main_instance=None):
        self.drive_service = drive_service
        self.main_instance = main_instance
    
    def _format_timeout_error_with_solutions(self, original_error, failed_path, failed_id=None):
        """
        格式化超时错误信息的统一模板
        
        Args:
            original_error (str): 原始错误信息
            failed_path (str): 失败的路径
            failed_id (str, optional): 失败的ID
            
        Returns:
            str: 格式化后的错误信息，包含三条解决方案
        """
        # 构建第二条原因的描述 - 指出错误可能在直接父目录
        if failed_id and failed_id != "unknown":
            reset_suggestion = f"更新正确的文件夹/文件ID（当前路径ID: {failed_id}）- 错误可能在直接父目录"
        else:
            reset_suggestion = "更新正确的文件夹/文件ID - 错误可能在直接父目录"
        
        return f"""{original_error}

等待结果超时。可能的原因：
  (1) 使用 'GOOGLE_DRIVE --remount' 重新挂载Google Drive，然后刷新整个网页
  (2) {reset_suggestion}
  (3) 检查网络连接，Google Drive API可能缓慢或无法访问"""

    def wait_and_read_result_file(self, result_filename, max_attempts=12):
        """
        等待并读取远端结果文件，最多等待12次
        
        Args:
            result_filename (str): 远端结果文件名（在tmp目录中）
            max_attempts (int): 最大尝试次数
        Returns:
            dict: 读取结果
        """
        # 检查main_instance是否正确初始化
        if not self.main_instance:
            import traceback
            call_stack = ''.join(traceback.format_stack()[-3:])
            return {
                "success": False,
                "data": {
                    "error": f"ResultProcessor main_instance is None. Call stack: {call_stack}"
                }
            }
            
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
        
        # 注册信号处理器（只在主线程有效）
        old_handler = None
        try:
            old_handler = signal.signal(signal.SIGINT, signal_handler)
        except ValueError:
            # 在worker线程中signal.signal会抛出ValueError
            # 跳过signal handler设置，worker线程不需要处理Ctrl+C
            pass
        
        try:
            last_access_error = None
            
            for i in range(max_attempts): 
                if interrupted:
                    raise KeyboardInterrupt()
                
                # 检查文件是否存在，使用简单的ls检查避免递归
                ls_result = self.main_instance.cmd_ls(logical_file_path, detailed=False, recursive=False)
                if ls_result.get("success"):
                    file_result = self.read_result_file_via_gds(result_filename)
                    
                    # 直接清除进度显示，不添加√标记（与upload validation保持一致）
                    from .progress_manager import clear_progress
                    clear_progress()
                    
                    # 恢复原来的信号处理器
                    if old_handler is not None:
                        signal.signal(signal.SIGINT, old_handler)
                    return file_result
                else:
                    if i == max_attempts - 1:
                        error_msg = ls_result.get("error", "")
                        last_access_error = ls_result
                        from .progress_manager import clear_progress
                        clear_progress()
                        if old_handler is not None:
                            signal.signal(signal.SIGINT, old_handler)
                        failed_path = ls_result.get("failed_path", logical_file_path)
                        failed_id = ls_result.get("failed_id")
                        detailed_error_msg = self._format_timeout_error_with_solutions(error_msg, failed_path, failed_id)
                        
                        # 直接返回访问错误，包含三条原因
                        return {
                            "success": False,
                            "data": {
                                "error": detailed_error_msg,
                                "access_error": True,
                                "failed_path": failed_path,
                                "failed_id": ls_result.get("failed_id")
                            }
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
            if old_handler is not None:
                signal.signal(signal.SIGINT, old_handler)
            return {
                "success": False,
                "data": {
                    "error": "Operation cancelled by Ctrl+C during waiting for result from remote. ",
                    "cancelled": True
                }
            }
        finally:
            # 确保信号处理器总是被恢复
            if old_handler is not None:
                try:
                    signal.signal(signal.SIGINT, old_handler)
                except:
                    pass
        
        # 超时处理，恢复信号处理器并显示超时信息
        if old_handler is not None:
            signal.signal(signal.SIGINT, old_handler)
        
        # 清除进度指示器
        from .progress_manager import clear_progress
        clear_progress()
        print()  # 换行
        
        # 如果有记录的访问错误，优先显示
        access_error_msg = ""
        failed_path = ""
        
        if last_access_error:
            access_error_msg = last_access_error.get("error", "")
            failed_path = last_access_error.get("failed_path", "")
        
        # 显示具体的访问错误
        if access_error_msg:
            print(access_error_msg)
            print()  # 空行分隔
            
        # 构建详细的错误信息，包含三条原因
        timeout_error_msg = self._format_timeout_error_with_solutions("", failed_path, None)
        print(timeout_error_msg)
        
        # 检查是否在真正的后台模式（更严格的检测）
        import sys
        import os
        is_real_background_mode = (
            os.getenv('PYTEST_CURRENT_TEST') is not None or  # pytest环境
            os.getenv('CI') is not None or  # CI环境
            (not sys.stdin.isatty() and not sys.stdout.isatty()) or  # 真正的后台：输入输出都被重定向
            (hasattr(self.main_instance, 'command_executor') and 
             hasattr(self.main_instance.command_executor, '_no_direct_feedback') and 
             self.main_instance.command_executor._no_direct_feedback)  # --no-direct-feedback模式
        )
        
        if is_real_background_mode:
            return {
                "success": False,
                "error": timeout_error_msg,  # 包含完整的错误信息
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
                "error": timeout_error_msg  # 使用包含三条原因的完整错误信息
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
                    "data": {
                        "error": f"Remote result file does not exist: {remote_file_path}"
                    }
                }

            # 使用cat命令读取文件内容
            cat_result = self.main_instance.cmd_cat(remote_file_path)
            if not cat_result.get("success"):
                return {
                    "success": False,
                    "data": {
                        "error": f"Read file content failed: {cat_result.get('error', 'unknown error')}"
                    }
                }

            # 获取文件内容
            content = cat_result.get("output", "")

            # 尝试解析JSON
            try:
                import json
                from .debug_logger import debug_log
                
                # 预处理JSON内容以修复格式问题
                cleaned_content = self.preprocess_json_content(content)
                result_data = json.loads(cleaned_content)
                
                # Debug log记录结果处理过程
                debug_log('result_processor', 'result_file_processed', {
                    'result_filename': result_filename,
                    'raw_content_length': len(content),
                    'cleaned_content_length': len(cleaned_content),
                    'result_data_keys': list(result_data.keys()) if isinstance(result_data, dict) else 'not_dict',
                    'stdout_content': result_data.get('stdout', '') if isinstance(result_data, dict) else '',
                    'stdout_length': len(result_data.get('stdout', '')) if isinstance(result_data, dict) else 0,
                    'exit_code': result_data.get('exit_code', 'not_found') if isinstance(result_data, dict) else 'not_dict'
                })

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
            import traceback
            call_stack = ''.join(traceback.format_stack()[-3:])
            return {
                "success": False,
                "data": {
                    "error": f"Read result file failed: {str(e)}. Call stack: {call_stack}"
                }
            }

