#!/usr/bin/env python3
"""
测试脚本：测试修复"T"文件夹问题的方案
"""

import tempfile
import subprocess
import os
import shutil
from pathlib import Path
import time

def test_alternative_approaches():
    """测试不同的解决方案"""
    print("=== 测试不同的解决方案 ===")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="GDS_MANUAL_UPLOAD_")
    temp_path = Path(temp_dir)
    
    print(f"临时目录: {temp_dir}")
    print(f"父目录名: {temp_path.parent.name}")
    
    try:
        # 方案1: 使用原始路径（不使用resolve()）
        print("\n方案1: 使用原始路径（不使用resolve()）")
        cmd1 = ["open", str(temp_path)]
        print(f"命令: {' '.join(cmd1)}")
        
        # 方案2: 先cd到目录再打开
        print("\n方案2: 先cd到目录再打开")
        cmd2 = f"cd '{temp_path}' && open ."
        print(f"命令: {cmd2}")
        
        # 方案3: 使用绝对路径但避免resolve()
        print("\n方案3: 使用绝对路径但避免resolve()")
        abs_path = os.path.abspath(temp_dir)
        cmd3 = ["open", abs_path]
        print(f"命令: {' '.join(cmd3)}")
        
        # 方案4: 创建一个README文件，然后打开包含该文件的目录
        print("\n方案4: 通过打开文件来定位目录")
        readme_file = temp_path / "README.txt"
        readme_file.write_text("请将大文件拖放到此文件夹中")
        cmd4 = ["open", "-R", str(readme_file)]  # -R 选项会在Finder中选中文件并显示其所在目录
        print(f"命令: {' '.join(cmd4)}")
        
        # 测试方案1（推荐）
        print(f"\n执行方案1: open {temp_path}")
        result = subprocess.run(["open", str(temp_path)], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ 方案1执行成功")
        else:
            print(f"✗ 方案1执行失败: {result.stderr}")
        
        time.sleep(2)
        
        # 测试方案4（备选）
        print(f"\n执行方案4: open -R {readme_file}")
        result = subprocess.run(["open", "-R", str(readme_file)], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ 方案4执行成功")
        else:
            print(f"✗ 方案4执行失败: {result.stderr}")
        
    finally:
        # 清理
        shutil.rmtree(temp_dir)
        print(f"\n✓ 已清理: {temp_dir}")

def main():
    print("测试修复'T'文件夹问题的方案")
    test_alternative_approaches()
    
    print("\n=== 建议的修复方案 ===")
    print("1. 不使用Path.resolve()，直接使用原始路径")
    print("2. 或者使用 'open -R README.txt' 来精确定位目录")
    print("3. 添加错误处理和重试机制")

if __name__ == "__main__":
    main()
