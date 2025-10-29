"""
FileCore - 文件操作核心类（Delegator模式）
将所有具体实现委托给专门的command类
"""

from .commands.navigation_command import NavigationCommand
from .commands.ls_operations import LsOperations
from .commands.file_command import FileCommand


class FileCore:
    """
    Core file operations (委托模式)
    所有方法委托给专门的command类
    """
    def __init__(self, drive_service, main_instance):
        self.drive_service = drive_service
        self.main_instance = main_instance
        
        # 初始化各个command类
        self.navigation_cmd = NavigationCommand(main_instance)
        self.ls_ops = LsOperations(main_instance)
        self.file_cmd = FileCommand(main_instance)
    
    def cleanup_local_equivalent_files(self, file_moves):
        """委托到cache_manager的本地等效文件清理"""
        return self.main_instance.cache_manager.cleanup_local_equivalent_files(file_moves)
    
    # Navigation commands
    def cmd_pwd(self):
        """显示当前路径"""
        return self.navigation_cmd.cmd_pwd()
    
    def cmd_cd(self, path):
        """切换目录"""
        return self.navigation_cmd.cmd_cd(path)
    
    # Listing commands
    def cmd_ls(self, path=None, detailed=False, recursive=False, show_hidden=False):
        """列出目录内容"""
        return self.ls_ops.cmd_ls(path, detailed, recursive, show_hidden)
    
    def ls_recursive(self, root_folder_id, root_path, detailed, show_hidden=False, max_depth=5):
        """递归列出目录内容"""
        return self.ls_ops.ls_recursive(root_folder_id, root_path, detailed, show_hidden, max_depth)
    
    def build_nested_structure(self, all_items, root_path):
        """构建嵌套的文件夹结构"""
        return self.ls_ops.build_nested_structure(all_items, root_path)
    
    def _generate_folder_url(self, folder_id):
        """生成文件夹的网页链接"""
        return self.ls_ops._generate_folder_url(folder_id)
    
    def generate_web_url(self, file):
        """为文件生成网页链接"""
        return self.ls_ops.generate_web_url(file)
    
    def _resolve_file_path(self, file_path, current_shell):
        """解析文件路径"""
        return self.ls_ops._resolve_file_path(file_path, current_shell)
    
    # File commands
    def cmd_touch(self, filename):
        """创建空文件"""
        return self.file_cmd.cmd_touch(filename)
    
    def cmd_rm(self, path, recursive=False, force=False):
        """删除文件或目录"""
        return self.file_cmd.cmd_rm(path, recursive, force)
    
    def cmd_mv(self, source, destination, force=False):
        """移动/重命名文件或文件夹"""
        return self.file_cmd.cmd_mv(source, destination, force)
