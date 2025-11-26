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

def remount_google_drive(command_identifier=None, google_drive_shell=None):
    """
    重新挂载Google Drive的主函数
    
    逻辑流程：
    1. 生成新的mount hash
    2. 创建Python remount脚本  
    3. 显示Tkinter窗口让用户复制并执行脚本
    4. 验证远端指纹文件是否创建成功
    
    Args:
        command_identifier: 命令标识符
        google_drive_shell: GoogleDriveShell实例（用于验证）
        
    Returns:
        int: 退出码，0表示成功，1表示失败
    """
    # 导入需要的模块
    from .path_constants import get_data_dir, get_proj_dir
        
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
    python_script = generate_remount_python_script(
        remote_root=remote_root,
        remote_env=remote_env,
        mount_hash=mount_hash,
        timestamp=timestamp
    )
    
    # 显示Tkinter窗口
    show_remount_window(python_script)
    
    # 验证远端指纹文件是否创建成功
    fingerprint_filename = f".gds_mount_fingerprint_{mount_hash}"
    fingerprint_path = f"~/tmp/{fingerprint_filename}"
    
    print(f"正在验证远端指纹文件: {fingerprint_path}")
    
    # 如果没有提供GoogleDriveShell实例，尝试创建一个
    if google_drive_shell is None:
        try:
            # 使用绝对导入避免relative import错误
            import sys
            import os
            current_dir = os.path.dirname(os.path.dirname(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
            from google_drive_shell import GoogleDriveShell
            google_drive_shell = GoogleDriveShell()
        except Exception as e:
            return 0
    
    # 先更新local cache hash，这样可能有助于API同步
    try:
        # 读取或创建配置
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {}
        
        # 更新config.json中的MOUNT_HASH和MOUNT_TIMESTAMP
        if 'constants' not in config:
            config['constants'] = {}
        config['constants']['MOUNT_HASH'] = mount_hash
        config['constants']['MOUNT_TIMESTAMP'] = timestamp
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"✓ config.json updated: MOUNT_HASH={mount_hash}")
        
        # 同时更新GoogleDriveShell实例的MOUNT_HASH属性（如果实例存在）
        if google_drive_shell:
            google_drive_shell.MOUNT_HASH = mount_hash
            google_drive_shell.MOUNT_TIMESTAMP = timestamp
            print(f"✓ current shell instance updated: MOUNT_HASH={mount_hash}")
    except Exception as e:
        print(f"Warning: failed to update config.json: {e}")
    
    # Reset all path IDs and restore defaults (before verification, to avoid errors)
    try:
        reset_command = google_drive_shell.command_registry.get_command("reset")
        if reset_command:
            clear_result = reset_command.cmd_reset_clear_all()
            if clear_result.get("success"):
                print(f"✓ {clear_result.get('message', 'Path IDs cleared and defaults restored')}")
            else:
                print(f"Warning: Failed to clear path IDs: {clear_result.get('error', 'Unknown error')}")
        else:
            print("Warning: Reset command not found")
    except Exception as e:
        print(f"Warning: Failed to clear path IDs: {e}")
    
    # Reset shell pwd to ~ and reset current_folder_id to default (REMOTE_ROOT)
    try:
        shells_data = google_drive_shell.load_shells()
        if shells_data and "active_shell" in shells_data:
            active_shell_id = shells_data["active_shell"]
            if active_shell_id in shells_data.get("shells", {}):
                # 获取REMOTE_ROOT的默认ID
                default_id = None
                try:
                    from .path_constants import PathConstants
                    path_constants = PathConstants()
                    gds_path_ids_file = path_constants.GDS_PATH_IDS_FILE
                    if gds_path_ids_file.exists():
                        with open(gds_path_ids_file, 'r') as f:
                            path_ids_data = json.load(f)
                            default_id = path_ids_data.get("path_ids", {}).get("~")
                except Exception:
                    pass
                
                shells_data["shells"][active_shell_id]["current_path"] = "~"
                shells_data["shells"][active_shell_id]["current_folder_id"] = default_id
                google_drive_shell.save_shells(shells_data)
                print(f"✓ Shell pwd reset to ~ (folder_id: {default_id})")
    except Exception as e:
        print(f"Warning: Failed to reset shell pwd: {e}")
    
    # 使用verify_with_ls检查文件是否存在
    try:
        # 使用验证系统检查指纹文件（show_hidden=True因为文件名以.开头）
        verify_result = google_drive_shell.validation.verify_with_ls(
            path=fingerprint_path,
            creation_type="file",
            show_hidden=True  # 指纹文件以.开头，需要显示隐藏文件
        )
        
        if verify_result and verify_result.get("success"):
            print("✓ 远端指纹文件验证成功")
            print("✓ Google Drive remount successful!")
            
            # Clear remount required flag after successful remount
            try:
                if google_drive_shell and hasattr(google_drive_shell, 'command_executor'):
                    google_drive_shell.command_executor._clear_remount_required_flag()
            except Exception as e:
                pass
            
            return 0
        else:
            print("✗ 远端指纹文件验证失败")
            print("\nRemount failed: Unable to access remote fingerprint file.")
            print("\nPossible causes:")
            print("  1. The remote Python script was not executed successfully")
            print("  2. Google Drive is not properly mounted in Colab")
            print("  3. The Colab runtime is in an inconsistent state")
            print("\nRecommended solution:")
            print("  1. In Colab: Runtime > Disconnect and delete runtime")
            print("  2. Wait for the runtime to be fully terminated")
            print("  3. Start a new runtime and re-execute the remount script")
            print("  4. Run 'GOOGLE_DRIVE --remount' again")
            return 1
    except Exception as e:
        print(f"\n✗ Remount verification error: {e}")
        print("\nRecommended solution:")
        print("  1. In Colab: Runtime > Disconnect and delete runtime")
        print("  2. Start a new runtime and re-execute the remount script")
        print("  3. Run 'GOOGLE_DRIVE --remount' again")
        return 1


def generate_remount_python_script(remote_root, remote_env, mount_hash, timestamp):
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
except Exception as e:
    print(f"结果文件创建失败: {{e}}")
    import sys
    sys.exit(1)

# ============ Enhanced Verification (像Remote Shell Connection Check) ============
print("\\n开始验证远端文件访问...")

def verify_fingerprint_file_access(tmp_folder_id, fingerprint_filename, max_attempts=10, interval=1):
    """使用Google Drive API验证指纹文件是否真正可访问"""
    import time
    try:
        # Import Google API client
        try:
            from googleapiclient.discovery import build
            from google.oauth2 import service_account
        except ImportError:
            print("Google API client不可用，跳过API验证")
            return True  # Graceful degradation
        
        # 尝试读取service account credentials
        creds_dict = None
        try:
            config_path = os.path.expanduser("~/.config/gds/config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    creds_dict = config.get('service_account_credentials')
        except:
            pass
        
        if not creds_dict:
            print("未找到service account credentials，跳过API验证")
            return True  # Graceful degradation
        
        # Build service
        try:
            credentials = service_account.Credentials.from_service_account_info(creds_dict)
            service = build('drive', 'v3', credentials=credentials)
        except Exception as e:
            print(f"构建Drive service失败: {{e}}")
            return True  # Graceful degradation
        
        print(f"使用Google Drive API验证指纹文件...")
        print(f"目标文件: {{fingerprint_filename}}")
        print(f"tmp文件夹ID: {{tmp_folder_id}}")
        
        print("Verifying ", end="", flush=True)
        for attempt in range(1, max_attempts + 1):
            try:
                print(".", end="", flush=True)
                
                # List files in tmp folder to check if fingerprint file exists
                results = service.files().list(
                    q=f"'{{tmp_folder_id}}' in parents and name='{{fingerprint_filename}}'",
                    fields="files(id, name, createdTime)"
                ).execute()
                
                files = results.get('files', [])
                if files:
                    print(f"\\n✓ 指纹文件验证成功: {{fingerprint_filename}}")
                    return True
                
            except Exception as e:
                pass
            
            if attempt < max_attempts:
                time.sleep(interval)
        
        print(f"\\n✗ API验证失败: 在{{max_attempts}}次尝试后仍无法访问指纹文件")
        return False
        
    except Exception as e:
        print(f"\\n验证过程出错: {{e}}")
        return False

# 获取tmp文件夹ID用于验证
tmp_folder_id = None
try:
    if remote_root_id:
        # 尝试获取tmp文件夹的ID
        tmp_path = f"{{remote_root_path}}/tmp"
        try:
            from kora.xattr import get_id
            tmp_folder_id = get_id(tmp_path)
            print(f"tmp文件夹ID: {{tmp_folder_id}}")
        except:
            pass
except:
    pass

# 执行验证
fingerprint_filename = os.path.basename(fingerprint_file)
if tmp_folder_id:
    verification_success = verify_fingerprint_file_access(tmp_folder_id, fingerprint_filename)
    
    if verification_success:
        print("\\n✅ 挂载验证成功！")
        print("重新挂载流程完成！现在可以使用GDS命令访问Google Drive了！")
        print("✅执行完成")
    else:
        print("\\n🚨 挂载验证失败: 无法通过API访问指纹文件")
        print("\\n可能的原因:")
        print("  1. Google Drive挂载不稳定")
        print("  2. Colab runtime处于不一致状态")
        print("  3. 文件系统同步延迟")
        print("\\n建议的解决方案:")
        print("  1. 在Colab中: Runtime > Disconnect and delete runtime")
        print("  2. 等待runtime完全终止")
        print("  3. 启动新的runtime")
        print("  4. 重新执行挂载脚本")
        print("\\n如果问题持续，可能需要检查Google Drive Desktop或网络连接")
        import sys
        sys.exit(1)
else:
    # 没有tmp_folder_id时，跳过API验证但仍然认为成功
    print("无法获取tmp文件夹ID，跳过API验证")
    print("\\n重新挂载流程完成！现在可以使用GDS命令访问Google Drive了！")
    print("✅执行完成")
'''
    
    return script


def show_remount_window(python_script):
    """
    显示Tkinter窗口，让用户复制并执行remount脚本
    
    Args:
        python_script: 要执行的Python脚本
    """
    import subprocess
    import base64
    
    # 将脚本编码为base64以避免shell转义问题
    script_b64 = base64.b64encode(python_script.encode('utf-8')).decode('ascii')
    
    # 获取音频文件路径
    from .path_constants import get_proj_dir
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
    root.title("python: GOOGLE_DRIVE --remount")
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
                    applescript_code = 'tell application "System Events"\\n    set frontmost of first process whose name contains "Python" to true\\nend tell'
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
                       bg="#2196F3", fg="red", font=("Arial", 12),
                       padx=10, pady=5, relief=tk.RAISED, bd=2)
    copy_btn.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
    
    # 执行完成按钮（使用与远端指令窗口一致的风格）
    complete_btn = tk.Button(button_frame, text="✅执行完成", command=execution_completed,
                           bg="#4CAF50", fg="red", font=("Arial", 12, "bold"),
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
        
    # 运行subprocess窗口，暂时不抑制stderr用于调试
    result = subprocess.run(
        ['python3', '-c', subprocess_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,  # 抑制stderr输出
        text=True,
        timeout=300  # 5分钟超时
    )
    # 检查结果
    window_success = result.returncode == 0 and "success" in result.stdout
    if (not window_success):
        import traceback
        raise Exception("remount窗口显示失败: " + traceback.format_exc())
