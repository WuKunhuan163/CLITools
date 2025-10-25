from .base_command import BaseCommand

class DownloadCommand(BaseCommand):
    @property
    def command_name(self):
        return "download"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行download命令"""
        if not args:
            print("Error: download command needs a file name")
            return 1
        
        filename = args[0]
        local_path = args[1] if len(args) > 1 else None
        
        # 检查是否有--force参数
        force = False
        if "--force" in args:
            force = True
            # 从args中移除--force参数
            args = [arg for arg in args if arg != "--force"]
            filename = args[0] if args else None
            local_path = args[1] if len(args) > 1 else None
        
        if not filename:
            print("Error: download command needs a file name")
            return 1
        
        # 调用shell的download方法
        result = self.shell.cmd_download(filename, local_path=local_path, force=force)
        
        if result.get("success", False):
            message = result.get("message", "Downloaded successfully")
            print(message)
            
            # 如果有本地路径信息，也显示出来
            if result.get("local_path"):
                print(f"Local path: {result.get('local_path')}")
            
            # 如果是目录下载，显示额外信息
            if result.get("source") == "directory_download":
                print(f"Directory compressed and downloaded as zip file")
                if result.get("zip_filename"):
                    print(f"Temporary zip filename: {result.get('zip_filename')}")
            
            return 0
        else:
            error_msg = result.get("error", "Download failed")
            print(error_msg)
            return 1

