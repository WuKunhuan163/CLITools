"""
Command Generator Module
从 remote_commands.py 重构而来
"""

import os
import json
import time
import subprocess

class CommandGenerator:
    """重构后的command_generator功能"""

    def __init__(self, drive_service=None, main_instance=None):
        self.drive_service = drive_service
        self.main_instance = main_instance
    
    def _check_bash_syntax(self, script_content):
        """
        检查bash脚本语法
        
        Args:
            script_content (str): 要检查的bash脚本内容
            
        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            import subprocess
            import tempfile
            import os
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as temp_file:
                temp_file.write(script_content)
                temp_file_path = temp_file.name
            
            try:
                # 使用bash -n检查语法
                result = subprocess.run(
                    ['bash', '-n', temp_file_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    return True, None
                else:
                    return False, result.stderr.strip()
                    
            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                    
        except Exception as e:
            return False, f"Syntax check failed: {str(e)}"

    def calculate_command_hash(self, cmd):
        """
        计算命令的hash值
        
        Args:
            cmd (str): 用户命令字符串
            
        Returns:
            str: 8字符的hash值（小写）
        """
        import hashlib
        window_hash = hashlib.md5(cmd.encode()).hexdigest()[:8]
        # print(f"[DEBUG] 计算窗口hash: {window_hash.upper()} (命令: {cmd[:80]}...)")
        return window_hash


    def generate_command(self, cmd, result_filename=None, current_shell=None):
        """
        统一的JSON结果生成接口 - 为任何用户命令生成包含JSON结果的远程脚本
        
        Args:
            cmd (str): 用户要执行的完整命令
            result_filename (str, optional): 指定的结果文件名，如果不提供则自动生成
            current_shell (dict, optional): 当前shell信息，用于路径解析
            
        Returns:
            tuple: (远端命令字符串, 结果文件名, 命令hash)
        """

        import time
        cmd_hash = self.calculate_command_hash(cmd)
        
        # 生成统一JSON命令
        import shlex
        from datetime import datetime
        if '!' in cmd and len(cmd) < 200 and not cmd.strip().startswith('#'):
            print(f"Warning: Command contains exclamation marks which may cause shell history expansion issues.")
            print(f"Original command: {cmd}")
            cleaned_command = cmd.replace('!', '')
            print(f"Cleaned command: {cleaned_command}")
            print(f"Suggestion: Avoid using '!' in commands to prevent shell history expansion errors.")
            cmd = cleaned_command
        
        # 检测和处理printf格式字符问题
        # 如果命令以printf开头且包含%字符，需要特殊处理避免格式指令错误
        if cmd.strip().startswith('printf '):
            import re
            # 匹配printf命令的模式: printf "content" 或 printf 'content'
            printf_pattern = r'^printf\s+(["\'])(.*?)\1(.*)$'
            match = re.match(printf_pattern, cmd.strip())
            if match:
                quote_char = match.group(1)
                content = match.group(2)
                rest_args = match.group(3).strip()  # 可能包含重定向等
                
                # 检查内容是否包含%字符（可能导致格式指令问题）
                if '%' in content:
                    # 转换为安全的printf "%s" "content"格式
                    safe_command = f'printf "%s" {quote_char}{content}{quote_char}'
                    if rest_args:
                        safe_command += f' {rest_args}'
                    cmd = safe_command
        
        # 检测和处理echo命令中的转义序列问题
        # 确保echo命令能正确处理\n和\t等转义序列
        if cmd.strip().startswith('echo '):
            import re
            # 匹配echo命令的模式: echo "content" 或 echo 'content'
            echo_pattern = r'^echo\s+(["\'])(.*?)\1(.*)$'
            match = re.match(echo_pattern, cmd.strip())
            if match:
                quote_char = match.group(1)
                content = match.group(2)
                rest_args = match.group(3).strip()  # 可能包含重定向等
                
                # 检查内容是否包含转义序列
                if '\\n' in content or '\\t' in content:
                    # 添加-e标志以启用转义序列解释
                    safe_command = f'echo -e {quote_char}{content}{quote_char}'
                    if rest_args:
                        safe_command += f' {rest_args}'
                    cmd = safe_command
        
        
        # 路径替换：将用户命令中的~替换为REMOTE_ROOT
        if '~' in cmd:
            cmd = cmd.replace('~', self.main_instance.REMOTE_ROOT)
            import re
            pattern = f"'({re.escape(self.main_instance.REMOTE_ROOT)}[^']*?)'"
            def remove_quotes_if_safe(match):
                path = match.group(1)
                if ' ' not in path and not any(c in path for c in ['&', '|', ';', '(', ')', '<', '>', '$', '`']):
                    return path
                return match.group(0)  # 保持原样
            cmd = re.sub(pattern, remove_quotes_if_safe, cmd)
        
        # 获取当前路径
        if current_shell:
            current_path = current_shell.get("current_path", "~")
            is_background = current_shell.get("_background_mode", False)
            bg_pid = current_shell.get("_background_pid", "")
            bg_original_cmd = current_shell.get("_background_original_cmd", "")
        else:
            current_path = "~"
            is_background = False
            bg_pid = ""
            bg_original_cmd = ""
        
        
        # 使用统一的路径解析接口
        remote_path = self.main_instance.path_resolver.resolve_remote_absolute_path(current_path, current_shell)
        
        # 生成结果文件名（如果未提供）
        if not result_filename:
            if is_background:
                result_filename = f"cmd_main_{bg_pid}.result.json"
            else: 
                timestamp = str(int(time.time()))
                result_filename = f"cmd_{timestamp}_{cmd_hash}.json"
        
        result_path = f"{self.main_instance.REMOTE_ROOT}/tmp/{result_filename}"
        
        # 预计算所有需要的值，避免f-string中的复杂表达式
        timestamp = str(int(time.time()))
        
        # 根据是否为background模式生成不同的远程命令脚本
        # 检查是否为背景任务
        if is_background:
            import shlex
            start_time = datetime.now().isoformat()
            
            # 使用常量定义background文件名
            BG_STATUS_FILE = get_bg_status_file(bg_pid)
            BG_SCRIPT_FILE = get_bg_script_file(bg_pid)
            BG_LOG_FILE = get_bg_log_file(bg_pid)
            BG_RESULT_FILE = get_bg_result_file(bg_pid)
                            
            # 创建后台管理脚本内容
            background_manager_content = f'''#!/bin/bash
# Background Task Manager for {bg_pid}

# 确保工作目录存在并切换到正确的基础目录
mkdir -p "{remote_path}"
cd "{remote_path}"

# 确保tmp目录存在
mkdir -p "{self.main_instance.REMOTE_ROOT}/tmp"

# 创建后台执行脚本
cat > "{self.main_instance.REMOTE_ROOT}/tmp/{BG_SCRIPT_FILE}" << 'SCRIPT_EOF'
#!/bin/bash
set -e

# 首先创建初始的result.json文件，状态为running
python3 << 'INITIAL_RESULT_EOF'
import json
import os
from datetime import datetime

result = {{
"status": "running",
"pid": "{bg_pid}",
"command": {shlex.quote(bg_original_cmd)},
"start_time": "{start_time}",
"stdout": "",
"stderr": "",
"exit_code": None,
"working_dir": os.getcwd(),
"timestamp": datetime.now().isoformat()
}}

with open("{self.main_instance.REMOTE_ROOT}/tmp/{BG_RESULT_FILE}", "w", encoding="utf-8") as f:
json.dump(result, f, indent=2, ensure_ascii=False)
INITIAL_RESULT_EOF

# 执行用户命令并捕获输出（同时写入log文件以便实时查看）
STDOUT_FILE="{self.main_instance.REMOTE_ROOT}/tmp/{bg_pid}_stdout.tmp"
STDERR_FILE="{self.main_instance.REMOTE_ROOT}/tmp/{bg_pid}_stderr.tmp"
LOG_FILE="{self.main_instance.REMOTE_ROOT}/tmp/{BG_LOG_FILE}"

# 使用tee将输出同时写入临时文件和log文件
# 使用heredoc避免复杂的引号转义问题
bash << 'USER_COMMAND_EOF' 2>&1 | tee "$LOG_FILE" > "$STDOUT_FILE"
{bg_original_cmd[1:-1] if bg_original_cmd.startswith('"') and bg_original_cmd.endswith('"') else bg_original_cmd}
USER_COMMAND_EOF
EXIT_CODE=${{PIPESTATUS[0]}}

# 分离stdout和stderr（从log文件中提取）
# 由于使用了2>&1，所有输出都在stdout中，stderr为空
cp "$STDOUT_FILE" "$STDOUT_FILE.bak"
touch "$STDERR_FILE"

# 生成后台任务的JSON结果文件
python3 << 'PYTHON_EOF'
import json
import os
from datetime import datetime

try:
exit_code = int(os.environ.get('EXIT_CODE', '0'))

# 读取实际的命令输出
stdout_content = ""
stderr_content = ""

stdout_file = "{self.main_instance.REMOTE_ROOT}/tmp/{bg_pid}_stdout.tmp"
stderr_file = "{self.main_instance.REMOTE_ROOT}/tmp/{bg_pid}_stderr.tmp"

if os.path.exists(stdout_file):
    try:
        with open(stdout_file, "r", encoding="utf-8", errors="ignore") as f:
            stdout_content = f.read().rstrip('\\n')
    except Exception:
        stdout_content = ""

if os.path.exists(stderr_file):
    try:
        with open(stderr_file, "r", encoding="utf-8", errors="ignore") as f:
            stderr_content = f.read().rstrip('\\n')
    except Exception:
        stderr_content = ""

result = {{
    "status": "completed",
    "pid": "{bg_pid}",
    "command": {shlex.quote(bg_original_cmd)},
    "start_time": "{start_time}",
    "end_time": datetime.now().isoformat(),
    "stdout": stdout_content,
    "stderr": stderr_content,
    "exit_code": exit_code,
    "working_dir": os.getcwd(),
    "timestamp": datetime.now().isoformat()
}}

with open("{self.main_instance.REMOTE_ROOT}/tmp/{BG_RESULT_FILE}", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

# 清理临时文件
if os.path.exists(stdout_file):
    os.remove(stdout_file)
if os.path.exists(stderr_file):
    os.remove(stderr_file)
    
except Exception as e:
print(f"ERROR: Failed to generate JSON result: {{e}}", file=sys.stderr)
sys.exit(1)
PYTHON_EOF
SCRIPT_EOF

# 给脚本执行权限并启动后台任务
chmod +x "{self.main_instance.REMOTE_ROOT}/tmp/{BG_SCRIPT_FILE}"
nohup "{self.main_instance.REMOTE_ROOT}/tmp/{BG_SCRIPT_FILE}" < /dev/null > "{self.main_instance.REMOTE_ROOT}/tmp/{BG_LOG_FILE}" 2>&1 &
REAL_PID=$!

# 验证background任务文件是否被正确创建
sleep 1  # 等待文件系统同步
if [ -f "{self.main_instance.REMOTE_ROOT}/tmp/{BG_RESULT_FILE}" ]; then
echo "Background task started with ID: {bg_pid}"
echo "Command: {bg_original_cmd}"
echo ""
echo "Run the following commands to track the background task status:"
echo "  GDS --bg --status {bg_pid}    # Check task status"
echo "  GDS --bg --result {bg_pid}    # View task result"
echo "  GDS --bg --log {bg_pid}       # View task log"
echo "  GDS --bg --cleanup {bg_pid}   # Clean up task files"
else
echo "Error: Background task creation failed - status file not found"
exit 1
fi
'''

            # 主程序：创建后台管理进程并立即返回，同时生成主程序的JSON结果
            remote_command = f'''# Background任务启动脚本 - 主程序立即返回
# 确保基础目录存在
mkdir -p "{self.main_instance.REMOTE_ROOT}/tmp"

# 创建后台任务管理脚本
cat > "{self.main_instance.REMOTE_ROOT}/tmp/bg_manager_{bg_pid}.sh" << 'MANAGER_EOF'
{background_manager_content}
MANAGER_EOF

# 给管理脚本执行权限
chmod +x "{self.main_instance.REMOTE_ROOT}/tmp/bg_manager_{bg_pid}.sh"

# 启动后台管理进程
nohup "{self.main_instance.REMOTE_ROOT}/tmp/bg_manager_{bg_pid}.sh" > "{self.main_instance.REMOTE_ROOT}/tmp/bg_manager_{bg_pid}.log" 2>&1 &

# 主程序立即返回消息
echo "Background task manager started for ID: {bg_pid}"
echo "Task creation is proceeding in background..."

# 统一的执行完成提示
clear && echo "✅执行完成"
echo "Command hash: {cmd_hash.upper()}"

# 立即生成主程序的JSON结果文件（用于本地wait and read）
cd "{self.main_instance.REMOTE_ROOT}"
export TIMESTAMP="{timestamp}"
export HASH="{cmd_hash}"
python3 << 'MAIN_JSON_EOF'
import json
import os
from datetime import datetime

# 构建主程序执行结果
result = {{
"cmd": "background_task_created",
"working_dir": os.getcwd(),
"timestamp": datetime.now().isoformat(),
"exit_code": 0,
"stdout": "",
"stderr": ""
}}

# 写入主程序结果文件（注意：这是主程序的结果文件，不是背景任务的结果文件）
result_file = "{self.main_instance.REMOTE_ROOT}/tmp/{result_filename}"
result_dir = os.path.dirname(result_file)
if result_dir:
os.makedirs(result_dir, exist_ok=True)

with open(result_file, "w", encoding="utf-8") as f:
json.dump(result, f, indent=2, ensure_ascii=False)
MAIN_JSON_EOF'''
        else:
            # 普通模式：使用原有的统一JSON生成脚本
            remote_command = f'''
# 确保工作目录存在并切换到正确的基础目录
mkdir -p "{remote_path}"
cd "{remote_path}" && {{
    # 确保tmp目录存在
    mkdir -p "{self.main_instance.REMOTE_ROOT}/tmp"
    
    # 执行用户命令并捕获输出
    TIMESTAMP="{timestamp}"
    HASH="{cmd_hash}"
    OUTPUT_FILE="{self.main_instance.REMOTE_ROOT}/tmp/cmd_stdout_${{TIMESTAMP}}_${{HASH}}"
    ERROR_FILE="{self.main_instance.REMOTE_ROOT}/tmp/cmd_stderr_${{TIMESTAMP}}_${{HASH}}"
    EXITCODE_FILE="{self.main_instance.REMOTE_ROOT}/tmp/cmd_exitcode_${{TIMESTAMP}}_${{HASH}}"
    
    # 直接执行用户命令，捕获输出和错误
    set +e  # 允许命令失败
    # 忽略SIGPIPE信号以避免broken pipe错误
    trap '' PIPE
    bash << 'USER_COMMAND_EOF' > "$OUTPUT_FILE" 2> "$ERROR_FILE"
{cmd}
USER_COMMAND_EOF
    EXIT_CODE=$?
    echo "$EXIT_CODE" > "$EXITCODE_FILE"
    set -e
    
    # 显示stderr内容（如果有）
    if [ -s "$ERROR_FILE" ]; then
        cat "$ERROR_FILE" >&2
    fi
    
    # 统一的执行完成提示
    clear && echo "✅执行完成"
    echo "Command hash: {cmd_hash.upper()}"
    
    # 生成JSON结果文件
    export EXIT_CODE=$EXIT_CODE
    export TIMESTAMP=$TIMESTAMP
    export HASH=$HASH
    python3 << 'JSON_SCRIPT_EOF'
import json
import os
import sys
from datetime import datetime

# 从环境变量获取文件路径参数
timestamp = os.environ.get('TIMESTAMP', '{timestamp}')
hash_val = os.environ.get('HASH', '{cmd_hash}')

# 构建文件路径
stdout_file = f"{self.main_instance.REMOTE_ROOT}/tmp/cmd_stdout_{{timestamp}}_{{hash_val}}"
stderr_file = f"{self.main_instance.REMOTE_ROOT}/tmp/cmd_stderr_{{timestamp}}_{{hash_val}}"
exitcode_file = f"{self.main_instance.REMOTE_ROOT}/tmp/cmd_exitcode_{{timestamp}}_{{hash_val}}"

# 读取输出文件
stdout_content = ""
stderr_content = ""

if os.path.exists(stdout_file):
try:
    with open(stdout_file, "r", encoding="utf-8", errors="ignore") as f:
        stdout_content = f.read()
except Exception as e:
    stdout_content = f"ERROR: 无法读取stdout文件: {{e}}"
else:
stdout_content = ""

if os.path.exists(stderr_file):
try:
    with open(stderr_file, "r", encoding="utf-8", errors="ignore") as f:
        stderr_content = f.read()
except Exception as e:
    stderr_content = f"ERROR: 无法读取stderr文件: {{e}}"
else:
stderr_content = ""

# 读取退出码
exit_code = int(os.environ.get('EXIT_CODE', '0'))

# 构建统一的结果JSON格式
result = {{
"cmd": "remote_command_executed",
"working_dir": os.getcwd(),
"timestamp": datetime.now().isoformat(),
"exit_code": exit_code,
"stdout": stdout_content,
"stderr": stderr_content
}}

# 写入结果文件
result_file = "{result_path}"
result_dir = os.path.dirname(result_file)
if result_dir:
os.makedirs(result_dir, exist_ok=True)

with open(result_file, "w", encoding="utf-8") as f:
json.dump(result, f, indent=2, ensure_ascii=False)


JSON_SCRIPT_EOF
    
    # 清理临时文件
    rm -f "$OUTPUT_FILE" "$ERROR_FILE" "$EXITCODE_FILE"
}}'''
        
        
        # 检查生成的完整脚本语法（包括wrapper部分）
        is_valid, error_msg = self._check_bash_syntax(remote_command)
        if not is_valid:
            print(f"Error: Bash syntax error detected in generated remote script:")
            print(f"Error: {error_msg}")
            print(f"Script content preview:")
            print(remote_command[:500] + "..." if len(remote_command) > 500 else remote_command)
            print(f"Full script length: {len(remote_command)} characters")
            raise Exception(f"Generated remote script has syntax errors: {error_msg}")
        
        # 最终生成的remote_command
        return remote_command, result_filename, cmd_hash

    def generate_commands(self, file_moves, target_path, folder_upload_info=None):
        """
        生成远程命令

        Args:
            file_moves (list): 文件移动信息列表
            target_path (str): 目标路径
            folder_upload_info (dict, optional): 文件夹上传信息

        Returns:
            str: 生成的远程命令
        """
        try:
            # 准备文件移动信息
            all_file_moves = []
            for file_move in file_moves:
                all_file_moves.append({
                    "filename": file_move["filename"],
                    "original_filename": file_move.get("original_filename", file_move["filename"]),
                    "renamed": file_move.get("renamed", False),
                    "target_path": target_path
                })

            # 调用多文件远程命令生成方法
            base_command = self._generate_multi_file_commands(all_file_moves)

            # 如果是文件夹上传，需要添加解压和清理命令
            if folder_upload_info and folder_upload_info.get("is_folder_upload", False):
                zip_filename = folder_upload_info.get("zip_filename", "")
                keep_zip = folder_upload_info.get("keep_zip", False)

                if zip_filename:
                    # 使用统一的路径解析接口
                    current_shell = self.main_instance.get_current_shell()
                    remote_target_path = self.main_instance.path_resolver.resolve_remote_absolute_path(target_path, current_shell)

                    # 生成解压命令 - 使用统一函数
                    # generate_unzip_command现在是类方法
                    unzip_command = self.generate_unzip_command(
                        remote_target_path, 
                        zip_filename, 
                        delete_zip=not keep_zip,
                        handle_empty_zip=True
                    )

                    # 将解压命令添加到基础命令之后
                    combined_command = f"{base_command}\n\n# 解压和清理zip文件\n({unzip_command})"
                    return combined_command

            return base_command

        except Exception as e:
            return f"# Error generating remote commands: {e}"


    def generate_command_interface(self, cmd, args, current_shell):
        """
        生成远端执行命令 - 现在使用统一的JSON生成接口

        Args:
            cmd (str): 命令名称
            args (list): 命令参数
            current_shell (dict): 当前shell信息

        Returns:
            tuple: (远端命令字符串, 结果文件名)
        """
        try:
            # 构建完整的用户命令
            if args:
                # 处理特殊命令格式
                if cmd == "bash" and len(args) >= 2 and args[0] == "-c":
                    # 修复：使用shlex.quote来安全处理包含引号的命令
                    import shlex
                    safe_command = shlex.quote(args[1])
                    cmd = f'bash -c {safe_command}'
                elif cmd == "sh" and len(args) >= 2 and args[0] == "-c":
                    cmd = f'sh -c "{args[1]}"'
                elif cmd in ["python", "python3"] and len(args) >= 2 and args[0] == "-c":
                    # 对于python -c命令，使用base64编码避免转义问题
                    import base64
                    python_code = args[1]
                    python_code_b64 = base64.b64encode(python_code.encode('utf-8')).decode('ascii')
                    cmd = f'{cmd} -c "import base64; exec(base64.b64decode(\'{python_code_b64}\').decode(\'utf-8\'))"'
                elif cmd in ["python", "python3"] and len(args) == 1:
                    # 对于直接的python代码执行（如测试中的格式），转换为python -c格式
                    import base64
                    python_code = args[0]
                    python_code_b64 = base64.b64encode(python_code.encode('utf-8')).decode('ascii')
                    cmd = f'{cmd} -c "import base64; exec(base64.b64decode(\'{python_code_b64}\').decode(\'utf-8\'))"'
                else:
                    # 处理重定向和其他参数
                    import shlex
                    if '>' in args:
                        # 处理重定向：将参数分为命令部分和重定向部分
                        redirect_index = args.index('>')
                        cmd_args = args[:redirect_index]
                        target_file = args[redirect_index + 1] if redirect_index + 1 < len(args) else None

                        if target_file:
                            if cmd_args:
                                # 对命令参数进行适当的引号处理，避免引号冲突
                                quoted_args = []
                                for arg in cmd_args:
                                    # 智能引号处理：优先使用双引号，避免与外层单引号冲突
                                    if '"' not in arg:
                                        quoted_args.append(f'"{arg}"')
                                    elif "'" not in arg:
                                        quoted_args.append(f"'{arg}'")
                                    else:
                                        # 如果同时包含单引号和双引号，使用shlex.quote
                                        quoted_args.append(shlex.quote(arg))
                                cmd = f"{cmd} {' '.join(quoted_args)} > {target_file}"
                            else:
                                cmd = f"{cmd} > {target_file}"
                        else:
                            cmd = f"{cmd} {' '.join(args)}"
                    else:
                        # 处理~路径展开和智能引号处理
                        processed_args = []
                        for arg in args:
                            if arg == "~":
                                processed_args.append(f'"{self.main_instance.REMOTE_ROOT}"')
                            elif arg.startswith("~/"):
                                processed_args.append(f'"{self.main_instance.REMOTE_ROOT}/{arg[2:]}"')
                            else:
                                # 智能引号处理：优先使用双引号，避免与外层单引号冲突
                                if '"' not in arg:
                                    processed_args.append(f'"{arg}"')
                                elif "'" not in arg:
                                    processed_args.append(f"'{arg}'")
                                else:
                                    # 如果同时包含单引号和双引号，使用shlex.quote
                                    processed_args.append(shlex.quote(arg))
                        cmd = f"{cmd} {' '.join(processed_args)}"
            else:
                cmd = cmd

            # 计算hash并使用统一的JSON生成接口
            return self.generate_command(cmd, current_shell)

        except Exception as e:
            raise Exception(f"Generate remote command failed: {str(e)}")


    def generate_mkdir_commands(self, target_path):
        """
        生成创建远端目录结构的命令

        Args:
            target_path (str): 目标路径

        Returns:
            str: mkdir 命令字符串，如果不需要创建目录则返回空字符串
        """
        try:
            # 如果是当前目录或根目录，不需要创建
            if target_path == "." or target_path == "" or target_path == "~":
                return ""

            # 计算需要创建的目录路径
            if target_path.startswith("/"):
                # 绝对路径
                full_target_path = target_path
            else:
                # 相对路径，基于 REMOTE_ROOT
                full_target_path = f"{self.main_instance.REMOTE_ROOT}/{target_path.lstrip('/')}"

            # 生成 mkdir -p 命令来创建整个目录结构，添加清屏和成功/失败提示
            mkdir_command = f'mkdir -p "{full_target_path}"'

            return mkdir_command

        except Exception as e:
            print(f"Error: Generate mkdir command failed: {e}")
            return ""




    def _generate_multi_file_commands(self, all_file_moves):
        """生成简化的多文件上传远端命令，只显示关键状态信息"""
        try:
            # 生成文件信息数组 - 保留原有的路径解析逻辑
            file_info_list = []
            for i, file_info in enumerate(all_file_moves):
                filename = file_info["filename"]  # 重命名后的文件名（在DRIVE_EQUIVALENT中）
                original_filename = file_info.get("original_filename", filename)  # 原始文件名（目标文件名）
                target_path = file_info["target_path"]

                # 计算目标绝对路径 - 使用original_filename作为最终文件名
                target_filename = original_filename

                if target_path == "." or target_path == "":
                    # 当前目录
                    current_shell = self.main_instance.get_current_shell()
                    if current_shell and current_shell.get("current_path") != "~":
                        current_path = current_shell.get("current_path", "~")
                        if current_path.startswith("~/"):
                            relative_path = current_path[2:]
                            target_absolute = f"{self.main_instance.REMOTE_ROOT}/{relative_path}" if relative_path else self.main_instance.REMOTE_ROOT
                        else:
                            target_absolute = self.main_instance.REMOTE_ROOT
                    else:
                        target_absolute = self.main_instance.REMOTE_ROOT
                    dest_absolute = f"{target_absolute.rstrip('/')}/{target_filename}"
                else:
                    # 使用统一的路径解析接口
                    current_shell = self.main_instance.get_current_shell()
                    target_absolute = self.main_instance.path_resolver.resolve_remote_absolute_path(target_path, current_shell)
                    dest_absolute = f"{target_absolute.rstrip('/')}/{target_filename}"

                # 源文件路径使用重命名后的文件名
                source_absolute = f"{self.main_instance.DRIVE_EQUIVALENT}/{filename}"

                file_info_list.append({
                    'source': source_absolute,
                    'dest': dest_absolute,
                    'original_filename': original_filename
                })

            # 收集所有需要创建的目录
            target_dirs = set()
            for file_info in file_info_list:
                dest_dir = '/'.join(file_info['dest'].split('/')[:-1])
                target_dirs.add(dest_dir)

            # 生成简化的命令 - 按照用户要求的格式
            mv_commands = []
            for file_info in file_info_list:
                mv_commands.append(f'mv "{file_info["source"]}" "{file_info["dest"]}"')

            # 创建目录命令
            mkdir_commands = [f'mkdir -p "{target_dir}"' for target_dir in sorted(target_dirs)]

            # 组合所有命令
            all_commands = mkdir_commands + mv_commands
            command_summary = f"mkdir + mv {len(file_info_list)} files"

            # 创建实际命令的显示列表 - 保持引号显示
            actual_commands_display = []
            if mkdir_commands:
                actual_commands_display.extend(mkdir_commands)
            actual_commands_display.extend(mv_commands)

            # 生成重试命令
            retry_commands = []
            for cmd in mv_commands:
                # 提取文件名用于显示
                try:
                    filename = cmd.split('"')[3].split('/')[-1] if len(cmd.split('"')) > 3 else 'file'
                except:
                    filename = 'file'

                # 提取源文件和目标文件路径用于debug
                try:
                    cmd_parts = cmd.split('"')
                    source_path = cmd_parts[1] if len(cmd_parts) > 1 else "unknown_source"
                    dest_path = cmd_parts[3] if len(cmd_parts) > 3 else "unknown_dest"
                except:
                    source_path = "unknown_source"
                    dest_path = "unknown_dest"

                retry_cmd = f'''
for attempt in $(seq 1 30); do
    if {cmd} 2>/dev/null; then
        break
    elif [ "$attempt" -eq 30 ]; then
        echo "Error: Error: {filename} move failed, still failed after 30 retries" >&2
        exit 1
    else
        sleep 1
    fi
done'''
                retry_commands.append(retry_cmd)

            # 生成简化的脚本，包含视觉分隔和实际命令显示
            script = f'''

# 创建目录
{chr(10).join(mkdir_commands)}

# 移动文件（带重试机制）
{chr(10).join(retry_commands)}

clear
echo "✅执行完成"'''

            return script

        except Exception as e:
            return f'echo "Error: 生成命令失败: {e}"'


    def generate_unzip_command(self, remote_target_path, zip_filename, delete_zip=True, handle_empty_zip=True):
        """
        统一生成解压命令的工具函数，消除重复代码
        
        Args:
            remote_target_path: 远程目标路径
            zip_filename: zip文件名
            delete_zip: 是否删除zip文件
            handle_empty_zip: 是否处理空zip文件的警告
        
        Returns:
            str: 生成的解压命令
        """
        if handle_empty_zip:
            # 处理空zip文件警告的版本：过滤掉"zipfile is empty"警告，但不影响实际执行结果
            if delete_zip:
                unzip_command = f'cd "{remote_target_path}" && echo "Start decompressing {zip_filename}" && (unzip -o "{zip_filename}" 2>&1 | grep -v "zipfile is empty" || true) && echo "=== 删除zip ===" && rm "{zip_filename}" && echo "Verifying decompression result ..." && ls -la'
            else:
                unzip_command = f'cd "{remote_target_path}" && echo "Start decompressing {zip_filename}" && (unzip -o "{zip_filename}" 2>&1 | grep -v "zipfile is empty" || true) && echo "Verifying decompression result ..." && ls -la'
        else:
            # 原始版本（保持向后兼容）
            if delete_zip:
                unzip_command = f'cd "{remote_target_path}" && echo "Start decompressing {zip_filename}" && unzip -o "{zip_filename}" && echo "=== 删除zip ===" && rm "{zip_filename}" && echo "Verifying decompression result ..." && ls -la'
            else:
                unzip_command = f'cd "{remote_target_path}" && echo "Start decompressing {zip_filename}" && unzip -o "{zip_filename}" && echo "Verifying decompression result ..." && ls -la'
        
        return unzip_command
