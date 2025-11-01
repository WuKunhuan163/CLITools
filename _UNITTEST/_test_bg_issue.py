#!/usr/bin/env python3
"""
测试脚本：复现test_24中后台任务查询失败的问题
"""
import subprocess
import sys
import time
import re
from pathlib import Path

# 设置路径
GOOGLE_DRIVE_PY = Path(__file__).parent.parent / "GOOGLE_DRIVE.py"

def run_gds_bg_command(command):
    """运行GDS --bg命令并返回结果"""
    cmd = [sys.executable, str(GOOGLE_DRIVE_PY), "--shell", "--no-direct-feedback", "--bg", command]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result

def run_gds_bg_status(task_id, use_priority=False):
    """查询GDS --bg任务状态 - 支持优先队列"""
    if use_priority:
        cmd = [sys.executable, str(GOOGLE_DRIVE_PY), "--shell", "--no-direct-feedback", "--priority", "--bg", "--status", task_id]
    else:
        cmd = [sys.executable, str(GOOGLE_DRIVE_PY), "--shell", "--no-direct-feedback", "--bg", "--status", task_id]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result

def extract_task_id(output):
    """从--bg命令输出中提取任务ID"""
    match = re.search(r'Background task started with ID: (\d+_\d+)', output)
    if match:
        return match.group(1)
    return None

# 测试：复现test_24的长时间任务问题
print("=" * 30)
print("测试：复现test_24中的后台任务查询问题")
print("=" * 30)

long_command = '''python3 -c "
import time
import sys
print('First echo: Task started at', time.strftime('%H:%M:%S'))
sys.stdout.flush()
print('About to sleep for 30 seconds...')
sys.stdout.flush()
time.sleep(30)
print('Second echo: Task completed at', time.strftime('%H:%M:%S'))
sys.stdout.flush()
"'''

print("\n步骤1：创建长时间运行的后台任务...")
result = run_gds_bg_command(long_command)
print(f"创建结果 - 返回码: {result.returncode}")
print(f"标准输出:\n{result.stdout}")
print(f"标准错误:\n{result.stderr}")

if result.returncode != 0:
    print("\n错误：后台任务创建失败！")
    sys.exit(1)

task_id = extract_task_id(result.stdout)
if not task_id:
    print("\n错误：无法提取任务ID！")
    sys.exit(1)

print(f"\n成功创建任务，ID: {task_id}")

print("\n步骤2：等待10秒后查询任务状态（使用优先队列）...")
time.sleep(10)

first_status = run_gds_bg_status(task_id, use_priority=True)
print(f"\n第一次status查询结果:")
print(f"  返回码: {first_status.returncode}")
print(f"  标准输出:\n{first_status.stdout}")
print(f"  标准错误:\n{first_status.stderr}")

if first_status.returncode != 0:
    print("\n❌ 错误：第一次status查询失败！")
    print(f"这正是test_24中遇到的问题。")
else:
    print("\n✅ 第一次status查询成功！")
    
    # 检查输出内容
    if "First echo: Task started at" in first_status.stdout:
        print("  ✓ 包含第一个echo输出")
    else:
        print("  ✗ 缺少第一个echo输出")
    
    if "About to sleep for 30 seconds" in first_status.stdout:
        print("  ✓ 包含sleep提示")
    else:
        print("  ✗ 缺少sleep提示")
    
    if "Second echo: Task completed at" in first_status.stdout:
        print("  ✗ 不应包含第二个echo输出（任务还未完成）")
    else:
        print("  ✓ 正确：不包含第二个echo输出")

print("\n" + "=" * 30)
print("测试完成")
print("=" * 30)

