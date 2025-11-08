#!/usr/bin/env python3
"""
手动复现test_03的exact logic
"""
import sys
import subprocess
from pathlib import Path

# 添加路径
BIN_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BIN_DIR))

# 模拟test_03的echo -e命令
print("="*80)
print("模拟test 03 - echo -e多行输出")
print("="*80)

multiline_file = '/content/drive/MyDrive/REMOTE_ROOT/tmp/manual_test03_multiline.txt'

# 写入
write_cmd = f'echo -e "Line1\\nLine2\\nLine3" > {multiline_file}'
print(f"\n步骤1: write_cmd = {repr(write_cmd)}")
print(f"  \\的数量: {write_cmd.count(chr(92))}")

full_cmd = f'python3 {BIN_DIR}/GOOGLE_DRIVE.py --shell --no-direct-feedback {repr(write_cmd)}'
result_write = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=300)

print(f"\n执行写入:")
print(f"  返回码: {result_write.returncode}")

# 读取
read_cmd = f'cat {multiline_file}'
print(f"\n步骤2: read_cmd = {repr(read_cmd)}")

full_cmd2 = f'python3 {BIN_DIR}/GOOGLE_DRIVE.py --shell --no-direct-feedback {repr(read_cmd)}'
result_read = subprocess.run(full_cmd2, shell=True, capture_output=True, text=True, timeout=300)

print(f"\n执行读取:")
print(f"  返回码: {result_read.returncode}")
print(f"  stdout (repr): {repr(result_read.stdout)}")
print(f"  包含的换行符数量: {result_read.stdout.count(chr(10))}")

# 分析
print("\n" + "="*80)
print("分析")
print("="*80)
expected = "Line1\nLine2\nLine3"
print(f"期望（repr）: {repr(expected)}")
print(f"实际（repr）: {repr(result_read.stdout.strip())}")

# 检查是否是3行
lines = result_read.stdout.strip().split('\n')
print(f"\n行数: {len(lines)}")
if len(lines) >= 3:
    for i, line in enumerate(lines[:3]):
        print(f"  Line {i+1}: {repr(line)}")

if expected in result_read.stdout:
    print("\n✅ 匹配！echo -e正确解释了转义序列")
else:
    print("\n❌ 不匹配")

print("="*80)

