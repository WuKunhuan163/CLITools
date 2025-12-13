#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试窗口布局问题的调试脚本
"""

import tkinter as tk
from tkinter import scrolledtext

def create_test_window(window_height=300):
    """创建测试窗口来调试布局问题"""
    root = tk.Tk()
    root.title(f"布局测试 - 高度: {window_height}px")
    root.geometry(f"450x{window_height}")
    
    # 创建主框架
    main_frame = tk.Frame(root, padx=15, pady=15, bg="lightblue")
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # 说明标签
    instruction_label = tk.Label(main_frame, 
                               text="请在文本框中输入您的反馈，并点击 '提交' 按钮:",
                               font=("Arial", 11), fg="#555", bg="lightblue")
    instruction_label.pack(pady=(0, 15))
    
    # 文本框框架（用于调试）
    text_frame = tk.Frame(main_frame, bg="red", relief=tk.SOLID, borderwidth=2)
    text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
    
    # 创建文本框
    text_widget = scrolledtext.ScrolledText(
        text_frame,
        wrap=tk.WORD,
        width=50,
        font=("Arial", 12),
        bg="#f8f9fa",
        fg="#333"
    )
    text_widget.pack(fill=tk.BOTH, expand=True)
    
    # 按钮框架（用于调试）
    button_frame = tk.Frame(main_frame, bg="green", relief=tk.SOLID, borderwidth=2)
    button_frame.pack(fill=tk.X, pady=(0, 10))
    
    # 提交按钮
    submit_btn = tk.Button(
        button_frame,
        text="提交",
        bg="white",
        fg="black",
        font=("Arial", 11, "bold"),
        padx=20,
        pady=8,
        relief=tk.FLAT,
        borderwidth=0
    )
    submit_btn.pack(side=tk.RIGHT, padx=(10, 0))
    
    # 状态标签
    status_label = tk.Label(button_frame, text=f"窗口高度: {window_height}px", 
                          font=("Arial", 12), fg="black", bg="green")
    status_label.pack(side=tk.LEFT)
    
    # 添加关闭按钮
    def close_window():
        root.destroy()
    
    close_btn = tk.Button(button_frame, text="关闭", command=close_window, 
                         bg="red", fg="white")
    close_btn.pack(side=tk.RIGHT, padx=(5, 0))
    
    print(f"创建测试窗口 - 高度: {window_height}px")
    print("红色边框: 文本框区域")
    print("绿色边框: 按钮区域")
    print("蓝色背景: 主框架")
    
    root.mainloop()

def main():
    """测试不同窗口高度"""
    heights = [250, 300, 350, 400, 450, 500]
    
    print("测试窗口布局问题")
    print("=" * 40)
    
    for height in heights:
        choice = input(f"\n测试窗口高度 {height}px? (y/n/q): ").strip().lower()
        if choice == 'q':
            break
        elif choice == 'y':
            create_test_window(height)

if __name__ == "__main__":
    main()