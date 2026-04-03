from src.core.events import TuringStageInfo
"""[Internal]

@export_module("gui.blueprint.base")
"""
'[Internal]\n\n@export_module("gui.blueprint.base")\n'
'[Internal]\n\n'
from src.core.io import turing_internal
import signal
import sys
from src.core.io import io
import json
import time
import platform
import os
import hashlib
import queue
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List, Union
tk = None

@turing_internal
def _get_tk():
    global tk
    if tk is None:
        import tkinter as _tk
        tk = _tk
    return tk
TK_NOISE_PATTERNS = ['IMKClient subclass', 'IMKInputSession subclass', 'chose IMKClient_Legacy', 'chose IMKInputSession_Legacy', 'invalid command name', 'check_signals', 'after script', 'TK_SILENCE_DEPRECATION', '<lambda>', 'destroying', 'main_frame']

@turing_internal
def filter_tkinter_noise(stderr_content: str) -> str:
    """[Internal]

    Filters out common Tkinter/macOS system noise from stderr.
    """
    if not stderr_content:
        return ''
    lines = stderr_content.splitlines()
    filtered_lines = [l for l in lines if not any((p in l for p in TK_NOISE_PATTERNS))]
    return '\n'.join(filtered_lines).strip()
try:
    from src.gui.style import get_label_style, get_button_style, get_status_style, get_gui_colors, get_secondary_label_style
    from src.core.trans import get_msg as get_translation
except ImportError:

    @turing_internal
    def get_label_style():
        return ('Arial', 10)

    @turing_internal
    def get_secondary_label_style():
        return ('Arial', 9, 'italic')

    @turing_internal
    def get_button_style(primary=False):
        return ('Arial', 10, 'bold' if primary else 'normal')

    @turing_internal
    def get_status_style():
        return ('Arial', 11)

    @turing_internal
    def get_gui_colors():
        return {'blue': '#007AFF', 'green': '#28A745', 'red': '#DC3545', 'pulse': '#004085'}

    @turing_internal
    def get_translation(d, k, default):
        return default

