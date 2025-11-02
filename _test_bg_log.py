#!/usr/bin/env /usr/bin/python3
"""
测试脚本：手动测试test_24的后台任务log文件创建
"""
import subprocess
import sys
import time
import re
from pathlib import Path

# 设置路径
BIN_DIR = Path(__file__).parent
GOOGLE_DRIVE_PY = BIN_DIR / "GOOGLE_DRIVE.py"

def run_gds_command(command, use_priority=False):
    """运行GDS命令"""
    cmd_parts = ["/usr/bin/python3", str(GOOGLE_DRIVE_PY), "--shell", "--no-direct-feedback"]
    if use_priority:
        cmd_parts.append("--priority")
    
    if isinstance(command, list):
        cmd_parts.extend(command)
    else:
        cmd_parts.append(command)
    
    print(f"\n执行命令: {' '.join(cmd_parts[-3:])}")  # 只显示最后3个参数
    result = subprocess.run(cmd_parts, capture_output=True, text=True, cwd=BIN_DIR)
    return result

def extract_task_id(output):
    """从--bg命令输出中提取任务ID"""
    match = re.search(r'with ID:\s*(\S+)', output)
    if match:
        return match.group(1)
    return None

print("=" * 80)
print("测试：手动测试test_24的后台任务log文件创建")
print("=" * 80)

# 步骤1：启动一个长时间运行的后台任务（sleep 120秒）
print("\n步骤1：启动长时间运行的后台任务（sleep 120秒）")
long_command = '''python3 -c "
import time
import sys
print('First echo: Task started at', time.strftime('%H:%M:%S'))
sys.stdout.flush()
print('About to sleep for 120 seconds...')
sys.stdout.flush()
time.sleep(120)
print('Second echo: Task completed at', time.strftime('%H:%M:%S'))
sys.stdout.flush()
"'''

result = run_gds_command(f"--bg {long_command}")
print(f"返回码: {result.returncode}")
print(f"输出:\n{result.stdout}")
if result.stderr:
    print(f"错误:\n{result.stderr}")

if result.returncode != 0:
    print("\n❌ 后台任务启动失败！")
    sys.exit(1)

# 提取任务ID
task_id = extract_task_id(result.stdout)
if not task_id:
    print("\n❌ 无法提取任务ID！")
    sys.exit(1)

print(f"\n✓ 后台任务已启动，任务ID: {task_id}")

# 步骤2：等待10秒，然后检查log文件（使用优先队列）
print("\n步骤2：等待10秒，然后检查log文件（使用优先队列）")
time.sleep(10)

result = run_gds_command(f"--priority --bg --log {task_id}")
print(f"\nlog文件查询结果:")
print(f"返回码: {result.returncode}")
print(f"输出:\n{result.stdout}")
if result.stderr:
    print(f"错误:\n{result.stderr}")

# 分析结果
print("\n" + "=" * 80)
print("分析:")
print("=" * 80)

if result.returncode == 0:
    print("✓ log文件查询成功！")
    if "First echo" in result.stdout:
        print("✓ log文件包含部分输出（First echo）")
    else:
        print("⚠️ log文件不包含预期的部分输出")
else:
    print("❌ log文件查询失败！")
    if "not found" in result.stdout:
        print("❌ log文件不存在")

# 步骤3：清理后台任务
print("\n步骤3：清理后台任务")
result = run_gds_command(f"--bg --cleanup {task_id}")
print(f"清理结果: 返回码 {result.returncode}")

print("\n" + "=" * 80)
print("测试完成！")
print("=" * 80)

