#!/usr/bin/env python3
"""
临时测试脚本：连续调用5个GDS echo，观察remount flag的行为
"""

import sys
import time
sys.path.insert(0, '/Users/wukunhuan/.local/bin/_UNITTEST')

from test_gds import GDSTest

print("=" * 50)
print("开始测试remount flag行为")
print("=" * 50)

# Create test instance
print("\n初始化测试实例...")
test_instance = GDSTest()
GDSTest.setUpClass()
test_instance.setUp()

# 连续执行5次GDS echo
for i in range(1, 6):
    print(f"\n{'=' * 50}")
    print(f"GDS echo 调用 #{i}")
    print(f"{'=' * 50}")
    
    cmd = f'echo "Test message {i}"'
    print(f"执行命令: {cmd}")
    
    result = test_instance.gds(cmd)
    
    print(f"返回码: {result.returncode}")
    if result.returncode == 0:
        print(f"输出: {result.stdout.strip()}")
    else:
        print(f"错误: {result.stderr}")
    
    print(f"完成 #{i}")
    
    # 每次调用之间等待1秒
    if i < 5:
        time.sleep(1)

# 清理
print(f"\n{'=' * 50}")
print("清理测试环境")
print(f"{'=' * 50}")
test_instance.tearDown()
GDSTest.tearDownClass()

print("\n测试完成!")
print("\n请检查debug日志:")
print("  tail -f ~/.local/bin/GOOGLE_DRIVE_DATA/window_manager_debug.log")

