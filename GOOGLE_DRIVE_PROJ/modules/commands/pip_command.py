from .base_command import BaseCommand

class PipCommand(BaseCommand):
    @property
    def command_name(self):
        return "pip"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行pip命令"""
        # print(f"🔍 PIP_COMMAND DEBUG: Processing pip with args: {args}")
        
        if not args:
            print("Error: pip command needs arguments")
            return 1
        
        # 调用shell的pip方法
        result = self.shell.cmd_pip(*args)
        
        if result.get("success"):
            # 显示pip结果
            message = result.get("message", "")
            if message.strip():  # 只有当message不为空时才打印
                print(message)
            return 0
        else:
            error_msg = result.get("error", "Pip operation failed")
            print(error_msg)
            return 1
