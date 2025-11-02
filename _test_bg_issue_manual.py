#!/usr/bin/env python3
"""
手动测试test_24的失败步骤
"""

import sys
import subprocess
from pathlib import Path

# 获取GOOGLE_DRIVE.py路径
GOOGLE_DRIVE_PY = Path(__file__).parent / "GOOGLE_DRIVE.py"

def run_gds_bg_command(command):
    """运行GDS --bg命令并返回结果"""
    cmd = [sys.executable, str(GOOGLE_DRIVE_PY), "--shell", "--no-direct-feedback", "--bg", command]
    print(f"执行命令: {' '.join(cmd)}")
    print()
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result

def extract_task_id(output):
    """从--bg命令输出中提取任务ID"""
    import re
    match = re.search(r'Background task started with ID: (\d+_\d+)', output)
    if match:
        return match.group(1)
    return None

print("=" * 60)
print("手动测试test_24的失败步骤")
print("=" * 60)
print()

print("测试3: 错误命令处理")
print("创建一个会失败的后台任务（ls不存在的目录）")
print()

# 这是test_24失败的命令
result = run_gds_bg_command('ls "nonexistent_directory/that/should/not/exist"')

print("返回码:", result.returncode)
print()
print("标准输出:")
print(result.stdout)
print()
if result.stderr:
    print("标准错误:")
    print(result.stderr)
    print()

if result.returncode == 0:
    print("✅ 任务创建成功")
    task_id = extract_task_id(result.stdout)
    if task_id:
        print(f"任务ID: {task_id}")
    else:
        print("⚠️ 无法提取任务ID")
else:
    print(f"❌ 任务创建失败 (返回码: {result.returncode})")
    print("这不符合预期 - 后台任务创建应该成功，即使命令本身会失败")

