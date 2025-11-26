"""
Google Drive Shell - Command Generator Module

This module provides comprehensive command generation functionality for the Google Drive Shell system.
It handles the creation, formatting, and optimization of remote shell commands with support for
various command types, path expansion, and execution contexts.

Key Features:
- Remote shell command generation and formatting
- Path expansion with bash integration for proper ~ and @ handling
- Multi-file operation command generation (mv, mkdir, etc.)
- Background task command generation and management
- Command syntax validation and error checking
- Integration with remote shell environments
- Support for complex command chaining and piping

Command Types:
- File operations: mv, cp, mkdir, rm commands
- Path operations: Path expansion and resolution
- Background tasks: Long-running command management
- Batch operations: Multi-file and multi-directory commands

Generation Flow:
1. Parse command requirements and parameters
2. Apply path expansion and resolution
3. Generate appropriate shell command syntax
4. Validate command syntax and structure
5. Optimize for remote execution environment
6. Return formatted command ready for execution

Classes:
    CommandGenerator: Main command generation engine

Dependencies:
    - Bash shell integration for path expansion
    - Remote shell management for execution context
    - Path resolution for proper directory handling
    - Background task management for long operations
    - Syntax validation for command correctness

Migrated from: remote_commands.py (refactored for better modularity)
"""

import re, os, subprocess, hashlib, tempfile
import base64, time, re, shlex
from .config_loader import get_bg_script_file, get_bg_log_file, get_bg_result_file
from .debug_logger import debug_log

