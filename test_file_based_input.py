#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：创建基于文件的输入系统
支持时间戳命名、断点续传、INPUT_END标记
"""

import os
import sys
import time
import hashlib
import threading
from datetime import datetime
from pathlib import Path

def get_session_title():
    """获取session标题（简化版）"""
    try:
        # 尝试从环境变量获取
        cursor_trace = os.environ.get('CURSOR_TRACE_ID', '')
        if cursor_trace:
            return f"Cursor-{cursor_trace[:8]}"
        
        # 使用工作目录名称
        cwd = os.getcwd()
        return f"Session-{os.path.basename(cwd)}"
    except:
        return "USERINPUT-Session"

def generate_input_filename(session_title=None):
    """生成基于时间戳的输入文件名"""
    if not session_title:
        session_title = get_session_title()
    
    # 创建时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 创建hash（基于session标题和时间戳）
    hash_input = f"{session_title}_{timestamp}".encode('utf-8')
    hash_hex = hashlib.md5(hash_input).hexdigest()[:8]
    
    # 生成文件名
    filename = f"{session_title}_{timestamp}_{hash_hex}.input"
    
    return filename

def create_input_file(filename, input_dir="~/tmp"):
    """创建输入文件"""
    input_dir = os.path.expanduser(input_dir)
    os.makedirs(input_dir, exist_ok=True)
    
    filepath = os.path.join(input_dir, filename)
    
    # 如果文件不存在，创建带说明的文件
    if not os.path.exists(filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"""# USERINPUT 输入文件
# 创建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 
# 使用说明:
# 1. 在此文件中输入您的反馈内容
# 2. 完成后在最后一行添加: INPUT_END
# 3. 保存文件，系统会自动检测到您的输入
# 
# 注意: 
# - 以 # 开头的行会被忽略
# - 只有在检测到 INPUT_END 时才会视为输入完成
# - 您可以随时保存文件，系统支持断点续传
# 
# ========== 请在下方输入您的反馈 ==========

""")
        print(f"创建输入文件: {filepath}")
    else:
        print(f"使用现有输入文件: {filepath}")
    
    return filepath

def read_input_content(filepath):
    """读取输入文件内容"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 过滤注释行和空行
        content_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                content_lines.append(line.rstrip())
        
        return content_lines
    except Exception as e:
        print(f"读取文件失败: {e}")
        return []

def check_input_completion(content_lines):
    """检查输入是否完成（最后一行是INPUT_END）"""
    if not content_lines:
        return False, ""
    
    # 检查最后一行是否是INPUT_END
    last_line = content_lines[-1].strip()
    if last_line == "INPUT_END":
        # 移除INPUT_END行，返回实际内容
        actual_content = '\n'.join(content_lines[:-1]).strip()
        return True, actual_content
    
    return False, '\n'.join(content_lines).strip()

def monitor_input_file(filepath, timeout=180, check_interval=5):
    """监控输入文件，支持超时和定期检查"""
    print(f"开始监控输入文件: {filepath}")
    print(f"超时设置: {timeout}秒，检查间隔: {check_interval}秒")
    
    start_time = time.time()
    last_content = ""
    
    # 打开文件供用户编辑
    try:
        if sys.platform == 'darwin':  # macOS
            os.system(f'open -t "{filepath}"')
        elif sys.platform == 'linux':  # Linux
            os.system(f'xdg-open "{filepath}"')
        elif sys.platform == 'win32':  # Windows
            os.system(f'notepad "{filepath}"')
        print("已打开文件编辑器，请在其中输入您的反馈")
    except Exception as e:
        print(f"无法自动打开编辑器: {e}")
        print(f"请手动打开文件: {filepath}")
    
    while True:
        elapsed = time.time() - start_time
        remaining = max(0, timeout - elapsed)
        
        # 读取当前内容
        content_lines = read_input_content(filepath)
        current_content = '\n'.join(content_lines).strip()
        
        # 检查是否完成
        is_complete, final_content = check_input_completion(content_lines)
        
        if is_complete:
            print(f"\n✅ 检测到输入完成标记 INPUT_END")
            print(f"获取到用户输入 ({len(final_content)} 字符)")
            return final_content
        
        # 显示进度（如果内容有变化）
        if current_content != last_content:
            if current_content:
                print(f"\n📝 检测到内容更新 ({len(current_content)} 字符)")
                print(f"预览: {current_content[:100]}{'...' if len(current_content) > 100 else ''}")
            last_content = current_content
        
        # 检查超时
        if remaining <= 0:
            print(f"\n⏰ 输入超时 ({timeout}秒)")
            if current_content:
                print(f"保存部分输入内容 ({len(current_content)} 字符)")
                return f"输入超时，已保存部分内容:\n{current_content}"
            else:
                return f"输入超时，未收到任何内容 (超时: {timeout}秒)"
        
        # 显示剩余时间
        if remaining <= 30:
            print(f"\r⏳ 剩余时间: {int(remaining)}秒", end='', flush=True)
        elif int(remaining) % 30 == 0:  # 每30秒显示一次
            print(f"\n⏳ 剩余时间: {int(remaining)}秒")
        
        time.sleep(check_interval)

