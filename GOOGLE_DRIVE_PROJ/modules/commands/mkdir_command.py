from .base_command import BaseCommand

class MkdirCommand(BaseCommand):
    @property
    def command_name(self):
        return "mkdir"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行mkdir命令"""
        # print(f"DEBUG in MkdirCommand: Processing mkdir with args: {args}")
        
        if not args:
            print("Error: mkdir command needs a directory name")
            return 1
        
        # 解析参数
        create_parents = False
        directories = []
        
        for arg in args:
            if arg == '-p':
                create_parents = True
            else:
                directories.append(arg)
        
        if not directories:
            print("Error: mkdir command needs a directory name")
            return 1
        
        # 处理每个目录
        for directory in directories:
            result = self.shell.cmd_mkdir(directory, recursive=create_parents)
            
            if not result.get("success", False):
                print(result.get("error", f"Failed to create directory: {directory}"))
                return 1
        
        return 0
