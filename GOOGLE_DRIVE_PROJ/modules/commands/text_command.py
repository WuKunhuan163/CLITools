"""
Text operations commands (cat, read, create_text_file)
从text_operations.py迁移而来
合并了cat_command和read_command
"""

from .base_command import BaseCommand

class TextCommand(BaseCommand):
    """文本操作命令 - 统一处理cat, read"""
    
    @property
    def command_name(self):
        # 返回主命令名，但这个类会注册多个命令
        return "text"
    
    def execute(self, cmd, args, command_identifier=None):
        """根据命令名分发到具体的处理方法"""
        if cmd == "cat":
            return self.execute_cat(args)
        elif cmd == "read":
            return self.execute_read(args)
        else:
            print(f"Error: Unknown text command: {cmd}")
            return 1
    
    def execute_cat(self, args):
        """执行cat命令"""
        if not args:
            print("Error: cat command needs a file name")
            return 1
        
        filename = args[0]
        
        # 调用shell的cat方法
        result = self.cmd_cat(filename)
        
        if result.get("success", False):
            if not result.get("direct_feedback", False):
                print(result.get("output", ""), end = "")
            return 0
        else:
            print(result.get("error", "Failed to read file"))
            return 1
    
    def execute_read(self, args):
        """执行read命令"""
        if not args:
            print("Error: read command needs a file name")
            return 1
        
        # 解析参数
        force = False
        read_args = []
        
        for arg in args:
            if arg == '--force':
                force = True
            else:
                read_args.append(arg)
        
        if not read_args:
            print("Error: read command needs a file name")
            return 1
        
        filename = read_args[0]
        remaining_args = read_args[1:]
        
        # 调用shell的read方法
        result = self.cmd_read(filename, *remaining_args, force=force)
        
        if result.get("success", False):
            if not result.get("direct_feedback", False):
                # 添加行号显示，根据总行数动态调整宽度
                content = result.get("output", "")
                lines = content.split('\n')
                total_lines = len(lines)
                width = len(str(total_lines))  # 计算总行数的位数
                for i, line in enumerate(lines, 1):
                    print(f"{i:{width}}: {line}")
            return 0
        else:
            print(result.get("error", "Failed to read file"))
            return 1

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
    
    def cmd_read(self, filename, *remaining_args, force=False):
        """read命令 - 显示文件内容(带行号)"""
        # cmd_read is essentially the same as cmd_cat, but the execute_read method adds line numbers
        return self.cmd_cat(filename)