class CommandGenerator:
    """重构后的command_generator功能"""

    def __init__(self, drive_service=None, main_instance=None):
        self.drive_service = drive_service
        self.main_instance = main_instance
    
    @staticmethod
    def translate_remote_to_local(path):
        """
        将远端路径格式转换回本地路径格式
        
        在通用路径处理中，所有的~路径会被假设为远端路径并展开为/content/drive/MyDrive/REMOTE_ROOT/...
        但是对于某些命令（如upload、download），某些参数实际上是本地路径，需要转换回本地格式。
        
        转换规则：
        1. /content/drive/MyDrive/REMOTE_ROOT/... -> ~/... -> /Users/xxx/...
           (将REMOTE_ROOT替换为~，然后展开为绝对路径)
        2. /content/drive/MyDrive/REMOTE_ENV/... -> @/...
           
        Args:
            path (str): 可能是远端格式的路径
            
        Returns:
            str: 本地格式的路径
        """
        if not path:
            return path
        
        if path.startswith('/content/drive/MyDrive/REMOTE_ROOT/'):
            # 将 REMOTE_ROOT 替换为 ~
            remaining_path = path[len('/content/drive/MyDrive/REMOTE_ROOT/'):]
            if remaining_path:
                tilde_path = '~/' + remaining_path
            else:
                tilde_path = '~'
            
            # 使用 os.path.expanduser 将 ~ 展开为绝对路径
            return os.path.expanduser(tilde_path)
                
        elif path.startswith('/content/drive/MyDrive/REMOTE_ENV/'):
            # Remote env paths: /content/.../REMOTE_ENV/xxx -> @/xxx
            remaining_path = path[len('/content/drive/MyDrive/REMOTE_ENV/'):]
            return '@/' + remaining_path if remaining_path else '.'
        
        # Path is already in local format
        return path
    
    def check_bash_syntax(self, script_content):
        """
        检查bash脚本语法
        
        Args:
            script_content (str): 要检查的bash脚本内容
            
        Returns:
            tuple: (is_valid, error_message)
        """
        try:
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
        window_hash = hashlib.md5(cmd.encode()).hexdigest()[:8]
        return window_hash
    
    def expand_paths_with_bash(self, cmd, placeholder, placeholder_value):
        """
        使用bash展开路径，支持自定义placeholder
        不使用split，使用特殊字符保护系统来处理
        
        Args:
            cmd: 原始命令字符串
            placeholder: 要替换的占位符（如'~'或'@'）
            placeholder_value: placeholder的目标值（如'/Users/xxx/tmp'或'/content/drive/MyDrive/REMOTE_ENV'）
        
        Returns:
            展开后的命令字符串
        """
        from modules.path_resolver import PathResolver
        import subprocess
        import os
        import uuid
        
        # 如果命令中不包含placeholder，直接返回
        if placeholder not in cmd:
            return cmd
        
        # 步骤1: 保护所有特殊字符（包括多个连续空格、引号、重定向符等）
        protected_cmd, special_phs = PathResolver.protect_special_chars(cmd)
        
        # 步骤2: 保护原始的~（如果placeholder不是~）
        if placeholder == '~':
            tilde_placeholder = None
            cmd_for_bash = protected_cmd
        else:
            tilde_placeholder = f"__TILDE_PH_{uuid.uuid4().hex[:8].upper()}__"
            cmd_for_bash = protected_cmd.replace('~', tilde_placeholder)
        
        # 步骤3: 将placeholder替换成~，以便bash展开
        cmd_for_bash = cmd_for_bash.replace(placeholder, '~')
        
        # 步骤4: 用bash展开路径
        # 注意：不能用引号包裹cmd_for_bash，否则~不会被展开
        # 因为特殊字符已经被placeholder保护了，所以不用担心空格等问题
        bash_cmd = f"echo {cmd_for_bash}"
        result = subprocess.run(
            ['bash', '-c', bash_cmd],
            capture_output=True,
            text=True,
            timeout=2
        )
        expanded_cmd = result.stdout.strip()
        
        # 步骤5: 将展开的home目录替换为placeholder_value
        home_dir = os.path.expanduser('~')
        expanded_cmd = expanded_cmd.replace(home_dir, placeholder_value)
        
        # 步骤6: 恢复tilde_placeholder
        if tilde_placeholder:
            expanded_cmd = expanded_cmd.replace('~', placeholder)
            expanded_cmd = expanded_cmd.replace(tilde_placeholder, '~')
        
        # 步骤7: 恢复所有特殊字符
        expanded_cmd = PathResolver.restore_special_chars(expanded_cmd, special_phs)

        # 步骤8: 处理参数zhi中的路径
        import shlex
        try:
            tokens = shlex.split(expanded_cmd)
            processed_tokens = []
            
            for token in tokens:
                # 检查token是否是 --xxx=value 形式
                if '=' in token and f'{placeholder}/' in token:
                    # 分离参数名和值
                    param_name, param_value = token.split('=', 1)
                    
                    # 如果值包含placeholder，递归展开
                    if placeholder in param_value:
                        # 递归调用展开路径
                        expanded_value = self.expand_paths_with_bash(param_value, placeholder, placeholder_value)
                        processed_token = f"{param_name}={expanded_value}"
                        processed_tokens.append(processed_token)
                    else:
                        processed_tokens.append(token)
                else:
                    processed_tokens.append(token)
            
            # 重新组合命令
            expanded_cmd = ' '.join(processed_tokens)
        except ValueError:
            # shlex split失败，保持原样
            pass
        
        return expanded_cmd
    
    def _expand_single_path_with_bash(self, path_part, placeholder, placeholder_value):
        """
        对单个路径部分进行bash展开，使用统一的placeholder系统保护特殊字符
        
        实现策略：
        1. 保护所有特殊字符（引号、重定向、echo等）
        2. 让bash展开路径
        3. 恢复特殊字符
        4. 严禁fallback - bash展开失败时使用空结果，暴露实际问题
        """
        # 如果不包含placeholder，直接返回
        if placeholder not in path_part:
            return path_part
        
        from modules.path_resolver import PathResolver
        import subprocess
        import os
        import uuid
        
        # 步骤1: 保护所有特殊字符
        protected_part, special_phs = PathResolver.protect_special_chars(path_part)
        
        # 步骤2: 保护原始的~ (如果placeholder不是~)
        if placeholder == '~':
            tilde_placeholder = None
            path_for_bash = protected_part
        else:
            tilde_placeholder = f"__TILDE_PH_{uuid.uuid4().hex[:8].upper()}__"
            path_for_bash = protected_part.replace('~', tilde_placeholder)
            path_for_bash = path_for_bash.replace(placeholder, '~')

        # 步骤3: 用bash展开路径
        # 在传给bash前，先恢复引号，让bash能看到真实的引号结构
        # 这样bash才能正确处理引号内的~展开
        # 只恢复引号placeholder，其他特殊字符（如重定向）仍然保护
        quote_placeholders = {k: v for k, v in special_phs.items() if 'QUOTE' in k}
        path_for_bash_with_quotes = PathResolver.restore_special_chars(path_for_bash, quote_placeholders)
        
        # 使用恢复引号后的命令让bash展开
        bash_cmd = f"echo {path_for_bash_with_quotes}"
        result = subprocess.run(
            ['bash', '-c', bash_cmd],
            capture_output=True,
            text=True,
            timeout=2
        )

        # 步骤4: 使用bash展开结果（即使为空也不fallback，暴露问题）
        expanded_path = result.stdout.strip()
        
        # 步骤5: 将展开的home目录替换为placeholder_value
        home_dir = os.path.expanduser('~')
        expanded_path = expanded_path.replace(home_dir, placeholder_value)
        
        # 步骤6: 恢复tilde_placeholder
        if tilde_placeholder:
            expanded_path = expanded_path.replace('~', placeholder)
            expanded_path = expanded_path.replace(tilde_placeholder, '~')
        
        # 步骤7: 恢复所有特殊字符
        expanded_path = PathResolver.restore_special_chars(expanded_path, special_phs)
        return expanded_path
    
    def _expand_paths_with_bash_legacy(self, cmd, placeholder, placeholder_value):
        """
        原始的expand_paths_with_bash实现，作为fallback
        """
        # 特殊情况：如果placeholder就是~，跳过步骤1（不需要保护原始~）
        if placeholder == '~':
            tilde_placeholder = None
            cmd_for_bash = cmd  # 直接使用原命令，不需要替换
        else:
            # 步骤1: 为原始~生成随机placeholder
            import uuid
            tilde_placeholder = f"TILDE_PH_{uuid.uuid4().hex[:8].upper()}"
            cmd_with_tilde_placeholder = cmd.replace('~', tilde_placeholder)
            
            # 步骤2: 将placeholder替换为~
            cmd_for_bash = cmd_with_tilde_placeholder.replace(placeholder, '~')
        
        # 步骤3: 让bash展开（只展开~，不执行命令）
        # 使用bash -x来获取展开后的命令主体，然后检测并保留重定向部分
        # 注意：在执行前会将本地工作目录改到~/tmp，避免意外创建本地文件
        import subprocess
        import os
        result = subprocess.run(
            ['bash', '-x', '-c', cmd_for_bash],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=os.path.expanduser('~/tmp')  # 在~/tmp中执行，避免在项目目录创建文件
        )
        # bash -x 的输出在stderr中，格式为"+ command"
        if result.stderr:
            lines = result.stderr.strip().split('\n')
            expanded_main = None
            for line in lines:
                if line.startswith('+ '):
                    expanded_main = line[2:]
                    break
            
            if not expanded_main:
                return cmd
            
            # 步骤3.5: 检测重定向部分
            # 如果bash -x的输出比原命令短，说明有重定向被省略了
            # 我们需要从原命令中提取重定向部分
            # 策略：在原命令中找到expanded_main对应的部分，剩余的就是重定向
            # 简单策略：检测常见的重定向操作符
            redirect_operators = ['>', '>>', '<', '2>', '2>>', '&>', '&>>', '2>&1', '|']
            redirect_part = ""
            
            # 遍历原命令（cmd_for_bash），寻找重定向操作符
            for op in redirect_operators:
                if op in cmd_for_bash:
                    op_index = cmd_for_bash.find(op)
                    redirect_part = cmd_for_bash[op_index:]
                    
                    # 对重定向部分也进行路径展开（递归调用bash -x）
                    # 提取重定向符后的路径部分
                    redirect_path_match = re.search(r'[><|&]\s*(.+?)(?:\s+[><|&]|$)', redirect_part)
                    if redirect_path_match:
                        redirect_path = redirect_path_match.group(1).strip()
                        # 对redirect_path进行展开
                        redirect_expand_result = subprocess.run(
                            ['bash', '-x', '-c', f'echo {redirect_path}'],
                            capture_output=True,
                            text=True,
                            timeout=2
                        )
                        if redirect_expand_result.stderr:
                            redirect_lines = redirect_expand_result.stderr.strip().split('\n')
                            for line in redirect_lines:
                                if line.startswith('+ echo '):
                                    expanded_redirect_path = line[7:].strip()  # 去掉"+ echo "
                                    # 替换原redirect_part中的路径
                                    redirect_part = redirect_part.replace(redirect_path, expanded_redirect_path)
                                    break
                    break
            
            expanded_cmd = expanded_main + (' ' + redirect_part if redirect_part else '')
        else:
            return cmd
        
        # 步骤4: 将展开的home目录替换为placeholder_value
        home_dir = os.path.expanduser('~')
        expanded_cmd = expanded_cmd.replace(home_dir, placeholder_value)

        # 步骤5: 将剩余的~（原本是placeholder）换回成placeholder
        # 这些~没有被bash展开（在引号内），需要换回原始的placeholder
        expanded_cmd = expanded_cmd.replace('~', placeholder)
        
        # 步骤6: 将tilde_placeholder换回原始~（如果placeholder不是~的话）
        if tilde_placeholder:
            expanded_cmd = expanded_cmd.replace(tilde_placeholder, '~')
        
        return expanded_cmd

    def generate_command(self, cmd, result_filename=None, current_shell=None, capture_result=True):
        """
        统一的JSON结果生成接口 - 为任何用户命令生成包含JSON结果的远程脚本
        
        Args:
            cmd (str): 用户要执行的完整命令
            result_filename (str, optional): 指定的结果文件名，如果不提供则自动生成
            current_shell (dict, optional): 当前shell信息，用于路径解析
            capture_result (bool): 是否捕获结果（默认True）。False时直接执行命令不生成JSON
            
        Returns:
            tuple: (远端命令字符串, 结果文件名, 命令hash)
        """
        debug_log('command_generator', 'generate_command_input', {
            'cmd': cmd,
            'cmd_length': len(cmd),
            'has_newlines': '\n' in cmd,
            'newline_count': len(cmd.split('\n')) if '\n' in cmd else 0,
            'capture_result': capture_result
        })
        cmd_hash = self.calculate_command_hash(cmd)
        
        # 如果不捕获结果，仍然使用完整模板，但修改user command部分和JSON生成部分
        # （保留shell路径信息等上下文）
        
        # 生成统一JSON命令
        if '!' in cmd and len(cmd) < 200 and not cmd.strip().startswith('#'):
            print(f"Warning: Command contains ! which may cause shell history expansion issues.")
            print(f"Original command: {cmd}")
            cleaned_command = cmd.replace('!', '')
            print(f"Cleaned command: {cleaned_command}")
            cmd = cleaned_command
        
        # 检测和处理printf格式字符问题
        # 如果命令以printf开头且包含%字符，需要特殊处理避免格式指令错误
        if cmd.strip().startswith('printf '):
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
        
        # 获取当前路径
        if current_shell:
            is_background = current_shell.get("_background_mode", False)
            bg_pid = current_shell.get("_background_pid", "")
        else:
            is_background = False
            bg_pid = ""
        
        # 预计算所有需要的值，避免f-string中的复杂表达式
        timestamp = str(int(time.time()))
        
        # 生成结果文件名（如果未提供）
        if not result_filename:
            if is_background:
                result_filename = f"cmd_main_{bg_pid}.result.json"
            else: 
                result_filename = f"cmd_result_{timestamp}_{cmd_hash}.json"
        
        # 根据是否为background模式生成不同的远程命令脚本
        # 检查是否为背景任务
        if is_background:
            result = self.fill_background_command_template(cmd, bg_pid, execute=False, result_filename=result_filename)
            remote_command = result['remote_template']
        else:
            result = self.fill_remote_command_template(cmd, execute=False, result_filename=result_filename, capture_result=capture_result)
            remote_command = result['remote_template']
        
        # 最终生成的remote_command
        return remote_command, result_filename, cmd_hash

    def fill_remote_command_template(self, cmd, execute=False, result_filename=None, capture_result=True):
        """
        暴露远端命令模板生成过程的接口 - 用于调试和探究转译后的命令
        
        这个接口将完整地展示从用户输入的cmd到最终发送到远端的bash脚本的整个转换过程。
        
        Args:
            cmd (str): 用户输入的原始命令
            execute (bool): 是否实际执行远端窗口（默认False，仅返回模板）
            result_filename (str, optional): 指定结果文件名，如果不提供则自动生成
            capture_result (bool): 是否捕获结果JSON（默认True）
        
        Returns:
            dict: {
                'original_cmd': 原始命令,
                'processed_cmd': 处理后的命令（传入模板前）,
                'remote_template': 完整的远端bash脚本模板,
                'result_filename': 结果文件名,
                'cmd_hash': 命令hash,
                'execution_result': 执行结果（如果execute=True）,
                'template_snippet': 关键的heredoc模板片段（用于分析）
            }
        """
        import time
        
        # 记录原始命令
        original_cmd = cmd
        timestamp = str(int(time.time()))
        cmd_hash = self.calculate_command_hash(cmd)
        if result_filename is None:
            result_filename = f"cmd_result_{timestamp}_{cmd_hash}.json"

        debug_log('command_generator', 'template_cmd_input', {
            'cmd': cmd,
            'cmd_repr': repr(cmd),
            'cmd_length': len(cmd),
            'backslash_count': cmd.count('\\'),
            'contains_newline_escape': '\\n' in cmd
        })
        result_path = f"{self.main_instance.REMOTE_ROOT}/tmp/{result_filename}"
        remote_path = self.main_instance.REMOTE_ROOT
        
        # 获取当前shell路径用于相对路径解析
        current_shell = self.main_instance.get_current_shell()
        shell_path = current_shell.get("current_path", "~") if current_shell else "~"
        shell_absolute_path = self.main_instance.resolve_remote_absolute_path(shell_path, current_shell) if current_shell else f"{self.main_instance.REMOTE_ROOT}"
        
        # print(f"User command preview [in f-string]: ")
        # print("=====================")
        # print(cmd)
        # print("=====================")
        # print("\nRemote real output: ")
        # print("=====================")
        # exit(0)

        # 根据capture_result生成不同的模板
        if not capture_result:
            # 不捕获结果：保留shell路径信息，直接执行命令，不生成JSON
            remote_command = f'''
# 确保工作目录存在并切换到正确的基础目录
mkdir -p "{remote_path}"
cd "{remote_path}" && {{
    # 尝试切换到当前shell路径以支持相对路径
    if cd "{shell_absolute_path}" 2>/dev/null; then
        # 清屏并执行用户命令（输出直接显示在终端）
        clear
        {cmd}
    else
        echo "Error: Shell working directory does not exist: {shell_absolute_path}"
        exit 1
    fi
}}'''
        else:
            # 捕获结果：完整模板（原有逻辑）
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
    
    # 尝试切换到当前shell路径以支持相对路径
    # 检查shell路径是否存在，如果不存在则报错
    if ! cd "{shell_absolute_path}" 2>"$ERROR_FILE"; then
        echo "Error: Shell working directory does not exist: {shell_absolute_path}" > "$ERROR_FILE"
        echo "1" > "$EXITCODE_FILE"
        # 跳过用户命令执行
    else
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
    fi
    
    # 统一的执行完成提示
    clear && echo "✅执行完成"
    echo "Command hash: {cmd_hash.upper()}"
    
    # 生成JSON结果文件
    # 确保EXIT_CODE有值，如果为空则设为1（表示错误）
    EXIT_CODE=${{EXIT_CODE:-1}}
    export EXIT_CODE
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
        is_valid, error_msg = self.check_bash_syntax(remote_command)
        if not is_valid:
            print(f"Error: Bash syntax error detected in generated remote script. ")
            raise Exception(f"Generated remote script has syntax errors: {error_msg}")
        
        import re
        heredoc_match = re.search(r'bash << \'USER_COMMAND_EOF\'.*?USER_COMMAND_EOF', remote_command, re.DOTALL)
        template_snippet = heredoc_match.group(0) if heredoc_match else "未找到heredoc"
        
        # 构建返回结果
        result = {
            'original_cmd': original_cmd,
            'processed_cmd': cmd,  # 将在填充代码后更新
            'remote_template': remote_command,
            'result_filename': result_filename,
            'cmd_hash': cmd_hash,
            'template_snippet': template_snippet,
            'execution_result': None
        }
        
        # 如果需要执行
        if execute:
            execution_result = self.main_instance.command_executor.execute_command(
                remote_command, 
                result_filename, 
                cmd_hash, 
                raw_command=cmd
            )
            result['execution_result'] = execution_result
        
        return result

    def fill_background_command_template(self, cmd, bg_pid=None, execute=False, result_filename=None):
        """
        暴露后台模式远端命令模板生成过程的接口
        
        Args:
            cmd (str): 用户输入的原始命令
            bg_pid (str, optional): 后台任务PID，如果不提供则自动生成
            execute (bool): 是否实际执行远端窗口（默认False，仅返回模板）
            result_filename (str, optional): 指定结果文件名
        
        Returns:
            dict: {
                'original_cmd': 原始命令,
                'bg_pid': 后台任务PID,
                'bg_script_file': 后台脚本文件名,
                'bg_log_file': 后台日志文件名,
                'bg_result_file': 后台结果文件名,
                'remote_template': 完整的远端bash脚本模板,
                'result_filename': 结果文件名,
                'execution_result': 执行结果（如果execute=True）,
                'template_snippet': 关键的heredoc模板片段（用于分析）
            }
        """
        import time
        from datetime import datetime
        import shlex
        import re
        
        # 记录原始命令
        original_cmd = cmd
        
        # 生成后台任务相关信息
        if bg_pid is None:
            bg_pid = f"bg_{int(time.time())}_{os.getpid()}"
        
        timestamp = str(int(time.time()))
        cmd_hash = self.calculate_command_hash(cmd)
        
        if result_filename is None:
            result_filename = f"cmd_main_{bg_pid}.result.json"
        
        # 获取远端路径和时间
        start_time = datetime.now().isoformat()
        remote_path = self.main_instance.REMOTE_ROOT
        bg_original_cmd = cmd  # 用于后台命令
        
        # 使用常量定义background文件名
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

