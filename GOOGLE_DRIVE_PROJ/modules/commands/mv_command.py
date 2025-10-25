from .base_command import BaseCommand

class MvCommand(BaseCommand):
    @property
    def command_name(self):
        return "mv"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行mv命令"""
        if len(args) < 2:
            print("Error: mv command needs source and destination")
            return 1
        
        source = args[0]
        destination = args[1]
        
        result = self.shell.cmd_mv(source, destination)
        
        if not result.get("success", False):
            print(result.get("error", f"Failed to move {source} to {destination}"))
            return 1
        
        return 0
