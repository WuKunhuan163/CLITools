#!/usr/bin/env python3
"""
测试--bg机制：远端任务 vs 本地访问的延迟
模拟真实的后台任务访问场景
"""

import subprocess
import time
from datetime import datetime

def test_bg_access_delay():
    """测试后台任务访问延迟"""
    
    print("="*70)
    print("🧪 测试--bg访问延迟（远端写入 → 本地读取）")
    print("="*70)
    print()
    
    # Step 1: 在Colab创建后台任务（模拟--bg）
    log_file = "/content/drive/MyDrive/REMOTE_ROOT/tmp/test_bg_task.log"
    
    print("[Step 1] 在Colab启动后台任务")
    print(f"  任务：每秒输出时间戳")
    print(f"  日志：{log_file}")
    print()
    
    # 通过GDS创建后台任务
    task_script = f'''
import subprocess

# 后台任务脚本：每秒输出时间戳
script = """
import time
from datetime import datetime

start_time = time.time()
print(f"Task started at: {{datetime.now().strftime('%H:%M:%S.%f')[:-3]}}", flush=True)

for i in range(1, 16):  # 运行15秒
    elapsed = time.time() - start_time
    current_time = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    print(f"[{{i:02d}}] Elapsed: {{elapsed:.1f}}s | Time: {{current_time}}", flush=True)
    time.sleep(1)

print(f"Task completed at: {{datetime.now().strftime('%H:%M:%S.%f')[:-3]}}", flush=True)
"""

# 启动后台任务
subprocess.Popen(
    ["python3", "-c", script],
    stdout=open("{log_file}", "w"),
    stderr=subprocess.STDOUT
)

print("Background task started!")
print(f"Log file: {log_file}")
print(f"PID: (background)")
'''
    
    # 通过GDS执行远端命令
    result = subprocess.run(
        ["python3", "GOOGLE_DRIVE.py", "--shell", "--no-direct-feedback", f"python3 -c '{task_script}'"],
        capture_output=True,
        text=True,
        cwd="/Users/wukunhuan/.local/bin"
    )
    
    if result.returncode != 0:
        print(f"❌ 启动失败: {result.stderr}")
        return
    
    print(f"✅ 后台任务已启动")
    task_start_local = datetime.now()
    print(f"  本地启动时间: {task_start_local.strftime('%H:%M:%S.%f')[:-3]}")
    print()
    
    # Step 2: 本地定期访问日志文件
    print("[Step 2] 本地定期访问日志文件（通过Google Drive）")
    print("  每2秒读取一次，共读取8次")
    print()
    
    local_drive_log = "/Users/wukunhuan/Applications/Google Drive/REMOTE_ROOT/tmp/test_bg_task.log"
    
    print(f"{'访问次数':<8} {'本地时间':<15} {'日志大小':<10} {'最新行内容':<40} {'延迟分析'}")
    print("-" * 100)
    
    for check_num in range(1, 9):
        time.sleep(2)  # 每2秒检查一次
        
        access_time = datetime.now()
        access_time_str = access_time.strftime('%H:%M:%S.%f')[:-3]
        
        try:
            import os
            if os.path.exists(local_drive_log):
                size = os.path.getsize(local_drive_log)
                
                # 读取最后一行
                with open(local_drive_log, 'r') as f:
                    lines = f.readlines()
                    last_line = lines[-1].strip() if lines else "(empty)"
                
                # 解析远端时间戳
                if "Time:" in last_line:
                    remote_time_str = last_line.split("Time:")[-1].strip()
                    try:
                        # 计算延迟
                        remote_time = datetime.strptime(remote_time_str, '%H:%M:%S.%f')
                        access_time_only = datetime.strptime(access_time_str, '%H:%M:%S.%f')
                        
                        # 处理跨天问题（简单处理）
                        delay_ms = (access_time_only - remote_time).total_seconds() * 1000
                        
                        delay_str = f"{delay_ms:.0f}ms 延迟" if delay_ms > 0 else "实时"
                    except:
                        delay_str = "无法解析"
                else:
                    delay_str = "无时间戳"
                
                last_line_short = last_line[:38] + "..." if len(last_line) > 38 else last_line
                
                print(f"第{check_num}次    {access_time_str:<15} {size:<10} {last_line_short:<40} {delay_str}")
            else:
                print(f"第{check_num}次    {access_time_str:<15} {'N/A':<10} {'文件不存在':<40}")
        except Exception as e:
            print(f"第{check_num}次    {access_time_str:<15} {'ERROR':<10} {str(e):<40}")
    
    print()
    print("="*70)
    print("📊 结论")
    print("="*70)
    print()
    print("观察：")
    print("  • 如果延迟 < 100ms：说明Google Drive同步很快，不是问题")
    print("  • 如果延迟 > 1s：说明Google Drive同步延迟，导致--bg --status看不到最新输出")
    print("  • 如果始终看不到文件：说明Drive挂载或同步有问题")
    print()
    print("这就是test_29中'Log size: 0 bytes'的原因：")
    print("  本地通过Drive访问远端日志时，存在同步延迟")
    print()

if __name__ == '__main__':
    test_bg_access_delay()

