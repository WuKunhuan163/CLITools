#!/usr/bin/env python3
"""
监测远端长任务的访问延迟
通过本地Google Drive访问远端日志文件
"""

import time
import os
from datetime import datetime

# 本地Google Drive挂载的日志文件路径
local_log_path = "/Users/wukunhuan/Applications/Google Drive/REMOTE_ROOT/tmp/long_task.log"

# 通过GDS访问的路径（备用）
remote_log_gds = "@/tmp/long_task.log"

print("="*80)
print("🔍 监测远端长任务访问延迟")
print("="*80)
print(f"远端日志: /content/drive/MyDrive/REMOTE_ROOT/tmp/long_task.log")
print(f"本地访问: {local_log_path}")
print(f"监测开始: {datetime.now().strftime('%H:%M:%S')}")
print()
print("每10秒检查一次，持续监测...")
print()
print(f"{'检查次数':<10} {'本地时间':<12} {'文件大小':<12} {'最新行内容':<40} {'远端时间':<12} {'延迟(秒)'}")
print("-" * 110)

check_count = 0

while True:
    check_count += 1
    local_time = datetime.now()
    local_time_str = local_time.strftime('%H:%M:%S')
    
    try:
        if os.path.exists(local_log_path):
            # 读取文件大小
            size = os.path.getsize(local_log_path)
            size_str = f"{size} B"
            
            # 读取最后一行
            with open(local_log_path, 'r') as f:
                lines = f.readlines()
                if lines:
                    last_line = lines[-1].strip()
                    
                    # 提取远端时间戳（格式：[0001/3600] HH:MM:SS.fff）
                    if "] " in last_line:
                        remote_time_str = last_line.split("] ")[-1]
                        
                        try:
                            # 解析远端时间
                            remote_time = datetime.strptime(remote_time_str, '%H:%M:%S.%f')
                            local_time_only = datetime.strptime(local_time_str, '%H:%M:%S')
                            
                            # 计算延迟（秒）
                            # 注意：这里简单处理，假设不跨天
                            delay_seconds = (local_time_only.hour * 3600 + local_time_only.minute * 60 + local_time_only.second) - \
                                          (remote_time.hour * 3600 + remote_time.minute * 60 + remote_time.second)
                            
                            if delay_seconds < 0:
                                delay_seconds += 86400  # 跨天处理
                            
                            delay_str = f"{delay_seconds}s"
                            
                            # 分析
                            if delay_seconds <= 1:
                                analysis = "✅ 实时"
                            elif delay_seconds <= 5:
                                analysis = "⚠️ 轻微延迟"
                            else:
                                analysis = f"❌ 延迟{delay_seconds}秒"
                            
                        except Exception as e:
                            remote_time_str = "解析失败"
                            delay_str = f"N/A ({e})"
                            analysis = ""
                    else:
                        remote_time_str = "无时间戳"
                        delay_str = "N/A"
                        analysis = ""
                    
                    # 截断最新行显示
                    last_line_short = last_line[:38] + "..." if len(last_line) > 38 else last_line
                else:
                    last_line_short = "(文件为空)"
                    remote_time_str = "N/A"
                    delay_str = "N/A"
                    analysis = ""
        else:
            size_str = "不存在"
            last_line_short = "文件未同步"
            remote_time_str = "N/A"
            delay_str = "N/A"
            analysis = "❌ 文件不可见"
        
        print(f"{check_count:<10} {local_time_str:<12} {size_str:<12} {last_line_short:<40} {remote_time_str:<12} {delay_str:<10} {analysis}")
        
    except Exception as e:
        print(f"{check_count:<10} {local_time_str:<12} ERROR: {str(e)[:60]}")
    
    time.sleep(10)  # 每10秒检查一次
    
    # 检查30次后停止（5分钟）
    if check_count >= 30:
        print()
        print("="*80)
        print("✅ 监测完成（已检查30次，共5分钟）")
        print("="*80)
        break

