from .base_command import BaseCommand

class ReadCommand(BaseCommand):
    @property
    def command_name(self):
        return "read"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行read命令"""
        # print(f"DEBUG in ReadCommand: Processing read with args: {args}")
        
        if not args:
            print("Error: read command needs a file name")
            return 1
        
        # 解析参数
        force = False
        read_args = []
        
        for arg in args:
            if arg == '--force':
                force = True
            else:
                read_args.append(arg)
        
        if not read_args:
            print("Error: read command needs a file name")
            return 1
        
        filename = read_args[0]
        remaining_args = read_args[1:]
        
        # 调用shell的read方法
        result = self.shell.cmd_read(filename, *remaining_args, force=force)
        
        if result.get("success", False):
            if not result.get("direct_feedback", False):
                # 添加行号显示，根据总行数动态调整宽度
                content = result.get("output", "")
                lines = content.split('\n')
                total_lines = len(lines)
                width = len(str(total_lines))  # 计算总行数的位数
                for i, line in enumerate(lines, 1):
                    print(f"{i:{width}}: {line}")
            return 0
        else:
            print(result.get("error", "Failed to read file"))
            return 1
