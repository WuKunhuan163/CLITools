#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：研究获取Cursor session标题的各种方法
"""

import os
import sys
import subprocess
import json
import time
import psutil

def test_environment_variables():
    """测试环境变量方法"""
    print("=== 测试环境变量 ===")
    
    cursor_related_vars = []
    all_vars = dict(os.environ)
    
    # 查找Cursor相关的环境变量
    for key, value in all_vars.items():
        if 'cursor' in key.lower() or 'vscode' in key.lower():
            cursor_related_vars.append((key, value))
            print(f"  {key}: {value}")
    
    # 查找可能包含标题信息的变量
    title_candidates = []
    for key, value in all_vars.items():
        if any(word in key.lower() for word in ['title', 'name', 'session', 'window']):
            title_candidates.append((key, value))
            print(f"  标题候选 {key}: {value}")
    
    return cursor_related_vars, title_candidates

def test_process_information():
    """测试进程信息方法"""
    print("\n=== 测试进程信息 ===")
    
    cursor_processes = []
    
    try:
        # 使用psutil获取详细进程信息
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'environ']):
            try:
                if 'cursor' in proc.info['name'].lower():
                    cursor_processes.append(proc.info)
                    print(f"  进程: {proc.info['name']} (PID: {proc.info['pid']})")
                    
                    # 检查命令行参数
                    if proc.info['cmdline']:
                        for arg in proc.info['cmdline']:
                            if 'title' in arg.lower() or 'session' in arg.lower():
                                print(f"    可能的标题参数: {arg}")
                    
                    # 检查环境变量
                    if proc.info['environ']:
                        for key, value in proc.info['environ'].items():
                            if 'title' in key.lower() or 'session' in key.lower():
                                print(f"    环境变量 {key}: {value}")
            
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    
    except ImportError:
        print("  psutil不可用，使用ps命令")
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            for line in lines:
                if 'cursor' in line.lower() and 'helper' not in line.lower():
                    print(f"  进程: {line}")
        except Exception as e:
            print(f"  ps命令失败: {e}")
    
    return cursor_processes

def test_applescript_methods():
    """测试AppleScript方法（仅macOS）"""
    print("\n=== 测试AppleScript方法 ===")
    
    if sys.platform != 'darwin':
        print("  非macOS系统，跳过AppleScript测试")
        return []
    
    methods = []
    
    # 方法1: 获取前台应用窗口标题
    try:
        applescript1 = '''
        tell application "System Events"
            set frontApp to name of first application process whose frontmost is true
            return frontApp
        end tell
        '''
        result = subprocess.run(['osascript', '-e', applescript1], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            front_app = result.stdout.strip()
            print(f"  前台应用: {front_app}")
            methods.append(('front_app', front_app))
    except Exception as e:
        print(f"  获取前台应用失败: {e}")
    
    # 方法2: 尝试直接获取Cursor窗口标题
    try:
        applescript2 = '''
        tell application "Cursor"
            return name of front window
        end tell
        '''
        result = subprocess.run(['osascript', '-e', applescript2], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            cursor_title = result.stdout.strip()
            print(f"  Cursor窗口标题: {cursor_title}")
            methods.append(('cursor_window', cursor_title))
    except Exception as e:
        print(f"  获取Cursor窗口标题失败: {e}")
    
    # 方法3: 获取所有Cursor窗口
    try:
        applescript3 = '''
        tell application "Cursor"
            set windowList to {}
            repeat with w in windows
                set end of windowList to name of w
            end repeat
            return windowList
        end tell
        '''
        result = subprocess.run(['osascript', '-e', applescript3], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            windows = result.stdout.strip()
            print(f"  所有Cursor窗口: {windows}")
            methods.append(('all_windows', windows))
    except Exception as e:
        print(f"  获取所有Cursor窗口失败: {e}")
    
    # 方法4: 使用System Events获取窗口信息
    try:
        applescript4 = '''
        tell application "System Events"
            tell process "Cursor"
                set windowTitles to {}
                repeat with w in windows
                    set end of windowTitles to title of w
                end repeat
                return windowTitles
            end tell
        end tell
        '''
        result = subprocess.run(['osascript', '-e', applescript4], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            system_windows = result.stdout.strip()
            print(f"  System Events窗口: {system_windows}")
            methods.append(('system_events', system_windows))
    except Exception as e:
        print(f"  System Events获取窗口失败: {e}")
    
    return methods

def test_file_system_methods():
    """测试文件系统方法"""
    print("\n=== 测试文件系统方法 ===")
    
    methods = []
    
    # 检查可能的配置文件
    config_paths = [
        os.path.expanduser("~/Library/Application Support/Cursor"),
        os.path.expanduser("~/.cursor"),
        os.path.expanduser("~/.vscode"),
        os.path.expanduser("~/Library/Preferences/com.todesktop.230313mzl4w4u92.plist"),
        "/tmp/cursor-*",
        "/var/tmp/cursor-*"
    ]
    
    for path in config_paths:
        if os.path.exists(path):
            print(f"  找到配置路径: {path}")
            try:
                if os.path.isdir(path):
                    files = os.listdir(path)[:10]  # 限制显示文件数
                    print(f"    包含文件: {files}")
                    
                    # 查找可能包含session信息的文件
                    for file in files:
                        if any(word in file.lower() for word in ['session', 'workspace', 'window']):
                            file_path = os.path.join(path, file)
                            print(f"    可能的session文件: {file_path}")
                            methods.append(('config_file', file_path))
                
            except Exception as e:
                print(f"    读取失败: {e}")
    
    # 检查当前工作目录的.vscode文件夹
    vscode_path = os.path.join(os.getcwd(), '.vscode')
    if os.path.exists(vscode_path):
        print(f"  找到工作区.vscode: {vscode_path}")
        try:
            files = os.listdir(vscode_path)
            for file in files:
                if file.endswith('.json'):
                    file_path = os.path.join(vscode_path, file)
                    print(f"    配置文件: {file_path}")
                    methods.append(('workspace_config', file_path))
        except Exception as e:
            print(f"    读取.vscode失败: {e}")
    
    return methods

def test_network_methods():
    """测试网络方法"""
    print("\n=== 测试网络方法 ===")
    
    methods = []
    
    # 检查是否有本地API端点
    try:
        import requests
        
        # 常见的编辑器API端点
        endpoints = [
            'http://localhost:3000/api/session',
            'http://localhost:8080/api/session',
            'http://127.0.0.1:3000/api/session',
            'http://127.0.0.1:8080/api/session'
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.get(endpoint, timeout=1)
                if response.status_code == 200:
                    print(f"  成功连接到: {endpoint}")
                    print(f"  响应: {response.text[:200]}")
                    methods.append(('api_endpoint', endpoint, response.text))
            except:
                pass
    
    except ImportError:
        print("  requests模块不可用，跳过网络测试")
    
    return methods

def test_cursor_specific_methods():
    """测试Cursor特定方法"""
    print("\n=== 测试Cursor特定方法 ===")
    
    methods = []
    
    # 方法1: 检查Cursor的IPC通信
    try:
        # 查找可能的IPC socket文件
        import glob
        
        ipc_patterns = [
            '/tmp/cursor-*',
            '/var/folders/*/T/cursor-*',
            os.path.expanduser('~/Library/Application Support/Cursor/User/workspaceStorage/*/state.vscdb')
        ]
        
        for pattern in ipc_patterns:
            matches = glob.glob(pattern)
            for match in matches:
                print(f"  找到IPC相关文件: {match}")
                methods.append(('ipc_file', match))
    
    except Exception as e:
        print(f"  IPC文件搜索失败: {e}")
    
    # 方法2: 检查最近打开的工作区
    try:
        recent_workspaces_path = os.path.expanduser(
            "~/Library/Application Support/Cursor/User/globalStorage/storage.json"
        )
        if os.path.exists(recent_workspaces_path):
            print(f"  找到最近工作区文件: {recent_workspaces_path}")
            with open(recent_workspaces_path, 'r') as f:
                content = f.read()[:500]  # 限制读取长度
                print(f"  内容预览: {content}")
                methods.append(('recent_workspaces', content))
    
    except Exception as e:
        print(f"  读取最近工作区失败: {e}")
    
    return methods

def main():
    """主测试函数"""
    print("研究获取Cursor session标题的各种方法")
    print("=" * 60)
    
    all_methods = {}
    
    # 执行各种测试
    all_methods['environment'] = test_environment_variables()
    all_methods['process'] = test_process_information()
    all_methods['applescript'] = test_applescript_methods()
    all_methods['filesystem'] = test_file_system_methods()
    all_methods['network'] = test_network_methods()
    all_methods['cursor_specific'] = test_cursor_specific_methods()
    
    # 总结结果
    print("\n" + "=" * 60)
    print("总结 - 可能获取session标题的方法:")
    
    successful_methods = []
    
    for category, results in all_methods.items():
        if results:
            print(f"\n{category.upper()}:")
            if isinstance(results, tuple) and len(results) == 2:
                # 环境变量返回两个列表
                cursor_vars, title_vars = results
                if cursor_vars or title_vars:
                    successful_methods.append(category)
                    for var, val in cursor_vars + title_vars:
                        print(f"  ✅ {var}: {val[:100]}...")
            elif isinstance(results, list):
                if results:
                    successful_methods.append(category)
                    for item in results:
                        if isinstance(item, tuple):
                            print(f"  ✅ {item[0]}: {str(item[1])[:100]}...")
                        else:
                            print(f"  ✅ {str(item)[:100]}...")
    
    print(f"\n成功的方法: {successful_methods}")
    
    # 推荐的实现方案
    print(f"\n推荐的session标题获取方案:")
    if 'applescript' in successful_methods:
        print("1. 优先使用AppleScript获取Cursor窗口标题")
    if 'environment' in successful_methods:
        print("2. 备选使用环境变量")
    if 'filesystem' in successful_methods:
        print("3. 备选使用配置文件")
    
    print("4. 最后使用默认标题: 'USERINPUT - Agent Mode'")
    
    return successful_methods

if __name__ == "__main__":
    main()