def test_file_based_input():
    """测试基于文件的输入系统"""
    print("=== 测试基于文件的输入系统 ===")
    
    # 生成文件名
    session_title = get_session_title()
    filename = generate_input_filename(session_title)
    print(f"Session标题: {session_title}")
    print(f"生成的文件名: {filename}")
    
    # 创建输入文件
    filepath = create_input_file(filename)
    
    # 监控文件输入（测试用较短超时）
    result = monitor_input_file(filepath, timeout=120, check_interval=3)
    
    print(f"\n" + "="*50)
    print("输入结果:")
    print(result)
    
    return result

def test_resume_from_existing_file():
    """测试从现有文件恢复"""
    print("\n=== 测试断点续传功能 ===")
    
    # 创建一个测试文件
    test_filename = "test_resume_20241212_120000_abcd1234.input"
    test_filepath = create_input_file(test_filename)
    
    # 写入一些测试内容
    with open(test_filepath, 'a', encoding='utf-8') as f:
        f.write("这是之前写入的内容...\n")
        f.write("现在继续添加内容...\n")
    
    print(f"已创建测试文件: {test_filepath}")
    print("测试从现有文件继续输入...")
    
    # 监控文件（短超时用于测试）
    result = monitor_input_file(test_filepath, timeout=60, check_interval=2)
    
    print(f"\n断点续传结果:")
    print(result)
    
    return result

def test_input_end_detection():
    """测试INPUT_END检测功能"""
    print("\n=== 测试INPUT_END检测 ===")
    
    # 创建测试内容
    test_cases = [
        ["这是第一行", "这是第二行", "INPUT_END"],
        ["只有一行内容", "INPUT_END"],
        ["没有结束标记的内容"],
        ["", "INPUT_END"],  # 空内容但有结束标记
        []  # 完全空文件
    ]
    
    for i, test_content in enumerate(test_cases):
        print(f"\n测试用例 {i+1}: {test_content}")
        is_complete, content = check_input_completion(test_content)
        print(f"  完成状态: {is_complete}")
        print(f"  提取内容: '{content}'")
    
    return True

def main():
    """主测试函数"""
    print("测试基于文件的输入系统")
    print("=" * 50)
    
    results = {}
    
    # 测试INPUT_END检测
    results['input_end_detection'] = test_input_end_detection()
    
    # 测试文件输入系统
    print(f"\n{'='*50}")
    choice = input("是否测试实际文件输入? (y/N): ").strip().lower()
    
    if choice == 'y':
        results['file_input'] = test_file_based_input()
        
        # 测试断点续传
        choice2 = input("\n是否测试断点续传? (y/N): ").strip().lower()
        if choice2 == 'y':
            results['resume_test'] = test_resume_from_existing_file()
    else:
        print("跳过实际文件输入测试")
        results['file_input'] = "跳过"
        results['resume_test'] = "跳过"
    
    # 总结
    print(f"\n{'='*50}")
    print("测试结果总结:")
    for test_name, result in results.items():
        if isinstance(result, bool):
            status = "✅ 成功" if result else "❌ 失败"
        elif result == "跳过":
            status = "⏭️ 跳过"
        else:
            status = f"✅ 完成 ({len(str(result))} 字符)"
        print(f"  {test_name}: {status}")
    
    return results

if __name__ == "__main__":
    main()