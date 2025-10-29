#!/usr/bin/env python3
"""
Google Drive Shell - Remount Manager Module  
处理Google Drive的重新挂载功能
从历史代码中恢复的remount功能实现
"""

import os
import sys
import hashlib
import time
import json

def remount_google_drive(command_identifier=None):
    """
    重新挂载Google Drive的主函数
    
    逻辑流程：
    1. 生成新的mount hash
    2. 创建Python remount脚本  
    3. 显示Tkinter窗口让用户复制并执行脚本
    
    Args:
        command_identifier: 命令标识符
        
    Returns:
        int: 退出码，0表示成功，1表示失败
    """
    try:
        # 导入需要的模块
        try:
            from .path_constants import get_data_dir, get_proj_dir
        except ImportError:
            from path_constants import get_data_dir, get_proj_dir
            
        # 生成新的mount hash
        timestamp = str(int(time.time()))
        mount_hash = hashlib.md5(timestamp.encode()).hexdigest()[:8]
        
        # 获取配置
        config_file = get_data_dir() / "config.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
            constants = config.get('constants', {})
            remote_root = constants.get('REMOTE_ROOT', '/content/drive/MyDrive/REMOTE_ROOT')
            remote_env = constants.get('REMOTE_ENV', '/content/drive/MyDrive/REMOTE_ENV')
        else:
            remote_root = '/content/drive/MyDrive/REMOTE_ROOT'
            remote_env = '/content/drive/MyDrive/REMOTE_ENV'
        
        # 生成Python remount脚本
        python_script = _generate_remount_python_script(
            remote_root=remote_root,
            remote_env=remote_env,
            mount_hash=mount_hash,
            timestamp=timestamp
        )
        
        # 显示Tkinter窗口
        mount_point = "/content/drive"  # 默认挂载点
        result_path = f"/tmp/remount_result_{mount_hash}.json"
        
        success = _show_remount_window(python_script, mount_point, result_path)
        
        if success:
            print("Remount成功！")
            return 0
        else:
            print("Remount取消或失败")
            return 1
            
    except Exception as e:
        print(f"Error: Remount失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


def _generate_remount_python_script(remote_root, remote_env, mount_hash, timestamp):
    """
    生成在远端Colab执行的Python remount脚本
    
    这个脚本会：
    1. 挂载Google Drive
    2. 使用kora库动态获取文件夹ID
    3. 创建mount fingerprint文件
    4. 创建结果文件
    
    Args:
        remote_root: REMOTE_ROOT路径
        remote_env: REMOTE_ENV路径
        mount_hash: 新的mount hash
        timestamp: 时间戳
        
    Returns:
        str: Python脚本内容
    """
    
    mount_point = "/content/drive"
    fingerprint_path = f"{remote_root}/tmp/.gds_mount_fingerprint_{mount_hash}"
    result_path = f"{remote_root}/tmp/remount_result_{timestamp}_{mount_hash}.json"
    
    script = f'''# GDS 动态挂载脚本
import os
import json
from datetime import datetime

print("挂载点: {mount_point}")

# Google Drive挂载
try:
    from google.colab import drive
    drive.mount("{mount_point}", force_remount=True)
    mount_result = "挂载成功"
except Exception as e:
    mount_result = str(e)
    if "Drive already mounted" not in str(e):
        raise

print(f"挂载结果: {{mount_result}}")

# 验证并创建必要目录
remote_root_path = "{mount_point}/MyDrive/REMOTE_ROOT"
remote_env_path = "{mount_point}/MyDrive/REMOTE_ENV"

# 确保目录存在
os.makedirs(remote_root_path, exist_ok=True)
os.makedirs(f"{{remote_root_path}}/tmp", exist_ok=True)
os.makedirs(remote_env_path, exist_ok=True)

# 尝试获取文件夹ID（使用kora库）
remote_root_id = None
remote_env_id = None
remote_root_status = "失败"
remote_env_status = "失败"

try:
    try:
        import kora
    except:
        # 安装并导入kora库
        import subprocess
        subprocess.run(['pip', 'install', 'kora'], check=True, capture_output=True)
    from kora.xattr import get_id

    # 获取REMOTE_ROOT文件夹ID
    if os.path.exists(remote_root_path):
        try:
            remote_root_id = get_id(remote_root_path)
            remote_root_status = f"成功（ID: {{remote_root_id}}）"
        except Exception:
            remote_root_status = "失败"

    # 获取REMOTE_ENV文件夹ID
    if os.path.exists(remote_env_path):
        try:
            remote_env_id = get_id(remote_env_path)
            remote_env_status = f"成功（ID: {{remote_env_id}}）"
        except Exception:
            remote_env_status = "失败"

except Exception:
    remote_root_status = "失败（kora库问题）"
    remote_env_status = "失败（kora库问题）"

print(f"访问REMOTE_ROOT: {{remote_root_status}}")
print(f"访问REMOTE_ENV: {{remote_env_status}}")

# 创建指纹文件（包含挂载签名信息）
fingerprint_data = {{
    "mount_point": "{mount_point}",
    "timestamp": "{timestamp}",
    "hash": "{mount_hash}",
    "remote_root_id": remote_root_id,
    "remote_env_id": remote_env_id,
    "signature": f"{timestamp}_{mount_hash}_{{remote_root_id or 'unknown'}}_{{remote_env_id or 'unknown'}}",
    "created": datetime.now().isoformat(),
    "type": "mount_fingerprint"
}}

fingerprint_file = "{fingerprint_path}"
try:
    with open(fingerprint_file, 'w') as f:
        json.dump(fingerprint_data, f, indent=2)
    print(f"指纹文件已创建: {{fingerprint_file}}")
except Exception as e:
    print(f"指纹文件创建失败: {{e}}")

# 创建结果文件（包含文件夹ID）
result_file = "{result_path}"
try:
    with open(result_file, 'w') as f:
        result_data = {{
            "success": True,
            "mount_point": "{mount_point}",
            "timestamp": "{timestamp}",
            "remote_root": remote_root_path,
            "remote_env": remote_env_path,
            "remote_root_id": remote_root_id,
            "remote_env_id": remote_env_id,
            "fingerprint_signature": fingerprint_data.get("signature"),
            "completed": datetime.now().isoformat(),
            "type": "remount",
            "note": "Dynamic remount with kora folder ID detection and fingerprint"
        }}
        json.dump(result_data, f, indent=2)
    print(f"结果文件已创建: {{result_file}}")
    print("重新挂载流程完成！现在可以使用GDS命令访问Google Drive了！")
    print("✅执行完成")
except Exception as e:
    print(f"结果文件创建失败: {{e}}")
'''
    
    return script


def _show_remount_window(python_script, mount_point, result_path):
    """
    显示Tkinter窗口，让用户复制并执行remount脚本
    
    Args:
        python_script: 要执行的Python脚本
        mount_point: 挂载点路径
        result_path: 结果文件路径
        
    Returns:
        bool: True表示用户确认执行完成，False表示取消
    """
    import subprocess
    import base64
    
    try:
        # 将脚本编码为base64以避免shell转义问题
        script_b64 = base64.b64encode(python_script.encode('utf-8')).decode('ascii')
        
        # 获取音频文件路径
        try:
            from .path_constants import get_proj_dir
            audio_file_path = str(get_proj_dir() / "tkinter_bell.mp3")
        except ImportError:
            from path_constants import get_proj_dir
            audio_file_path = str(get_proj_dir() / "tkinter_bell.mp3")
        
        # 创建subprocess脚本 - 显示Tkinter窗口（使用完整历史UI）
        subprocess_script = f'''
import sys
import os
import base64
import time

# 抑制所有警告和IMK信息
import warnings
warnings.filterwarnings("ignore")

# 设置环境变量抑制tkinter警告
os.environ["TK_SILENCE_DEPRECATION"] = "1"

try:
    import tkinter as tk
    from tkinter import messagebox
    import subprocess
    
    result = False
    
    # 解码脚本
    python_script = base64.b64decode("{script_b64}").decode('utf-8')
    
    root = tk.Tk()
    root.title("GDS Remount")
    root.geometry("500x60")
    root.resizable(False, False)
    root.attributes('-topmost', True)
    
    # 居中窗口
    root.eval('tk::PlaceWindow . center')
    
    # 音频文件路径
    audio_file_path = "{audio_file_path}"
    
    # 定义统一的聚焦函数
    def force_focus():
        try:
            root.focus_force()
            root.lift()
            root.attributes('-topmost', True)
            
            # macOS特定的焦点获取方法
            import platform
            if platform.system() == 'Darwin':
                import subprocess
                try:
                    # 尝试多个可能的应用程序名称
                    app_names = ['Python', 'python3', 'tkinter', 'Tk']
                    for app_name in app_names:
                        try:
                            subprocess.run(['osascript', '-e', 'tell application "' + app_name + '" to activate'], 
                                          timeout=0.5, capture_output=True)
                            break
                        except:
                            continue
                    
                    # 尝试使用系统事件来强制获取焦点
                    applescript_code = "tell application \\\\"System Events\\\\"\\\\n    set frontmost of first process whose name contains \\\\"Python\\\\" to true\\\\nend tell"
                    subprocess.run(['osascript', '-e', applescript_code], timeout=0.5, capture_output=True)
                except:
                    pass  # 如果失败就忽略
        except:
            pass
    
    # 全局focus计数器和按钮点击标志
    focus_count = 0
    button_clicked = False
    
    # 定义音频播放函数
    def play_bell_in_subprocess():
        try:
            audio_path = audio_file_path
            if os.path.exists(audio_path):
                import platform
                import subprocess
                system = platform.system()
                if system == "Darwin":  # macOS
                    subprocess.run(["afplay", audio_path],
                                 capture_output=True, timeout=2)
                elif system == "Linux":
                    # 尝试多个Linux音频播放器
                    players = ["paplay", "aplay", "mpg123", "mpv", "vlc"]
                    for player in players:
                        try:
                            subprocess.run([player, audio_path],
                                         capture_output=True, timeout=2, check=True)
                            break
                        except (subprocess.CalledProcessError, FileNotFoundError):
                            continue
                elif system == "Windows":
                    # Windows可以使用winsound模块或powershell
                    try:
                        subprocess.run(["powershell", "-c",
                                      "(New-Object Media.SoundPlayer '" + audio_path + "').PlaySync()"],
                                     capture_output=True, timeout=2)
                    except:
                        pass
        except Exception:
            pass  # 如果播放失败，忽略错误
    
    # 带focus计数的聚焦函数
    def force_focus_with_count():
        global focus_count, button_clicked
        
        focus_count += 1
        force_focus()
        
        try:
            import threading
            threading.Thread(target=play_bell_in_subprocess, daemon=True).start()
            root.after(100, lambda: trigger_copy_button())
        except Exception:
            pass
    
    # 设置窗口置顶并初始聚焦（第1次，会播放音效）
    root.attributes('-topmost', True)
    force_focus_with_count()
    
    # 自动复制脚本到剪切板
    try:
        root.clipboard_clear()
        root.clipboard_append(python_script)
    except:
        pass
    
    def copy_script():
        global button_clicked
        button_clicked = True
        try:
            subprocess.run(['pbcopy'], input=python_script.encode('utf-8'),
                          capture_output=True)
            
            # 验证复制是否成功
            try:
                clipboard_content = root.clipboard_get()
                if clipboard_content == python_script:
                    copy_btn.config(text="✅复制成功", bg="#4CAF50")
                else:
                    # 复制不完整，重试一次
                    root.clipboard_clear()
                    root.clipboard_append(python_script)
                    copy_btn.config(text="🔄重新复制", bg="#FF9800")
            except Exception as verify_error:
                # 验证失败但复制可能成功，显示已复制
                copy_btn.config(text="已复制", bg="#4CAF50")
            
            root.after(1500, lambda: copy_btn.config(text="📋 复制指令", bg="#2196F3"))
        except Exception as e:
            copy_btn.config(text="Error: 复制失败", bg="#f44336")
    
    def trigger_copy_button():
        """触发复制按钮的点击效果（用于音效播放时自动触发）"""
        try:
            # 模拟按钮点击效果
            copy_btn.config(relief='sunken')
            root.after(50, lambda: copy_btn.config(relief='raised'))
            # 执行复制功能
            copy_script()
        except Exception:
            pass
    
    def execution_completed():
        global result, button_clicked
        button_clicked = True
        result = True
        root.quit()
    
    # 定期重新获取焦点的函数
    def refocus_window():
        global button_clicked
        if not button_clicked:  # 只有在用户未点击按钮时才重新获取焦点
            try:
                # 使用带focus计数的聚焦函数
                force_focus_with_count()
                # 每30秒重新获取焦点并播放音效
                root.after(30000, refocus_window)
            except:
                pass  # 如果窗口已关闭，忽略错误
    
    # 开始定期重新获取焦点 - 每30秒播放音效
    root.after(30000, refocus_window)
    
    # 主框架
    main_frame = tk.Frame(root, padx=10, pady=10)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # 按钮框架
    button_frame = tk.Frame(main_frame)
    button_frame.pack(fill=tk.X, expand=True)
    
    # 复制Python代码按钮（使用与远端指令窗口一致的风格）
    copy_btn = tk.Button(button_frame, text="📋 复制指令", command=copy_script,
                       bg="#2196F3", fg="white", font=("Arial", 9),
                       padx=10, pady=5, relief=tk.RAISED, bd=2)
    copy_btn.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
    
    # 执行完成按钮（使用与远端指令窗口一致的风格）
    complete_btn = tk.Button(button_frame, text="✅执行完成", command=execution_completed,
                           bg="#4CAF50", fg="white", font=("Arial", 9, "bold"),
                           padx=10, pady=5, relief=tk.RAISED, bd=2)
    complete_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    # 设置自动关闭定时器（5分钟）
    def timeout_destroy():
        global result
        result = False
        root.destroy()
    
    root.after(300000, timeout_destroy)  # 5分钟超时
    
    # 运行窗口
    root.mainloop()
    
    # 返回结果
    print("success" if result else "cancelled")
    
except Exception as e:
    print("error")
'''
        
        # 运行subprocess窗口，压制所有输出
        result = subprocess.run(
            ['python3', '-c', subprocess_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,  # 完全抑制stderr（包括IMK信息）
            text=True,
            timeout=300  # 5分钟超时
        )
        
        # 检查结果
        window_success = result.returncode == 0 and "success" in result.stdout
        
        return window_success
        
    except Exception as e:
        print(f"Error: 显示remount窗口失败: {e}")
        return False