class BaseGUIWindow:
    """
    std:docstring
bypass: [io]
    """

    def __init__(self, title: str, timeout: int, internal_dir: str, tool_name: str=None, focus_interval: int=90):
        self.title = title
        self.remaining_time = timeout
        self.internal_dir = internal_dir
        self.tool_name = tool_name
        self.root = None
        self.window_closed = False
        self.result = {'status': 'error', 'data': None}
        self.pulse_active = False
        self.focus_interval = focus_interval
        self.bell_path = str(Path(__file__).resolve().parent.parent.parent.parent.parent / 'logic' / '_' / 'utils' / 'asset' / 'audio' / 'bell.mp3')
        self.is_triggering_subtool = False
        self.add_time_increment = 60
        self.submit_btn = None
        self.cancel_btn = None
        self.add_time_btn = None
        self.bottom_bar_frame = None
        self.timer_frozen = False
        self.resizable_images: List[Dict[str, Any]] = []
        self.blocks: List[Any] = []
        self.debug_blocks = False
        self.callback_queue = queue.Queue()
        self._child_procs: List[Any] = []
        if self.internal_dir and isinstance(self.internal_dir, (str, Path)):
            self.project_root = Path(self.internal_dir).resolve()
            while self.project_root.parent != self.project_root and (not (self.project_root / 'blueprint.yml').exists()):
                self.project_root = self.project_root.parent
        else:
            self.project_root = Path.cwd()
        signal.signal(signal.SIGINT, self.handle_external_signal)
        signal.signal(signal.SIGTERM, self.handle_external_signal)

    @turing_internal
    def _(self, key: str, default: str, **kwargs) -> str:
        val = get_translation(self.internal_dir, f"blueprint:base.{key}", default)
        return val.format(**kwargs)

    @turing_internal
    def handle_external_signal(self, signum, frame):
        """
    std:docstring
bypass: [io]
    """
        if not self.window_closed:
            stop_file = self.project_root / 'data' / 'run' / 'stops' / f'{os.getpid()}.stop'
            reason = 'signal'
            if stop_file.exists():
                reason = 'stop'
            self.finalize('terminated', self.get_current_state(), reason=reason)
            TuringStageInfo('GDS_GUI_RESULT_JSON:' + json.dumps(self.result)).emit()
            sys.exit(128 + signum)

    @turing_internal
    def check_signals(self):
        """
    std:docstring
bypass: [io]
    """
        if not self.window_closed and self.root:
            try:
                stops_dir = self.project_root / 'data' / 'run' / 'stops'
                pid = os.getpid()
                stop_file = stops_dir / f'{pid}.stop'
                if stop_file.exists():
                    stop_file.unlink()
                    self.finalize('terminated', self.get_current_state(), reason='stop')
                    return
                submit_file = stops_dir / f'{pid}.submit'
                if submit_file.exists():
                    submit_file.unlink()
                    self.finalize('success', self.get_current_state())
                    return
                cancel_file = stops_dir / f'{pid}.cancel'
                if cancel_file.exists():
                    cancel_file.unlink()
                    self.finalize('cancelled', self.get_current_state())
                    return
                add_time_file = stops_dir / f'{pid}.add_time'
                if add_time_file.exists():
                    add_time_file.unlink()
                    if hasattr(self, 'on_remote_add_time'):
                        self.on_remote_add_time()
                    else:
                        self.remaining_time += self.add_time_increment
                        if not sys.stdout.isatty():
                            TuringStageInfo(f'GDS_GUI_TIME_ADDED:{self.add_time_increment}').emit()
            except Exception:
                pass
            try:
                self.root.after(500, self.check_signals)
            except Exception:
                pass

    @turing_internal
    def start_timer(self, status_label: Any):
        """[Internal]
Standardized countdown timer."""
        if self.window_closed:
            return
        if not hasattr(self, '_default_status_fg'):
            self._default_status_fg = status_label.cget('fg')
        if not self.pulse_active:
            try:
                rem_msg = self._('time_remaining', 'Remaining:')
                status_label.config(text=f'{rem_msg} {self.remaining_time}s', fg=self._default_status_fg)
            except Exception:
                pass
        if self.remaining_time > 0:
            if not self.timer_frozen:
                self.remaining_time -= 1
            if self.root:
                self.root.after(1000, lambda: self.start_timer(status_label))
        else:
            self.finalize('timeout', self.get_current_state())

    @turing_internal
    def play_bell(self):
        """[Internal]
Standard bell notification logic using unified interface."""
        import subprocess
        import threading
        from pathlib import Path

        def run_play():
            try:
                curr = Path(__file__).resolve()
                while curr.parent != curr and (not (curr / 'bin' / 'TOOL').exists()):
                    curr = curr.parent
                tool_path = curr / 'bin' / 'TOOL'
                if tool_path.exists():
                    subprocess.run([str(tool_path), '---gui', '--bell'], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, timeout=5)
            except Exception:
                pass
        threading.Thread(target=run_play, daemon=True).start()

    @turing_internal
    def start_periodic_focus(self, interval: int):
        """[Internal]
Starts periodic refocusing and bell."""
        self.focus_interval = interval
        if self.focus_interval <= 0:
            return

        @turing_internal
        def refocus():
            if not self.window_closed and self.root:
                if not self.is_triggering_subtool:
                    try:
                        self.root.lift()
                        self.root.attributes('-topmost', True)
                        self.play_bell()
                    except Exception:
                        pass
                self.root.after(self.focus_interval * 1000, refocus)
        if self.root:
            self.root.after(self.focus_interval * 1000, refocus)

    @turing_internal
    def register_child_proc(self, proc):
        """[Internal]
Register a child subprocess for cleanup when this window closes."""
        self._child_procs.append(proc)

    @turing_internal
    def _terminate_children(self):
        """[Internal]
Terminate all registered child subprocesses."""
        for proc in self._child_procs:
            try:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=2)
                    except Exception:
                        proc.kill()
            except Exception:
                pass
        self._child_procs.clear()

    @turing_internal
    def finalize(self, status: str, data: Any, reason: Optional[str]=None):
        """[Internal]
Unified closure point (Interface I). status: success, cancelled, timeout, terminated, error."""
        if not self.window_closed:
            self.window_closed = True
            self.result = {'status': status, 'data': data}
            if reason:
                self.result['reason'] = reason
            if status in ('timeout', 'terminated', 'cancelled') and data:
                self._salvage_content(data)
            self._terminate_children()
            try:
                if self.root:
                    self.root.withdraw()
                    self.root.update_idletasks()
                    self.root.after(50, self.root.destroy)
            except Exception:
                pass

    @turing_internal
    def _salvage_content(self, data: str):
        """[Internal]
On non-success exit, copy content to clipboard and write to a fallback file."""
        if not data or not str(data).strip():
            return
        content = str(data).strip()
        try:
            if self.root:
                self.root.clipboard_clear()
                self.root.clipboard_append(content)
                self.root.update()
        except Exception:
            pass
        try:
            fallback_dir = self.project_root / 'data' / 'input'
            fallback_dir.mkdir(parents=True, exist_ok=True)
            ts = time.strftime('%Y%m%d_%H%M%S')
            h = hashlib.md5(f'{os.getpid()}{time.time()}'.encode()).hexdigest()[:6]
            fallback_file = fallback_dir / f'salvage_{ts}_{h}.txt'
            with open(fallback_file, 'w', encoding='utf-8') as f:
                f.write(content)
            self.result['fallback_file'] = str(fallback_file)
        except Exception:
            pass

    @turing_internal
    def trigger_add_time(self, increment: int, status_label: Optional[Any]=None):
        """[Internal]

        Atomically increments remaining time, notifies parent, and updates UI.
        The signal notification happens BEFORE UI updates.
        """
        try:
            added_time_dir = self.project_root / 'data' / 'run' / 'added_time'
            added_time_dir.mkdir(parents=True, exist_ok=True)
            ts = time.time()
            flag_file = added_time_dir / f'{os.getpid()}_{ts}_{increment}.add'
            flag_file.touch()
        except Exception:
            pass
        self.remaining_time += increment
        self.pulse_active = True
        if status_label and (not self.window_closed):
            added_msg = self._('time_added', 'Time added!')
            status_label.config(text=f'{added_msg} {self.remaining_time}s', fg=get_gui_colors()['pulse'])

            @turing_internal
            def reset_pulse():
                if not self.window_closed:
                    self.pulse_active = False
                    rem_msg = self._('time_remaining', 'Remaining:')
                    status_label.config(text=f'{rem_msg} {self.remaining_time}s', fg=self._default_status_fg)
            self.root.after(2000, reset_pulse)

    @turing_internal
    def get_current_state(self) -> Any:
        """[Internal]
Subclasses MUST override this to return their current state (State A)."""
        return None

    @turing_internal
    def add_block(self, parent, pady=10, padx=0, bg=None):
        """[Internal]
Adds a new layout block (tk.Frame) that fills the width."""
        import tkinter as tk
        block_bg = bg
        if not block_bg:
            if getattr(self, 'debug_blocks', False):
                block_bg = '#f9f9f9'
            else:
                block_bg = parent.cget('bg')
        block = tk.Frame(parent, bg=block_bg)
        block.pack(fill=tk.X, side=tk.TOP, padx=padx, pady=pady)
        self.blocks.append(block)
        return block

    @turing_internal
    @io
    @io
    def setup_image(self, parent, image_path: Union[str, Path], max_width: int=None, max_height: int=None, upscale: int=2, dynamic: bool=True):
        """
    std:docstring
bypass: [io]
    """
        from PIL import Image
        import tkinter as tk
        try:
            img_path_str = str(image_path)
            img = Image.open(img_path_str)
            if img.mode in ('P', 'PA', 'L', 'LA', '1'):
                img = img.convert('RGBA')
            label = tk.Label(parent, bg=parent.cget('bg'))
            label.pack(pady=10, fill=tk.X)
            item = {'label': label, 'path': img_path_str, 'max_width': max_width, 'max_height': max_height, 'upscale': upscale, 'original_img': img, 'parent': parent}
            if dynamic:
                self.resizable_images.append(item)
                if not hasattr(parent, '_resize_bound'):
                    parent.bind('<Configure>', self.on_container_resize, add='+')
                    parent._resize_bound = True
            self.root.after(100, lambda: self._resize_single_image(item))
            return label
        except Exception as e:
            import tkinter as tk
            sys.stdout.write(f'Error loading image {image_path}: {e}\n')
            sys.stdout.flush()
            err_label = tk.Label(parent, text=f'Error loading image: {os.path.basename(str(image_path))}', fg='red')
            err_label.pack(pady=5)
            return err_label

    @turing_internal
    @io
    @io
    def _resize_single_image(self, item):
        """
    std:docstring
bypass: [io]
    """
        from PIL import ImageTk, Image
        import tkinter as tk
        label = item['label']
        try:
            if not label.winfo_exists():
                return
        except tk.TclError:
            return
        parent = item['parent']
        original_img = item['original_img']
        item['upscale']
        parent_w = parent.winfo_width()
        if parent_w <= 1:
            if self.root:
                parent_w = parent.winfo_width()
            if parent_w <= 1:
                parent_w = self.root.winfo_width() - 80 if self.root else 720
        prev_target_w = item.get('last_target_w', 0)
        target_w = parent_w - 40
        if target_w < 50:
            target_w = 50
        if prev_target_w > 0 and abs(target_w - prev_target_w) < 5:
            return
        if item.get('max_width'):
            target_w = min(target_w, item['max_width'])
        item['last_target_w'] = target_w
        orig_w, orig_h = original_img.size
        aspect = orig_h / orig_w
        target_h = int(target_w * aspect)
        if item['max_height'] and target_h > item['max_height']:
            target_h = item['max_height']
            target_w = int(target_h / aspect)
        if self.debug_blocks:
            sys.stdout.write(f"DEBUG: Resizing image {os.path.basename(item['path'])}\n")
            sys.stdout.write(f'  Parent width: {parent_w}, Calculated target_w: {target_w}, Target height: {target_h}\n')
            sys.stdout.flush()
        try:
            img_to_resize = original_img
            if img_to_resize.mode in ('P', 'PA', 'L', 'LA', '1'):
                img_to_resize = img_to_resize.convert('RGBA')
            resized_img = img_to_resize.resize((target_w, target_h), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(resized_img)
            label.config(image=photo)
            label.image = photo
        except Exception:
            label.config(text=f"[Image Error: {os.path.basename(item['path'])}]", fg='red')

    @turing_internal
    def setup_label(self, parent, text, font=None, pady=5, padx=0, justify='left', is_title=False):
        """[Internal]
Standardized label creation with automatic wrapping."""
        import tkinter as tk
        has_links = '[' in text and ']' in text and ('(' in text) and (')' in text)
        has_bold = '**' in text
        has_code = '`' in text
        if font is None:
            from src.gui.style import get_label_style as get_label_style
            if is_title:
                font = ('Arial', 22, 'bold')
            else:
                font = get_label_style()
        if has_links or has_bold or has_code:
            return self.add_inline_links(parent, text, base_font=font)
        w = parent.winfo_width()
        if w <= 1:
            if self.root:
                self.root.update_idletasks()
                w = parent.winfo_width()
                if w <= 1:
                    w = self.root.winfo_width()
            if w <= 1:
                w = 450
        label = tk.Label(parent, text=text, font=font, bg=parent.cget('bg'), justify=tk.CENTER if is_title else justify, wraplength=max(50, w - 10))
        label.pack(pady=pady, padx=padx, fill=tk.X)
        if self.debug_blocks:
            label.config(highlightthickness=1, highlightbackground='#ccc')
        if not hasattr(parent, '_resize_bound'):
            parent.bind('<Configure>', self.on_container_resize, add='+')
            parent._resize_bound = True
        return label

    @turing_internal
    def add_inline_links(self, frame, text_content, base_font=None, max_height=10):
        """[Internal]

        Creates a tk.Text widget that supports inline clickable links, bold text,
        and inline/multiline code blocks.
        Supported formats:
          - Links:  [Link Label](https://link.url)
          - Bold:   **bold text**
          - Code:   `code text` or ```...``` or ``...``
        """
        import webbrowser
        import re
        import tkinter as tk
        if base_font is None:
            base_font = get_label_style()
        container = tk.Frame(frame, bg=frame.cget('bg'))
        container.pack(fill=tk.X, expand=True)
        scrollbar = tk.Scrollbar(container)
        text_widget = tk.Text(container, wrap=tk.WORD, font=base_font, padx=0, pady=5, borderwidth=0, highlightthickness=0, bg=frame.cget('bg'), height=1, width=1, yscrollcommand=scrollbar.set)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)
        family = base_font[0] if isinstance(base_font, tuple) else 'Arial'
        size = base_font[1] if isinstance(base_font, tuple) and len(base_font) > 1 else 14
        bold_font = (family, size, 'bold')
        text_widget.tag_config('bold', font=bold_font)
        code_font_size = size - 1
        code_font = ('Menlo', code_font_size)
        text_widget.tag_config('code', font=code_font, background='#e8e8e8', lmargin1=5, lmargin2=5, rmargin=5)
        text_widget.tag_config('inline_code', font=code_font, background='#e8e8e8')
        parts = re.split('(```.*?```|``.*?``|`.*?`|\\*\\*.*?\\*\\*|\\[.*?\\]\\(.*?\\))', text_content, flags=re.DOTALL)
        link_counter = 0
        for p in parts:
            if not p:
                continue
            if p.startswith('[') and '](' in p and p.endswith(')'):
                m = re.match('\\[([^\\]]+)\\]\\(([^)]+)\\)', p)
                if m:
                    link_text, link_url = (m.group(1), m.group(2))
                    link_counter += 1
                    tag_name = f'link_{link_counter}'
                    text_widget.insert(tk.END, link_text, tag_name)
                    text_widget.tag_config(tag_name, foreground='#0066cc', underline=1)
                    text_widget.tag_bind(tag_name, '<Button-1>', lambda e, url=link_url: webbrowser.open(url))
                    text_widget.tag_bind(tag_name, '<Enter>', lambda e, t=text_widget: t.config(cursor='hand2'))
                    text_widget.tag_bind(tag_name, '<Leave>', lambda e, t=text_widget: t.config(cursor=''))
                else:
                    text_widget.insert(tk.END, p)
            elif p.startswith('```') and p.endswith('```') and (len(p) >= 6):
                content = p[3:-3]
                if content.startswith('\n'):
                    content = content[1:]
                else:
                    first_newline = content.find('\n')
                    if first_newline != -1:
                        content = content[first_newline + 1:]
                if content.endswith('\n'):
                    content = content[:-1]
                text_widget.insert(tk.END, '\n')
                lines = content.split('\n')
                for line in lines:
                    text_widget.insert(tk.END, line + '\n', 'code')
                if text_widget.get('end-2c', tk.END) == '\n':
                    text_widget.delete('end-2c', tk.END)

                @turing_internal
                def make_copy_cmd(txt=content):

                    @turing_internal
                    def cmd():
                        try:
                            self.root.clipboard_clear()
                            self.root.clipboard_append(txt)
                            self.root.update()
                        except Exception:
                            pass
                    return cmd
                text_widget.insert(tk.END, '  ', 'code')
                btn = tk.Button(text_widget, text='⎘ Copy', command=make_copy_cmd(), font=(family, max(8, size - 4)), padx=2, pady=0, cursor='hand2')
                text_widget.window_create(tk.END, window=btn)
                text_widget.insert(tk.END, '\n')
            elif p.startswith('``') and p.endswith('``') and (len(p) >= 4):
                content = p[2:-2]
                if content.startswith('\n'):
                    content = content[1:]
                if content.endswith('\n'):
                    content = content[:-1]
                if '\n' in content:
                    text_widget.insert(tk.END, '\n')
                    lines = content.split('\n')
                    for line in lines:
                        text_widget.insert(tk.END, line + '\n', 'code')
                    if text_widget.get('end-2c', tk.END) == '\n':
                        text_widget.delete('end-2c', tk.END)

                    @turing_internal
                    def make_copy_cmd(txt=content):

                        @turing_internal
                        def cmd():
                            try:
                                self.root.clipboard_clear()
                                self.root.clipboard_append(txt)
                                self.root.update()
                            except Exception:
                                pass
                        return cmd
                    text_widget.insert(tk.END, '  ', 'code')
                    btn = tk.Button(text_widget, text='⎘ Copy', command=make_copy_cmd(), font=(family, max(8, size - 4)), padx=2, pady=0, cursor='hand2')
                    text_widget.window_create(tk.END, window=btn)
                    text_widget.insert(tk.END, '\n')
                else:
                    text_widget.insert(tk.END, content, 'inline_code')
            elif p.startswith('`') and p.endswith('`') and (len(p) >= 2):
                content = p[1:-1]
                text_widget.insert(tk.END, content, 'inline_code')
                text_widget.insert(tk.END, ' ')

                @turing_internal
                def make_copy_cmd_inline(txt=content):

                    @turing_internal
                    def cmd(event=None):
                        try:
                            self.root.clipboard_clear()
                            self.root.clipboard_append(txt)
                            self.root.update()
                        except Exception:
                            pass
                    return cmd
                lbl = tk.Label(text_widget, text='⎘', font=('Menlo', max(10, size - 2)), cursor='hand2', bg='#e8e8e8', fg='#555', padx=0, pady=0)
                lbl.bind('<Button-1>', make_copy_cmd_inline())
                text_widget.window_create(tk.END, window=lbl)
            elif p.startswith('**') and p.endswith('**') and (len(p) >= 4):
                text_widget.insert(tk.END, p[2:-2], 'bold')
            else:
                text_widget.insert(tk.END, p)
        if text_widget.get('end-2c', tk.END) == '\n':
            text_widget.delete('end-2c', tk.END)

        @turing_internal
        def prevent_edit(event):
            if (event.state & 4 or event.state & 8) and event.keysym.lower() == 'c':
                return None
            if event.keysym in ('Left', 'Right', 'Up', 'Down'):
                return None
            return 'break'
        text_widget.bind('<Key>', prevent_edit)
        text_widget.bind('<Button-2>', lambda e: 'break')
        text_widget.bind('<Button-3>', lambda e: 'break')
        text_widget.bind('<<Paste>>', lambda e: 'break')

        @turing_internal
        def _update_height(event=None):
            try:
                num_lines = text_widget.count('1.0', 'end', 'displaylines')[0]
                if num_lines:
                    if num_lines > max_height:
                        text_widget.config(height=max_height)
                        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, before=text_widget)
                    else:
                        text_widget.config(height=num_lines)
                        scrollbar.pack_forget()
            except Exception:
                pass
        text_widget.after_idle(_update_height)
        text_widget.bind('<Configure>', _update_height)
        return text_widget

    @turing_internal
    def _copy_code(self, text, text_widget, tag_name):
        """[Internal]
Copy code text to clipboard and briefly flash the copy icon."""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            text_widget.tag_config(tag_name, foreground='#228B22')
            self.root.after(800, lambda: text_widget.tag_config(tag_name, foreground='#999999'))
        except Exception:
            pass

    @turing_internal
    def on_container_resize(self, event):
        """[Internal]
Callback for container <Configure> events to handle dynamic image and text wrapping."""
        prev_w = getattr(event.widget, '_last_config_w', 0)
        if prev_w > 0 and abs(event.width - prev_w) < 5:
            return
        event.widget._last_config_w = event.width
        if hasattr(self, '_resize_timer'):
            self.root.after_cancel(self._resize_timer)
        self._resize_timer = self.root.after(100, self.perform_ui_updates)

    @turing_internal
    def perform_ui_updates(self):
        """[Internal]
Actual resizing logic for images and text wrapping."""
        if self.window_closed or not self.root:
            return
        self.perform_image_resizing()
        self.perform_text_wrapping_updates()

    @turing_internal
    def perform_image_resizing(self):
        """[Internal]
Actual resizing logic for all registered dynamic images."""
        for item in list(self.resizable_images):
            self._resize_single_image(item)

    @turing_internal
    def perform_text_wrapping_updates(self):
        """[Internal]
Updates wraplength for all Labels within blocks to match current width."""
        import tkinter as tk
        if self.window_closed or not self.root:
            return

        @turing_internal
        def update_labels(container):
            for child in container.winfo_children():
                if isinstance(child, tk.Label):
                    try:
                        curr_wrap = child.cget('wraplength')
                        if curr_wrap and int(curr_wrap) > 0:
                            parent_w = container.winfo_width()
                            if parent_w > 10:
                                child.config(wraplength=parent_w - 10)
                    except Exception:
                        pass
                elif isinstance(child, tk.Frame):
                    update_labels(child)
        for block in self.blocks:
            try:
                if block.winfo_exists():
                    update_labels(block)
            except Exception:
                pass

    @turing_internal
    def process_callbacks(self):
        """[Internal]
Process callbacks from other threads (thread-safe UI updates)."""
        if self.window_closed or not self.root:
            return
        try:
            while True:
                callback = self.callback_queue.get_nowait()
                callback()
        except queue.Empty:
            pass
        except Exception:
            pass
        if not self.window_closed and self.root:
            self.root.after(100, self.process_callbacks)

    @io
    @io
    def run(self, setup_func: Callable, on_show: Optional[Callable]=None, custom_id: Optional[str]=None):
        """
    std:docstring
bypass: [io]
    """
        import tkinter as tk
        try:
            if platform.system() == 'Darwin':
                fd = os.open(os.devnull, os.O_WRONLY)
                old_stderr = os.dup(sys.stderr.fileno())
                try:
                    self.root = tk.Tk(className=self.__class__.__name__)
                    self.root.withdraw()
                    self.root.title(self.title)
                    setup_func()
                finally:
                    sys.stderr.flush()
                    os.dup2(old_stderr, sys.stderr.fileno())
                    os.close(fd)
                    os.close(old_stderr)
            else:
                self.root = tk.Tk()
                self.root.title(self.title)
                setup_func()
            self.check_signals()
            self.process_callbacks()
            try:
                instance_dir = self.project_root / 'data' / 'run' / 'instances'
                instance_dir.mkdir(parents=True, exist_ok=True)
                self.instance_file = instance_dir / f'gui_{os.getpid()}.json'
                with open(self.instance_file, 'w') as f:
                    json.dump({'pid': os.getpid(), 'tool_name': self.tool_name, 'title': self.title, 'custom_id': custom_id, 'class': self.__class__.__name__, 'start_time': time.time()}, f)
            except Exception:
                self.instance_file = None
            self.root.protocol('WM_DELETE_WINDOW', lambda: self.finalize('cancelled', self.get_current_state()))
            if on_show is not None:
                self.root.after(100, on_show)
            self.root.lift()
            self.root.attributes('-topmost', True)

            @turing_internal
            def _delayed_focus_and_bell():
                try:
                    if self.window_closed:
                        return
                    self.root.lift()
                    self.root.focus_force()
                    self.root.attributes('-topmost', True)
                    self.root.after(500, lambda: self.root.attributes('-topmost', False) if not self.window_closed else None)
                    self.play_bell()
                    if self.focus_interval > 0:
                        self.start_periodic_focus(self.focus_interval)
                except Exception:
                    pass
            self.root.after(300, _delayed_focus_and_bell)
            if platform.system() == 'Darwin':
                fd = os.open(os.devnull, os.O_WRONLY)
                old_stderr = os.dup(sys.stderr.fileno())
                try:
                    self.root.mainloop()
                finally:
                    sys.stderr.flush()
                    os.dup2(old_stderr, sys.stderr.fileno())
                    os.close(fd)
                    os.close(old_stderr)
            else:
                self.root.mainloop()
            try:
                stops_dir = self.project_root / 'data' / 'run' / 'stops'
                pid = os.getpid()
                for ext in ['stop', 'submit', 'cancel', 'add_time']:
                    f = stops_dir / f'{pid}.{ext}'
                    if f.exists():
                        f.unlink()
            except Exception:
                pass
            if hasattr(self, 'instance_file') and self.instance_file and self.instance_file.exists():
                try:
                    self.instance_file.unlink()
                except Exception:
                    pass
            is_managed = os.environ.get('GDS_GUI_MANAGED') == '1'
            result_line = 'GDS_GUI_RESULT_JSON:' + json.dumps(self.result)
            if is_managed:
                sys.stdout.write('\n' + result_line + '\n')
                sys.stdout.flush()
        except Exception as e:
            if hasattr(self, 'instance_file') and self.instance_file and self.instance_file.exists():
                try:
                    self.instance_file.unlink()
                except Exception:
                    pass
            import traceback
            traceback.print_exc()
            self.result = {'status': 'error', 'message': str(e)}
            result_line = 'GDS_GUI_RESULT_JSON:' + json.dumps(self.result)
            if os.environ.get('GDS_GUI_MANAGED') == '1':
                sys.stdout.write('\n' + result_line + '\n')
                sys.stdout.flush()