# 合并创建log文件和初始result.json文件，确保文件在任务开始时就存在
# 将command作为环境变量传递，避免在Python代码中处理复杂的引号转义
export BG_COMMAND={shlex.quote(bg_original_cmd)}
python3 << 'INITIAL_SETUP_EOF'
import json
import os
import sys
from datetime import datetime

# 首先创建log文件
log_file = "{self.main_instance.REMOTE_ROOT}/tmp/{BG_LOG_FILE}"
with open(log_file, "w", encoding="utf-8") as f:
    pass  # 创建空文件

# 然后创建初始result.json文件
# 从环境变量读取command，避免在代码中直接插入包含换行符的字符串
bg_command = os.environ.get("BG_COMMAND", "")

result = {{
"status": "running",
"pid": "{bg_pid}",
"command": bg_command,
"start_time": "{start_time}",
"stdout": "",
"stderr": "",
"exit_code": None,
"working_dir": os.getcwd(),
"timestamp": datetime.now().isoformat()
}}

with open("{self.main_instance.REMOTE_ROOT}/tmp/{BG_RESULT_FILE}", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
    
INITIAL_SETUP_EOF

# 执行用户命令并捕获输出（同时写入log文件以便实时查看）
STDOUT_FILE="{self.main_instance.REMOTE_ROOT}/tmp/{bg_pid}_stdout.tmp"
STDERR_FILE="{self.main_instance.REMOTE_ROOT}/tmp/{bg_pid}_stderr.tmp"
LOG_FILE="{self.main_instance.REMOTE_ROOT}/tmp/{BG_LOG_FILE}"

# 执行用户命令并捕获输出
# 由于外层重定向，所有输出都会进入log文件，所以简化tee逻辑
bash << 'USER_COMMAND_EOF' 2>&1 | tee "$STDOUT_FILE"
{bg_original_cmd[1:-1] if bg_original_cmd.startswith('"') and bg_original_cmd.endswith('"') else bg_original_cmd}
USER_COMMAND_EOF
EXIT_CODE=${{PIPESTATUS[0]}}

# 分离stdout和stderr（从log文件中提取）
# 由于使用了2>&1，所有输出都在stdout中，stderr为空
cp "$STDOUT_FILE" "$STDOUT_FILE.bak"
touch "$STDERR_FILE"

# 生成后台任务的JSON结果文件
# 使用环境变量传递command
python3 << 'PYTHON_EOF'
import json
import os
import sys
from datetime import datetime

try:
    exit_code = int(os.environ.get('EXIT_CODE', '0'))

    # 从环境变量读取command
    bg_command = os.environ.get("BG_COMMAND", "")

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
        "command": bg_command,
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
# 将所有输出重定向到log文件，但修改脚本内部逻辑来避免tee冲突
nohup "{self.main_instance.REMOTE_ROOT}/tmp/{BG_SCRIPT_FILE}" < /dev/null > "{self.main_instance.REMOTE_ROOT}/tmp/{BG_LOG_FILE}" 2>&1 &
REAL_PID=$!

# 验证background任务文件是否被正确创建（增加等待时间和重试逻辑）
MAX_WAIT=10
for i in $(seq 1 $MAX_WAIT); do
    if [ -f "{self.main_instance.REMOTE_ROOT}/tmp/{BG_RESULT_FILE}" ]; then
        echo "Background task started with ID: {bg_pid}"
        echo "Command: {bg_original_cmd}"
        echo ""
        echo "Run the following commands to track the background task:"
        echo "  GDS --bg --status {bg_pid}    # Check task status"
        echo "  GDS --bg --result {bg_pid}    # View task result"
        echo "  GDS --bg --log {bg_pid}       # View task log"
        echo "  GDS --bg --cleanup {bg_pid}   # Clean up task files"
        exit 0
    fi
    sleep 1
done

# 如果10秒后还没创建，报错
echo "Error: Background task creation failed - result file not created after ${{MAX_WAIT}} seconds"
echo "This may indicate a problem with the background task script execution"
exit 1
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

        # 提取关键的heredoc模板片段
        import re
        heredoc_match = re.search(r'bash << \'USER_COMMAND_EOF\'.*?USER_COMMAND_EOF', remote_command, re.DOTALL)
        template_snippet = heredoc_match.group(0) if heredoc_match else "未找到heredoc"
        
        # 构建返回结果
        result = {
            'original_cmd': original_cmd,
            'bg_pid': bg_pid,
            'bg_script_file': BG_SCRIPT_FILE,
            'bg_log_file': BG_LOG_FILE,
            'bg_result_file': BG_RESULT_FILE,
            'remote_template': remote_command,
            'result_filename': result_filename,
            'execution_result': None,
            'template_snippet': template_snippet
        }
        
        # 如果需要执行
        if execute:
            execution_result = self.main_instance.command_executor.execute_command(
                remote_command, 
                result_filename, 
                cmd_hash, 
                raw_command=cmd
            )
            result['execution_result'] = execution_result
        
        return result

    def generate_mv_commands(self, file_moves, target_path, folder_upload_info=None, force=False):
        """
        生成远程命令

        Args:
            file_moves (list): 文件移动信息列表
            target_path (str): 目标路径
            folder_upload_info (dict, optional): 文件夹上传信息
            force (bool): 是否强制覆盖现有文件

        Returns:
            str: 生成的远程命令
        """
        all_file_moves = []
        for file_move in file_moves:
            all_file_moves.append({
                "filename": file_move["filename"],
                "original_filename": file_move.get("original_filename", file_move["filename"]),
                "renamed": file_move.get("renamed", False),
                "target_path": target_path
            })

        # 调用多文件远程命令生成方法
        base_command = self.generate_multi_file_commands(all_file_moves, force=force)

        # 如果是文件夹上传，需要添加解压和清理命令
        if folder_upload_info and folder_upload_info.get("is_folder_upload", False):
            zip_filename = folder_upload_info.get("zip_filename", "")
            keep_zip = folder_upload_info.get("keep_zip", False)

            if zip_filename: 
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
                combined_command = f"{base_command}\n\n# 解压和清理zip文件\n({unzip_command})"
                return combined_command

        return base_command


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
        if args:
            # 处理特殊命令格式
            if cmd == "bash" and len(args) >= 2 and args[0] == "-c":
                safe_command = shlex.quote(args[1])
                cmd = f'bash -c {safe_command}'
            elif cmd == "sh" and len(args) >= 2 and args[0] == "-c":
                cmd = f'sh -c "{args[1]}"'
            elif cmd in ["python", "python3"] and len(args) >= 2 and args[0] == "-c":
                python_code = args[1]
                python_code_b64 = base64.b64encode(python_code.encode('utf-8')).decode('ascii')
                cmd = f'{cmd} -c "import base64; exec(base64.b64decode(\'{python_code_b64}\').decode(\'utf-8\'))"'
            elif cmd in ["python", "python3"] and len(args) == 1:
                python_code = args[0]
                python_code_b64 = base64.b64encode(python_code.encode('utf-8')).decode('ascii')
                cmd = f'{cmd} -c "import base64; exec(base64.b64decode(\'{python_code_b64}\').decode(\'utf-8\'))"'
            else:
                if '>' in args:
                    redirect_index = args.index('>')
                    cmd_args = args[:redirect_index]
                    target_file = args[redirect_index + 1] if redirect_index + 1 < len(args) else None
                    if target_file:
                        if cmd_args:
                            quoted_args = []
                            for arg in cmd_args:
                                if '"' not in arg:
                                    quoted_args.append(f'"{arg}"')
                                elif "'" not in arg:
                                    quoted_args.append(f"'{arg}'")
                                else:
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
                            if '"' not in arg:
                                processed_args.append(f'"{arg}"')
                            elif "'" not in arg:
                                processed_args.append(f"'{arg}'")
                            else:
                                processed_args.append(shlex.quote(arg))
                    cmd = f"{cmd} {' '.join(processed_args)}"
        else:
            cmd = cmd

        return self.generate_command(cmd, current_shell)

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

    def generate_multi_file_commands(self, all_file_moves, force=False):
        """生成简化的多文件上传远端命令，只显示关键状态信息
        
        Args:
            all_file_moves (list): 文件移动信息列表
            force (bool): 是否强制覆盖现有文件
        """
        try:
            # 生成文件信息数组 - 保留原有的路径解析逻辑
            file_info_list = []
            for i, file_info in enumerate(all_file_moves):
                filename = file_info["filename"]  # 重命名后的文件名（在DRIVE_EQUIVALENT中）
                original_filename = file_info.get("original_filename", filename)  # 原始文件名（目标文件名）
                target_path = file_info["target_path"]
                current_shell = self.main_instance.get_current_shell()
                
                # target_path现在已经是调用方解析好的绝对路径，直接使用
                # 不再进行二次解析（避免路径重复问题，如~/tmp/~/tmp/...）
                target_absolute = target_path
                
                # 修复：mv命令的目标应该是目录路径，不包含文件名
                dest_directory = target_absolute.rstrip('/')
                source_absolute = f"{self.main_instance.DRIVE_EQUIVALENT}/{filename}"
                file_info_list.append({
                    'source': source_absolute,
                    'dest': dest_directory,  # 使用目录路径而不是完整文件路径
                    'original_filename': original_filename,
                    'renamed': filename != original_filename  # 文件是否被重命名
                })

            # 收集所有需要创建的目录
            target_dirs = set()
            for file_info in file_info_list:
                # 现在dest已经是目录路径，直接使用
                dest_dir = file_info['dest']
                target_dirs.add(dest_dir)

            # 生成简化的命令 - 按照用户要求的格式
            mv_commands = []
            for file_info in file_info_list:
                source_file = file_info["source"]
                dest_dir = file_info["dest"]
                current_filename = source_file.split('/')[-1]  # 当前文件名（可能已重命名）
                original_filename = file_info['original_filename']  # 原始文件名（期望的最终文件名）
                renamed = file_info['renamed']  # 是否已被重命名
                
                # 如果force=True且文件被重命名，需要特殊处理
                if force and renamed:
                    # 1. 先删除目标位置的旧文件（如果存在）
                    target_file_path = f"{dest_dir}/{original_filename}"
                    mv_commands.append(f'rm -f "{target_file_path}"')
                    # 2. 移动文件到目标目录
                    mv_commands.append(f'mv "{source_file}" "{dest_dir}"')
                    # 3. 在目标目录内重命名回原始文件名
                    renamed_file_in_dest = f"{dest_dir}/{current_filename}"
                    mv_commands.append(f'mv "{renamed_file_in_dest}" "{target_file_path}"')
                elif renamed:
                    # 普通模式但文件已被重命名：智能处理
                    # 1. 检查目标目录中是否存在原名文件
                    # 2. 如果不存在，移动后改回原名
                    # 3. 如果存在，检查是否存在当前重命名后的文件名，如果也存在则继续重命名
                    target_original = f"{dest_dir}/{original_filename}"
                    target_renamed = f"{dest_dir}/{current_filename}"
                    
                    # 解析文件名和扩展名
                    if '.' in original_filename:
                        base_name = original_filename.rsplit('.', 1)[0]
                        ext = '.' + original_filename.rsplit('.', 1)[1]
                    else:
                        base_name = original_filename
                        ext = ''
                    
                    # 生成智能重命名逻辑的bash脚本
                    rename_logic = f'''
# 智能重命名逻辑：先检查目标目录中的冲突，再决定最终文件名
if [ ! -f "{target_original}" ]; then
    # 情况1：目标目录中不存在原名文件，直接改回原名
    mv "{source_file}" "{target_original}"
elif [ ! -f "{target_renamed}" ]; then
    # 情况2：目标目录中存在原名文件，但不存在当前重命名后的文件名，保持重命名后的名字
    mv "{source_file}" "{target_renamed}"
else
    # 情况3：目标目录中既存在原名文件，又存在重命名后的文件名，需要继续重命名
    counter=2
    while [ -f "{dest_dir}/{base_name}_${{counter}}{ext}" ]; do
        counter=$((counter + 1))
    done
    mv "{source_file}" "{dest_dir}/{base_name}_${{counter}}{ext}"
fi'''
                    mv_commands.append(rename_logic.strip())
                else:
                    # 普通模式且文件未被重命名：直接移动
                    mv_commands.append(f'mv "{source_file}" "{dest_dir}"')

            # 创建目录命令
            mkdir_commands = [f'mkdir -p "{target_dir}"' for target_dir in sorted(target_dirs)]

            # 创建实际命令的显示列表 - 保持引号显示
            actual_commands_display = []
            if mkdir_commands:
                actual_commands_display.extend(mkdir_commands)
            actual_commands_display.extend(mv_commands)

            # 生成重试命令
            retry_commands = []
            for i, cmd in enumerate(mv_commands):
                try:
                    # 尝试从命令中提取文件名用于错误消息
                    if '"' in cmd:
                        filename = cmd.split('"')[3].split('/')[-1] if len(cmd.split('"')) > 3 else 'file'
                    else:
                        filename = f'file_{i}'
                except:
                    filename = f'file_{i}'

                # 如果命令包含换行符（多行命令），直接执行不加重试（逻辑已经足够健壮）
                if '\n' in cmd:
                    # 多行命令：直接添加
                    retry_commands.append(cmd)
                else:
                    # 单行命令：添加重试逻辑
                    retry_cmd = f'''
for attempt in $(seq 1 30); do
    if {cmd} 2>/dev/null; then
        break
    elif [ "$attempt" -eq 30 ]; then
        echo "Error: {filename} move failed, still failed after 30 retries" >&2
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
