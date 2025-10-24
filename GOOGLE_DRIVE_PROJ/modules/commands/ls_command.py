from .base_command import BaseCommand

class LsCommand(BaseCommand):
    @property
    def command_name(self):
        return "ls"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行ls命令"""
        # print(f"DEBUG in LsCommand: Processing ls with args: {args}")
        
        # 解析参数
        detailed = False
        recursive = False
        path = None
        
        for arg in args:
            if arg == '--detailed':
                detailed = True
            elif arg == '-R':
                recursive = True
            elif not arg.startswith('-'):
                path = arg
        
        # 调用shell的ls方法
        result = self.shell.cmd_ls(path, detailed=detailed, recursive=recursive)
        
        if result.get("success", False):
            files = result.get("files", [])
            folders = result.get("folders", [])
            all_items = folders + files
            
            if all_items:
                # 按名称排序，文件夹优先
                sorted_folders = sorted(folders, key=lambda x: x.get('name', '').lower())
                sorted_files = sorted(files, key=lambda x: x.get('name', '').lower())
                
                # 合并列表，文件夹在前
                all_sorted_items = sorted_folders + sorted_files
                
                # 简单的列表格式，类似bash ls
                for item in all_sorted_items:
                    name = item.get('name', 'Unknown')
                    if item.get('mimeType') == 'application/vnd.google-apps.folder':
                        print(f"{name}/")
                    else:
                        print(name)
            
            return 0
        else:
            print(result.get("error", "Failed to list directory"))
            return 1
