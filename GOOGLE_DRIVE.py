#!/usr/bin/env python3
"""
Google Drive Shell - 主入口文件
简化版本，直接导入和使用 GoogleDriveShell
"""

import os
import sys
import warnings
from pathlib import Path

# 抑制urllib3的SSL警告
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 设置模块搜索路径
current_dir = Path(__file__).parent
google_drive_proj_dir = current_dir / "GOOGLE_DRIVE_PROJ"
google_drive_data_dir = current_dir / "GOOGLE_DRIVE_DATA"

# 确保数据目录存在
google_drive_data_dir.mkdir(exist_ok=True)
(google_drive_data_dir / "remote_files").mkdir(exist_ok=True)

if str(google_drive_proj_dir) not in sys.path:
    sys.path.insert(0, str(google_drive_proj_dir))

# 导入GoogleDriveShell
from GOOGLE_DRIVE_PROJ.google_drive_shell import GoogleDriveShell

def main():
    """主函数 - 初始化GoogleDriveShell并处理命令行参数"""
    try:
        # 初始化GoogleDriveShell
        shell = GoogleDriveShell()
        
        # 处理命令行参数
        exit_code = shell.handle_command_line_args()
        return exit_code
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
