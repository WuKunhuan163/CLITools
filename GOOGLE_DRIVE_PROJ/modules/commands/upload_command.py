from .base_command import BaseCommand

class UploadCommand(BaseCommand):
    @property
    def command_name(self):
        return "upload"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行upload命令"""
        # print(f"DEBUG in UploadCommand: Processing upload with args: {args}")
        
        if not args:
            print("Error: upload command needs a file name")
            return 1
        
        # 参数解析规则：
        # 格式: upload [--target-dir TARGET] [--force] [--remove-local] file1 file2 file3 ...
        # 或者: upload file1 file2 file3 ... [--force] [--remove-local]
        
        target_path = "."  # 默认上传到当前目录
        source_files = []
        force = False
        remove_local = False
        
        i = 0
        while i < len(args):
            if args[i] == '--target-dir':
                if i + 1 < len(args):
                    target_path = args[i + 1]
                    i += 2  # 跳过--target-dir和其值
                else:
                    print("Error: --target-dir option requires a directory path")
                    return 1
            elif args[i] == '--force':
                force = True
                i += 1
            elif args[i] == '--remove-local':
                remove_local = True
                i += 1
            else:
                source_files.append(args[i])
                i += 1
        
        if not source_files:
            print("Error: No source files specified for upload")
            return 1
        
        # 调用upload命令
        result = self.shell.cmd_upload(source_files, target_path=target_path, force=force, remove_local=remove_local)
        
        if result.get("success"):
            # 统一在命令处理结束后打印输出
            stdout = result.get("stdout", "")
            if stdout:
                print(stdout)
            return 0
        else:
            error_msg = result.get("error", "Upload failed")
            print(error_msg)
            return 1
