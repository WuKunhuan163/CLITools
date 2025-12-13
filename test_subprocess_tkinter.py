#!/usr/bin/env python3
"""
测试subprocess方式运行tkinter
"""
import subprocess
import sys
import time
import random

# 生成Window ID
window_id = f"win_{int(time.time())}_{random.randint(1000, 9999)}"
print(f"Window ID: {window_id}")

# 简单的tkinter脚本
tkinter_script = '''
import os
import sys
import warnings
warnings.filterwarnings('ignore')
os.environ['TK_SILENCE_DEPRECATION'] = '1'

import tkinter as tk

root = tk.Tk()
root.title("测试窗口")
root.geometry("300x200")

label = tk.Label(root, text="测试subprocess tkinter", font=("Arial", 14))
label.pack(pady=50)

result = "测试成功"

def close_window():
    global result
    root.quit()
    root.destroy()

button = tk.Button(root, text="关闭", command=close_window)
button.pack(pady=20)

# 5秒后自动关闭
root.after(5000, close_window)

root.mainloop()
print(result)
'''

# 运行subprocess
result = subprocess.run(
    [sys.executable, '-c', tkinter_script],
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,  # 抑制IMK消息
    text=True,
    timeout=10
)

if result.returncode == 0:
    print(f"subprocess结果: {result.stdout.strip()}")
else:
    print("subprocess失败")