@turing_internal
def setup_common_bottom_bar(parent, window_instance: BaseGUIWindow, submit_text: str, submit_cmd: Callable, add_time_increment: int=60) -> Any:
    """[Internal]

    Creates a standardized bottom bar with status, countdown, and buttons.
    Returns: status_label
    """
    import tkinter as tk
    window_instance.add_time_increment = add_time_increment
    bottom_frame = tk.Frame(parent)
    window_instance.bottom_bar_frame = bottom_frame
    bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=(5, 15))
    status_label = tk.Label(bottom_frame, text='', font=get_status_style())
    status_label.pack(side=tk.LEFT)
    submit_btn = tk.Button(bottom_frame, text=submit_text, command=submit_cmd, font=get_button_style(primary=True))
    submit_btn.pack(side=tk.RIGHT)
    if hasattr(window_instance, 'submit_btn'):
        window_instance.submit_btn = submit_btn
    if add_time_increment > 0:
        add_msg = window_instance._('add_time', 'Add {seconds}s', seconds=add_time_increment)

        @turing_internal
        def on_add_time():
            window_instance.trigger_add_time(add_time_increment, status_label)
        window_instance.on_remote_add_time = on_add_time
        add_btn = tk.Button(bottom_frame, text=add_msg, command=on_add_time, font=get_button_style())
        add_btn.pack(side=tk.RIGHT, padx=(0, 10))
        window_instance.add_time_btn = add_btn
    cancel_btn = tk.Button(bottom_frame, text=window_instance._('btn_cancel', 'Cancel'), command=lambda: window_instance.finalize('cancelled', window_instance.get_current_state()), font=get_button_style())
    cancel_btn.pack(side=tk.RIGHT, padx=(0, 10))
    window_instance.cancel_btn = cancel_btn
    return status_label
