#!/usr/bin/env python3
"""
测试脚本：模拟大文件上传的文件夹打开过程
用于调试macOS上打开"T"文件夹的问题
"""

import tempfile
import subprocess
import os
import shutil
from pathlib import Path
import time

def test_folder_opening_process(test_num):
    """模拟一次完整的文件夹打开过程"""
    print(f"\n=== 测试 #{test_num} ===")
    
    try:
        # 1. 创建临时目录（模拟GDS_MANUAL_UPLOAD_xxx）
        temp_dir = tempfile.mkdtemp(prefix="GDS_MANUAL_UPLOAD_")
        print(f"创建临时目录: {temp_dir}")
        
        # 2. 创建测试文件
        test_file = Path(temp_dir) / "test_large_file.txt"
        with open(test_file, 'w') as f:
            f.write("Test large file content")
        print(f"创建测试文件: {test_file}")
        
        # 3. 获取路径信息
        temp_path = Path(temp_dir)
        resolved_path = temp_path.resolve()
        real_path = temp_path.resolve()
        
        print(f"原始路径: {temp_path}")
        print(f"resolve()路径: {resolved_path}")
        print(f"realpath: {real_path}")
        print(f"exists(): {temp_path.exists()}")
        print(f"is_symlink(): {temp_path.is_symlink()}")
        
        # 4. 检查父目录
        parent_dir = temp_path.parent
        parent_resolved = parent_dir.resolve()
        print(f"父目录: {parent_dir}")
        print(f"父目录resolved: {parent_resolved}")
        print(f"父目录名称: {parent_dir.name}")
        
        # 5. 模拟不同的打开方式
        print("\n--- 测试不同的打开方式 ---")
        
        # 方式1: 直接使用原始路径
        print("方式1: 使用原始路径")
        cmd1 = ["open", str(temp_path)]
        print(f"命令: {' '.join(cmd1)}")
        
        # 方式2: 使用resolve()路径
        print("方式2: 使用resolve()路径")
        cmd2 = ["open", str(resolved_path)]
        print(f"命令: {' '.join(cmd2)}")
        
        # 方式3: 使用realpath
        print("方式3: 使用realpath")
        cmd3 = ["open", str(real_path)]
        print(f"命令: {' '.join(cmd3)}")
        
        # 6. 实际执行打开命令（使用resolve()路径，这是当前GDS使用的方式）
        print(f"\n实际执行: open {resolved_path}")
        result = subprocess.run(["open", str(resolved_path)], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ 文件夹打开成功")
        else:
            print(f"✗ 文件夹打开失败: {result.stderr}")
        
        # 7. 等待一下，让用户观察是否打开了错误的文件夹
        print("等待3秒，请观察是否打开了正确的文件夹...")
        time.sleep(3)
        
        return temp_dir, resolved_path
        
    except Exception as e:
        print(f"测试过程中出错: {e}")
        return None, None

def main():
    """主测试函数"""
    print("开始测试大文件上传文件夹打开过程")
    print("目标：重现macOS上打开'T'文件夹的问题")
    
    test_dirs = []
    
    try:
        # 连续进行5次测试
        for i in range(1, 6):
            temp_dir, resolved_path = test_folder_opening_process(i)
            if temp_dir:
                test_dirs.append(temp_dir)
            
            # 每次测试之间暂停
            if i < 5:
                input(f"按Enter继续下一次测试 (还剩{5-i}次)...")
        
        print(f"\n=== 测试总结 ===")
        print(f"共进行了 {len(test_dirs)} 次测试")
        print("请观察是否有任何测试打开了错误的文件夹（如'T'文件夹）")
        
        # 显示所有测试目录的路径模式
        print("\n所有测试目录的路径模式:")
        for i, dir_path in enumerate(test_dirs, 1):
            path = Path(dir_path)
            print(f"测试{i}: {path}")
            print(f"  父目录: {path.parent}")
            print(f"  父目录名: {path.parent.name}")
            
    finally:
        # 清理所有测试目录
        print(f"\n清理 {len(test_dirs)} 个测试目录...")
        for temp_dir in test_dirs:
            try:
                shutil.rmtree(temp_dir)
                print(f"✓ 已删除: {temp_dir}")
            except Exception as e:
                print(f"✗ 删除失败: {temp_dir} - {e}")

if __name__ == "__main__":
    main()
