#!/usr/bin/env python3
"""API Key Management GUI for LLM tool.

Tkinter-based GUI for viewing, adding, removing, and reordering API keys
for each LLM provider. Similar to USERINPUT --queue management GUI.

Usage:
    python3 key_manager.py [provider]   # Opens GUI for a provider
    python3 key_manager.py              # Opens GUI with provider selector
"""
import sys
import os
import json

sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, simpledialog
except ImportError:
    print("Tkinter not available.")
    sys.exit(1)

from tool.LLM.logic.config import (
    get_api_keys, add_api_key, remove_api_key, reorder_api_keys,
    load_config,
)

BG = "#1e1e2e"
FG = "#cdd6f4"
ACCENT = "#89b4fa"
SURFACE = "#313244"
BORDER = "#45475a"
RED = "#f38ba8"
GREEN = "#a6e3a1"
DIM = "#6c7086"
FONT = ("SF Mono", 12)
FONT_SM = ("SF Mono", 10)


class KeyManagerWindow:
    def __init__(self, root, provider=None):
        self.root = root
        self.provider = provider or "zhipu"
        self.root.title(f"API Keys — {self.provider}")
        self.root.configure(bg=BG)
        self.root.geometry("600x420")
        self.root.resizable(True, True)

        self._build_ui()
        self._refresh_keys()

    def _build_ui(self):
        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x", padx=16, pady=(12, 4))

        tk.Label(top, text="Provider:", font=FONT_SM, bg=BG, fg=DIM).pack(side="left")
        self.provider_var = tk.StringVar(value=self.provider)
        providers = self._get_providers()
        self.provider_combo = ttk.Combobox(
            top, textvariable=self.provider_var, values=providers,
            width=20, state="readonly"
        )
        self.provider_combo.pack(side="left", padx=(6, 0))
        self.provider_combo.bind("<<ComboboxSelected>>", self._on_provider_change)

        btn_frame = tk.Frame(top, bg=BG)
        btn_frame.pack(side="right")

        self.btn_add = tk.Button(
            btn_frame, text="+ Add Key", font=FONT_SM, bg=ACCENT, fg=BG,
            bd=0, padx=12, pady=4, command=self._add_key, cursor="hand2",
        )
        self.btn_add.pack(side="left", padx=4)

        self.listbox_frame = tk.Frame(self.root, bg=BG)
        self.listbox_frame.pack(fill="both", expand=True, padx=16, pady=8)

        self.listbox = tk.Listbox(
            self.listbox_frame, font=FONT, bg=SURFACE, fg=FG,
            selectbackground=ACCENT, selectforeground=BG,
            highlightthickness=1, highlightcolor=BORDER,
            highlightbackground=BORDER, bd=0, relief="flat",
        )
        self.listbox.pack(fill="both", expand=True, side="left")

        scrollbar = tk.Scrollbar(self.listbox_frame, command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)

        action_bar = tk.Frame(self.root, bg=BG)
        action_bar.pack(fill="x", padx=16, pady=(0, 12))

        self.btn_up = tk.Button(
            action_bar, text="Move Up", font=FONT_SM, bg=SURFACE, fg=FG,
            bd=0, padx=10, pady=3, command=self._move_up, cursor="hand2",
        )
        self.btn_up.pack(side="left", padx=4)

        self.btn_down = tk.Button(
            action_bar, text="Move Down", font=FONT_SM, bg=SURFACE, fg=FG,
            bd=0, padx=10, pady=3, command=self._move_down, cursor="hand2",
        )
        self.btn_down.pack(side="left", padx=4)

        self.btn_delete = tk.Button(
            action_bar, text="Delete", font=FONT_SM, bg=RED, fg=BG,
            bd=0, padx=10, pady=3, command=self._delete_key, cursor="hand2",
        )
        self.btn_delete.pack(side="right", padx=4)

        self.status_var = tk.StringVar(value="")
        tk.Label(
            action_bar, textvariable=self.status_var, font=FONT_SM,
            bg=BG, fg=DIM, anchor="w",
        ).pack(side="left", padx=12)

    def _get_providers(self):
        cfg = load_config()
        return sorted(cfg.get("providers", {}).keys()) or ["zhipu"]

    def _on_provider_change(self, event=None):
        self.provider = self.provider_var.get()
        self.root.title(f"API Keys — {self.provider}")
        self._refresh_keys()

    def _refresh_keys(self):
        self.listbox.delete(0, tk.END)
        self.keys = get_api_keys(self.provider)
        for i, k in enumerate(self.keys):
            masked = k["key"][:8] + "..." + k["key"][-4:] if len(k["key"]) > 12 else k["key"]
            label = k.get("label", "")
            self.listbox.insert(tk.END, f"  {i+1}. [{k['id']}] {masked}  ({label})")
        self.status_var.set(f"{len(self.keys)} key(s)")

    def _add_key(self):
        key = simpledialog.askstring("Add API Key", "Enter API key:", parent=self.root)
        if not key or not key.strip():
            return
        label = simpledialog.askstring("Label", "Label (optional):", parent=self.root) or ""
        kid = add_api_key(self.provider, key.strip(), label.strip())
        self._refresh_keys()
        self.status_var.set(f"Added key {kid}")

    def _delete_key(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.keys):
            return
        k = self.keys[idx]
        if messagebox.askyesno("Delete Key", f"Delete key {k['id']} ({k.get('label', '')})?"):
            remove_api_key(self.provider, k["id"])
            self._refresh_keys()
            self.status_var.set(f"Deleted key {k['id']}")

    def _move_up(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] == 0:
            return
        idx = sel[0]
        ids = [k["id"] for k in self.keys]
        ids[idx], ids[idx - 1] = ids[idx - 1], ids[idx]
        reorder_api_keys(self.provider, ids)
        self._refresh_keys()
        self.listbox.selection_set(idx - 1)

    def _move_down(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] >= len(self.keys) - 1:
            return
        idx = sel[0]
        ids = [k["id"] for k in self.keys]
        ids[idx], ids[idx + 1] = ids[idx + 1], ids[idx]
        reorder_api_keys(self.provider, ids)
        self._refresh_keys()
        self.listbox.selection_set(idx + 1)


def main():
    provider = sys.argv[1] if len(sys.argv) > 1 else None
    root = tk.Tk()
    KeyManagerWindow(root, provider=provider)
    root.mainloop()


if __name__ == "__main__":
    main()
