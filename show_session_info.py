#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立的session信息显示脚本
"""

import os
import sys
import time
import socket
from pathlib import Path

def get_project_name():
    """获取项目名称"""
    try:
        current_dir = Path.cwd()
        project_dir = current_dir
        while project_dir.parent != project_dir:
            if (project_dir / '.git').exists():
                break
            project_dir = project_dir.parent
        
        project_name = current_dir.name
        return project_name, str(current_dir), str(project_dir)
    except Exception:
        return "Unknown", os.getcwd(), os.getcwd()

def get_enhanced_session_info():
    """获取增强的session信息"""
    info = {}
    
    # 基础环境变量
    info['CURSOR_TRACE_ID'] = os.environ.get('CURSOR_TRACE_ID', '')
    info['CURSOR_AGENT'] = os.environ.get('CURSOR_AGENT', '')
    info['PWD'] = os.environ.get('PWD', '')
    info['SHELL'] = os.environ.get('SHELL', '')
    info['VSCODE_PROCESS_TITLE'] = os.environ.get('VSCODE_PROCESS_TITLE', '')
    
    # 工作目录信息
    project_name, current_dir, project_dir = get_project_name()
    info['project_name'] = project_name
    info['current_dir'] = current_dir
    info['project_dir'] = project_dir
    
    # 时间戳信息
    current_time = time.time()
    info['timestamp'] = int(current_time)
    info['readable_time'] = time.strftime("%H:%M:%S", time.localtime(current_time))
    
    # 进程信息
    try:
        info['current_pid'] = os.getpid()
        info['parent_pid'] = os.getppid()
    except:
        pass
    
    # 网络信息
    try:
        info['hostname'] = socket.gethostname().split('.')[0]
    except:
        pass
    
    # 终端信息
    info['TERM'] = os.environ.get('TERM', '')
    info['TERM_PROGRAM'] = os.environ.get('TERM_PROGRAM', '')
    
    return info

if __name__ == "__main__":
    print("=== 当前Session信息 ===")
    
    info = get_enhanced_session_info()
    
    print(f"\n📊 完整Session信息:")
    for key, value in info.items():
        if value:  # 只显示非空值
            print(f"   {key}: {value}")
    
    # 生成窗口标题
    project_name = info.get('project_name', 'USERINPUT')
    window_title = f"{project_name} - Agent Mode"
    print(f"\n🎯 窗口标题: {window_title}")
    
    print(f"\n💡 可用于区分窗口的关键信息:")
    print(f"   - 项目名: {info.get('project_name', 'N/A')}")
    print(f"   - 当前时间: {info.get('readable_time', 'N/A')}")
    print(f"   - Cursor Trace ID: {info.get('CURSOR_TRACE_ID', 'N/A')[:8]}...")
    print(f"   - 进程PID: {info.get('current_pid', 'N/A')}")
    print(f"   - 主机名: {info.get('hostname', 'N/A')}")
    
    print(f"\n🔍 这些信息可以帮助用户区分不同的USERINPUT窗口:")
    print(f"   - 不同项目会显示不同的项目名")
    print(f"   - 同一时间启动的窗口会有相同的时间戳")
    print(f"   - 每个Cursor session有唯一的CURSOR_TRACE_ID")
    print(f"   - 每个进程有唯一的PID")