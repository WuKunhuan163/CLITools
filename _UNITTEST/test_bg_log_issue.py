#!/usr/bin/env python3
"""
测试后台任务log文件问题的脚本
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

def run_gds_bg_log(task_id):
    """获取GDS --bg任务log"""
    cmd = [sys.executable, str(GOOGLE_DRIVE_PY), "--shell", "--no-direct-feedback", "--bg", "--log", task_id]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result

def run_gds_bg_result(task_id):
    """获取GDS --bg任务结果"""
    cmd = [sys.executable, str(GOOGLE_DRIVE_PY), "--shell", "--no-direct-feedback", "--bg", "--result", task_id]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result

def extract_task_id(output):
    """从--bg命令输出中提取任务ID"""
    match = re.search(r'Background task started with ID: (\d+_\d+)', output)
    if match:
        return match.group(1)
    return None

def main():
    print("=" * 60)
    print("测试后台任务log文件问题")
    print("=" * 60)
    
    # 创建一个简单的测试命令
    test_command = '''python3 -c "
import time
print('TEST_OUTPUT: Hello from background task')
print('TEST_OUTPUT: Current time is', time.strftime('%H:%M:%S'))
print('TEST_OUTPUT: Task completed')
"'''
    
    print("步骤1：创建后台任务...")
    result = run_gds_bg_command(test_command)
    print(f"创建结果 - 返回码: {result.returncode}")
    print(f"标准输出:\n{result.stdout}")
    if result.stderr:
        print(f"标准错误:\n{result.stderr}")
    
    if result.returncode != 0:
        print("❌ 后台任务创建失败！")
        return 1
    
    task_id = extract_task_id(result.stdout)
    if not task_id:
        print("❌ 无法提取任务ID！")
        return 1
    
    print(f"✅ 成功创建任务，ID: {task_id}")
    
    print("\n步骤2：等待5秒后查询log...")
    time.sleep(5)
    
    log_result = run_gds_bg_log(task_id)
    print(f"Log查询结果 - 返回码: {log_result.returncode}")
    print(f"Log内容:\n{log_result.stdout}")
    if log_result.stderr:
        print(f"Log错误:\n{log_result.stderr}")
    
    print("\n步骤3：查询result...")
    result_output = run_gds_bg_result(task_id)
    print(f"Result查询结果 - 返回码: {result_output.returncode}")
    print(f"Result内容:\n{result_output.stdout}")
    if result_output.stderr:
        print(f"Result错误:\n{result_output.stderr}")
    
    print("\n" + "=" * 60)
    print("分析结果:")
    
    # 检查log内容
    if "TEST_OUTPUT:" in log_result.stdout:
        print("✅ Log文件包含用户输出")
    else:
        print("❌ Log文件不包含用户输出（这是bug！）")
    
    # 检查result内容
    if "TEST_OUTPUT:" in result_output.stdout:
        print("✅ Result文件包含用户输出")
    else:
        print("❌ Result文件不包含用户输出")
    
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())

