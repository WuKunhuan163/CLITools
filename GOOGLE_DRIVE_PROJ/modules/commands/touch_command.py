"""Touch command wrapper - delegates to FileCommand"""
from .file_command import FileCommand

class TouchCommand(FileCommand):
    @property
    def command_name(self):
        return "touch"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行touch命令"""
        return self.execute_touch(args)
    
    # cmd_touch method is inherited from FileCommand
