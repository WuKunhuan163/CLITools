"""
Text operations commands (cat, read)
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
