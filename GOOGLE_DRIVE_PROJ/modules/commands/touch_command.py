from .base_command import BaseCommand

class TouchCommand(BaseCommand):
    @property
    def command_name(self):
        return "touch"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行touch命令"""
        if not args:
            print("Error: touch command needs a file name")
            return 1
        
        # 处理每个文件
        for file_path in args:
            result = self.shell.cmd_touch(file_path)
            
            if not result.get("success", False):
                print(result.get("error", f"Failed to create file: {file_path}"))
                return 1
        
        return 0
