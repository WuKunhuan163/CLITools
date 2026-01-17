#!/usr/bin/env python3
"""
最小化测试用例 - 测试echo "Hello World"命令
直接调用test_gds.py的.gds()接口
"""

from test_gds import GDSTest
import sys

# Create an instance
print("=== 初始化测试实例 ===")
test_instance = GDSTest()
GDSTest.setUpClass()
test_instance.setUp()

print(f"\n=== 测试最简单的echo命令 ===")
cmd = 'echo "Hello World"'
print(f"命令: {repr(cmd)}")

print(f"\n=== 执行GDS命令 ===")
print(f"\n=== 调用栈 ===")
import traceback
traceback.print_stack()

result = test_instance.gds(cmd)

print(f"\n=== 命令执行结果 ===")
print(f"returncode: {result.returncode}")
print(f"stdout (repr): {repr(result.stdout)}")
print(f"stdout (显示): {result.stdout}")
print(f"stderr (repr): {repr(result.stderr)}")
if result.stderr:
    print(f"stderr (显示): {result.stderr}")

print(f"\n=== 使用get_cleaned_stdout清理ANSI码 ===")
cleaned = test_instance.get_cleaned_stdout(result)
print(f"cleaned (repr): {repr(cleaned)}")
print(f"cleaned (显示): {cleaned}")
print(f"cleaned.strip(): {repr(cleaned.strip())}")

print(f"\n=== 对比bash结果 ===")
bash_result = test_instance.bash(cmd)
print(f"bash returncode: {bash_result.returncode}")
print(f"bash stdout (repr): {repr(bash_result.stdout)}")
print(f"bash stdout.strip(): {repr(bash_result.stdout.strip())}")

print(f"\n=== 比较结果 ===")
if cleaned.strip() == bash_result.stdout.strip():
    print("GDS和bash输出一致！")
else:
    print("GDS和bash输出不一致")
    print(f"  Expected (bash): {repr(bash_result.stdout.strip())}")
    print(f"  Got (GDS):       {repr(cleaned.strip())}")

# 清理
print(f"\n=== 清理测试环境 ===")
test_instance.tearDown()
GDSTest.tearDownClass()
