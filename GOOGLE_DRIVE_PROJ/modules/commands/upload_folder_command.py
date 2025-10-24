from .base_command import BaseCommand

class UploadFolderCommand(BaseCommand):
    @property
    def command_name(self):
        return "upload-folder"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行upload-folder命令"""
        # print(f"🔍 UPLOAD_FOLDER_COMMAND DEBUG: Processing upload-folder with args: {args}")
        
        if not args:
            print("Error: upload-folder command needs a folder path")
            return 1
        
        # 参数解析规则：
        # 格式: upload-folder [--target-dir TARGET] [--keep-zip] [--force] folder_path
        
        folder_path = None
        target_path = "."  # 默认上传到当前目录
        keep_zip = False
        force = False
        
        i = 0
        while i < len(args):
            if args[i] == '--target-dir':
                if i + 1 < len(args):
                    target_path = args[i + 1]
                    i += 2  # 跳过--target-dir和其值
                else:
                    print("Error: --target-dir option requires a directory path")
                    return 1
            elif args[i] == '--keep-zip':
                keep_zip = True
                i += 1
            elif args[i] == '--force':
                force = True
                i += 1
            else:
                if folder_path is None:
                    folder_path = args[i]
                else:
                    # 如果没有使用--target-dir，最后一个参数可以是目标路径（向后兼容）
                    target_path = args[i]
                i += 1
        
        if not folder_path:
            print("Error: No folder path specified for upload-folder")
            return 1
        
        # 调用upload-folder命令
        result = self.shell.cmd_upload_folder(folder_path, target_path=target_path, keep_zip=keep_zip, force=force)
        
        if result.get("success"):
            # 统一在命令处理结束后打印输出
            stdout = result.get("stdout", "")
            if stdout:
                print(stdout)
            return 0
        else:
            error_msg = result.get("error", "Upload folder failed")
            print(error_msg)
            return 1
