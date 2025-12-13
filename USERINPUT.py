#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USERINPUT tkinter版本 - 解决Cursor AI环境输入问题
"""

import os
import sys

# 必须在导入tkinter之前设置环境变量来抑制IMK消息
os.environ['TK_SILENCE_DEPRECATION'] = '1'
import warnings
warnings.filterwarnings('ignore')

import tkinter as tk
from tkinter import scrolledtext
import threading
import time
import random
import traceback
import subprocess
import platform
import contextlib

def get_project_name():
    """获取项目名称"""
    try:
        current_dir = os.getcwd()
        
        # 尝试找到git根目录
        git_root = None
        check_dir = current_dir
        while check_dir != os.path.dirname(check_dir):  # 直到根目录
            if os.path.exists(os.path.join(check_dir, '.git')):
                git_root = check_dir
                break
            check_dir = os.path.dirname(check_dir)
        
        if git_root:
            project_name = os.path.basename(git_root)
            project_dir = git_root
        else:
            project_name = os.path.basename(current_dir)
            project_dir = current_dir
        
        # 确保项目名称不为空
        if not project_name:
            project_name = "root"
            
        return project_name, str(current_dir), str(project_dir)
    except Exception:
        return "Unknown", str(os.getcwd()), str(os.getcwd())

def get_cursor_session_title(custom_id=None):
    """获取Cursor session标题"""
    try:
        project_name, _, _ = get_project_name()
        base_title = f"{project_name} - Agent Mode"
        if custom_id:
            return f"{base_title} [{custom_id}]"
        return base_title
    except:
        base_title = "Agent Mode"
        if custom_id:
            return f"{base_title} [{custom_id}]"
        return base_title

class TkinterInputWindow:
    def __init__(self, title=None, timeout=180, window_id=None, hint_text=None):
        self.title = title or get_cursor_session_title()
        self.timeout = timeout
        self.window_id = window_id or f"win_{int(time.time())}_{random.randint(1000, 9999)}"
        self.hint_text = hint_text
        self.result = None
        self.window_closed = False
        self.root = None
        self.text_widget = None
        self.status_label = None
        
    def create_window(self):
        """创建tkinter窗口"""
        try:
            # 抑制tkinter警告
            warnings.filterwarnings('ignore')
            os.environ['TK_SILENCE_DEPRECATION'] = '1'
            
            self.root = tk.Tk()
            self.root.title(f"{self.title}")
            self.root.geometry("450x250")
            
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
            
            # 创建文本框
            self.text_widget = scrolledtext.ScrolledText(
                main_frame,
                wrap=tk.WORD,
                height=8,
                font=("Arial", 12),
                bg="#f8f9fa",
                fg="#333",
                insertbackground="#007acc",
                selectbackground="#007acc",
                relief=tk.FLAT,
                borderwidth=1
            )
            self.text_widget.pack(fill=tk.X, pady=(0, 15))
            
            # 插入提示文本（如果有）
            if self.hint_text:
                self.text_widget.insert("1.0", self.hint_text)
            
            # 绑定窗口大小变化事件
            self.root.bind('<Configure>', self.on_window_resize)
            
            # 按钮框架
            button_frame = tk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=(0, 10))
            
            # 提交按钮
            submit_btn = tk.Button(
                button_frame,
                text="提交",
                command=self.submit_input,
                bg="white",
                fg="black",
                font=("Arial", 11, "bold"),
                padx=20,
                pady=8,
                relief=tk.FLAT,
                cursor="hand2",
                borderwidth=0,
                highlightthickness=0,
                activebackground="#f0f0f0"
            )
            submit_btn.pack(side=tk.RIGHT, padx=(10, 0))
            
            # 状态标签
            self.status_label = tk.Label(button_frame, text="", 
                                       font=("Arial", 12), fg="black")
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
            
            # 窗口创建时播放音效
            self.play_bell()
            
            return True
            
        except Exception as e:
            # 静默处理错误，不输出到终端
            return False
    
    def on_window_resize(self, event):
        """窗口大小变化时动态调整文本框宽度和高度"""
        if event.widget == self.root and self.text_widget:
            try:
                window_width = self.root.winfo_width()
                new_width = max(30, (window_width - 50) // 8)
                window_height = self.root.winfo_height()
                new_height = max(3, (window_height - 100) // 16)
                self.text_widget.config(width=new_width, height=new_height)
            except:
                pass
    
    def start_timeout_timer(self):
        """启动超时计时器"""
        def update_timer():
            remaining = self.timeout
            while remaining > 0 and not self.window_closed:
                # 显示倒计时（所有时间都显示）
                self.status_label.config(text=f"剩余时间: {remaining}秒")
                time.sleep(1)
                remaining -= 1
            if not self.window_closed:
                self.timeout_input()
        threading.Thread(target=update_timer, daemon=True).start()
    
    def start_periodic_focus(self):
        """启动定期重新获取焦点和播放音效"""
        def refocus():
            if not self.window_closed and self.root:
                try:
                    self.root.lift()
                    self.root.focus_force()
                    self.root.attributes('-topmost', True)
                    self.text_widget.focus_set()
                    self.play_bell()
                    # 每30秒重新获取焦点（恢复原版间隔）
                    self.root.after(30000, refocus)
                except:
                    pass
        # 30秒后开始第一次重新获取焦点
        if self.root:
            self.root.after(30000, refocus)
    
    def play_bell(self):
        """播放提示音效"""
        def play_in_thread():
            try:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                audio_file_path = os.path.join(current_dir, "USERINPUT_PROJ", "tkinter_bell.mp3")
                if os.path.exists(audio_file_path):
                    system = platform.system()
                    if system == "Darwin":
                        subprocess.run(["afplay", audio_file_path], 
                                     capture_output=True, timeout=2)
            except:
                pass
        threading.Thread(target=play_in_thread, daemon=True).start()
    
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
        """超时处理"""
        if self.window_closed:
            return
        try:
            text_content = self.text_widget.get("1.0", tk.END).strip()
            timeout_hint = "用户还在测试代码，或者准备给你的反馈。如果你没有得到指导你下一步工作的信息，请通过再次执行USERINPUT等待用户，不要直接结束。"
            if text_content:
                self.result = f"{text_content}\n{timeout_hint}"
            else:
                self.result = f"输入超时 ({self.timeout}秒)。{timeout_hint}"
        except:
            self.result = f"输入超时 ({self.timeout}秒)。用户还在测试代码，或者准备给你的反馈。"
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
            self.root.mainloop()
            return self.result
        except Exception as e:
            return f"窗口运行时出错: {e}"

@contextlib.contextmanager
def suppress_stderr():
    """抑制stderr输出（包括IMK消息）"""
    with open(os.devnull, "w") as devnull:
        old_stderr = sys.stderr
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stderr = old_stderr

def get_user_input_tkinter(title=None, timeout=180, max_retries=3, hint_text=None):
    """使用tkinter获取用户输入（通过subprocess抑制IMK消息）"""
    
    for attempt in range(max_retries):
        try:
            # 先生成Window ID并打印（在subprocess之前！）
            window_id = f"win_{int(time.time())}_{random.randint(1000, 9999)}"
            
            
            # 创建完整的tkinter脚本
            tkinter_script = f'''
import os
import sys
import warnings
warnings.filterwarnings('ignore')
os.environ['TK_SILENCE_DEPRECATION'] = '1'

import tkinter as tk
from tkinter import scrolledtext
import threading
import time
import subprocess
import platform

class TkinterInputWindow:
    def __init__(self):
        self.title = "{title or 'USERINPUT - Agent Mode'}"
        self.timeout = {timeout}
        self.window_id = "{window_id}"
        self.result = None
        self.window_closed = False
        self.root = None
        self.text_widget = None
        self.status_label = None
        
    def create_window(self):
        try:
            self.root = tk.Tk()
            self.root.title(f"{{self.title}}")
            self.root.geometry("450x250")
            self.root.attributes('-topmost', True)
            self.root.focus_force()
            
            main_frame = tk.Frame(self.root, padx=15, pady=15)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            instruction_label = tk.Label(main_frame, 
                                       text="请在文本框中输入您的反馈，并点击 '提交' 按钮:",
                                       font=("Arial", 11), fg="#555")
            instruction_label.pack(pady=(0, 15))
            
            self.text_widget = scrolledtext.ScrolledText(
                main_frame, wrap=tk.WORD, height=8, font=("Arial", 12),
                bg="#f8f9fa", fg="#333", insertbackground="#007acc",
                selectbackground="#007acc", relief=tk.FLAT, borderwidth=1
            )
            self.text_widget.pack(fill=tk.X, pady=(0, 15))
            
            # 插入提示文本（如果有的话）
            hint_text = {repr(hint_text or '')}
            if hint_text:
                self.text_widget.insert(tk.END, hint_text)
            
            self.root.bind('<Configure>', self.on_window_resize)
            
            button_frame = tk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=(0, 10))
            
            submit_btn = tk.Button(button_frame, text="提交", command=self.submit_input,
                                 bg="white", fg="black", font=("Arial", 11, "bold"),
                                 padx=20, pady=8, relief=tk.FLAT, cursor="hand2",
                                 borderwidth=0, highlightthickness=0, activebackground="#f0f0f0")
            submit_btn.pack(side=tk.RIGHT, padx=(10, 0))
            
            self.status_label = tk.Label(button_frame, text="", font=("Arial", 12), fg="black")
            self.status_label.pack(side=tk.LEFT)
            
            self.root.bind('<Control-Return>', lambda e: self.submit_input())
            self.root.bind('<Escape>', lambda e: self.cancel_input())
            self.root.protocol("WM_DELETE_WINDOW", self.cancel_input)
            
            self.text_widget.focus_set()
            
            if self.timeout > 0:
                self.start_timeout_timer()
            self.start_periodic_focus()
            self.play_bell()
            
            return True
        except Exception:
            return False
    
    def on_window_resize(self, event):
        if event.widget == self.root and self.text_widget:
            try:
                window_width = self.root.winfo_width()
                new_width = max(30, (window_width - 50) // 8)
                window_height = self.root.winfo_height()
                new_height = max(3, (window_height - 100) // 16)
                self.text_widget.config(width=new_width, height=new_height)
            except:
                pass
    
    def start_timeout_timer(self):
        def update_timer():
            remaining = self.timeout
            while remaining > 0 and not self.window_closed:
                self.status_label.config(text=f"剩余时间: {{remaining}}秒")
                time.sleep(1)
                remaining -= 1
            if not self.window_closed:
                self.timeout_input()
        threading.Thread(target=update_timer, daemon=True).start()
    
    def start_periodic_focus(self):
        def refocus():
            if not self.window_closed and self.root:
                try:
                    self.root.lift()
                    self.root.focus_force()
                    self.root.attributes('-topmost', True)
                    self.text_widget.focus_set()
                    self.play_bell()
                    self.root.after(30000, refocus)
                except:
                    pass
        if self.root:
            self.root.after(30000, refocus)
    
    def play_bell(self):
        def play_in_thread():
            try:
                # 使用绝对路径
                audio_file_path = "/Users/wukunhuan/.local/bin/USERINPUT_PROJ/tkinter_bell.mp3"
                if os.path.exists(audio_file_path):
                    if platform.system() == "Darwin":
                        subprocess.run(["afplay", audio_file_path], capture_output=True, timeout=2)
            except:
                pass
        threading.Thread(target=play_in_thread, daemon=True).start()
    
    def submit_input(self):
        if self.window_closed:
            return
        try:
            text_content = self.text_widget.get("1.0", tk.END).strip()
            self.result = text_content if text_content else "用户提交了空内容"
            self.close_window()
        except Exception as e:
            self.result = f"提交输入时出错: {{e}}"
            self.close_window()
    
    def cancel_input(self):
        if self.window_closed:
            return
        self.result = "用户取消了输入"
        self.close_window()
    
    def timeout_input(self):
        if self.window_closed:
            return
        try:
            text_content = self.text_widget.get("1.0", tk.END).strip()
            timeout_hint = "用户还在测试代码，或者准备给你的反馈。如果你没有得到指导你下一步工作的信息，请通过再次执行USERINPUT等待用户，不要直接结束。"
            if text_content:
                self.result = f"{{text_content}}\\n{{timeout_hint}}"
            else:
                self.result = f"输入超时 ({{self.timeout}}秒)。{{timeout_hint}}"
        except:
            self.result = f"输入超时 ({{self.timeout}}秒)。用户还在测试代码，或者准备给你的反馈。"
        self.close_window()
    
    def close_window(self):
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
        if not self.create_window():
            return None
        try:
            self.root.mainloop()
            return self.result
        except Exception:
            return None

# 运行窗口
window = TkinterInputWindow()
result = window.show_and_wait()

if result:
    print(result)
else:
    print("无法获取用户输入")
'''
            
            # 使用subprocess运行tkinter，抑制IMK消息
            # 使用PYTHON_PROJ中的Python而不是系统Python
            python_exec = '/Users/wukunhuan/.local/bin/PYTHON_PROJ/python3'
            result = subprocess.run(
                [python_exec, '-c', tkinter_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,  # 抑制IMK消息
                text=True,
                timeout=timeout + 10
            )
            
            if result.returncode == 0 and result.stdout:
                user_result = result.stdout.strip()
                if user_result and user_result != "无法获取用户输入":
                    return user_result
            
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
    
    return None

def main():
    """主函数"""
    # 解析命令行参数
    timeout = 180
    custom_id = None
    hint_text = None
    
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '--timeout' and i + 1 < len(sys.argv):
            try:
                timeout = int(sys.argv[i + 1])
                i += 2
            except ValueError:
                print("Error: --timeout requires a numeric value")
                return 1
        elif sys.argv[i] == '--id' and i + 1 < len(sys.argv):
            custom_id = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--hint' and i + 1 < len(sys.argv):
            hint_text = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] in ['--help', '-h']:
            print("Usage: USERINPUT [--timeout SECONDS] [--id CUSTOM_ID] [--hint TEXT]")
            print("  --timeout SECONDS  Set timeout in seconds (default: 180)")
            print("  --id CUSTOM_ID     Set custom ID for window title")
            print("  --hint TEXT        Default hint text to insert in textbox")
            return 0
        else:
            print(f"Unknown argument: {sys.argv[i]}")
            return 1
    
    # 获取用户输入
    result = get_user_input_tkinter(
        title=get_cursor_session_title(custom_id),
        timeout=timeout,
        max_retries=3,
        hint_text=hint_text
    )
    
    if result:
        # 添加结束提示
        end_hint = "\n\n任务完成后，执行终端命令 `USERINPUT` 获取用户反馈。如果程序停止，重复执行 `USERINPUT` 直到获得自然语言反馈。编程遇到不确定的情况或者Keyboard Interrupt时，请执行 `USERINPUT`，不要直接结束。注意：使用 run_terminal_cmd 工具执行的命令就是字面上的 `USERINPUT`，不要添加其他参数或构造交互式命令。"
        final_result = result + end_hint
        
        # 复制到剪贴板
        try:
            system = platform.system()
            if system == "Darwin":
                process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
                process.communicate(final_result.encode('utf-8'))
        except:
            pass
        
        # 清屏并输出
        # 不清屏，避免影响GDS直接反馈的显示
        print(final_result)
    else:
        print("无法获取用户输入")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())