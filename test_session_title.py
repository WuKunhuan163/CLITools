#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试获取当前Cursor session标题
"""

import os
import sys
import subprocess
import json
import time

def test_cursor_session_title():
    """测试获取Cursor session标题的各种方法"""
    print("=== 测试获取Cursor session标题 ===")
    
    methods = {}
    
    # 方法1: 环境变量
    print("\n1. 检查环境变量:")
    cursor_vars = {}
    for key, value in os.environ.items():
        if any(word in key.lower() for word in ['cursor', 'session', 'title', 'window']):
            cursor_vars[key] = value
            print(f"   {key}: {value}")
    
    methods['environment'] = cursor_vars
    
    # 方法2: AppleScript获取Cursor窗口标题
    if sys.platform == 'darwin':
        print("\n2. AppleScript获取Cursor窗口标题:")
        try:
            # 获取前台应用
            applescript1 = '''
            tell application "System Events"
                set frontApp to name of first application process whose frontmost is true
                return frontApp
            end tell
            '''
            result1 = subprocess.run(['osascript', '-e', applescript1], 
                                   capture_output=True, text=True, timeout=3)
            if result1.returncode == 0:
                front_app = result1.stdout.strip()
                print(f"   前台应用: {front_app}")
                methods['front_app'] = front_app
            
            # 尝试获取Cursor窗口标题
            applescript2 = '''
            tell application "Cursor"
                try
                    return name of front window
                on error
                    return "无法获取窗口标题"
                end try
            end tell
            '''
            result2 = subprocess.run(['osascript', '-e', applescript2], 
                                   capture_output=True, text=True, timeout=3)
            if result2.returncode == 0:
                cursor_title = result2.stdout.strip()
                print(f"   Cursor窗口标题: {cursor_title}")
                methods['cursor_window'] = cursor_title
            
            # 获取所有Cursor窗口
            applescript3 = '''
            tell application "Cursor"
                try
                    set windowList to {}
                    repeat with w in windows
                        set end of windowList to name of w
                    end repeat
                    return my list_to_string(windowList)
                on error
                    return "无法获取窗口列表"
                end try
            end tell
            
            on list_to_string(lst)
                set AppleScript's text item delimiters to " | "
                set result to lst as string
                set AppleScript's text item delimiters to ""
                return result
            end list_to_string
            '''
            result3 = subprocess.run(['osascript', '-e', applescript3], 
                                   capture_output=True, text=True, timeout=3)
            if result3.returncode == 0:
                all_windows = result3.stdout.strip()
                print(f"   所有Cursor窗口: {all_windows}")
                methods['all_windows'] = all_windows
                
        except Exception as e:
            print(f"   AppleScript测试失败: {e}")
    
    # 方法3: 进程信息
    print("\n3. 检查进程信息:")
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        cursor_processes = []
        for line in result.stdout.split('\n'):
            if 'cursor' in line.lower() and 'helper' not in line.lower():
                cursor_processes.append(line)
                print(f"   {line}")
        methods['processes'] = cursor_processes
    except Exception as e:
        print(f"   进程信息获取失败: {e}")
    
    # 方法4: 文件系统
    print("\n4. 检查配置文件:")
    config_files = [
        os.path.expanduser("~/.cursor/projects"),
        os.path.expanduser("~/Library/Application Support/Cursor/User/globalStorage"),
        os.path.expanduser("~/Library/Application Support/Cursor/User/workspaceStorage")
    ]
    
    for config_path in config_files:
        if os.path.exists(config_path):
            print(f"   找到配置目录: {config_path}")
            try:
                if os.path.isdir(config_path):
                    files = os.listdir(config_path)[:5]  # 限制显示
                    print(f"     包含: {files}")
            except:
                pass
    
    # 总结最有希望的方法
    print(f"\n{'='*50}")
    print("总结 - 可能获取session标题的方法:")
    
    if 'cursor_window' in methods and methods['cursor_window'] != "无法获取窗口标题":
        print(f"✅ 最佳方案: AppleScript获取Cursor窗口标题")
        print(f"   标题: {methods['cursor_window']}")
        return methods['cursor_window']
    
    if 'all_windows' in methods and methods['all_windows'] != "无法获取窗口列表":
        print(f"✅ 备选方案: 从所有窗口中选择")
        print(f"   窗口列表: {methods['all_windows']}")
        return methods['all_windows']
    
    if cursor_vars:
        print(f"✅ 备选方案: 使用环境变量")
        return f"Cursor-{cursor_vars.get('CURSOR_TRACE_ID', 'Unknown')[:8]}"
    
    print("❌ 无法获取session标题，使用默认值")
    return "Agent Mode"

if __name__ == "__main__":
    session_title = test_cursor_session_title()
    print(f"\n🎯 最终获取的session标题: {session_title}")