from .base_command import BaseCommand

class LinterCommand(BaseCommand):
    @property
    def command_name(self):
        return "linter"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行linter命令"""
        # print(f"DEBUG in LinterCommand: Processing linter with args: {args}")
        
        if not args:
            print("Error: linter command needs a file name")
            return 1
        
        filename = args[0]
        
        # 调用linter命令
        result = self.shell.cmd_linter(filename)
        
        if result.get("success"):
            # 显示linter结果
            language = result.get("language", "unknown")
            status = "PASS" if result.get("success", False) else "FAIL"
            message = result.get("message", "")
            
            print(f"Language: {language}")
            print(f"Status: {status}")
            print(f"Message: {message}")
            
            # 显示错误信息
            errors = result.get("errors", [])
            if errors:
                print("\nErrors:")
                for error in errors:
                    print(f"  • {error}")
            
            # 显示警告信息
            warnings = result.get("warnings", [])
            if warnings:
                print("\nWarnings:")
                for warning in warnings:
                    print(f"  • {warning}")
            
            # 根据是否有错误或警告决定返回码
            if errors or warnings:
                return 1  # 有问题时返回1
            else:
                return 0  # 无问题时返回0
        else:
            error_msg = result.get("error", "Linter failed")
            print(error_msg)
            return 1

