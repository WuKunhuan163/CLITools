
import time
import os
from pathlib import Path

# 导入debug捕获系统
from .command_executor import debug_capture, debug_print

class FileCore:
    """
    Core file operations (upload, download, navigation)
    """
    def __init__(self, drive_service, main_instance):
        self.drive_service = drive_service
        self.main_instance = main_instance

    def cleanup_local_equivalent_files(self, file_moves):
        """委托到cache_manager的本地等效文件清理"""
        return self.main_instance.cache_manager.cleanup_local_equivalent_files(file_moves)

    def _generate_folder_url(self, folder_id):
        """生成文件夹的网页链接"""
        return f"https://drive.google.com/drive/folders/{folder_id}"

    def generate_web_url(self, file):
        """为文件生成网页链接"""
        file_id = file['id']
        mime_type = file['mimeType']
        
        if mime_type == 'application/vnd.google.colaboratory':
            # Colab文件
            return f"https://colab.research.google.com/drive/{file_id}"
        elif mime_type == 'application/vnd.google-apps.document':
            # Google文档
            return f"https://docs.google.com/document/d/{file_id}/edit"
        elif mime_type == 'application/vnd.google-apps.spreadsheet':
            # Google表格
            return f"https://docs.google.com/spreadsheets/d/{file_id}/edit"
        elif mime_type == 'application/vnd.google-apps.presentation':
            # Google幻灯片
            return f"https://docs.google.com/presentation/d/{file_id}/edit"
        elif mime_type == 'application/vnd.google-apps.folder':
            # 文件夹
            return f"https://drive.google.com/drive/folders/{file_id}"
        else:
            # 其他文件（预览或下载）
            return f"https://drive.google.com/file/d/{file_id}/view"

    def _resolve_file_path(self, file_path, current_shell):
        """解析文件路径，返回文件信息（如果存在）"""
        try:
            # 分离目录和文件名
            if "/" in file_path:
                dir_path = "/".join(file_path.split("/")[:-1])
                filename = file_path.split("/")[-1]
            else:
                dir_path = "."
                filename = file_path
            
            # 解析目录路径
            if dir_path == ".":
                parent_folder_id = current_shell.get("current_folder_id", self.main_instance.REMOTE_ROOT_FOLDER_ID)
            else:
                parent_folder_id, _ = self.main_instance.resolve_path(dir_path, current_shell)
                if not parent_folder_id:
                    return None
            
            # 在父目录中查找文件
            result = self.drive_service.list_files(folder_id=parent_folder_id, max_results=100)
            
            if not result['success']:
                return None
            
            files = result.get('files', [])
            for i, file in enumerate(files):
                file_name = file.get('name', 'UNKNOWN')
                if file_name == filename:
                    file['url'] = self.generate_web_url(file)
                    return file
            
            return None
            
        except Exception as e:
            return None
