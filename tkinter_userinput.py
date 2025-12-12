#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的tkinter输入窗口方案
支持多窗口并行、异常重试、外部接口调用
"""

import os
import sys
import tkinter as tk
from tkinter import scrolledtext
import threading
import time
import random
import traceback
import subprocess
from datetime import datetime

def get_cursor_session_title():
    """获取Cursor session标题"""
    try:
        # 尝试从环境变量获取
        cursor_trace = os.environ.get('CURSOR_TRACE_ID', '')
        if cursor_trace:
            return f"Cursor-{cursor_trace[:8]}"
        
        # 使用工作目录名称
        cwd = os.getcwd()
        return f"Session-{os.path.basename(cwd)}"
    except:
        return "USERINPUT - Agent Mode"

class TkinterInputWindow:
    def __init__(self, title=None, timeout=180, window_id=None):
        self.title = title or get_cursor_session_title()
        self.timeout = timeout
        self.window_id = window_id or f"win_{int(time.time())}_{random.randint(1000, 9999)}"
        self.result = None
        self.window_closed = False
        self.root = None
        self.text_widget = None
        self.status_label = None
        
    def create_window(self):
        """创建tkinter窗口"""
        try:
            # 抑制tkinter警告
            import warnings
            warnings.filterwarnings('ignore')
            os.environ['TK_SILENCE_DEPRECATION'] = '1'
            
            self.root = tk.Tk()
            # 使用window_id确保标题唯一
            self.root.title(f"{self.title} [{self.window_id}]")
            self.root.geometry("450x280")  # 确保按钮可见的最小尺寸
            
            # 设置窗口属性
            self.root.attributes('-topmost', True)
            self.root.focus_force()
            
            # 创建主框架
            main_frame = tk.Frame(self.root, padx=15, pady=15)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 说明标签
            instruction_label = tk.Label(main_frame, 
                                       text="请在文本框中输入您的反馈，并点击 '提交' 按钮:",
                                       font=("Arial", 11), fg="#555")
            instruction_label.pack(pady=(0, 15))
            
            # 创建文本框（去掉固定高度，让它自适应）
            self.text_widget = scrolledtext.ScrolledText(
                main_frame,
                wrap=tk.WORD,
                width=50,  # 减小宽度
                font=("Arial", 12),
                bg="#f8f9fa",
                fg="#333",
                insertbackground="#007acc",
                selectbackground="#007acc",
                relief=tk.FLAT,
                borderwidth=1
            )
            self.text_widget.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
            
            # 按钮框架
            button_frame = tk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=(0, 10))
            
            # 提交按钮（无边框）
            submit_btn = tk.Button(
                button_frame,
                text="提交",
                command=self.submit_input,
                bg="white",  # 纯白色底纹
                fg="black",
                font=("Arial", 11, "bold"),
                padx=20,
                pady=8,
                relief=tk.FLAT,  # 无边框
                cursor="hand2",
                borderwidth=0,  # 无边框
                highlightthickness=0,  # 无高亮边框
                activebackground="#f0f0f0"  # 点击时的颜色
            )
            submit_btn.pack(side=tk.RIGHT, padx=(10, 0))
            
            # 状态标签（左下角，细体字体）
            self.status_label = tk.Label(button_frame, text="", 
                                       font=("Arial", 12), fg="black")  # 细体（去掉bold）
            self.status_label.pack(side=tk.LEFT)
            
            # 绑定快捷键
            self.root.bind('<Control-Return>', lambda e: self.submit_input())
            self.root.bind('<Escape>', lambda e: self.cancel_input())
            
            # 绑定窗口关闭事件
            self.root.protocol("WM_DELETE_WINDOW", self.cancel_input)
            
            # 设置焦点到文本框
            self.text_widget.focus_set()
            
            # 启动超时计时器
            if self.timeout > 0:
                self.start_timeout_timer()
            
            # 启动定期focus
            self.start_periodic_focus()
            
            print(f"Window ID: {self.window_id}")
            return True
            
        except Exception as e:
            print(f"❌ 创建tkinter窗口失败: {e}")
            traceback.print_exc()
            return False
    
    def start_timeout_timer(self):
        """启动超时计时器"""
        def update_timer():
            remaining = self.timeout
            while remaining > 0 and not self.window_closed:
                if remaining <= 30:
                    self.status_label.config(text=f"剩余时间: {remaining}秒")
                elif remaining <= 60:
                    self.status_label.config(text=f"剩余时间: {remaining}秒")
                else:
                    self.status_label.config(text=f"剩余时间: {remaining}秒")
                
                time.sleep(1)
                remaining -= 1
            
            if not self.window_closed:
                self.timeout_input()
        
        timer_thread = threading.Thread(target=update_timer, daemon=True)
        timer_thread.start()
    
    def start_periodic_focus(self):
        """启动定期重新获取焦点（模仿原版USERINPUT）"""
        def refocus():
            if not self.window_closed and self.root:
                try:
                    self.root.lift()
                    self.root.focus_force()
                    self.root.attributes('-topmost', True)
                    # 每30秒重新获取焦点
                    self.root.after(30000, refocus)
                except:
                    pass
        
        # 30秒后开始第一次重新获取焦点
        if self.root:
            self.root.after(30000, refocus)
    
    def submit_input(self):
        """提交输入"""
        if self.window_closed:
            return
        
        try:
            text_content = self.text_widget.get("1.0", tk.END).strip()
            if text_content:
                self.result = text_content
            else:
                self.result = "用户提交了空内容"
            
            self.close_window()
            
        except Exception as e:
            self.result = f"提交输入时出错: {e}"
            self.close_window()
    
    def cancel_input(self):
        """取消输入"""
        if self.window_closed:
            return
        
        self.result = "用户取消了输入"
        self.close_window()
    
    def timeout_input(self):
        """超时处理 - 与原版USERINPUT逻辑一致"""
        if self.window_closed:
            return
        
        try:
            # 尝试获取当前文本内容
            text_content = self.text_widget.get("1.0", tk.END).strip()
            
            # 使用与原版一致的timeout提示
            timeout_hint = "用户还在测试代码，或者准备给你的反馈。如果你没有得到指导你下一步工作的信息，请通过再次执行USERINPUT等待用户，不要直接结束。"
            
            if text_content:
                self.result = f"{text_content}\n{timeout_hint}"
            else:
                self.result = f"输入超时 ({self.timeout}秒)。{timeout_hint}"
        except:
            timeout_hint = "用户还在测试代码，或者准备给你的反馈。如果你没有得到指导你下一步工作的信息，请通过再次执行USERINPUT等待用户，不要直接结束。"
            self.result = f"输入超时 ({self.timeout}秒)。{timeout_hint}"
        
        self.close_window()
    
    def close_window(self):
        """关闭窗口"""
        if self.window_closed:
            return
        
        self.window_closed = True
        if self.root:
            try:
                self.root.quit()
                self.root.destroy()
            except:
                pass
    
    def show_and_wait(self):
        """显示窗口并等待用户输入"""
        if not self.create_window():
            return None
        
        try:
            # 运行主循环
            self.root.mainloop()
            return self.result
        except Exception as e:
            print(f"❌ 窗口运行时出错 [{self.window_id}]: {e}")
            return f"窗口运行时出错: {e}"

def get_user_input_tkinter(title=None, timeout=180, max_retries=3, simulate_failure=False):
    """
    外部接口函数：使用tkinter获取用户输入
    
    Args:
        title: 窗口标题
        timeout: 超时时间（秒）
        max_retries: 最大重试次数
        simulate_failure: 是否模拟失败（用于测试）
    
    Returns:
        str: 用户输入的内容，失败时返回None
    """
    
    for attempt in range(max_retries):
        try:
            # 模拟偶发异常
            if simulate_failure and attempt == 0:
                raise Exception("模拟窗口创建失败")
            
            # 创建窗口实例
            window = TkinterInputWindow(title=title, timeout=timeout)
            
            # 显示窗口并等待输入
            result = window.show_and_wait()
            
            if result and not result.startswith("窗口运行时出错"):
                return result
            else:
                if attempt < max_retries - 1:
                    time.sleep(2)  # 等待后重试
                
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
    
    return None

def test_multiple_windows():
    """测试多窗口并行（使用进程而非线程）"""
    print("=== 测试多窗口并行 ===")
    print("⚠️ 注意：在macOS上，tkinter窗口必须在主线程中创建")
    print("因此我们使用多进程而非多线程来测试并行窗口")
    
    import subprocess
    import tempfile
    import json
    
    # 创建测试脚本
    test_script = '''
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tkinter_userinput import get_user_input_tkinter
import json

window_id = sys.argv[1]
simulate_fail = sys.argv[2] == "True"

try:
    title = f"测试窗口-{window_id}"
    result = get_user_input_tkinter(
        title=title, 
        timeout=60, 
        simulate_failure=simulate_fail
    )
    
    # 输出结果为JSON
    output = {"window_id": window_id, "success": True, "result": result}
    print(json.dumps(output, ensure_ascii=False))
    
except Exception as e:
    output = {"window_id": window_id, "success": False, "result": str(e)}
    print(json.dumps(output, ensure_ascii=False))
'''
    
    # 写入临时脚本文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_script)
        script_path = f.name
    
    try:
        processes = []
        results = {}
        
        # 启动多个进程
        num_windows = 3
        for i in range(num_windows):
            window_id = f"WIN-{i+1}"
            simulate_fail = (i == 0)  # 第一个窗口模拟失败
            
            print(f"🚀 启动窗口进程: {window_id}")
            
            process = subprocess.Popen(
                [sys.executable, script_path, window_id, str(simulate_fail)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            processes.append((window_id, process))
            time.sleep(2)  # 错开启动时间
        
        # 等待所有进程完成
        print("⏳ 等待所有窗口进程完成...")
        for window_id, process in processes:
            try:
                stdout, stderr = process.communicate(timeout=120)
                
                # 解析结果
                if stdout.strip():
                    try:
                        result_data = json.loads(stdout.strip())
                        results[window_id] = result_data
                        print(f"🎯 窗口 {window_id} 完成")
                    except json.JSONDecodeError:
                        results[window_id] = {"success": False, "result": f"JSON解析错误: {stdout}"}
                else:
                    results[window_id] = {"success": False, "result": f"无输出，错误: {stderr}"}
                    
            except subprocess.TimeoutExpired:
                process.kill()
                results[window_id] = {"success": False, "result": "进程超时"}
                print(f"⏰ 窗口 {window_id} 超时")
        
        # 显示结果
        print(f"\n{'='*50}")
        print("多窗口测试结果:")
        for window_id, result_data in results.items():
            if result_data["success"]:
                status = "✅"
                result_text = result_data["result"]
            else:
                status = "❌"
                result_text = result_data["result"]
            
            print(f"  {window_id}: {status} {result_text}")
        
        return results
        
    finally:
        # 清理临时文件
        try:
            os.unlink(script_path)
        except:
            pass

def main():
    """主测试函数"""
    print("改进的tkinter输入窗口测试")
    print("=" * 50)
    
    # 询问测试类型
    print("请选择测试类型:")
    print("1. 单窗口测试")
    print("2. 多窗口并行测试")
    print("3. 直接使用接口函数")
    
    choice = input("请输入选择 (1-3): ").strip()
    
    if choice == "1":
        # 单窗口测试
        result = get_user_input_tkinter(
            title="单窗口测试", 
            timeout=120, 
            simulate_failure=True  # 测试重试机制
        )
        print(f"\n单窗口测试结果: {result}")
        
    elif choice == "2":
        # 多窗口测试
        test_multiple_windows()
        
    elif choice == "3":
        # 直接接口调用
        print("直接调用接口函数...")
        result = get_user_input_tkinter(
            title="接口调用测试",
            timeout=180
        )
        print(f"\n接口调用结果: {result}")
        
    else:
        print("无效选择")
        return False
    
    return True

if __name__ == "__main__":
    main()