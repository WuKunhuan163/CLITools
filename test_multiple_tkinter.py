#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试多个tkinter窗口并行
"""

import subprocess
import sys
import os
import time

def test_multiple_windows():
    """启动多个tkinter窗口进程"""
    print("=== 测试多个tkinter窗口并行 ===")
    
    processes = []
    
    # 启动3个窗口进程
    for i in range(3):
        window_id = f"WIN-{i+1}"
        print(f"🚀 启动窗口: {window_id}")
        
        # 每个窗口使用不同的超时时间
        timeout = 30 + (i * 10)  # 30, 40, 50秒
        
        process = subprocess.Popen([
            sys.executable, 
            "USERINPUT_TKINTER", 
            "--timeout", str(timeout)
        ])
        
        processes.append((window_id, process, timeout))
        time.sleep(1)  # 错开启动
    
    print(f"\n✅ 已启动 {len(processes)} 个窗口进程")
    print("请查看是否有多个tkinter窗口同时出现")
    
    # 等待所有进程完成
    for window_id, process, timeout in processes:
        print(f"⏳ 等待窗口 {window_id} 完成 (超时: {timeout}秒)...")
        try:
            process.wait(timeout=timeout + 10)
            print(f"✅ 窗口 {window_id} 已完成")
        except subprocess.TimeoutExpired:
            print(f"⏰ 窗口 {window_id} 超时，强制结束")
            process.kill()

if __name__ == "__main__":
    test_multiple_windows()