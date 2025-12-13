#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
显示当前获得的session信息
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# 导入USERINPUT.py中的函数
exec(open('USERINPUT.py').read())

if __name__ == "__main__":
    print("=== 当前获得的Session信息 ===")
    
    # 获取增强的session信息
    info = get_enhanced_session_info()
    
    print(f"\n📊 完整Session信息:")
    for key, value in info.items():
        if value:  # 只显示非空值
            print(f"   {key}: {value}")
    
    print(f"\n🎯 窗口标题: {get_cursor_session_title()}")
    
    print(f"\n💡 可用于区分窗口的关键信息:")
    print(f"   - 项目名: {info.get('project_name', 'N/A')}")
    print(f"   - 当前时间: {info.get('readable_time', 'N/A')}")
    print(f"   - Cursor Trace ID: {info.get('CURSOR_TRACE_ID', 'N/A')[:8]}...")
    print(f"   - 进程PID: {info.get('current_pid', 'N/A')}")
    print(f"   - 主机名: {info.get('hostname', 'N/A')}")