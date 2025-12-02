#!/usr/bin/env python3
"""
临时测试脚本：使用subprocess直接调用GDS echo
观察remount flag的行为和debug输出
"""

import subprocess
import time
import sys

print("=" * 50)
print("开始测试remount flag行为（subprocess方式）")
print("=" * 50)
print("\nDebug日志将输出到:")
print("  ~/.local/bin/GOOGLE_DRIVE_DATA/window_manager_debug.log")
print()

# 连续执行5次GDS echo
for i in range(1, 6):
    print(f"\n{'=' * 50}")
    print(f"GDS echo 调用 #{i}")
    print(f"{'=' * 50}")
    
    cmd = ["python3", "/Users/wukunhuan/.local/bin/GOOGLE_DRIVE.py", "--shell", f'echo "Test message {i}"']
    print(f"执行命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(f"返回码: {result.returncode}")
        if result.returncode == 0:
            print(f"输出: {result.stdout.strip()}")
        else:
            print(f"错误: {result.stderr.strip()}")
        
        print(f"完成 #{i}")
        
    except subprocess.TimeoutExpired:
        print(f"命令超时 (60秒)")
    except FileNotFoundError:
        print(f"错误: python3或GOOGLE_DRIVE.py未找到")
        sys.exit(1)
    except Exception as e:
        print(f"执行失败: {e}")
        sys.exit(1)
    
    # 每次调用之间等待1秒
    if i < 5:
        time.sleep(1)

print(f"\n{'=' * 50}")
print("测试完成!")
print(f"{'=' * 50}")

print("\n请检查debug日志:")
print("  tail -100 ~/.local/bin/GOOGLE_DRIVE_DATA/window_manager_debug.log | grep REMOUNT")

