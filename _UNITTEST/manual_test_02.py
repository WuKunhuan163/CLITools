#!/usr/bin/env python3
"""
手动复现test_02的exact logic
"""
import sys
import subprocess
from pathlib import Path

# 添加路径
BIN_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BIN_DIR))

from GOOGLE_DRIVE_PROJ.google_drive_shell import GoogleDriveShell

# 模拟test_gds的gds()方法
def run_gds_command(cmd):
    """模拟test_gds的gds()方法"""
    print(f'命令: {repr(cmd)}')
    
    # 构造完整的GDS命令
    full_cmd = f'python3 {BIN_DIR}/GOOGLE_DRIVE.py --shell --no-direct-feedback {repr(cmd)}'
    
    # 执行
    result = subprocess.run(
        full_cmd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=300
    )
    
    print(f'返回码: {result.returncode}')
    print(f'stdout (repr): {repr(result.stdout)}')
    print(f'stdout中\\的数量: {result.stdout.count(chr(92))}')
    
    return result

# 模拟test 02的逻辑
print("="*80)
print("模拟test 02")
print("="*80)

# Line 1586
content = "Line 1\\nLine 2\\tTabbed\\Backslash"
print(f"\n步骤1: content = {repr(content)}")
print(f"  \\的数量: {content.count(chr(92))}")

# Line 1587
content_escaped = content.replace("'", "\\'")
print(f"\n步骤2: content_escaped = {repr(content_escaped)}")
print(f"  \\的数量: {content_escaped.count(chr(92))}")

# Line 1588 - 写入文件
complex_echo_file = '/content/drive/MyDrive/REMOTE_ROOT/tmp/manual_test02_complex.txt'
write_cmd = f'echo "{content_escaped}" > {complex_echo_file}'
print(f"\n步骤3: write_cmd = {repr(write_cmd)}")
print(f"  \\的数量: {write_cmd.count(chr(92))}")

print(f"\n执行写入命令:")
result_write = run_gds_command(write_cmd)

# 读取文件
read_cmd = f'cat {complex_echo_file}'
print(f"\n执行读取命令:")
result_read = run_gds_command(read_cmd)

print("\n" + "="*80)
print("分析")
print("="*80)
print(f"期望内容（repr）: {repr(content)}")
print(f"实际内容（repr）: {repr(result_read.stdout.strip())}")
print(f"期望\\数量: {content.count(chr(92))}")
print(f"实际\\数量: {result_read.stdout.count(chr(92))}")

if result_read.stdout.count(chr(92)) == content.count(chr(92)):
    print("✅ 匹配")
else:
    print(f"❌ 不匹配！差异: {result_read.stdout.count(chr(92)) - content.count(chr(92))}")

print("="*80)

