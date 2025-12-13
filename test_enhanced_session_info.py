#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版session信息检测 - 获取更多可区分的信息
"""

import os
import sys
import subprocess
import json
import time
import socket
import psutil
from pathlib import Path

def get_enhanced_session_info():
    """获取增强的session信息用于窗口区分"""
    info = {}
    
    print("=== 增强版Session信息检测 ===")
    
    # 1. 基础环境变量
    print("\n1. 基础环境变量:")
    basic_vars = {
        'CURSOR_TRACE_ID': os.environ.get('CURSOR_TRACE_ID', ''),
        'CURSOR_AGENT': os.environ.get('CURSOR_AGENT', ''),
        'PWD': os.environ.get('PWD', ''),
        'OLDPWD': os.environ.get('OLDPWD', ''),
        'SHELL': os.environ.get('SHELL', ''),
        'TERM_SESSION_ID': os.environ.get('TERM_SESSION_ID', ''),
        'VSCODE_PROCESS_TITLE': os.environ.get('VSCODE_PROCESS_TITLE', ''),
    }
    
    for key, value in basic_vars.items():
        if value:
            print(f"   {key}: {value}")
            info[key] = value
    
    # 2. 工作目录信息
    print("\n2. 工作目录信息:")
    current_dir = os.getcwd()
    dir_name = os.path.basename(current_dir)
    parent_dir = os.path.basename(os.path.dirname(current_dir))
    print(f"   当前目录: {current_dir}")
    print(f"   目录名: {dir_name}")
    print(f"   父目录: {parent_dir}")
    info['current_dir'] = current_dir
    info['dir_name'] = dir_name
    info['parent_dir'] = parent_dir
    
    # 3. 时间戳信息
    print("\n3. 时间戳信息:")
    current_time = time.time()
    readable_time = time.strftime("%H:%M:%S", time.localtime(current_time))
    print(f"   当前时间戳: {int(current_time)}")
    print(f"   可读时间: {readable_time}")
    info['timestamp'] = int(current_time)
    info['readable_time'] = readable_time
    
    # 4. 进程信息
    print("\n4. 进程信息:")
    try:
        current_pid = os.getpid()
        parent_pid = os.getppid()
        print(f"   当前进程PID: {current_pid}")
        print(f"   父进程PID: {parent_pid}")
        
        # 获取父进程信息
        try:
            parent_process = psutil.Process(parent_pid)
            parent_name = parent_process.name()
            parent_cmdline = ' '.join(parent_process.cmdline())
            print(f"   父进程名: {parent_name}")
            print(f"   父进程命令行: {parent_cmdline[:100]}...")
            info['parent_process'] = parent_name
            info['parent_cmdline'] = parent_cmdline
        except:
            pass
            
        info['current_pid'] = current_pid
        info['parent_pid'] = parent_pid
    except Exception as e:
        print(f"   进程信息获取失败: {e}")
    
    # 5. 网络信息
    print("\n5. 网络信息:")
    try:
        hostname = socket.gethostname()
        print(f"   主机名: {hostname}")
        info['hostname'] = hostname
    except Exception as e:
        print(f"   网络信息获取失败: {e}")
    
    # 6. Cursor特定文件
    print("\n6. Cursor特定文件:")
    cursor_files = [
        "~/.cursor/projects/Users-wukunhuan-local-bin",
        "~/.cursor/User/settings.json",
        "~/.cursor/User/globalStorage/state.vscdb"
    ]
    
    for file_path in cursor_files:
        expanded_path = os.path.expanduser(file_path)
        if os.path.exists(expanded_path):
            try:
                stat = os.stat(expanded_path)
                mod_time = time.strftime("%H:%M:%S", time.localtime(stat.st_mtime))
                print(f"   {file_path}: 存在，修改时间 {mod_time}")
                info[f'file_{os.path.basename(file_path)}'] = mod_time
            except:
                pass
    
    # 7. 终端特定信息
    print("\n7. 终端特定信息:")
    terminal_vars = ['TERM', 'TERM_PROGRAM', 'TERM_PROGRAM_VERSION', 'ITERM_SESSION_ID']
    for var in terminal_vars:
        value = os.environ.get(var)
        if value:
            print(f"   {var}: {value}")
            info[var] = value
    
    # 8. 生成唯一标识符
    print("\n8. 生成唯一标识符:")
    
    # 方案A: 基于CURSOR_TRACE_ID + 目录 + 时间
    if info.get('CURSOR_TRACE_ID'):
        trace_short = info['CURSOR_TRACE_ID'][:8]
        dir_short = info['dir_name'][:10]
        time_short = str(info['timestamp'])[-4:]
        identifier_a = f"{trace_short}-{dir_short}-{time_short}"
        print(f"   方案A (trace+dir+time): {identifier_a}")
        info['identifier_a'] = identifier_a
    
    # 方案B: 基于工作目录 + 可读时间
    dir_short = info['dir_name'][:15]
    time_readable = info['readable_time'].replace(':', '')
    identifier_b = f"{dir_short}@{time_readable}"
    print(f"   方案B (dir@time): {identifier_b}")
    info['identifier_b'] = identifier_b
    
    # 方案C: 基于父进程 + PID
    if info.get('parent_process'):
        parent_short = info['parent_process'][:8]
        pid_short = str(info['current_pid'])[-3:]
        identifier_c = f"{parent_short}-{pid_short}"
        print(f"   方案C (parent-pid): {identifier_c}")
        info['identifier_c'] = identifier_c
    
    return info

def generate_window_title(info):
    """基于session信息生成有意义的窗口标题"""
    
    # 优先级1: 使用目录名 + 时间
    if info.get('dir_name') and info.get('readable_time'):
        title = f"{info['dir_name']} [{info['readable_time']}]"
        return title
    
    # 优先级2: 使用CURSOR_TRACE_ID + 目录
    if info.get('CURSOR_TRACE_ID') and info.get('dir_name'):
        trace_short = info['CURSOR_TRACE_ID'][:8]
        title = f"{info['dir_name']} [Cursor-{trace_short}]"
        return title
    
    # 优先级3: 使用标识符
    if info.get('identifier_b'):
        return f"USERINPUT [{info['identifier_b']}]"
    
    # 默认
    return "Agent Mode"

if __name__ == "__main__":
    info = get_enhanced_session_info()
    
    print(f"\n{'='*60}")
    print("推荐的窗口标题方案:")
    
    title = generate_window_title(info)
    print(f"🎯 推荐标题: {title}")
    
    # 显示JSON格式的完整信息
    print(f"\n📊 完整session信息 (JSON):")
    print(json.dumps(info, indent=2, ensure_ascii=False))