#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：创建tkinter文本框输入窗口
解决按键时文本框显示问题，并添加异常处理和重试机制
"""

import os
import sys
import tkinter as tk
from tkinter import scrolledtext
import threading
import time
import subprocess
import traceback

def get_cursor_session_title():
    """尝试获取Cursor session标题"""
    try:
        # 方法1: 检查环境变量
        cursor_title = os.environ.get('CURSOR_SESSION_TITLE')
        if cursor_title:
            print(f"从环境变量获取标题: {cursor_title}")
            return cursor_title
        
        # 方法2: 尝试从进程信息获取
        try:
            # 查找Cursor相关进程
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            for line in lines:
                if 'Cursor' in line and 'Helper' not in line:
                    print(f"找到Cursor进程: {line}")
                    # 尝试提取标题信息
                    break
        except:
            pass
        
        # 方法3: 尝试从AppleScript获取活动窗口标题（仅macOS）
        if sys.platform == 'darwin':
            try:
                applescript = '''
                tell application "System Events"
                    set frontApp to name of first application process whose frontmost is true
                    if frontApp contains "Cursor" then
                        tell application "Cursor"
                            return name of front window
                        end tell
                    end if
                end tell
                '''
                result = subprocess.run(['osascript', '-e', applescript], 
                                      capture_output=True, text=True, timeout=3)
                if result.returncode == 0 and result.stdout.strip():
                    title = result.stdout.strip()
                    print(f"从AppleScript获取标题: {title}")
                    return title
            except Exception as e:
                print(f"AppleScript获取标题失败: {e}")
        
        # 方法4: 检查窗口标题相关环境变量
        for env_var in ['TERM_PROGRAM', 'TERM_PROGRAM_VERSION', 'PWD']:
            value = os.environ.get(env_var)
            if value:
                print(f"环境变量 {env_var}: {value}")
        
        # 默认标题
        return "USERINPUT - Agent Mode"
        
    except Exception as e:
        print(f"获取session标题失败: {e}")
        return "USERINPUT - Agent Mode"

class TkinterInputWindow:
    def __init__(self, title=None, timeout=180):
        self.title = title or get_cursor_session_title()
        self.timeout = timeout
        self.result = None
        self.window_closed = False
        self.root = None
        self.text_widget = None
        
    def create_window(self):
        """创建tkinter窗口"""
        try:
            # 抑制tkinter警告
            import warnings
            warnings.filterwarnings('ignore')
            os.environ['TK_SILENCE_DEPRECATION'] = '1'
            
            self.root = tk.Tk()
            self.root.title(self.title)
            self.root.geometry("600x400")
            
            # 设置窗口属性
            self.root.attributes('-topmost', True)
            self.root.focus_force()
            
            # 创建主框架
            main_frame = tk.Frame(self.root, padx=10, pady=10)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 标题标签
            title_label = tk.Label(main_frame, text=self.title, 
                                 font=("Arial", 14, "bold"), fg="#333")
            title_label.pack(pady=(0, 10))
            
            # 说明标签
            instruction_label = tk.Label(main_frame, 
                                       text="请在下方文本框中输入您的反馈，完成后点击'提交'按钮:",
                                       font=("Arial", 10), fg="#666")
            instruction_label.pack(pady=(0, 10))
            
            # 创建文本框（使用ScrolledText解决显示问题）
            self.text_widget = scrolledtext.ScrolledText(
                main_frame,
                wrap=tk.WORD,
                width=70,
                height=15,
                font=("Arial", 11),
                bg="#f8f9fa",
                fg="#333",
                insertbackground="#007acc",  # 光标颜色
                selectbackground="#007acc",  # 选中背景色
                relief=tk.FLAT,
                borderwidth=1
            )
            self.text_widget.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            
            # 按钮框架
            button_frame = tk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=(0, 10))
            
            # 提交按钮
            submit_btn = tk.Button(
                button_frame,
                text="提交反馈 (Ctrl+Enter)",
                command=self.submit_input,
                bg="#28a745",
                fg="white",
                font=("Arial", 11, "bold"),
                padx=20,
                pady=8,
                relief=tk.FLAT,
                cursor="hand2"
            )
            submit_btn.pack(side=tk.RIGHT, padx=(5, 0))
            
            # 取消按钮
            cancel_btn = tk.Button(
                button_frame,
                text="取消",
                command=self.cancel_input,
                bg="#6c757d",
                fg="white",
                font=("Arial", 11),
                padx=20,
                pady=8,
                relief=tk.FLAT,
                cursor="hand2"
            )
            cancel_btn.pack(side=tk.RIGHT)
            
            # 状态标签
            self.status_label = tk.Label(button_frame, text="", font=("Arial", 9), fg="#666")
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
            
            print(f"tkinter窗口创建成功: {self.title}")
            return True
            
        except Exception as e:
            print(f"创建tkinter窗口失败: {e}")
            traceback.print_exc()
            return False
    
    def start_timeout_timer(self):
        """启动超时计时器"""
        def update_timer():
            remaining = self.timeout
            while remaining > 0 and not self.window_closed:
                if remaining <= 30:
                    self.status_label.config(text=f"剩余时间: {remaining}秒", fg="#dc3545")
                elif remaining <= 60:
                    self.status_label.config(text=f"剩余时间: {remaining}秒", fg="#ffc107")
                else:
                    self.status_label.config(text=f"剩余时间: {remaining}秒", fg="#666")
                
                time.sleep(1)
                remaining -= 1
            
            if not self.window_closed:
                self.timeout_input()
        
        timer_thread = threading.Thread(target=update_timer, daemon=True)
        timer_thread.start()
    
    def submit_input(self):
        """提交输入"""
        if self.window_closed:
            return
        
        try:
            text_content = self.text_widget.get("1.0", tk.END).strip()
            if text_content:
                self.result = text_content
                print(f"用户提交输入: {len(text_content)} 字符")
            else:
                self.result = "用户提交了空内容"
                print("用户提交了空内容")
            
            self.close_window()
            
        except Exception as e:
            print(f"提交输入时出错: {e}")
            self.result = f"提交输入时出错: {e}"
            self.close_window()
    
    def cancel_input(self):
        """取消输入"""
        if self.window_closed:
            return
        
        self.result = "用户取消了输入"
        print("用户取消了输入")
        self.close_window()
    
    def timeout_input(self):
        """超时处理"""
        if self.window_closed:
            return
        
        try:
            # 尝试获取当前文本内容
            text_content = self.text_widget.get("1.0", tk.END).strip()
            if text_content:
                self.result = f"输入超时，已保存部分内容: {text_content}"
                print(f"输入超时，保存了 {len(text_content)} 字符")
            else:
                self.result = f"输入超时，未收到任何内容 (超时: {self.timeout}秒)"
                print(f"输入超时，未收到内容")
        except:
            self.result = f"输入超时 (超时: {self.timeout}秒)"
        
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
            print(f"窗口运行时出错: {e}")
            return f"窗口运行时出错: {e}"

def test_tkinter_input_with_retry(max_retries=3):
    """测试tkinter输入窗口，带重试机制"""
    print("=== 测试tkinter输入窗口 ===")
    
    for attempt in range(max_retries):
        print(f"\n尝试第 {attempt + 1} 次创建tkinter窗口...")
        
        try:
            # 创建窗口实例
            window = TkinterInputWindow(timeout=60)  # 60秒超时用于测试
            
            # 显示窗口并等待输入
            result = window.show_and_wait()
            
            if result and not result.startswith("窗口运行时出错"):
                print(f"✅ 成功获取用户输入: {result}")
                return result
            else:
                print(f"❌ 第 {attempt + 1} 次尝试失败: {result}")
                
        except Exception as e:
            print(f"❌ 第 {attempt + 1} 次尝试异常: {e}")
            traceback.print_exc()
        
        # 如果不是最后一次尝试，等待一下再重试
        if attempt < max_retries - 1:
            print("等待2秒后重试...")
            time.sleep(2)
    
    print(f"❌ 所有 {max_retries} 次尝试都失败了")
    return None

def main():
    """主测试函数"""
    print("测试tkinter文本框输入窗口")
    print("=" * 50)
    
    # 测试获取session标题
    print("测试获取Cursor session标题:")
    title = get_cursor_session_title()
    print(f"获取到的标题: {title}")
    
    # 测试tkinter窗口
    result = test_tkinter_input_with_retry()
    
    print("\n" + "=" * 50)
    print("测试结果:")
    if result:
        print(f"✅ 成功: {result}")
    else:
        print("❌ 失败: 无法获取用户输入")
    
    return result is not None

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)