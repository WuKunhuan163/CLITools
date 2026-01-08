#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GDS Setup Manager Module
Handles the guided setup process for Google Drive Shell using a Tkinter GUI.
"""

import os
import sys
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

class SetupManager:
    def __init__(self, main_instance=None):
        self.main_instance = main_instance
        self.root = None
        self.current_step = 0
        
        # Load path constants dynamically
        try:
            from .path_constants import get_data_dir
            self.data_dir = get_data_dir()
        except ImportError:
            # Fallback
            self.data_dir = Path(__file__).parent.parent.parent / "GOOGLE_DRIVE_DATA"
            
        self.config_path = self.data_dir / "cache_config.json"
        self.config_data = self.load_config()
        
        # Define steps
        self.steps = [
            {
                "id": "service_account",
                "title": "Step 1: Service Account Setup",
                "content": "To access Google Drive via API, you need a Service Account JSON key file.\n\n"
                           "If you have already uploaded it, the information will be displayed below.\n"
                           "Otherwise, click 'Upload JSON' to select your 'console-control-....json' file.",
                "verify": self.verify_service_account,
                "has_upload": True
            }
        ]

    def load_config(self):
        """Load configuration from cache_config.json"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_config(self):
        """Save configuration to cache_config.json"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def start_setup(self):
        """Initialize and start the Tkinter setup GUI"""
        self.root = tk.Tk()
        self.root.title("GDS guided setup")
        self.root.geometry("600x450")
        
        # Make it appear on top
        self.root.attributes('-topmost', True)
        self.root.focus_force()

        # --- Top: Progress Bar ---
        progress_frame = tk.Frame(self.root, pady=20)
        progress_frame.pack(fill=tk.X)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            variable=self.progress_var, 
            maximum=len(self.steps)
        )
        self.progress_bar.pack(fill=tk.X, padx=40)
        
        self.step_label = tk.Label(progress_frame, text="", font=("Arial", 10))
        self.step_label.pack(pady=(5, 0))

        # --- Middle: Content Area ---
        content_main_frame = tk.Frame(self.root, padx=40)
        content_main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.title_label = tk.Label(
            content_main_frame, 
            text="", 
            font=("Arial", 14, "bold"),
            anchor="w"
        )
        self.title_label.pack(fill=tk.X, pady=(0, 10))
        
        # Use a frame for text and scrollbar
        text_frame = tk.Frame(content_main_frame, relief=tk.GROOVE, borderwidth=1)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.info_text = tk.Text(
            text_frame, 
            wrap=tk.WORD, 
            font=("Arial", 11),
            bg="#f9f9f9",
            padx=10,
            pady=10,
            state=tk.DISABLED
        )
        self.info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(text_frame, command=self.info_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.info_text.config(yscrollcommand=scrollbar.set)

        # --- Bottom: Button Area ---
        self.button_frame = tk.Frame(self.root, padx=40, pady=20)
        self.button_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.upload_btn = tk.Button(
            self.button_frame, 
            text="Upload JSON", 
            command=self.handle_upload,
            width=15
        )
        # We'll pack it conditionally in update_ui
        
        self.continue_btn = tk.Button(
            self.button_frame, 
            text="Continue", 
            command=self.handle_continue,
            width=15,
            font=("Arial", 11, "bold"),
            bg="#007acc",
            fg="black" # Tkinter button fg behavior varies by OS
        )
        self.continue_btn.pack(side=tk.RIGHT)

        # Initialize the first step
        self.update_ui()
        
        # Center the window
        self.root.eval('tk::PlaceWindow . center')
        
        self.root.mainloop()

    def update_ui(self):
        """Update the GUI based on the current step"""
        step = self.steps[self.current_step]
        
        # Update progress and labels
        self.progress_var.set(self.current_step + 1)
        self.step_label.config(text=f"Step {self.current_step + 1} of {len(self.steps)}")
        self.title_label.config(text=step["title"])
        
        # Update content
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete("1.0", tk.END)
        self.info_text.insert(tk.END, step["content"])
        
        # Step-specific pre-loading logic
        if step["id"] == "service_account":
            if "service_account_info" in self.config_data:
                info = self.config_data["service_account_info"]
                sa_details = (
                    f"\n\n----------------------------------\n"
                    f"PRE-LOADED SERVICE ACCOUNT INFO:\n"
                    f"Project ID: {info.get('project_id', 'N/A')}\n"
                    f"Client Email: {info.get('client_email', 'N/A')}\n"
                    f"Key Type: {info.get('type', 'N/A')}\n"
                    f"----------------------------------"
                )
                self.info_text.insert(tk.END, sa_details)
        
        self.info_text.config(state=tk.DISABLED)
        
        # Update buttons
        if step.get("has_upload"):
            self.upload_btn.pack(side=tk.LEFT)
        else:
            self.upload_btn.pack_forget()
            
        if self.current_step == len(self.steps) - 1:
            self.continue_btn.config(text="Finish")
        else:
            self.continue_btn.config(text="Continue")

    def handle_upload(self):
        """Handle upload button click based on step"""
        step = self.steps[self.current_step]
        if step["id"] == "service_account":
            self.upload_service_account_json()

    def upload_service_account_json(self):
        """Open file dialog to upload Service Account JSON"""
        file_path = filedialog.askopenfilename(
            title="Select Service Account JSON Key File",
            filetypes=[("JSON files", "*.json")]
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate essential fields
            required = ["type", "project_id", "private_key", "client_email"]
            if all(k in data for k in required):
                self.config_data["service_account_info"] = data
                if self.save_config():
                    messagebox.showinfo("Success", "Service Account JSON validated and saved successfully.")
                    self.update_ui()
                else:
                    messagebox.showerror("Error", "Failed to save configuration file.")
            else:
                messagebox.showerror("Error", "Invalid Service Account JSON. Missing required fields.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read JSON file: {e}")

    def verify_service_account(self):
        """Verification logic for the service account step"""
        if "service_account_info" in self.config_data:
            info = self.config_data["service_account_info"]
            # Basic structural check already done on upload, 
            # here we could do more if needed (e.g. test API connection)
            return True
        else:
            messagebox.showwarning("Incomplete", "Please upload your Service Account JSON file first.")
            return False

    def handle_continue(self):
        """Handle continue button click"""
        step = self.steps[self.current_step]
        if step["verify"]():
            self.current_step += 1
            if self.current_step >= len(self.steps):
                # Setup completed
                messagebox.showinfo("Completed", "Setup has been completed successfully.")
                self.root.destroy()
            else:
                self.update_ui()

if __name__ == "__main__":
    # Test execution
    manager = SetupManager()
    manager.start_setup()

