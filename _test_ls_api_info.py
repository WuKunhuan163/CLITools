#!/usr/bin/env python3
"""
测试脚本：查看Google Drive API返回的ls结果包含哪些信息
"""
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from GOOGLE_DRIVE_PROJ.google_drive_shell import GoogleDriveShell
import json

def main():
    print("=" * 80)
    print("测试：Google Drive API ls结果信息查看")
    print("=" * 80)
    
    # 创建shell实例
    print("\n步骤1：创建GoogleDriveShell实例...")
    shell = GoogleDriveShell()
    print("✓ Shell实例创建成功")
    
    # 测试路径
    test_path = "~/tmp"
    print(f"\n步骤3：列出测试路径的内容: {test_path}")
    
    # 执行ls命令
    result = shell.cmd_ls(test_path, detailed=False, recursive=False)
    
    if not result.get("success"):
        print(f"错误：ls命令失败: {result.get('error')}")
        return 1
    
    print("✓ ls命令执行成功")
    
    # 分析返回的文件信息
    print("\n" + "=" * 80)
    print("文件信息分析")
    print("=" * 80)
    
    files = result.get("files", [])
    folders = result.get("folders", [])
    
    print(f"\n找到 {len(files)} 个文件和 {len(folders)} 个文件夹")
    
    # 打印第一个文件的所有字段（如果存在）
    if files:
        print("\n" + "-" * 80)
        print("第一个文件的所有字段:")
        print("-" * 80)
        first_file = files[0]
        print(json.dumps(first_file, indent=2, ensure_ascii=False))
        
        print("\n" + "-" * 80)
        print("可用字段列表:")
        print("-" * 80)
        for key in sorted(first_file.keys()):
            value = first_file[key]
            # 截断长值
            if isinstance(value, str) and len(value) > 50:
                value_str = f"{value[:50]}..."
            else:
                value_str = str(value)
            print(f"  {key:20s} : {value_str}")
    
    # 打印第一个文件夹的所有字段（如果存在）
    if folders:
        print("\n" + "-" * 80)
        print("第一个文件夹的所有字段:")
        print("-" * 80)
        first_folder = folders[0]
        print(json.dumps(first_folder, indent=2, ensure_ascii=False))
        
        print("\n" + "-" * 80)
        print("可用字段列表:")
        print("-" * 80)
        for key in sorted(first_folder.keys()):
            value = first_folder[key]
            # 截断长值
            if isinstance(value, str) and len(value) > 50:
                value_str = f"{value[:50]}..."
            else:
                value_str = str(value)
            print(f"  {key:20s} : {value_str}")
    
    # 总结可用字段
    print("\n" + "=" * 80)
    print("总结：所有可用的字段")
    print("=" * 80)
    
    all_keys = set()
    for item in files + folders:
        all_keys.update(item.keys())
    
    for key in sorted(all_keys):
        print(f"  - {key}")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

