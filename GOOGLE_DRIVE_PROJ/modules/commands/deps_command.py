from .base_command import BaseCommand

class DepsCommand(BaseCommand):
    @property
    def command_name(self):
        return "deps"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行deps命令"""
        # print(f"DEBUG in DepsCommand: Processing deps with args: {args}")
        
        if not args:
            print("Error: deps command needs arguments")
            return 1
        
        # 调用shell的deps方法
        result = self.shell.cmd_deps(*args)
        
        if result.get("success"):
            # 显示deps结果
            message = result.get("message", "")
            if message.strip():  # 只有当message不为空时才打印
                print(message)
            return 0
        else:
            error_msg = result.get("error", "Dependency analysis failed")
            print(error_msg)
            return 1

