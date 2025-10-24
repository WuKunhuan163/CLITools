from .base_command import BaseCommand

class PyenvCommand(BaseCommand):
    @property
    def command_name(self):
        return "pyenv"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行pyenv命令"""
        # print(f"DEBUG in PyenvCommand: Processing pyenv with args: {args}")
        # 调用pyenv操作
        result = self.shell.cmd_pyenv(*args)
        
        if result.get("success"):
            # 统一在命令处理结束后打印输出
            stdout = result.get("stdout", "")
            if stdout:
                print(stdout)
            return 0
        else:
            error_msg = result.get("error", "Pyenv operation failed")
            print(error_msg)
            return 1

