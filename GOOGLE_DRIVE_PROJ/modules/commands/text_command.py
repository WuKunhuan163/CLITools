"""
Text operations commands (cat, create_text_file)
从text_operations.py迁移而来
"""


class TextCommand:
    """文本操作命令"""
    
    def __init__(self, main_instance):
        self.main_instance = main_instance
        self.drive_service = main_instance.drive_service
    
    def create_text_file(self, filename, content):
        """通过远程命令创建文本文件
        
        Args:
            filename (str): 文件名
            content (str): 文件内容
            
        Returns:
            dict: 创建结果
        """
        # 从text_operations.py的create_text_file方法复制实现（行29-73）
        pass

    def create_text_file(self, filename, content):
        """通过远程命令创建文本文件"""
        try:
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell"}
            
            # 构建远程echo命令
            remote_absolute_path = self.main_instance.resolve_remote_absolute_path(filename, current_shell)
            
            # 使用base64编码来完全避免引号和特殊字符问题
            import base64
            content_bytes = content.encode('utf-8')
            content_base64 = base64.b64encode(content_bytes).decode('ascii')
            
            # 构建远程命令 - 使用base64解码避免所有引号问题
            remote_command = f'echo "{content_base64}" | base64 -d > "{remote_absolute_path}"'
            
            # 使用远程命令执行接口
            result = self.main_instance.execute_command_interface("bash", ["-c", remote_command])
            
            if result.get("success"):
                # 验证文件是否真的被创建了
                verification_result = self.main_instance.verify_creation_with_ls(filename, current_shell, creation_type="file")
                if verification_result.get("success", False):
                    return {
                        "success": True,
                        "filename": filename,
                        "message": f"File created: {filename}"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"File create verification failed: {verification_result.get('error', 'Unknown verification error')}"
                    }
            else:
                # 优先使用用户提供的错误信息
                error_msg = (result.get('error_info') if 'error_info' in result else result.get('error', 'Unknown error'))
                return {
                    "success": False,
                    "error": f"Create file failed: {error_msg}"
                }
                
        except Exception as e:
            return {"success": False, "error": f"Create file failed: {e}"}

    def cmd_cat(self, filename):
        """cat命令 - 显示文件内容"""
        try:
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API service not initialized"}
                
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell, please create or switch to a shell"}
            
            if not filename:
                return {"success": False, "error": "Please specify the file to view"}
            
            # 查找文件
            try:
                folder_id, resolved_path = self.main_instance.resolve_path(filename, current_shell)
                # 获取文件信息
                files_result = self.main_instance.drive_service.list_files(folder_id=folder_id, max_results=1)
                if not files_result.get('success') or not files_result.get('files'):
                    converted_filename = self.main_instance.path_resolver.convert_local_path_to_remote(filename)
                    return {"success": False, "error": f"File or directory does not exist: {converted_filename}"}
                file_info = files_result['files'][0]
            except Exception as e:
                converted_filename = self.main_instance.path_resolver.convert_local_path_to_remote(filename)
                return {"success": False, "error": f"File or directory does not exist: {converted_filename}"}
            
            # 检查是否为文件
            if file_info['mimeType'] == 'application/vnd.google-apps.folder':
                return {"success": False, "error": f"cat: {filename}: Is a directory"}
            
            # 下载并读取文件内容
            try:
                import io
                from googleapiclient.http import MediaIoBaseDownload
                
                request = self.drive_service.service.files().get_media(fileId=file_info['id'])
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                
                content = fh.getvalue().decode('utf-8', errors='replace')
                return {"success": True, "output": content, "filename": filename}
                
            except Exception as e:
                return {"success": False, "error": f"无法读取文件内容: {e}"}
                
        except Exception as e:
            return {"success": False, "error": f"执行cat命令时出错: {e}"}

