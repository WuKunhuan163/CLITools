from .base_command import BaseCommand

class RmCommand(BaseCommand):
    @property
    def command_name(self):
        return "rm"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行rm命令"""
        if not args:
            print("Error: rm command needs a file or directory name")
            return 1
        
        # 解析参数
        recursive = False
        force = False
        files = []
        
        for arg in args:
            if arg == '-r':
                recursive = True
            elif arg == '-f':
                force = True
            elif arg == '-rf' or arg == '-fr':
                recursive = True
                force = True
            else:
                files.append(arg)
        
        if not files:
            print("Error: rm command needs a file or directory name")
            return 1
        
        # 处理每个文件/目录
        for file_path in files:
            result = self.shell.cmd_rm(file_path, recursive=recursive, force=force)
            
            if not result.get("success", False):
                print(result.get("error", f"Failed to remove: {file_path}"))
                return 1
        
        return 0

