#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USERINPUT tkinter版本 (v5)
- 按钮恢复纯粹的系统默认风格
- 调整了按钮顺序
- 修复了音效无法播放的问题
- 增大了按钮字体
"""

import os
import sys
import warnings
import subprocess
import platform
import time
import random

# 在导入tkinter之前设置环境变量
os.environ['TK_SILENCE_DEPRECATION'] = '1'
warnings.filterwarnings('ignore')

# 动态导入tkinter，以处理潜在的显示问题
try:
    import tkinter as tk
    from tkinter import font as tkFont
except ImportError:
    print("错误: Tkinter模块未找到。请确保您的Python环境包含Tkinter。", file=sys.stderr)
    sys.exit(1)

def get_project_name():
    """获取项目名称"""
    try:
        current_dir = os.getcwd()
        git_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], stderr=subprocess.DEVNULL, text=True).strip()
        if git_root:
            project_name = os.path.basename(git_root)
        else:
            project_name = os.path.basename(current_dir)
        return project_name or "root"
    except (subprocess.CalledProcessError, FileNotFoundError):
        current_dir = os.getcwd()
        project_name = os.path.basename(current_dir)
        return project_name or "root"

def get_cursor_session_title(custom_id=None):
    """获取Cursor session标题"""
    try:
        project_name = get_project_name()
        base_title = f"{project_name} - Agent Mode"
        return f"{base_title} [{custom_id}]" if custom_id else base_title
    except Exception:
        return f"Agent Mode [{custom_id}]" if custom_id else "Agent Mode"

def get_user_input_tkinter(title=None, timeout=180, hint_text=None):
    """
    通过在一个独立的Python子进程中运行Tkinter脚本来获取用户输入。
    """
    
    # --- 音效路径修复 ---
    # 在父进程中计算好音频文件的绝对路径，因为子进程中没有 __file__
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        bell_path = os.path.join(script_dir, "USERINPUT_PROJ", "tkinter_bell.mp3")
        bell_path_str_literal = repr(bell_path)
    except Exception:
        bell_path_str_literal = "''"  # 如果失败，则传递空字符串
    # --- 修复结束 ---

    # 将要作为独立脚本执行的Python代码。
    tkinter_script = f'''
import os
import sys
import warnings
warnings.filterwarnings('ignore')
os.environ['TK_SILENCE_DEPRECATION'] = '1'

import tkinter as tk
import threading
import time
import subprocess
import platform

class TkinterInputWindow:
    def __init__(self, title, timeout, hint_text):
        self.root = None
        self.text_widget = None
        self.status_label = None
        
        self.title = title
        self.initial_timeout = timeout
        self.hint_text = hint_text
        
        self.result = None
        self.window_closed = False
        self.remaining_time = self.initial_timeout

    def create_window(self):
        try:
            self.root = tk.Tk()
            self.root.title(self.title)
            self.root.geometry("450x250")
            
            self.root.attributes('-topmost', True)
            self.root.focus_force()
            
            main_frame = tk.Frame(self.root, padx=15, pady=15)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            instruction_label = tk.Label(main_frame, text="请在文本框中输入您的反馈:", font=("Arial", 11), fg="#555")
            instruction_label.pack(pady=(0, 10), anchor='w')
            
            text_frame = tk.Frame(main_frame, relief=tk.FLAT, borderwidth=1)
            text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

            scrollbar = tk.Scrollbar(text_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            self.text_widget = tk.Text(
                text_frame, wrap=tk.WORD, height=8, font=("Arial", 12), bg="#f8f9fa",
                fg="#333", insertbackground="#007acc", selectbackground="#007acc",
                relief=tk.FLAT, borderwidth=0,
                yscrollcommand=scrollbar.set
            )
            self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            scrollbar.config(command=self.text_widget.yview)
            
            if self.hint_text:
                self.text_widget.insert("1.0", self.hint_text)
            
            button_frame = tk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=(0, 10))
            
            # --- 样式和顺序改动: 恢复完全默认风格，调整顺序和字体 ---
            default_font = ("Arial", 12)
            submit_font = ("Arial", 13, "bold")
            
            # 先 pack 提交按钮，它会最靠右
            submit_btn = tk.Button(
                button_frame, text="提交", command=self.submit_input,
                font=submit_font
            )
            submit_btn.pack(side=tk.RIGHT)

            # 后 pack 加时按钮，它会靠在提交按钮的左边
            add_time_btn = tk.Button(
                button_frame, text="加时60秒", command=self.add_time,
                font=default_font
            )
            # padx=(0, 10) 在此按钮右侧增加10像素间距
            add_time_btn.pack(side=tk.RIGHT, padx=(0, 10))
            # --- 样式和顺序改动结束 ---
            
            self.status_label = tk.Label(button_frame, text="", font=("Arial", 12), fg="black")
            self.status_label.pack(side=tk.LEFT)
            
            self.root.bind('<Control-Return>', lambda e: self.submit_input())
            self.root.bind('<Command-Return>', lambda e: self.submit_input())
            self.root.bind('<Escape>', lambda e: self.cancel_input())
            self.root.protocol("WM_DELETE_WINDOW", self.cancel_input)
            
            self.text_widget.focus_set()
            
            self.start_timeout_timer()
            self.start_periodic_focus()
            self.play_bell()
            
            return True
        except Exception:
            import traceback
            print(f"ERROR: Failed to create Tkinter window.\\n{{traceback.format_exc()}}", file=sys.stdout)
            sys.exit(1)

    def add_time(self):
        if self.remaining_time > 0:
            self.remaining_time += 60
            self.status_label.config(text=f"已加时！剩余: {{self.remaining_time}}秒")

    def start_timeout_timer(self):
        def update_timer():
            while self.remaining_time > 0 and not self.window_closed:
                try:
                    self.status_label.config(text=f"剩余时间: {{self.remaining_time}}秒")
                except tk.TclError:
                    break
                time.sleep(1)
                self.remaining_time -= 1
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
                except: pass
        if self.root: self.root.after(30000, refocus)
    
    def play_bell(self):
        def play_in_thread():
            try:
                # --- 音效路径修复 ---
                # 直接使用从父进程注入的、经过repr()处理的完整路径字符串
                audio_file_path = {bell_path_str_literal}
                if audio_file_path and os.path.exists(audio_file_path) and platform.system() == "Darwin":
                    subprocess.run(["afplay", audio_file_path], capture_output=True, timeout=2)
            except: pass
        threading.Thread(target=play_in_thread, daemon=True).start()
    
    def submit_input(self):
        if self.window_closed: return
        self.result = self.text_widget.get("1.0", tk.END).strip() or "用户提交了空内容"
        self.close_window()
    
    def cancel_input(self):
        if self.window_closed: return
        self.result = "用户取消了输入"
        self.close_window()
    
    def timeout_input(self):
        if self.window_closed: return
        try:
            text_content = self.text_widget.get("1.0", tk.END).strip()
            timeout_hint = "\\n用户还在测试代码，或者准备给你的反馈。如果你没有得到指导你下一步工作的信息，请通过再次执行USERINPUT等待用户，不要直接结束。"
            self.result = f"{{text_content}}\\n{{timeout_hint}}" if text_content else f"输入超时 ({{self.initial_timeout}}秒)。{{timeout_hint}}"
        except:
            self.result = f"输入超时 ({{self.initial_timeout}}秒)。用户还在测试代码，或者准备给你的反馈。"
        self.close_window()
    
    def close_window(self):
        if self.window_closed: return
        self.window_closed = True
        if self.root:
            try: self.root.destroy()
            except: pass
    
    def show_and_wait(self):
        if not self.create_window(): return
        self.root.mainloop()
        if self.result is not None: print(self.result, file=sys.stdout)

if __name__ == "__main__":
    title_str = {repr(title)}
    timeout_int = {timeout}
    hint_text_str = {repr(hint_text)}
    
    window = TkinterInputWindow(title=title_str, timeout=timeout_int, hint_text=hint_text_str)
    window.show_and_wait()
'''
    try:
        python_exec = sys.executable
        watchdog_timeout = 3600 # 1 hour

        result = subprocess.run(
            [python_exec, '-c', tkinter_script],
            capture_output=True, text=True, encoding='utf-8', timeout=watchdog_timeout
        )

        if result.returncode != 0:
            error_message = result.stdout.strip() or result.stderr.strip()
            raise RuntimeError(f"USERINPUT子进程执行失败: {error_message}")

        user_input = result.stdout.strip()
        if not user_input:
             raise RuntimeError("USERINPUT子进程没有返回任何内容。")
        
        return user_input

    except subprocess.TimeoutExpired:
        raise RuntimeError(f"USERINPUT窗口运行超过 {watchdog_timeout} 秒，已被强制终止。")
    except Exception as e:
        raise RuntimeError(f"执行USERINPUT时发生未知错误: {e}")

def main():
    """主函数"""
    timeout = 180
    custom_id = None
    hint_text = None
    
    try:
        args = sys.argv[1:]
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == '--timeout' and i + 1 < len(args): timeout = int(args[i+1]); i += 2
            elif arg == '--id' and i + 1 < len(args): custom_id = args[i+1]; i += 2
            elif arg == '--hint' and i + 1 < len(args): hint_text = args[i+1]; i += 2
            elif arg in ['--help', '-h']:
                print("Usage: USERINPUT [--timeout SECONDS] [--id CUSTOM_ID] [--hint TEXT]")
                return 0
            else: raise ValueError(f"未知参数: {arg}")
    except (IndexError, ValueError) as e:
        print(f"参数错误: {e}", file=sys.stderr)
        return 1

    try:
        result = get_user_input_tkinter(
            title=get_cursor_session_title(custom_id), timeout=timeout, hint_text=hint_text
        )
        
        end_hint = "\n\n任务完成后，执行终端命令 `USERINPUT` 获取用户反馈。如果程序停止，重复执行 `USERINPUT` 直到获得自然语言反馈。编程遇到不确定的情况或者Keyboard Interrupt时，请执行 `USERINPUT`，不要直接结束。注意：使用 run_terminal_cmd 工具执行的命令就是字面上的 `USERINPUT`，不要添加其他参数或构造交互式命令。"
        final_result = result + end_hint
        
        if platform.system() == "Darwin":
            try:
                subprocess.run('pbcopy', input=final_result, text=True, encoding='utf-8', check=True, stderr=subprocess.DEVNULL)
            except (FileNotFoundError, subprocess.CalledProcessError): pass

        print(final_result)
        return 0

    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
