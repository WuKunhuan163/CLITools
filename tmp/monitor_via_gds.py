#!/usr/bin/env python3
"""
通过GDS命令监测远端任务的访问延迟
"""

import subprocess
import time
from datetime import datetime

remote_log = "/content/drive/MyDrive/REMOTE_ROOT/tmp/long_task.log"
gds_cmd = "/Users/wukunhuan/.local/bin/GOOGLE_DRIVE.py"

print("="*90)
print("🔍 通过GDS监测远端任务访问延迟")
print("="*90)
print(f"远端日志: {remote_log}")
print(f"监测开始: {datetime.now().strftime('%H:%M:%S')}")
print()
print("每10秒通过GDS读取远端日志，持续30次（5分钟）")
print()
print(f"{'次数':<6} {'本地时间':<12} {'远端时间':<15} {'延迟':<10} {'最新行内容':<50}")
print("-" * 100)

for i in range(1, 31):
    local_time = datetime.now()
    local_str = local_time.strftime('%H:%M:%S')
    
    try:
        # 通过GDS tail读取最后一行
        result = subprocess.run(
            ["python3", gds_cmd, "--shell", f"tail -1 {remote_log}"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            last_line = result.stdout.strip()
            
            # 解析远端时间（格式：[0001/3600] HH:MM:SS.fff）
            if "] " in last_line:
                remote_time_str = last_line.split("] ")[-1]
                
                try:
                    remote_time = datetime.strptime(remote_time_str, '%H:%M:%S.%f')
                    
                    # 计算延迟（假设不跨天）
                    local_seconds = local_time.hour * 3600 + local_time.minute * 60 + local_time.second
                    remote_seconds = remote_time.hour * 3600 + remote_time.minute * 60 + remote_time.second
                    delay = local_seconds - remote_seconds
                    
                    if delay < 0:
                        delay += 86400
                    
                    if delay <= 1:
                        delay_str = f"{delay}s ✅"
                    elif delay <= 5:
                        delay_str = f"{delay}s ⚠️"
                    else:
                        delay_str = f"{delay}s ❌"
                    
                except:
                    remote_time_str = "解析失败"
                    delay_str = "N/A"
                
                last_line_short = last_line[:48] + "..." if len(last_line) > 48 else last_line
            else:
                remote_time_str = "无时间戳"
                delay_str = "N/A"
                last_line_short = last_line[:48]
        else:
            remote_time_str = "读取失败"
            delay_str = "N/A"
            last_line_short = result.stderr[:48] if result.stderr else "(无输出)"
            
    except subprocess.TimeoutExpired:
        remote_time_str = "超时"
        delay_str = "N/A"
        last_line_short = "(GDS命令超时)"
    except Exception as e:
        remote_time_str = "错误"
        delay_str = "N/A"
        last_line_short = str(e)[:48]
    
    print(f"{i:<6} {local_str:<12} {remote_time_str:<15} {delay_str:<10} {last_line_short:<50}")
    
    if i < 30:
        time.sleep(10)

print()
print("="*90)
print("✅ 监测完成")
print("="*90)
print()
print("分析：")
print("  • 如果延迟 ≤ 1s：说明GDS访问实时，没有问题")
print("  • 如果延迟 > 1s：说明存在访问延迟")
print("  • 如果一直读取失败：说明GDS访问机制有问题")

