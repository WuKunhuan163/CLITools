from .base_command import BaseCommand

class PwdCommand(BaseCommand):
    @property
    def command_name(self):
        return "pwd"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行pwd命令"""
        # print(f"DEBUG in PwdCommand: Processing pwd with args: {args}")
        
        # pwd命令不需要参数
        if args:
            print("pwd: too many arguments")
            return 1
        
        # 导入shell_commands模块中的具体函数
        import os
        import sys
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        modules_dir = os.path.join(current_dir, 'modules')
        if modules_dir not in sys.path:
            sys.path.append(modules_dir)
        
        try:
            from shell_commands import shell_pwd
            return shell_pwd(command_identifier)
        except ImportError as e:
            print(f"Error: Failed to import shell_pwd: {e}")
            return 1
