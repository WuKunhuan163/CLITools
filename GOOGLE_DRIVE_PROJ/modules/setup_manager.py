#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Drive Shell - Setup Manager Module
Provides a GUI-based guided setup process using Tkinter.
"""

import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import base64

class SetupManager:
    def __init__(self, main_instance=None):
        self.main_instance = main_instance
        self.root = None
        self.current_step_idx = 0
        self.steps = []
        self.setup_data = {}
        
        # 获取项目根目录和数据目录
        try:
            from .path_constants import get_data_dir, path_constants
            self.data_dir = get_data_dir()
            self.project_root = path_constants.PROJECT_ROOT
        except ImportError:
            self.project_root = Path(__file__).parent.parent.parent.absolute()
            self.data_dir = self.project_root / "GOOGLE_DRIVE_DATA"
            
        self.config_file = self.data_dir / "setup_config.json"
        self.cache_config_file = self.data_dir / "cache_config.json"
        
        # 加载持久化数据
        self.load_setup_data()
        
        # 定义步骤
        self.init_steps()

    def load_setup_data(self):
        """加载已有的设置数据"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.setup_data = json.load(f)
            except Exception:
                self.setup_data = {}
        
        # 同时也尝试从 cache_config.json 加载一些信息
        if self.cache_config_file.exists():
            try:
                with open(self.cache_config_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                    # 将 cache 中的信息合并到 setup_data（如果不冲突）
                    for k, v in cache.items():
                        if k not in self.setup_data:
                            self.setup_data[k] = v
            except Exception:
                pass

    def save_setup_data(self):
        """保存设置数据"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.setup_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save setup data: {e}")

    def init_steps(self):
        """初始化设置步骤"""
        self.steps = [
            {
                "title": "服务账户设置",
                "description": "请上传 Google Drive API 服务账户 JSON 密钥文件。\n这个文件通常名为 'console-control-....json'。\n您可以从 Google Cloud Console 下载它。",
                "verification": self.verify_service_account,
                "ui_builder": self.build_service_account_ui
            }
            # 可以在此处添加更多步骤
        ]

    def build_gui(self):
        """构建主 GUI 框架"""
        self.root = tk.Tk()
        self.root.title("GDS - Setup Wizard")
        self.root.geometry("600x450")
        self.root.resizable(False, False)
        
        # 顶部进度条
        self.progress_frame = tk.Frame(self.root, pady=20)
        self.progress_frame.pack(fill=tk.X)
        
        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, 
            variable=self.progress_var, 
            maximum=len(self.steps) * 100
        )
        self.progress_bar.pack(padx=40, fill=tk.X)
        
        self.step_label = tk.Label(self.progress_frame, text="", font=("Arial", 10))
        self.step_label.pack(pady=(5, 0))
        
        # 中间内容区域
        self.content_frame = tk.Frame(self.root, padx=40, pady=10)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        self.title_label = tk.Label(self.content_frame, text="", font=("Arial", 14, "bold"))
        self.title_label.pack(anchor='w', pady=(0, 10))
        
        self.desc_text = tk.Text(
            self.content_frame, 
            wrap=tk.WORD, 
            height=6, 
            font=("Arial", 11),
            bg=self.root.cget("bg"),
            relief=tk.FLAT,
            state=tk.DISABLED
        )
        self.desc_text.pack(fill=tk.X, pady=(0, 20))
        
        # 步骤特有的 UI 容器
        self.step_specific_frame = tk.Frame(self.content_frame)
        self.step_specific_frame.pack(fill=tk.BOTH, expand=True)
        
        # 底部按钮区域
        self.button_frame = tk.Frame(self.root, padx=40, pady=20)
        self.button_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.upload_btn = tk.Button(self.button_frame, text="上传 JSON", command=self.handle_upload)
        self.upload_btn.pack(side=tk.LEFT)
        
        self.continue_btn = tk.Button(self.button_frame, text="继续", command=self.handle_continue, width=10)
        self.continue_btn.pack(side=tk.RIGHT)
        
        # 初始显示第一步
        self.show_step(0)
        
        self.root.mainloop()

    def show_step(self, idx):
        """显示指定索引的步骤"""
        self.current_step_idx = idx
        step = self.steps[idx]
        
        # 更新进度条
        self.progress_var.set((idx + 1) * 100)
        self.step_label.config(text=f"步骤 {idx + 1} / {len(self.steps)}")
        
        # 更新标题和描述
        self.title_label.config(text=step["title"])
        self.desc_text.config(state=tk.NORMAL)
        self.desc_text.delete("1.0", tk.END)
        self.desc_text.insert("1.0", step["description"])
        self.desc_text.config(state=tk.DISABLED)
        
        # 清除旧的步骤特有 UI
        for widget in self.step_specific_frame.winfo_children():
            widget.destroy()
            
        # 构建新的步骤特有 UI
        step["ui_builder"](self.step_specific_frame)
        
        # 更新按钮状态
        if idx == len(self.steps) - 1:
            self.continue_btn.config(text="完成")
        else:
            self.continue_btn.config(text="继续")
            
        # 只有第一步显示上传按钮（目前）
        if idx == 0:
            self.upload_btn.pack(side=tk.LEFT)
        else:
            self.upload_btn.pack_forget()

    def build_service_account_ui(self, parent):
        """构建服务账户步骤的 UI"""
        info_frame = tk.LabelFrame(parent, text="已加载的服务账户信息", padx=10, pady=10)
        info_frame.pack(fill=tk.X, pady=10)
        
        self.sa_info_var = tk.StringVar(value="未加载服务账户信息")
        
        if self.setup_data.get("service_account_info"):
            info = self.setup_data["service_account_info"]
            display_text = f"项目 ID: {info.get('project_id', 'N/A')}\n"
            display_text += f"客户端 Email: {info.get('client_email', 'N/A')}\n"
            display_text += f"私钥 ID: {info.get('private_key_id', 'N/A')[:10]}..."
            self.sa_info_var.set(display_text)
            
        tk.Label(info_frame, textvariable=self.sa_info_var, justify=tk.LEFT, font=("Courier", 10)).pack(fill=tk.X)

    def handle_upload(self):
        """处理上传 JSON 文件的点击事件"""
        if self.current_step_idx == 0:
            file_path = filedialog.askopenfilename(
                title="选择服务账户 JSON 文件",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            if file_path:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    # 验证是否是有效的服务账户 JSON
                    required_keys = ["project_id", "private_key", "client_email", "token_uri"]
                    if all(key in data for key in required_keys):
                        self.setup_data["service_account_info"] = data
                        self.save_setup_data()
                        
                        # 更新显示
                        display_text = f"项目 ID: {data.get('project_id', 'N/A')}\n"
                        display_text += f"客户端 Email: {data.get('client_email', 'N/A')}\n"
                        display_text += f"私钥 ID: {data.get('private_key_id', 'N/A')[:10]}..."
                        self.sa_info_var.set(display_text)
                        
                        messagebox.showinfo("成功", "服务账户信息已加载！")
                    else:
                        messagebox.showerror("错误", "所选文件似乎不是有效的 Google 服务账户 JSON 密钥文件。")
                except Exception as e:
                    messagebox.showerror("错误", f"读取文件失败: {e}")

    def handle_continue(self):
        """处理“继续”按钮的点击事件"""
        step = self.steps[self.current_step_idx]
        
        # 执行验证
        if step["verification"]():
            if self.current_step_idx < len(self.steps) - 1:
                self.show_step(self.current_step_idx + 1)
            else:
                # 最后一步完成
                self.finalize_setup()
        else:
            # 验证失败，具体错误信息由 verification 函数显示
            pass

    def verify_service_account(self):
        """验证服务账户信息"""
        if not self.setup_data.get("service_account_info"):
            messagebox.showwarning("验证失败", "请先上传服务账户 JSON 密钥文件。")
            return False
        
        # 尝试初始化 Google Drive 服务进行验证
        try:
            from ..google_drive_api import GoogleDriveService
            # 使用内存中的数据初始化，不依赖文件
            service = GoogleDriveService()
            # 基础验证通过后再设置 self.key_data（内部已经处理了）
            result = service.test_connection()
            if result.get("success"):
                messagebox.showinfo("验证成功", f"连接成功！\n用户: {result.get('user_name')}\n邮箱: {result.get('user_email')}")
                return True
            else:
                messagebox.showerror("验证失败", f"无法连接到 Google Drive API:\n{result.get('error')}")
                return False
        except Exception as e:
            messagebox.showerror("验证失败", f"发生错误:\n{e}")
            return False

    def finalize_setup(self):
        """完成设置流程，保存最终配置"""
        # 将 setup_data 中的关键信息同步到 cache_config.json
        try:
            config = {}
            if self.cache_config_file.exists():
                with open(self.cache_config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            # 这里的逻辑可以根据需要调整
            if "service_account_info" in self.setup_data:
                # 某些时候我们可能希望将 SA 信息保存在独立文件或环境变量中
                # 这里我们先保存在 cache_config 中
                config["service_account_info"] = self.setup_data["service_account_info"]
            
            with open(self.cache_config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                
            messagebox.showinfo("完成", "设置已完成并保存！")
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("错误", f"保存最终配置失败: {e}")

def run_setup_wizard():
    """运行设置向导"""
    manager = SetupManager()
    manager.build_gui()

if __name__ == "__main__":
    run_setup_wizard()
