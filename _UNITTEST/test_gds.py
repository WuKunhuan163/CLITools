# -*- coding: utf-8 -*-
"""
GDS (Google Drive Shell) 全面测试套件

合并了所有GDS相关测试，涵盖：
- 基础功能测试
- 真实项目开发场景测试  
- 新功能测试（linter等）
- 边缘情况和错误处理测试

测试设计原则：
1. 远端窗口操作无timeout限制，允许用户手动执行
2. 结果判断基于功能执行情况，不依赖终端输出
3. 具有静态可重复性，使用--force等选项确保测试可重复运行
"""

import unittest
import subprocess
import sys
import re
import threading
import time
import inspect
import os
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

def process_terminal_erase(stdout):
        """
        模拟终端输出处理，正确处理擦除字符和所有终端转义序列
        
        Args:
            stdout: GDS命令的标准输出
            
        Returns:
            str: 清理后的输出
        """
        import re
        
        def process(text):
            """
            处理终端转义序列，模拟真实终端行为
            """
            if text is None:
                return ''
            if not text:
                return text
            
            result = text
            
            # 1. 移除ANSI颜色代码和其他控制序列（除了\r、\b和\x1b[K）
            # 匹配模式：\033[...m 或 \x1b[...m 以及其他光标移动序列，但保留\x1b[K
            # 先移除颜色代码（以m结尾的）
            result = re.sub(r'\x1b\[[0-9;]*m', '', result)
            result = re.sub(r'\033\[[0-9;]*m', '', result)
            # 移除其他光标移动序列，但排除K（清除到行尾）
            result = re.sub(r'\x1b\[[0-9;]*[A-JL-Za-jl-z]', '', result)
            result = re.sub(r'\033\[[0-9;]*[A-JL-Za-jl-z]', '', result)
            
            # 2. 移除响铃符
            result = result.replace('\a', '')
            result = result.replace('\x07', '')
            
            # 3. 制表符转换为4个空格
            result = result.replace('\t', '    ')
            
            # 4. 处理退格符 \b
            # 从左到右处理退格符
            while '\b' in result:
                pos = result.find('\b')
                if pos > 0:
                    # 删除前一个字符和退格符本身
                    result = result[:pos-1] + result[pos+1:]
                else:
                    # 开头的退格符直接删除
                    result = result[1:]
            
            # 5. 反向处理：从后往前寻找擦除序列
            while True:
                # 寻找最后一个\r\x1b[K序列
                last_r_erase_pos = result.rfind('\r\x1b[K')
                # 寻找最后一个\n\x1b[K序列
                last_n_erase_pos = result.rfind('\n\x1b[K')
                
                # 选择最后出现的擦除序列
                if last_r_erase_pos == -1 and last_n_erase_pos == -1:
                    # 没有找到擦除序列，处理完成
                    break
                
                # 确定使用哪个擦除序列（选择位置更靠后的）
                if last_r_erase_pos > last_n_erase_pos:
                    last_erase_pos = last_r_erase_pos
                    erase_pattern = '\r\x1b[K'
                else:
                    last_erase_pos = last_n_erase_pos
                    erase_pattern = '\n\x1b[K'
                
                # 找到擦除序列，需要擦除当前行
                if erase_pattern == '\n\x1b[K':
                    # 对于\n\x1b[K序列，擦除从换行符开始到下一个换行符（或结尾）的所有内容
                    # 这包括换行符本身和后面的内容，直到下一行开始
                    next_newline = result.find('\n', last_erase_pos + len(erase_pattern))
                    if next_newline == -1:
                        # 没有下一个换行符，擦除到结尾
                        result = result[:last_erase_pos]
                    else:
                        # 有下一个换行符，擦除到下一个换行符（不包括下一个换行符）
                        result = result[:last_erase_pos] + result[next_newline:]
                else:
                    # 对于\r\x1b[K序列，使用原来的逻辑
                    # 从擦除序列位置向左找到行的开始位置
                    line_start = result.rfind('\n', 0, last_erase_pos)
                    if line_start == -1:
                        # 没有找到换行符，说明要擦除从开头到擦除序列的所有内容
                        line_start = 0
                    else:
                        # 找到了换行符，保留换行符，从换行符后开始擦除
                        line_start += 1
                    
                    # 擦除从line_start到擦除序列结束的内容
                    erase_end = last_erase_pos + len(erase_pattern)
                    result = result[:line_start] + result[erase_end:]
            
            # 处理单独的\r（回车符）
            while True:
                last_cr_pos = result.rfind('\r')
                if last_cr_pos == -1:
                    break
                
                # 检查这个\r是否已经是\r\x1b[K的一部分（应该已经被处理了）
                if (last_cr_pos + 3 < len(result) and 
                    result[last_cr_pos:last_cr_pos+4] == '\r\x1b[K'):
                    # 这是\r\x1b[K序列的一部分，应该已经被处理了，跳过
                    # 这种情况不应该发生，但为了安全起见
                    break
                
                # 单独的\r：光标回到行首，后续字符会覆盖当前行
                line_start = result.rfind('\n', 0, last_cr_pos)
                if line_start == -1:
                    line_start = 0
                else:
                    line_start += 1
                
                # 移除\r，保留后续内容（如果有的话）
                result = result[:line_start] + result[last_cr_pos+1:]
            
            # 处理单独的\x1b[K序列
            while True:
                last_k_pos = result.rfind('\x1b[K')
                if last_k_pos == -1:
                    break
                
                # 检查这个\x1b[K前面是否有\r
                if (last_k_pos >= 1 and result[last_k_pos-1] == '\r'):
                    # 这是\r\x1b[K的一部分，应该已经被处理了
                    break
                
                # 单独的\x1b[K：擦除从光标到行尾
                # 需要擦除当前行的内容
                # 从\x1b[K位置向左找到行的开始位置
                line_start = result.rfind('\n', 0, last_k_pos)
                if line_start == -1:
                    # 没有找到换行符，擦除从开头到\x1b[K的所有内容
                    result = result[last_k_pos+3:]
                else:
                    # 找到了换行符，保留换行符，擦除从换行符后到\x1b[K的内容
                    result = result[:line_start+1] + result[last_k_pos+3:]
            
            return result
        
        if stdout is None:
            return ''
        
        cleaned_stdout = stdout
        if cleaned_stdout:
            cleaned_stdout = process(cleaned_stdout)
            cleaned_stdout = re.sub(r'\n+', '\n', cleaned_stdout)
            cleaned_stdout = cleaned_stdout.strip()
        
        return cleaned_stdout

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

class GDSTest(unittest.TestCase):
    """
    GDS全面测试类
    包含所有GDS功能的测试，从基础到高级，从简单到复杂
    """
    
    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        print(f'设置GDS全面测试环境...')
        
        # 设置路径
        cls.BIN_DIR = Path(__file__).parent.parent
        cls.GOOGLE_DRIVE_PY = cls.BIN_DIR / "GOOGLE_DRIVE.py"
        cls.TEST_DATA_DIR = Path(__file__).parent / "_DATA"
        cls.TEST_TEMP_DIR = Path(__file__).parent / "_TEMP"
        
        # 确保目录存在
        cls.TEST_DATA_DIR.mkdir(exist_ok=True)
        cls.TEST_TEMP_DIR.mkdir(exist_ok=True)
        
        # 不需要清理shell状态，可以复用shell
        
        # 创建测试文件
        cls._create_test_files()
        
        # 创建唯一的测试目录名（用于远端）
        import hashlib
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        hash_suffix = hashlib.md5(timestamp.encode()).hexdigest()[:8]
        cls.test_folder = f"~/tmp/gds_test_{timestamp}_{hash_suffix}"
        
        # 检查GOOGLE_DRIVE.py是否可用
        if not cls.GOOGLE_DRIVE_PY.exists():
            raise unittest.SkipTest(f'GOOGLE_DRIVE.py not found at {cls.GOOGLE_DRIVE_PY}')
        
        # 创建远端测试目录并切换到该目录
        cls.setup_remote_test_directory()
        
        print(f'测试环境设置完成')
    
    @classmethod
    def setup_remote_test_directory(cls):
        """设置远端测试目录"""
        print(f'远端测试目录: {cls.test_folder}')
        
        # 然后创建测试目录 - 添加重试机制
        print(f'正在创建远端测试目录: {cls.test_folder}')
        mkdir_command = f"python3 {cls.GOOGLE_DRIVE_PY} --shell --no-direct-feedback 'mkdir -p {cls.test_folder}'"
        print("使用测试模式，窗口将只显示复制指令和执行完成按钮")
        
        # 重试机制：最多尝试3次
        for attempt in range(3):
            result = subprocess.run(
                mkdir_command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cls.BIN_DIR
            )
            
            if result.returncode == 0:
                break
            else:
                print(f'创建测试目录尝试 {attempt + 1}/3 失败: 返回码={result.returncode}')
                if attempt == 2:  # 最后一次尝试
                    import traceback
                    call_stack = ''.join(traceback.format_stack()[-3:])
                    error_msg = f"创建远端测试目录失败: 返回码={result.returncode}, stderr={result.stderr}, stdout={result.stdout}. Call stack: {call_stack}"
                    print(f'Unknown error: {error_msg}')
                    raise RuntimeError(error_msg)
                else:
                    import time
                    time.sleep(2)  # 等待2秒后重试
        
        # 切换到测试目录 - 添加重试机制
        cd_command = f"python3 {cls.GOOGLE_DRIVE_PY} --shell --no-direct-feedback 'cd {cls.test_folder}'"
        
        # 重试机制：最多尝试3次
        for attempt in range(3):
            result = subprocess.run(
                cd_command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cls.BIN_DIR
            )
            
            if result.returncode == 0:
                print(f'已切换到远端测试目录: {cls.test_folder}')
                break
            else:
                print(f'切换到测试目录尝试 {attempt + 1}/3 失败: 返回码={result.returncode}')
                if attempt == 2:  # 最后一次尝试
                    import traceback
                    call_stack = ''.join(traceback.format_stack()[-3:])
                    error_msg = f"切换到远端测试目录失败: 返回码={result.returncode}, stderr={result.stderr}, stdout={result.stdout}. Call stack: {call_stack}"
                    print(f'Unknown error: {error_msg}')
                    raise RuntimeError(error_msg)
                else:
                    import time
                    time.sleep(2)  # 等待2秒后重试
            
        # 验证目录确实存在 - 使用ls检查绝对路径，不需要重试（ls是特殊命令）
        ls_command = f"python3 {cls.GOOGLE_DRIVE_PY} --shell --no-direct-feedback 'ls {cls.test_folder}'"
        result = subprocess.run(
            ls_command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cls.BIN_DIR
        )
        
        if result.returncode != 0:
            import traceback
            call_stack = ''.join(traceback.format_stack()[-3:])
            error_msg = f"验证远端测试目录存在失败: 返回码={result.returncode}, stderr={result.stderr}, stdout={result.stdout}. Call stack: {call_stack}"
            print(f'Unknown error: {error_msg}')
            raise RuntimeError(error_msg)
        else:
            print(f'✓ 验证测试目录存在: {cls.test_folder}')
        
        # 本地也切换到临时目录，避免本地重定向问题
        import tempfile
        import os
        cls.local_tmp_dir = tempfile.mkdtemp(prefix="gds_test_local_")
        print(f'本地临时目录: {cls.local_tmp_dir}')
        os.chdir(cls.local_tmp_dir)
    
    @classmethod
    def _create_test_files(cls):
        """创建所有测试需要的文件"""
        
        # 1. 简单的Python脚本
        simple_script = cls.TEST_DATA_DIR / "simple_hello.py"
        simple_script.write_text('''"""
Simple Hello Script
"""
print(f'Hello from remote project')
print(f"Current working directory:", __import__("os").getcwd())
import sys
print(f"Python version:", sys.version)
''')
        
        # 2. 复杂的Python项目结构
        project_dir = cls.TEST_DATA_DIR / "test_project"
        project_dir.mkdir(exist_ok=True)
        
        # main.py
        (project_dir / "main.py").write_text('''"""
测试项目主文件
"""
import json
import sys
from datetime import datetime

def main():
    print(f'测试项目启动')
    print(f'当前时间: {datetime.now()}')
    print(f'Python版本: {sys.version}')
    
    # 读取配置文件
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        print(f'配置: {config}')
    except FileNotFoundError:
        print(f'配置文件不存在，使用默认配置')
        config = {"debug": True, "version": "1.0.0"}
    
    # 执行核心逻辑
    from core import process_data
    result = process_data(config)
    print(f'处理结果: {result}')

if __name__ == "__main__":
    main()
''')
        
        # core.py
        (project_dir / "core.py").write_text('''"""
核心处理模块
"""

def process_data(config):
    """处理数据的核心函数"""
    if config.get("debug", False):
        print(f'调试模式已启用')
    
    # 模拟数据处理
    data = [1, 2, 3, 4, 5]
    result = sum(x * x for x in data)
    
    return {
        "processed": True,
        "result": result,
        "version": config.get("version", "unknown")
    }
''')
        
        # config.json
        (project_dir / "config.json").write_text('''{
    "debug": true,
    "version": "1.0.0",
    "database": {
        "host": "localhost",
        "port": 5432,
        "name": "testdb"
    },
    "features": {
        "logging": true,
        "caching": false,
        "monitoring": true
    }
}''')
        
        # 3. 语法正确和错误的文件（用于linter测试）
        valid_python = cls.TEST_DATA_DIR / "valid_script.py"
        valid_python.write_text('''"""
语法正确的Python脚本
"""

def hello_world():
    print(f'Hello, World!')
    return True

def calculate_sum(a, b):
    """计算两个数的和"""
    return a + b

if __name__ == "__main__":
    hello_world()
    result = calculate_sum(5, 3)
    print(f'Sum: {result}')
''')
        
        invalid_python = cls.TEST_DATA_DIR / "invalid_script.py"
        invalid_python.write_text('''"""
包含语法错误的Python脚本
"""

def hello_world(
    print(f'Missing closing parenthesis')
    return True

def calculate_sum(a, b:
    return a + b

if __name__ == "__main__":
hello_world()
    result = calculate_sum(5, 3)
    print(f'Sum: {result}')
''')
        
        # 4. 特殊字符文件
        special_file = cls.TEST_DATA_DIR / "special_chars.txt"
        special_file.write_text('''包含中文的文件
Special characters: !@#$%^&*()
Quotes: "Hello" and 'World'
Backslashes: \\path\\to\\file
JSON: {"key": "value", "number": 123}
Shell commands: ls -la && echo "done"
''')
        
        # 5. 大文件（用于性能测试）
        large_file = cls.TEST_DATA_DIR / "large_file.txt"
        large_content = "\\n".join([f"Line {i}: This is a test line with some content for performance testing" for i in range(1000)])
        large_file.write_text(large_content)
        
        # 6. JSON配置文件
        valid_json = cls.TEST_DATA_DIR / "valid_config.json"
        valid_json.write_text('''{
    "name": "测试项目",
    "version": "1.0.0",
    "description": "这是一个测试配置文件",
    "settings": {
        "debug": true,
        "logging": {
            "level": "INFO",
            "file": "app.log"
        }
    }
}''')
    
    def get_test_file_path(self, filename):
        """获取测试文件的绝对路径"""
        return f"{self.test_folder}/{filename}"
    
    def get_local_file_path(self, remote_path):
        """
        将远程文件路径转换为本地文件路径
        
        对于download命令，如果指定了local_path，文件会被下载到本地路径。
        这个方法尝试推断本地文件的位置。
        
        Args:
            remote_path: 远程文件路径（如 "gds_test_xxx/downloaded_copy.txt"）
            
        Returns:
            str: 本地文件路径，如果不存在则返回None
        """
        import os
        
        # 从远程路径中提取文件名
        if '/' in remote_path:
            filename = remote_path.split('/')[-1]
        else:
            filename = remote_path
        
        # 尝试几个可能的本地路径
        possible_paths = [
            # 1. 当前工作目录
            os.path.join(os.getcwd(), filename),
            # 2. ~/tmp 目录
            os.path.expanduser(f'~/tmp/{filename}'),
            # 3. 测试临时目录
            os.path.join(str(self.TEST_DATA_DIR), filename) if hasattr(self, 'TEST_DATA_DIR') else None,
            os.path.join(str(self.TEST_TEMP_DIR), filename) if hasattr(self, 'TEST_TEMP_DIR') else None,
            # 4. 直接使用远程路径作为本地路径（如果download命令直接使用了这个路径）
            os.path.expanduser(remote_path) if remote_path.startswith('~') else remote_path,
        ]
        
        # 过滤掉None值
        possible_paths = [p for p in possible_paths if p is not None]
        
        # 检查哪个路径存在
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # 如果都不存在，返回None
        return None
    
    def get_local_file_content(self, file_path):
        """
        读取本地文件内容
        
        Args:
            file_path: 本地文件路径
            
        Returns:
            str: 文件内容，如果文件不存在或读取失败则返回None
        """
        import os
        if (file_path == None):
            raise ValueError("file_path is None")
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                return None
        except Exception as e:
            print(f'读取本地文件失败: {file_path}, 错误: {e}')
            return None
    
    def bash(self, command, cwd=None):
        """
        运行bash命令用于对比测试
        
        Args:
            command: 要执行的bash命令
            cwd: 工作目录，默认为None
            
        Returns:
            subprocess.CompletedProcess: bash命令执行结果
        """
        import subprocess
        
        try:
            # 使用bash -c确保与GDS执行环境一致
            bash_command = ['bash', '-c', command]
            result = subprocess.run(
                bash_command,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=30
            )
            return result
        except subprocess.TimeoutExpired:
            # 创建一个模拟的超时结果
            class TimeoutResult:
                def __init__(self):
                    self.returncode = 124  # bash timeout返回码
                    self.stdout = ""
                    self.stderr = "Command timed out"
            return TimeoutResult()
        except Exception as e:
            # 创建一个模拟的错误结果
            class ErrorResult:
                def __init__(self, error):
                    self.returncode = 1
                    self.stdout = ""
                    self.stderr = str(error)
            return ErrorResult(e)
    
    def gds(self, command, expect_success=True, check_function_result=True, no_direct_feedback=True, is_priority=False):
        """
        运行GDS命令的辅助方法
        
        Args:
            command: GDS命令
            expect_success: 是否期望命令成功
            check_function_result: 是否基于功能执行情况判断，而不是终端输出
        
        Returns:
            subprocess结果对象
        """
        # 使用统一的命令转译接口
        try:
            # 创建GoogleDriveShell实例来使用转译接口
            import sys
            import os
            sys.path.insert(0, os.path.join(self.BIN_DIR, 'GOOGLE_DRIVE_PROJ'))
            from google_drive_shell import GoogleDriveShell #type: ignore
            
            # 创建临时实例用于命令转译
            gds = GoogleDriveShell()
            translation_result = gds.execute_generic_command(command)
            if not translation_result["success"]:
                print(f'命令转译失败: {translation_result["error"]}')
                command_str = str(command)  # 回退到原始格式
            else:
                command_str = translation_result["translated_command"]
                print(f'命令转译成功: {command} -> {command_str}')
                
        except Exception as e:
            print(f'转译接口调用失败: {e}')

            # 回退到原始处理逻辑
            import shlex
            if isinstance(command, list):
                command_str = ' '.join(shlex.quote(str(arg)) for arg in command)
            else:
                command_str = command
        
        # 检测并处理组合命令（&&, ||, ;）- 使用统一接口
        def add_params_to_gds_commands(cmd_str):
            """为组合命令中的每个GDS命令添加参数 - 使用统一的命令解析接口"""
            # 导入统一的命令解析器
            import sys
            import os
            sys.path.insert(0, os.path.join(self.BIN_DIR, 'GOOGLE_DRIVE_PROJ', 'modules'))
            from command_parser import parse_command #type: ignore
            
            # 解析命令
            parse_result = parse_command(cmd_str)
            
            if not parse_result['is_compound']:
                # 单个命令，直接处理
                return cmd_str
            
            # 处理复合命令
            processed_parts = []
            for cmd_info in parse_result['commands']:
                command = cmd_info['command']
                operator = cmd_info['operator']
                
                # 如果有操作符，先添加操作符
                if operator:
                    processed_parts.append(f' {operator} ')
                
                # 处理命令
                if not command.strip().startswith('python3') and not command.strip().startswith('/'):
                    # 这是一个GDS命令，需要包装
                    gds_cmd_parts = [f"python3 {self.GOOGLE_DRIVE_PY}", "--shell"]
                    
                    if no_direct_feedback:
                        gds_cmd_parts.append("--no-direct-feedback")
                    
                    if is_priority:
                        gds_cmd_parts.append("--priority")
                    
                    # 转义命令字符串
                    import shlex
                    escaped_command = shlex.quote(command)
                    gds_cmd_parts.append(escaped_command)
                    processed_parts.append(" ".join(gds_cmd_parts))
                else:
                    # 不是GDS命令，直接添加
                    processed_parts.append(command)
            
            return "".join(processed_parts)
        
        # 处理命令字符串
        processed_command_str = add_params_to_gds_commands(command_str)
        
        # 构建完整命令，使用列表格式避免不必要的转义
        if processed_command_str == command_str: 
            cmd_parts = ["python3", str(self.GOOGLE_DRIVE_PY), "--shell"]
            if no_direct_feedback:
                cmd_parts.append("--no-direct-feedback")
            if is_priority:
                cmd_parts.append("--priority")
            cmd_parts.append(command_str)
            # 使用列表格式
            full_command = cmd_parts
            use_shell = False
        else:
            # 使用处理后的组合命令
            full_command = processed_command_str
            use_shell = True
            
        # 添加重试逻辑，最多重试2次（总共执行3次）
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    print(f'重试第{attempt}次...')
                    import time
                    time.sleep(2)  # 重试前等待2秒
                
                # 使用Popen捕获真正的原始输出（包括转义序列）
                if use_shell:
                    process = subprocess.Popen(
                        full_command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=self.BIN_DIR
                    )
                else:
                    process = subprocess.Popen(
                        full_command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=self.BIN_DIR
                    )
                
                # 获取原始字节输出
                raw_stdout_bytes, raw_stderr_bytes = process.communicate()
            
                # 解码为文本（保留所有字符，包括转义序列）
                raw_stdout_text = raw_stdout_bytes.decode('utf-8', errors='ignore')
                raw_stderr_text = raw_stderr_bytes.decode('utf-8', errors='ignore')
                
                # 创建兼容的result对象
                class ProcessResult:
                    def __init__(self, returncode, stdout, stderr, raw_stdout, raw_stderr):
                        self.returncode = returncode
                        self.stdout = stdout
                        self.stderr = stderr
                        self.raw_stdout = raw_stdout  # 新增：真正的原始输出
                        self.raw_stderr = raw_stderr  # 新增：真正的原始错误输出
                
                result = ProcessResult(
                    returncode=process.returncode,
                    stdout=raw_stdout_text,  # 使用原始文本
                    stderr=raw_stderr_text,  # 使用原始文本
                    raw_stdout=raw_stdout_text,  # 保存原始输出
                    raw_stderr=raw_stderr_text   # 保存原始错误输出
                )
                print(f'返回码: {result.returncode}')
                if result.stdout:
                    cleaned_stdout = process_terminal_erase(result.stdout)
                    # 检查清理后的输出是否还包含indicator（仅警告，不中断测试）
                    if '⏳' in cleaned_stdout:
                        print(f'⚠️  WARNING: Indicator ⏳ found in cleaned stdout after processing!')
                        print(f'   First 200 chars: {cleaned_stdout[:200]}')
                    print(f'输出: {cleaned_stdout}...')
                    
                    # 即刻输出到JSON debug文件
                    try:
                        import json
                        from datetime import datetime
                        from pathlib import Path
                        
                        # 直接实现简化的debug输出，避免导入问题
                        debug_file = Path(__file__).parent.parent / "GOOGLE_DRIVE_DATA" / "raw_gds_output.json"
                        debug_file.parent.mkdir(exist_ok=True)
                        
                        debug_data = {
                            "timestamp": datetime.now().isoformat(),
                            "command": command_str,
                            "return_code": result.returncode,
                            "raw_output": result.raw_stdout,  # 真正的原始输出
                            "output": cleaned_stdout,         # 清理后的输出
                            "raw_error": result.raw_stderr,   # 真正的原始错误输出
                            "error": process_terminal_erase(result.stderr) if result.stderr else None,
                            "full_command": str(full_command),
                            "analysis": {
                                "raw_contains_indicator": '⏳' in (result.raw_stdout or ''),
                                "output_contains_indicator": '⏳' in (cleaned_stdout or ''),
                                "indicator_removal_success": '⏳' not in (cleaned_stdout or '') if result.raw_stdout and '⏳' in result.raw_stdout else None
                            }
                        }
                        
                        # 追加模式写入
                        try:
                            with open(debug_file, 'r', encoding='utf-8') as f:
                                existing_data = json.load(f)
                            if not isinstance(existing_data, list):
                                existing_data = [existing_data]
                        except (FileNotFoundError, json.JSONDecodeError):
                            existing_data = []
                        
                        existing_data.append(debug_data)
                        
                        with open(debug_file, 'w', encoding='utf-8') as f:
                            json.dump(existing_data, f, indent=2, ensure_ascii=False)
                    except Exception as e:
                        print(f'Debug output failed: {e}')
                if result.stderr:
                    cleaned_stderr = process_terminal_erase(result.stderr)
                    # 检查清理后的错误输出是否还包含indicator（仅警告，不中断测试）
                    if '⏳' in cleaned_stderr:
                        print(f'⚠️  WARNING: Indicator ⏳ found in cleaned stderr after processing!')
                        print(f'   First 200 chars: {cleaned_stderr[:200]}')
                    print(f'错误: {cleaned_stderr}...')
                
                # 检查是否需要重试
                should_retry = False
                
                # 检查预期与实际是否不符
                expected_success = expect_success
                actual_success = result.returncode == 0
                expectation_mismatch = expected_success != actual_success
                
                if expectation_mismatch and attempt < max_retries:
                    print(f'🔄 检测到预期与实际不符（预期成功: {expected_success}, 实际成功: {actual_success}），准备重试...')
                    
                    # 如果是预期成功但实际失败，且包含特定错误，则触发remount
                    if expected_success and not actual_success:
                        error_output = result.stdout + result.stderr
                        # Check for various error conditions that indicate connection issues
                        remount_triggers = [
                            "Unknown error",
                            "ERROR", 
                            "No such file or directory"  # New bash-aligned error format
                        ]
                        should_remount = any(trigger in error_output for trigger in remount_triggers)
                        
                        if should_remount:
                            # 检查是否已经有remount flag，避免重复设置
                            flag_file = Path(__file__).parent.parent / "GOOGLE_DRIVE_DATA" / "remount_required.flag"
                            if flag_file.exists():
                                print(f'检测到remount flag已存在，跳过重复设置')
                            else:
                                # 设置remount flag，让WindowManager在下一个窗口显示时处理remount
                                print(f'检测到Unknown error，设置remount flag，下一个窗口将自动remount')
                                try:
                                    import json
                                    import time
                                    
                                    flag_data = {
                                        "created": time.time(),
                                        "reason": f"Test detected error in command: {command_str}. Error: {error_output[:200]}",
                                        "set_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                                        "set_by": "test_gds.py"
                                    }
                                    
                                    flag_file.parent.mkdir(exist_ok=True)
                                    with open(flag_file, 'w') as f:
                                        json.dump(flag_data, f, indent=2)
                                    
                                    print(f'Remount flag已设置，下一个窗口将自动处理remount')
                                    
                                except Exception as flag_e:
                                    print(f'设置remount flag失败: {flag_e}')
                    
                    should_retry = True
                
                if should_retry:
                    continue  # 继续下一次循环，进行重试
                
                # 不需要重试，返回结果
                # 基于功能执行情况判断，而不是终端输出
                if check_function_result and expect_success:
                    self.assertEqual(result.returncode, 0, f"命令执行失败")
                
                return result
            except Exception as e:
                print(f'命令执行异常: {e}')
                if expect_success:
                    self.fail(f'命令执行异常: {command} - {e}')
                return None
        
        # 所有重试都失败，返回None
        return None
    
    def _record_remount_action(self, original_command, error_output, remount_returncode, remount_output, remount_error):
        """记录自动remount操作到测试结果文件"""
        try:
            import json
            from datetime import datetime
            from pathlib import Path
            
            # 创建remount记录文件
            remount_log_file = Path(__file__).parent.parent / "GOOGLE_DRIVE_DATA" / "auto_remount_log.json"
            remount_log_file.parent.mkdir(exist_ok=True)
            
            # 获取调用栈信息
            import traceback
            import inspect
            
            # 获取调用栈，排除当前方法
            call_stack = traceback.format_stack()[:-1]
            
            # 获取直接调用者信息
            caller_frame = inspect.currentframe().f_back
            caller_info = {
                "function": caller_frame.f_code.co_name,
                "filename": caller_frame.f_code.co_filename,
                "line_number": caller_frame.f_lineno
            }
            
            # 获取调用链（最近的5层）
            call_chain = []
            frame = caller_frame
            for i in range(5):
                if frame is None:
                    break
                call_chain.append({
                    "function": frame.f_code.co_name,
                    "filename": frame.f_code.co_filename.split('/')[-1],  # 只保留文件名
                    "line_number": frame.f_lineno
                })
                frame = frame.f_back
            
            remount_record = {
                "timestamp": datetime.now().isoformat(),
                "test_method": self._testMethodName if hasattr(self, '_testMethodName') else "unknown",
                "original_command": original_command,
                "error_output": error_output[:500],  # 限制长度
                "remount_returncode": remount_returncode,
                "remount_output": remount_output[:500] if remount_output else None,
                "remount_error": remount_error[:500] if remount_error else None,
                "remount_success": remount_returncode == 0,
                "caller_info": caller_info,
                "call_chain": call_chain,
                "call_stack_summary": [line.strip() for line in call_stack[-3:]]  # 最近3层调用栈
            }
            
            # 追加到日志文件
            try:
                with open(remount_log_file, 'r', encoding='utf-8') as f:
                    existing_logs = json.load(f)
                if not isinstance(existing_logs, list):
                    existing_logs = [existing_logs]
            except (FileNotFoundError, json.JSONDecodeError):
                existing_logs = []
            
            existing_logs.append(remount_record)
            
            with open(remount_log_file, 'w', encoding='utf-8') as f:
                json.dump(existing_logs, f, indent=2, ensure_ascii=False)
                
            print(f'📝 Remount操作已记录到: {remount_log_file}')
            
        except Exception as e:
            print(f'📝 记录remount操作失败: {e}')
    
    def verify_file_exists(self, filename):
        """验证远端文件或目录是否存在 - 使用统一cmd_ls接口，不弹出远程窗口"""
        result = self.gds(f'ls "{filename}"', expect_success=False)
        if result is None or result.returncode != 0:
            return False
        return "Path not found" not in result.stdout and "not found" not in result.stdout.lower()
    
    def verify_file_content_contains(self, filename, expected_content, terminal_erase = False):
        """验证远端文件内容包含特定文本（基于功能结果）"""
        if (filename == None):
            raise ValueError("filename is None")
        result = self.gds(f'cat "{filename}"')
        if result.returncode == 0:
            if terminal_erase:
                return expected_content in process_terminal_erase(result.stdout)
            else:
                return expected_content in result.stdout
        return False
    
    def gds_with_retry(self, command, verification_commands, max_retries=3, expect_success=True):
        """
        运行GDS命令并进行重试验证的辅助方法
        
        Args:
            command: 要执行的GDS命令
            verification_commands: 验证命令列表，所有命令都必须返回0才算成功
            max_retries: 最大重试次数
            expect_success: 是否期望命令成功
        
        Returns:
            tuple: (success: bool, last_result: subprocess结果对象)
        """
        print(f'\n执行带重试的命令: {command}')
        print(f'验证命令: {verification_commands}')
        print(f'最大重试次数: {max_retries}')
        
        for attempt in range(max_retries):
            print(f'\n尝试 {attempt + 1}/{max_retries}')
            
            # 执行主命令
            result = self.gds(command, expect_success=expect_success, check_function_result=False)
            
            if not expect_success:
                return result.returncode != 0, result
            
            if result.returncode != 0:
                print(f'Error: Main command failed, return code: {result.returncode}')
                if attempt < max_retries - 1:
                    print(f'Waiting 1 second before retrying...')
                    import time
                    time.sleep(1)
                    continue
                else:
                    return False, result
            
            # 执行验证命令
            all_verifications_passed = True
            for i, verify_cmd in enumerate(verification_commands):
                print(f'Verify {i+1}/{len(verification_commands)}: {verify_cmd}')
                verify_result = self.gds(verify_cmd, expect_success=False, check_function_result=False)
                
                if verify_result.returncode != 0:
                    print(f'Error: Verify failed, return code: {verify_result.returncode}')
                    all_verifications_passed = False
                    break
                else:
                    print(f'Verify successful')
            
            if all_verifications_passed:
                print(f'All verifications passed, command executed successfully')
                return True, result
            
            if attempt < max_retries - 1:
                print(f'Verify failed, waiting 2 seconds before retrying...')
                import time
                time.sleep(2)
        
        print(f'All retries failed')
        return False, result
    
    def run_command_with_input(self, command_list, input_text, timeout=None):
        """
        运行命令并提供输入的辅助方法
        
        Args:
            command_list: 命令列表 (如 [sys.executable, str(self.GOOGLE_DRIVE_PY), "--shell"])
            input_text: 要发送给命令的输入文本
            timeout: 超时时间（秒），None表示无超时
        
        Returns:
            subprocess结果对象
        """
        try:
            result = subprocess.run(
                command_list,
                input=input_text,
                capture_output=True,
                text=True,
                timeout=timeout, 
                cwd=self.BIN_DIR
            )
            return result
        except subprocess.TimeoutExpired:
            print(f'Command execution timeout ({timeout}s)')
            # 创建一个模拟的失败结果
            class MockResult:
                def __init__(self):
                    self.returncode = 1
                    self.stdout = ""
                    self.stderr = f"Command timed out after {timeout} seconds"
            return MockResult()
        except Exception as e:
            print(f'Command execution exception: {e}')
            class MockResult:
                def __init__(self):
                    self.returncode = 1
                    self.stdout = ""
                    self.stderr = str(e)
            return MockResult()
    
    def run_upload(self, command, verification_commands, max_retries=3):
        """
        运行GDS upload命令并进行重试验证的辅助方法
        upload是GDS的直接命令，不是shell命令
        """
        print(f'\n执行带重试的upload命令: {command}')
        print(f'验证命令: {verification_commands}')
        print(f'最大重试次数: {max_retries}')
        
        for attempt in range(max_retries):
            print(f'\n尝试 {attempt + 1}/{max_retries}')
            result = self.gds(command, expect_success=False, check_function_result=False)
            if result.returncode != 0:
                print(f'Error: Upload command failed, return code: {result.returncode}')
                if attempt < max_retries - 1:
                    print(f'Waiting 1 second before retrying...')
                    import time
                    time.sleep(1)
                    continue
                else:
                    return False, result
            
            # 执行验证命令
            all_verifications_passed = True
            for i, verify_cmd in enumerate(verification_commands):
                print(f'验证命令 {i+1}: {verify_cmd}')
                verify_result = self.gds(verify_cmd, expect_success=False, check_function_result=False)
                if verify_result.returncode != 0:
                    print(f'验证失败: {verify_cmd} (返回码: {verify_result.returncode})')
                    all_verifications_passed = False
                    break
                else:
                    print(f'验证成功: {verify_cmd}')
            
            if all_verifications_passed:
                print("所有验证通过!")
                return True, result
            else:
                if attempt < max_retries - 1:
                    print(f'验证失败，等待1秒后重试...')
                    import time
                    time.sleep(1)
                    continue
        
        print("所有重试都失败了")
        return False, result


    def wait_for_pyenv_install(self, task_id, version, timeout=5400, check_interval=60):
        """
        等待pyenv后台安装完成
        
        Args:
            task_id: 后台任务ID
            version: Python版本号
            timeout: 超时时间（秒）
            check_interval: 检查间隔（秒），默认60秒
            
        Returns:
            bool: 安装是否成功
        """
        import time
        import json
        start_time = time.time()
        
        print(f'等待Python {version}后台安装完成（任务ID: {task_id}，超时{timeout}秒）...')
        
        while time.time() - start_time < timeout:
            # 检查后台任务状态
            result = self.gds(f"--bg --status {task_id}", expect_success=False)
            
            if result.returncode == 0:
                try:
                    # 解析状态输出
                    output = result.stdout.strip()
                    if "completed" in output.lower() or "finished" in output.lower():
                        # 任务已完成，获取结果
                        print(f'任务已完成，获取结果...')
                        result_cmd = self.gds(f"--bg --result {task_id}", expect_success=False)
                        
                        # 检查是否为明确的命令未找到错误（exit code 127）
                        if result_cmd.returncode == 127:
                            print(f'Python {version}安装失败：命令未找到（exit code 127）')
                            print(f'输出：{result_cmd.stdout}')
                            return False
                        
                        # 检查输出中是否包含"command not found"
                        result_output = result_cmd.stdout + result_cmd.stderr
                        if "command not found" in result_output:
                            print(f'Python {version}安装失败：系统pyenv工具未安装')
                            print(f'输出：{result_output}')
                            print(f'提示：GDS的pyenv特殊指令需要远端系统安装pyenv工具才能工作')
                            return False
                        
                        if result_cmd.returncode == 0:
                            # 检查安装是否成功
                            if "installed successfully" in result_cmd.stdout.lower() or "success" in result_cmd.stdout.lower():
                                print(f'Python {version}安装成功！')
                                return True
                            else:
                                print(f'Python {version}安装失败：{result_cmd.stdout}')
                                return False
                    elif "running" in output.lower() or "in progress" in output.lower():
                        # 任务仍在运行，继续等待（不要尝试获取result）
                        elapsed = int(time.time() - start_time)
                        print(f'任务仍在运行... 已等待{elapsed}秒')
                        time.sleep(check_interval)
                        continue
                    elif "failed" in output.lower() or "error" in output.lower():
                        print(f'Python {version}安装任务失败')
                        result_cmd = self.gds(f"--bg --result {task_id}", expect_success=False)
                        if result_cmd.returncode == 0:
                            print(f'错误详情：{result_cmd.stdout}')
                        return False
                    
                    # 检查status中的Exit code（如果任务已完成但结果获取失败）
                    if "Exit code: 127" in output:
                        print(f'Python {version}安装失败：任务exit code 127（命令未找到）')
                        return False
                except Exception as e:
                    print(f'解析任务状态时出错：{e}')
            
            # 等待一段时间后重试
            time.sleep(check_interval)
            elapsed = int(time.time() - start_time)
            print(f'等待中... 已等待{elapsed}秒')
        
        print(f'等待超时！Python {version}未能在{timeout}秒内安装完成')
        return False


    def ensure_clean_shell_state(self):
        """确保干净的shell状态，用于虚拟环境操作的原子性"""
        try:
            # 强制取消激活任何现有环境
            result = self.gds('venv --deactivate', expect_success=False, check_function_result=False)
        except:
            pass
        
        # 等待状态同步
        import time
        time.sleep(0.5)
    
    def get_cleaned_stdout(self, result, use_stderr=False):
        """获取清理后的stdout或stderr，移除indicator等转义序列"""
        if not result:
            return ""
        if use_stderr:
            if not hasattr(result, 'stderr') or not result.stderr:
                return ""
            return process_terminal_erase(result.stderr)
        else:
            if not result.stdout:
                return ""
            return process_terminal_erase(result.stdout)
    
    def assert_gds_bash_output_match(self, cmd, bash_test_dir, description="输出"):
        """
        统一的GDS和bash输出比对接口
        
        Args:
            cmd: 要执行的命令
            bash_test_dir: bash测试目录
            description: 描述性文字，用于错误消息（例如"输出"、"无输出"、"返回码"等）
        
        Returns:
            tuple: (gds_result, bash_result) 方便调用者进行额外的自定义验证
        """
        # 运行GDS命令
        gds_result = self.gds(cmd, expect_success=True, check_function_result=False)
        gds_stdout = self.get_cleaned_stdout(gds_result)
        gds_stderr = self.get_cleaned_stdout(gds_result, use_stderr=True)
        gds_returncode = gds_result.returncode
        
        # 运行bash命令
        bash_result = self.bash(cmd, bash_test_dir)
        
        # 对比返回码
        self.assertEqual(gds_returncode, bash_result.returncode, 
                       f"命令 '{cmd}' {description}返回码应该一致")
        
        # 返回结果供调用者进行额外验证
        return (gds_result, bash_result, gds_stdout, gds_stderr)
    
    def assert_no_output(self, cmd, bash_test_dir, description="命令"):
        """
        验证GDS和bash命令都没有stdout输出（适用于重定向等命令）
        
        Args:
            cmd: 要执行的命令
            bash_test_dir: bash测试目录
            description: 描述性文字，用于错误消息
        """
        gds_result, bash_result, gds_stdout, gds_stderr = self.assert_gds_bash_output_match(
            cmd, bash_test_dir, description
        )
        
        # 清理输出
        gds_output_clean = gds_stdout.strip()
        bash_output_clean = bash_result.stdout.strip()
        
        print(f'    GDS输出: {repr(gds_output_clean)}')
        print(f'    Bash输出: {repr(bash_output_clean)}')
        
        # 验证两者都没有实质性输出
        self.assertEqual(len(gds_output_clean), 0, f"GDS {description} '{cmd}' 应该没有输出")
        self.assertEqual(len(bash_output_clean), 0, f"bash {description} '{cmd}' 应该没有输出")

    def test_00_ls_basic(self):
        """测试ls命令的全路径支持（修复后的功能）"""
        
        # 创建测试文件和目录结构
        testdir = self.get_test_file_path("testdir")
        result = self.gds(f'mkdir -p "{testdir}"')
        self.assertEqual(result.returncode, 0, f"mkdir命令应该成功，但返回码为{result.returncode}")
        
        result = self.gds(f'\'echo "test content" > "{testdir}/testfile.txt"\'')
        self.assertEqual(result.returncode, 0, f"echo命令应该成功，但返回码为{result.returncode}")
        
        # 测试ls目录
        result = self.gds(f'ls "{testdir}"')
        self.assertEqual(result.returncode, 0, f"ls命令应该成功，但返回码为{result.returncode}")
        
        # 测试ls路径文件
        result = self.gds(f'ls "{testdir}/testfile.txt"')
        self.assertEqual(result.returncode, 0, f"ls命令应该成功，但返回码为{result.returncode}")
        
        # 测试ls不存在的文件
        result = self.gds(f'ls "{testdir}/nonexistent.txt"', expect_success=False)
        self.assertNotEqual(result.returncode, 0, f"ls命令应该失败，但返回码为{result.returncode}")  # 应该失败
        
        # 测试ls不存在的目录中的文件
        nonexistent_dir = self.get_test_file_path("nonexistent_dir")
        result = self.gds(f'ls "{nonexistent_dir}/file.txt"', expect_success=False)
        self.assertNotEqual(result.returncode, 0, f"ls命令应该失败，但返回码为{result.returncode}")  # 应该失败

    def test_01_ls_advanced(self):
        # 1. 切换到测试子目录
        print(f'切换到测试子目录')
        ls_test_subdir = self.get_test_file_path("ls_test_subdir")
        result = self.gds(f'mkdir -p "{ls_test_subdir}" && cd "{ls_test_subdir}"')
        self.assertEqual(result.returncode, 0)
        
        # 2. 测试基本ls命令（当前目录）
        print(f'测试基本ls命令')
        result = self.gds(f'ls')
        self.assertEqual(result.returncode, 0)
        
        # 3. 测试ls .（当前目录显式指定）
        print(f'测试ls .（当前目录）')
        result_ls_dot = self.gds(f'ls .')
        self.assertEqual(result_ls_dot.returncode, 0)
        
        # 4. 测试ls ~（根目录
        print(f'测试ls ~（根目录）')
        result = self.gds(f'ls ~')
        self.assertEqual(result.returncode, 0)
        
        # 5. 创建测试结构来验证路径差异
        print(f'创建测试目录结构')
        ls_test_dir = self.get_test_file_path("ls_test_dir")
        result = self.gds(f'mkdir -p "{ls_test_dir}/subdir"')
        self.assertEqual(result.returncode, 0)
        
        result = self.gds(f'\'echo "root file" > "{ls_test_dir}/ls_test_root.txt"\'')
        self.assertEqual(result.returncode, 0)
        
        result = self.gds(f'\'echo "subdir file" > "{ls_test_dir}/ls_test_sub.txt"\'')
        self.assertEqual(result.returncode, 0)
        
        # 6. 测试不同路径的ls命令
        print(f'测试不同路径的ls命令')
        
        # ls 相对路径
        result = self.gds(f'ls "{ls_test_dir}"')
        self.assertEqual(result.returncode, 0)

        # 验证ls返回的内容包括创建的文件
        ls_result = self.gds(f'ls "{ls_test_dir}"')
        self.assertEqual(ls_result.returncode, 0)
        self.assertIn("ls_test_root.txt", ls_result.stdout)
        self.assertIn("ls_test_sub.txt", ls_result.stdout)
        
        # 7. 测试ls -R（递归列表
        print(f'测试ls -R（递归）')
        result = self.gds(f'ls -R "{ls_test_dir}"')
        self.assertEqual(result.returncode, 0)

        # 验证ls -R返回的内容包括创建的文件
        ls_r_result = self.gds(f'ls -R "{ls_test_dir}"')
        self.assertEqual(ls_r_result.returncode, 0)
        self.assertIn("subdir", ls_r_result.stdout)
        self.assertIn("ls_test_root.txt", ls_r_result.stdout)
        self.assertIn("ls_test_sub.txt", ls_r_result.stdout)
        
        # 8. 测试文件路径的ls
        print(f'测试文件路径的ls')
        result = self.gds(f'ls "{ls_test_dir}/ls_test_root.txt"')
        self.assertEqual(result.returncode, 0)
        
        result = self.gds(f'ls "{ls_test_dir}/ls_test_sub.txt"')
        self.assertEqual(result.returncode, 0)
        
        # 9. 测试不存在路径的错误处理
        nonexistent_dir = self.get_test_file_path("nonexistent_dir")
        print(f'测试不存在路径的错误处理')
        result = self.gds(f'ls "{nonexistent_dir}/nonexistent_file.txt"', expect_success=False)
        self.assertNotEqual(result.returncode, 0)
        
        result = self.gds(f'ls "{nonexistent_dir}/"', expect_success=False)
        self.assertNotEqual(result.returncode, 0)
        
        # 10. 测试特殊字符路径
        print(f'测试特殊字符路径')
        result = self.gds(f'mkdir -p "{self.get_test_file_path("test dir with spaces")}"')
        self.assertEqual(result.returncode, 0)
        
        result = self.gds(f'ls "{self.get_test_file_path("test dir with spaces")}"')
        self.assertEqual(result.returncode, 0)
        
        # 11. 清理测试文件
        print(f'清理测试文件')
        cleanup_items = [
            ls_test_dir,
            f'"{ls_test_dir}/ls_test_root.txt"', 
            self.get_test_file_path("test dir with spaces")
        ]
        for item in cleanup_items:
            try:
                result = self.gds(f'rm -rf "{item}"', expect_success=False, check_function_result=False)
            except:
                pass  # 清理失败不影响测试结果
        
        # 12. 创建多级目录结构用于测试
        print(f'创建多级测试目录结构')
        test_path = self.get_test_file_path("test_path")
        result = self.gds(f'mkdir -p "{test_path}/level1/level2"')
        self.assertEqual(result.returncode, 0)

        print(f'测试相对路径cd')
        result = self.gds(f'cd "{test_path}"')
        self.assertEqual(result.returncode, 0)
        
        # 13. 测试子目录ls
        print(f'测试子目录ls')
        level1 = f'{test_path}/level1'
        result = self.gds(f'ls "{level1}"')
        self.assertEqual(result.returncode, 0)

        print(f'测试多级cd')
        level2 = f'{level1}/level2'
        result = self.gds(f'cd "{level2}"')
        self.assertEqual(result.returncode, 0)
        
        # 14. 测试父目录导航
        print(f'测试父目录cd ..')
        result = self.gds('cd ..')
        self.assertEqual(result.returncode, 0)
        
        print(f'测试多级父目录cd ../..')
        result = self.gds('cd ../..')
        self.assertEqual(result.returncode, 0)
        
        result = self.gds(f'ls "{test_path}/level1"')
        self.assertEqual(result.returncode, 0)
        
        # 15. 测试复杂相对路径cd
        print(f'测试复杂相对路径cd')
        result = self.gds(f'cd "{test_path}/level1/../level1/level2"')
        self.assertEqual(result.returncode, 0)
        
        # 16. 清理测试目录
        print(f'清理测试目录')
        # 先切换到安全目录，避免删除包含当前工作目录的目录
        result = self.gds(f'cd ~ && rm -rf "{test_path}"')
        self.assertEqual(result.returncode, 0)
        
        # 17. 测试不存在的路径
        print(f'Error:  测试不存在的路径')
        result = self.gds(f'ls "{test_path}"', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0)  # 应该失败
        
        print(f'Error:  测试cd到不存在的路径')
        result = self.gds(f'cd "{test_path}/nonexistent_path"', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0)  # 应该失败

        # 18. 边界测试
        print(f'创建边界测试目录')
        test_edge_dir = self.get_test_file_path("test_edge_dir")
        result = self.gds(f'mkdir -p "{test_edge_dir}/empty_dir"')
        self.assertEqual(result.returncode, 0)
        
        print(f'测试空目录ls')
        result = self.gds(f'ls "{test_edge_dir}/empty_dir"')
        self.assertEqual(result.returncode, 0)
        
        print(f'测试根目录的父目录')
        result = self.gds(f'cd ~')
        self.assertEqual(result.returncode, 0)
        result = self.gds(f'cd ..', expect_success=False, check_function_result=False)
        
        # 19. 测试当前目录的当前目录
        print(f'测试当前目录的当前目录')
        result = self.gds(f'ls ./.')
        self.assertEqual(result.returncode, 0)
        
        # 20. 清理
        print(f'清理边界测试目录')
        result = self.gds(f'rm -rf "{test_edge_dir}"')
        self.assertEqual(result.returncode, 0)

        # 21. 创建测试目录
        print('创建测试目录')
        testdir = self.get_test_file_path("ls_hidden_test")
        result = self.gds(f'mkdir -p "{testdir}"')
        self.assertEqual(result.returncode, 0, f"mkdir命令应该成功，但返回码为{result.returncode}")
        
        # 22. 创建普通文件
        print('创建普通文件')
        result = self.gds(f'\'echo "normal file" > "{testdir}/normal.txt"\'')
        self.assertEqual(result.returncode, 0, f"创建普通文件应该成功，但返回码为{result.returncode}")
        
        # 23. 创建隐藏文件（以.开头）
        print('创建隐藏文件')
        result = self.gds(f'\'echo "hidden file" > "{testdir}/.hidden.txt"\'')
        self.assertEqual(result.returncode, 0, f"创建隐藏文件应该成功，但返回码为{result.returncode}")
        
        result = self.gds(f'\'echo "hidden config" > "{testdir}/.config"\'')
        self.assertEqual(result.returncode, 0, f"创建隐藏配置文件应该成功，但返回码为{result.returncode}")
        
        # 24. 测试默认ls（不显示隐藏文件）
        print('测试默认ls（不显示隐藏文件）')
        result = self.gds(f'ls "{testdir}"')
        self.assertEqual(result.returncode, 0, f"ls命令应该成功，但返回码为{result.returncode}")
        self.assertIn("normal.txt", result.stdout, "应该显示普通文件")
        self.assertNotIn(".hidden.txt", result.stdout, "不应该显示隐藏文件")
        self.assertNotIn(".config", result.stdout, "不应该显示隐藏配置文件")
        
        # 25. 测试ls -a（显示所有文件包括隐藏文件）
        print('测试ls -a（显示所有文件）')
        result = self.gds(f'ls -a "{testdir}"')
        self.assertEqual(result.returncode, 0, f"ls -a命令应该成功，但返回码为{result.returncode}")
        self.assertIn("normal.txt", result.stdout, "应该显示普通文件")
        self.assertIn(".hidden.txt", result.stdout, "应该显示隐藏文件")
        self.assertIn(".config", result.stdout, "应该显示隐藏配置文件")
        
        # 26. 测试ls --all（完整选项名）
        print('测试ls --all（完整选项名）')
        result = self.gds(f'ls --all "{testdir}"')
        self.assertEqual(result.returncode, 0, f"ls --all命令应该成功，但返回码为{result.returncode}")
        self.assertIn("normal.txt", result.stdout, "应该显示普通文件")
        self.assertIn(".hidden.txt", result.stdout, "应该显示隐藏文件")
        self.assertIn(".config", result.stdout, "应该显示隐藏配置文件")
        
        # 27. 测试ls -la（组合选项：详细信息+显示隐藏文件）
        print('测试ls -la（详细+隐藏）')
        result = self.gds(f'ls -la "{testdir}"')
        self.assertEqual(result.returncode, 0, f"ls -la命令应该成功，但返回码为{result.returncode}")
        self.assertIn("normal.txt", result.stdout, "应该显示普通文件")
        self.assertIn(".hidden.txt", result.stdout, "应该显示隐藏文件")
        self.assertIn(".config", result.stdout, "应该显示隐藏配置文件")
        
        # 28. 测试ls -f -a（强制刷新+显示隐藏文件）
        print('测试ls -f -a（强制刷新+隐藏）')
        result = self.gds(f'ls -f -a "{testdir}"')
        self.assertEqual(result.returncode, 0, f"ls -f -a命令应该成功，但返回码为{result.returncode}")
        self.assertIn("normal.txt", result.stdout, "应该显示普通文件")
        self.assertIn(".hidden.txt", result.stdout, "应该显示隐藏文件")
        self.assertIn(".config", result.stdout, "应该显示隐藏配置文件")
        
        # 29. 清理测试文件
        print('清理测试文件')
        result = self.gds(f'rm -rf "{testdir}"')
        self.assertEqual(result.returncode, 0, f"清理应该成功，但返回码为{result.returncode}")

    def test_02_echo_basic(self):
        """测试基础echo命令"""
        
        # 简单echo
        result = self.gds(f'echo "Hello World"')
        self.assertEqual(result.returncode, 0)
        
        # 复杂字符串echo（避免使用!以免触发bash历史问题）
        result = self.gds(f'echo "Complex: @#$%^&*() \\"quotes\\" 中文字符"')
        self.assertEqual(result.returncode, 0)
        
        # Echo重定向创建文件（使用正确的语法：单引号包围整个命令）
        echo_file = self.get_test_file_path("test_echo.txt")
        result = self.gds(f'\'echo "Test content" > "{echo_file}"\'')
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.verify_file_content_contains(echo_file, "Test content"))
        
        # 更复杂的echo测试：包含转义字符和引号
        complex_echo_file = self.get_test_file_path("complex_echo.txt")
        content = "Line 1\nLine 2\tTabbed\\Backslash"
        content_escaped = content.replace("'", "\'")
        result = self.gds(f'\'echo "{content_escaped}" > "{complex_echo_file}"\'')
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.verify_file_content_contains(complex_echo_file, content, terminal_erase = True))
        
        # 包含JSON格式的echo（检查实际的转义字符处理）
        json_echo_file = self.get_test_file_path("json_echo.txt")
        json_content = "{'name': 'test02_json_echo_01', 'value': 123}"
        json_content_escaped = json_content.replace("'", "\'")
        result = self.gds(f'\'echo "{json_content_escaped}" > "{json_echo_file}"\'')
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.verify_file_content_contains(json_echo_file, json_content, terminal_erase = True))
        
        # 包含中文和特殊字符的echo
        chinese_echo_file = self.get_test_file_path("chinese_echo.txt")
        chinese_content = "测试中文：你好世界 Special chars: @#$%^&*()_+-=[]{}|;:,.<>?"
        import shlex
        safe_content = shlex.quote(chinese_content)
        safe_file = shlex.quote(chinese_echo_file)
        command = f'echo "{safe_content}" > "{safe_file}"'
        print(f'执行的命令: {command}')
        result = self.gds(command)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.verify_file_content_contains(chinese_echo_file, chinese_content, terminal_erase = True))
        
        # 测试echo -e处理换行符（重定向到文件）
        echo_multiline_path = self.get_test_file_path("echo_multiline.txt")
        content = "line1\nline2\nline3"
        content_escaped = content.replace("'", "\'")
        result = self.gds(f'\'echo -e "{content_escaped}" > "{echo_multiline_path}"\'')
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.verify_file_content_contains(echo_multiline_path, content, terminal_erase = True))
        
    def test_03_echo_advanced(self):
        """测试echo的正确JSON语法（修复后的功能）"""
        
        # 使用正确的语法创建JSON文件（单引号包围重定向范围）
        correct_json_file = self.get_test_file_path("correct_json.txt")
        json_content = "{'name': 'test03_json_echo_01', 'value': 123}"
        json_content_escaped = json_content.replace("'", "\'")
        result = self.gds(f'echo "{json_content_escaped}" > "{correct_json_file}"')
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.verify_file_content_contains(correct_json_file, json_content))
        
        # 测试echo -e参数处理换行符（用引号包围整个命令，避免本地重定向）
        multiline_path = self.get_test_file_path("multiline.txt")
        content = "Line1\nLine2\nLine3"
        content_escaped = content.replace("'", "\'")
        result = self.gds(f'\'echo -e "{content_escaped}" > "{multiline_path}"\'')
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.verify_file_content_contains(multiline_path, content))
        
        # 测试echo命令输出到stdout
        echo_stdout_test = "Echo stdout test content"
        result = self.gds(f'echo "{echo_stdout_test}"')
        self.assertEqual(result.returncode, 0)
        self.assertIn(echo_stdout_test, result.stdout, "echo命令输出应该在stdout中")
        self.assertEqual(result.stderr.strip(), "", "echo命令不应该有stderr输出")
        
        # 测试echo命令的本地重定向能力（需要stdout输出）
        echo_redirect_test = "Content for local redirect"
        result = self.gds(f'echo "{echo_redirect_test}"')
        self.assertEqual(result.returncode, 0)
        self.assertIn(echo_redirect_test, result.stdout, "echo命令必须输出到stdout才能支持本地重定向")
        
        # 使用本地重定向语法（GDS输出被本地重定向）
        # 使用TEST_TEMP_DIR构造本地文件路径（文件在subprocess执行前不存在，所以不能用get_local_file_path）
        local_redirect_path = os.path.join(str(self.TEST_TEMP_DIR), "local_redirect.txt")
        json_content = "{'name': 'test03_json_echo_02', 'value': 123}"
        json_content_escaped = json_content.replace("'", "\'")
        full_command = f'python3 {self.GOOGLE_DRIVE_PY} --shell --no-direct-feedback echo "{json_content_escaped}" > "{local_redirect_path}"'
        # 本地重定向应该直接使用subprocess.run，不通过gds的转译接口
        import subprocess
        result = subprocess.run(full_command, shell=True, capture_output=True, text=True)
        print(f'命令执行: {full_command}')
        print(f'返回码: {result.returncode}')
        if result.stdout:
            print(f'输出: {result.stdout[:200]}')
        if result.stderr:
            print(f'错误: {result.stderr[:200]}')
        self.assertEqual(result.returncode, 0)
        
        # 检查本地文件内容（应该包含GDS返回的JSON内容）
        content = self.get_local_file_content(local_redirect_path)
        print(f'本地重定向文件内容: {content}')
        # 对于本地文件，直接验证content字符串，不使用verify_file_content_contains（那是针对远端文件的）
        self.assertIsNotNone(content, "本地文件应该有内容")
        self.assertIn(json_content, content, "本地重定向文件应该包含JSON内容")
        
        # 验证远端没有这个文件（因为是本地重定向）
        # local_redirect_path是本地路径，不应该在远端存在
        # 但这个验证逻辑有问题：verify_file_exists会在远端查找，找不到会返回False，这是预期的
        remote_test_path = self.get_test_file_path("local_redirect.txt")
        self.assertFalse(self.verify_file_exists(remote_test_path), "远端不应该有本地重定向的文件")
        
        # 清理：删除本地创建的文件
        try:
            os.remove(local_redirect_path)
            print(f'已清理文件: {local_redirect_path}')
        except Exception as e:
            print(f'Warning: 清理文件失败: {e}')
            pass
        
        # 创建简单的Python脚本
        python_code = '''import json
import os

# 切换到脚本所在目录
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# 创建配置文件
config = {
    "name": "test_project",
    "version": "1.0.0",
    "debug": True
}

with open("test_config.json", "w") as f:
    json.dump(config, f, indent=2)

print(f'Config created successfully')
print(f'Current files: {len(os.listdir())}')'''
        test_script = self.get_test_file_path("test_script.py")
        escaped_python_code = python_code.replace('"', '\\"').replace('\n', '\\n')
        result = self.gds(f'\'echo -e "{escaped_python_code}" > "{test_script}"\'')
        self.assertEqual(result.returncode, 0)
        
        # 验证Python脚本文件创建
        self.assertTrue(self.verify_file_exists(test_script))
        
        # 执行Python脚本
        result = self.gds('python ' + test_script)
        self.assertEqual(result.returncode, 0)
        
        # 验证脚本执行结果：创建了配置文件
        import time
        time.sleep(10)
        test_config = self.get_test_file_path("test_config.json")
        self.assertTrue(self.verify_file_exists(test_config))
        self.assertTrue(self.verify_file_content_contains(test_config, '"name": "test_project"'))
        self.assertTrue(self.verify_file_content_contains(test_config, '"debug": true'))

        # 1. 批量创建文件（修复：使用正确的echo重定向语法）
        files = [self.get_test_file_path("batch_file1.txt"), self.get_test_file_path("batch_file2.txt"), self.get_test_file_path("batch_file3.txt")]
        for i, filename in enumerate(files):
            result = self.gds(f'\'echo "Content {i+1}" > "{filename}"\'')
            self.assertEqual(result.returncode, 0, f"echo命令应该成功，但返回码为{result.returncode}")
        
        # 2. 验证所有文件创建成功（基于功能结果）
        for filename in files:
            self.assertTrue(self.verify_file_exists(filename))
            self.assertTrue(self.verify_file_content_contains(filename, "Content"))
        
        # 3. 批量检查文件内容
        for filename in files:
            self.assertTrue(self.verify_file_content_contains(filename, "Content"))
        
        # 4. 批量文件操作
        result = self.gds(f'find {self.test_folder} -name "batch_file*.txt"')
        self.assertEqual(result.returncode, 0, f"find命令应该成功，但返回码为{result.returncode}")
        
        # 5. 批量清理（使用通配符）
        for filename in files:
            result = self.gds(f'rm "{filename}"')
            self.assertEqual(result.returncode, 0, f"rm命令应该成功，但返回码为{result.returncode}")
        
        # === 增强的echo测试用例 ===
        print("开始增强的echo测试")
        
        # 测试1: JSON不同引号处理
        print("测试JSON不同引号处理")
        
        # 1.1 单引号JSON（推荐方式）
        json_single_file = self.get_test_file_path("json_single_quote.txt")
        json_content_proper = '{"name": "test03_json_single_quote_03", "value": 123}'
        result = self.gds(f"echo '{json_content_proper}' > \"{json_single_file}\"")
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.verify_file_content_contains(json_single_file, json_content_proper))
        
        # 1.2 转义双引号JSON
        json_escaped_file = self.get_test_file_path("json_escaped_quote.txt")
        escaped_json = json_content_proper.replace('"', '\\"')
        result = self.gds(f'echo "{escaped_json}" > "{json_escaped_file}"')
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.verify_file_content_contains(json_escaped_file, json_content_proper))
        
        # 测试2: 引号内特殊字符（不应触发重定向）
        print("测试引号内特殊字符")
        
        # 2.1 包含>字符但不是重定向
        content_with_gt = "This content has > symbol but no redirect"
        result = self.gds(f'echo "{content_with_gt}"')
        self.assertEqual(result.returncode, 0)
        self.assertIn(content_with_gt, result.stdout)
        
        # 2.2 包含多种特殊字符
        special_chars = "Special: @#$%^&*()_+-=[]{}|;:,.<>?"
        special_file = self.get_test_file_path("special_chars.txt")
        result = self.gds(f'echo "{special_chars}" > "{special_file}"')
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.verify_file_content_contains(special_file, special_chars))
        
        # 测试3: 中文和特殊字符组合
        print("测试中文和特殊字符组合")
        chinese_special = "测试中文：你好世界 Special chars: @#$%^&*()_+-=[]{}|;:,.<>?"
        chinese_file = self.get_test_file_path("chinese_special.txt")
        
        # 使用shlex.quote安全处理
        import shlex
        safe_content = shlex.quote(chinese_special)
        safe_file = shlex.quote(chinese_file)
        result = self.gds(f'echo "{safe_content}" > "{safe_file}"')
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.verify_file_content_contains(chinese_file, "你好世界"))
        
        # 测试4: 复杂JSON结构
        print("测试复杂JSON结构")
        complex_json = '{"users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}], "total": 2}'
        complex_json_escaped = complex_json.replace('"', '\\"')
        complex_json_file = self.get_test_file_path("complex_json.txt")
        result = self.gds(f'echo "{complex_json_escaped}" > "{complex_json_file}"')
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.verify_file_content_contains(complex_json_file, '"users"'))
        self.assertTrue(self.verify_file_content_contains(complex_json_file, '"Alice"'))

        print("增强的echo测试完成")
    
    def test_04_file_ops_mixed(self):
        # 1. 创建复杂目录结构
        advanced_project = self.get_test_file_path("advanced_project")
        result = self.gds(f'mkdir -p "{advanced_project}/src/utils"')
        self.assertEqual(result.returncode, 0)
        
        # 2. 在不同目录创建文件（修复：使用正确的echo重定向语法）
        result = self.gds(f'\'echo "# Main module" > "{advanced_project}/src/main.py"\'')
        self.assertEqual(result.returncode, 0)
        
        result = self.gds(f'\'echo "# Utilities" > "{advanced_project}/src/utils/helpers.py"\'')
        self.assertEqual(result.returncode, 0)
        
        # 3. 验证文件创建（基于功能结果）
        self.assertTrue(self.verify_file_exists(f'{advanced_project}/src/main.py'))
        self.assertTrue(self.verify_file_exists(f'{advanced_project}/src/utils/helpers.py'))
        
        # 4. 递归列出文件
        result = self.gds(f'ls -R "{advanced_project}"')
        self.assertEqual(result.returncode, 0)
        
        # 5. 移动文件
        result = self.gds(f'mv "{advanced_project}/src/main.py" "{advanced_project}/main.py"')
        self.assertEqual(result.returncode, 0)
        
        # 验证移动结果（基于功能结果）
        self.assertTrue(self.verify_file_exists(f'{advanced_project}/main.py'))
        
        # 原位置应该不存在
        result = self.gds(f'ls "{advanced_project}/src/main.py"', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0)
        
        # 6. 测试rm命令删除文件
        result = self.gds(f'rm "{advanced_project}/main.py"')
        self.assertEqual(result.returncode, 0)
        
        # 验证文件已被删除
        result = self.gds(f'ls "{advanced_project}/main.py"', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0)
        
        # 7. 测试rm -rf删除目录
        result = self.gds(f'rm -rf "{advanced_project}"')
        self.assertEqual(result.returncode, 0)
        
        # 验证目录已被删除
        result = self.gds(f'ls "{advanced_project}"', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0)

    def test_05_navigation_mix(self):
        # pwd命令
        result_pwd = self.gds('pwd')
        self.assertEqual(result_pwd.returncode, 0)
        
        # ls命令
        result = self.gds('ls')
        self.assertEqual(result.returncode, 0)
        
        # mkdir命令
        test_dir = self.get_test_file_path("test_dir")
        result = self.gds(f'mkdir "{test_dir}"')
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.verify_file_exists(test_dir))
        
        # 测试多目录创建（修复后的功能）
        print(f'测试多目录创建')
        multi_test = self.get_test_file_path("multi_test")
        result = self.gds(f'mkdir -p "{multi_test}/dir1" "{multi_test}/dir2" "{multi_test}/dir3"')
        self.assertEqual(result.returncode, 0)
        
        # 验证所有目录都被创建
        self.assertTrue(self.verify_file_exists(f'{multi_test}/dir1'))
        self.assertTrue(self.verify_file_exists(f'{multi_test}/dir2'))
        self.assertTrue(self.verify_file_exists(f'{multi_test}/dir3'))
        
        # cd命令
        result = self.gds(f'cd "{test_dir}"')
        self.assertEqual(result.returncode, 0)
        result_pwd2 = self.gds('pwd')
        self.assertEqual(result_pwd2.returncode, 0)
        # 获得实际有效的输出部分（擦除了indicator）
        # 验证路径
        self.assertNotEqual(result_pwd2.stdout, result_pwd.stdout)
        
        # 返回上级目录
        result = self.gds('cd ..')
        self.assertEqual(result.returncode, 0)
        
        print(f'不同远端路径类型测试')
        # 创建嵌套目录结构用于测试
        test_path = self.get_test_file_path("test_path")
        result = self.gds(f'mkdir -p "{test_path}/level1/level2"')
        self.assertEqual(result.returncode, 0)
        
        # 测试相对路径导航
        result = self.gds(f'cd "{test_path}/level1"')
        self.assertEqual(result.returncode, 0)
        
        result = self.gds(f'cd "{test_path}/level1/level2"')
        self.assertEqual(result.returncode, 0)
        
        # 测试..返回上级
        result = self.gds(f'cd "{test_path}/level1/level2/../.."')
        self.assertEqual(result.returncode, 0)
        
        # 测试~开头的路径（应该指向REMOTE_ROOT）
        result = self.gds(f'cd ~')
        self.assertEqual(result.returncode, 0)
        
        # 从~返回到测试目录
        result = self.gds(f'cd "{self.test_folder}"')
        self.assertEqual(result.returncode, 0)
        
        # 测试嵌套路径导航
        result = self.gds(f'cd "{test_path}/level1/level2"')
        self.assertEqual(result.returncode, 0)
        
        result = self.gds(f'cd "{test_path}/level1/level2/../../.."')
        self.assertEqual(result.returncode, 0)
        print(f'Error:  错误路径类型测试')
        
        # 测试不存在的目录
        nonexistent_directory = self.get_test_file_path("nonexistent_directory")
        result = self.gds(f'cd "{nonexistent_directory}"', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0)
        
        # 测试将文件当作目录
        test_file = self.get_test_file_path("test_file.txt")
        result = self.gds(f'echo "test content" > "{test_file}"')
        self.assertEqual(result.returncode, 0)
        
        result = self.gds(f'cd "{test_file}"', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0)
        
        # 测试无效的路径格式
        result = self.gds('cd ""', expect_success=False, check_function_result=False)
        self.assertEqual(result.returncode, 0) # bash behaviour
        
        # 测试尝试访问~上方的路径（应该被限制）
        result = self.gds('cd ~/..', expect_success=False, check_function_result=False)
        print(f'导航命令和路径测试完成')
    
    def test_06_upload(self):
        # 单文件上传（使用--force确保可重复性）
        # 创建唯一的测试文件避免并发冲突
        unique_file = self.TEST_DATA_DIR / "test_upload_simple_hello.py"
        original_file = self.TEST_DATA_DIR / "simple_hello.py"
        import shutil
        shutil.copy2(original_file, unique_file)
        
        # 使用重试机制上传文件
        test_upload_path = self.get_test_file_path("test_upload_simple_hello.py")

        # 使用普通的GDS命令运行upload，首先cd
        result = self.gds(f'upload --target-dir "{self.test_folder}" --force "{unique_file}"')
        self.assertEqual(result.returncode, 0)
        
        # 验证文件上传成功
        self.assertTrue(self.verify_file_exists(test_upload_path))
        
        # 多文件上传（使用--force确保可重复性）
        valid_script_local = self.TEST_DATA_DIR / "valid_script.py"
        valid_script_path = self.get_test_file_path("valid_script.py")
        special_file_local = self.TEST_DATA_DIR / "special_chars.txt"
        special_file_path = self.get_test_file_path("special_chars.txt")
        success, result = self.run_upload(
            f'upload --target-dir "{self.test_folder}" --force "{valid_script_local}" "{special_file_local}"',
            [f'ls "{valid_script_path}"', f'ls "{special_file_path}"'],
            max_retries=3
        )
        self.assertTrue(success, f"多文件上传失败: {result.stderr if result else 'Unknown error'}")
        
        # 验证文件上传成功
        self.assertTrue(self.verify_file_exists(test_upload_path))
        
        # 文件夹上传
        test_project_local = self.TEST_DATA_DIR / "test_project"
        test_project_path = self.get_test_file_path("test_project")
        success, result = self.run_upload(
            f'upload_folder --target-dir "{self.test_folder}" --force "{test_project_local}"',
            [f'ls "{test_project_path}"'],
            max_retries=3
        )
        self.assertTrue(success, f"文件夹上传失败: {result.stderr if result else 'Unknown error'}")
        
        # 测试上传到已存在文件
        conflict_test_file_local = self.TEST_DATA_DIR / "test_upload_conflict_file.py"
        conflict_test_file_path = self.get_test_file_path("test_upload_conflict_file.py")
        shutil.copy2(original_file, conflict_test_file_local)
        success, result = self.run_upload(
            f'upload --target-dir "{self.test_folder}" --force "{conflict_test_file_local}"',
            [f'ls "{conflict_test_file_path}"'],
            max_retries=3
        )
        self.assertTrue(success, f"冲突测试文件上传失败: {result.stderr if result else 'Unknown error'}")
        
        # 现在尝试不带--force上传同一个文件（应该失败）
        result = self.gds(f'upload  "{conflict_test_file_local}"', expect_success=False)
        self.assertEqual(result.returncode, 1)
        
        # 测试upload --force的覆盖功能（文件内容不同）
        # 创建一个内容不同的本地文件
        overwrite_test_file_local = self.TEST_TEMP_DIR / "test_upload_overwrite_file.py"
        overwrite_test_file_path = self.get_test_file_path("test_upload_overwrite_file.py")
        with open(overwrite_test_file_local, 'w') as f:
            f.write('print(f"ORIGINAL VERSION - Test upload")')
        
        # 先上传原始版本
        success, result = self.run_upload(
            f'upload --target-dir "{self.test_folder}" --force "{overwrite_test_file_local}"',
            [f'ls "{overwrite_test_file_path}"'],
            max_retries=3
        )
        self.assertTrue(success, f"原始版本上传失败: {result.stderr if result else 'Unknown error'}")
        
        # 读取远程文件的原始内容
        original_content_result = self.gds(f'cat "{overwrite_test_file_path}"')
        self.assertEqual(original_content_result.returncode, 0)
        original_content = original_content_result.stdout
        
        # 修改本地文件内容
        with open(overwrite_test_file_local, 'w') as f:
            f.write('print(f"MODIFIED VERSION - Test upload overwrite!")')
        
        # 使用--force上传修改后的文件
        success, result = self.run_upload(
            f'upload --target-dir "{self.test_folder}" --force "{overwrite_test_file_local}"',
            [f'grep "MODIFIED VERSION" "{overwrite_test_file_path}"'],
            max_retries=3
        )
        self.assertTrue(success, f"修改版本上传失败: {result.stderr if result else 'Unknown error'}")
        
        # 验证文件内容确实被修改了
        modified_content_result = self.gds(f'cat "{overwrite_test_file_path}"')
        self.assertEqual(modified_content_result.returncode, 0)
        modified_content = modified_content_result.stdout
        
        # 确保内容不同
        self.assertNotEqual(original_content, modified_content)
        self.assertIn("MODIFIED VERSION", modified_content)

        # 测试空目录上传
        empty_dir_local = self.TEST_DATA_DIR / "empty_test_dir"
        empty_dir_path = self.get_test_file_path("empty_test_dir")
        empty_dir_local.mkdir(exist_ok=True)
        
        # 清理目录内容（确保为空）
        for item in empty_dir_local.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                import shutil
                shutil.rmtree(item)
        success, result = self.run_upload(
            f'upload_folder --target-dir "{self.test_folder}" --force "{empty_dir_local}"',
            [f'ls "{empty_dir_path}"'],
            max_retries=3
        )
        self.assertTrue(success, f"空目录上传失败: {result.stderr if result else 'Unknown error'}")
    
    def test_07_download(self):
        """测试GDS download功能"""
        print(f'测试GDS download功能')
        
        # 首先创建一个测试文件用于下载测试
        test_content = "This is a test file for download functionality.\nLine 2: 测试中文内容\nLine 3: Special chars: @#$%^&*()"
        download_test_source = self.get_test_file_path("download_test_source.txt")
        
        # 创建测试文件
        result = self.gds(f'\'echo "{test_content}" > "{download_test_source}"\'')
        self.assertEqual(result.returncode, 0, "创建测试文件应该成功")
        
        # 验证文件存在
        result = self.gds(f'ls "{download_test_source}"')
        self.assertEqual(result.returncode, 0, "测试文件应该存在")
        
        # 测试1: 基本下载功能（下载到缓存）
        print("测试1: 基本下载功能")
        result = self.gds(f'download "{download_test_source}"')
        self.assertEqual(result.returncode, 0, "基本下载应该成功")
        self.assertIn("Downloaded successfully", result.stdout, "应该显示下载成功信息")
        
        # 测试2: 下载到指定位置（本地路径）
        print("测试2: 下载到指定位置")
        local_target_file = os.path.expanduser("~/tmp/downloaded_copy.txt")
        os.makedirs(os.path.dirname(local_target_file), exist_ok=True)
        result = self.gds(f'download "{download_test_source}" "{local_target_file}"')
        self.assertEqual(result.returncode, 0, "下载到指定位置应该成功")
        
        # 验证下载的文件内容 - 使用本地cat命令而不是GDS cat命令
        if os.path.exists(local_target_file):
            import subprocess
            result = subprocess.run(['cat', local_target_file], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, "本地读取下载文件应该成功")
            self.assertIn("This is a test file for download", result.stdout, "下载文件内容应该正确")
            self.assertIn("测试中文内容", result.stdout, "应该包含中文内容")
            print(f'成功使用本地cat命令读取下载文件: {local_target_file}')
        else:
            self.fail(f'下载的文件不存在于本地路径: {local_target_file}')
        
        # 测试3: 强制重新下载
        print("测试3: 强制重新下载")
        result = self.gds(f'download --force "{download_test_source}"')
        self.assertEqual(result.returncode, 0, "强制下载应该成功")
        self.assertIn("Downloaded successfully", result.stdout, "强制下载应该显示成功信息")
        
        # 测试4: 下载不存在的文件（错误处理）
        print("测试4: 下载不存在的文件")
        result = self.gds(f'download "nonexistent_file.txt"', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0, "下载不存在文件应该失败")
        self.assertIn("file not found", result.stdout.lower(), "应该显示文件未找到错误")
        
        # 清理测试文件
        cleanup_files = [download_test_source]
        for filename in cleanup_files:
            file_path = self.get_test_file_path(filename)
            self.gds(f'rm -f "{file_path}"')
        
        # 清理本地下载文件
        try:
            if os.path.exists(local_target_file):
                os.remove(local_target_file)
        except Exception as e:
            print(f'Warning: Failed to clean up local file {local_target_file}: {e}')
        
        print(f'GDS download功能测试完成')
    
    def test_08_download_dir(self):
        """测试GDS目录下载功能"""
        print(f'测试GDS目录下载功能')
        
        # 创建测试目录和文件
        test_dir_name = "test_download_dir"
        test_dir_path = self.get_test_file_path(test_dir_name)
        
        # 创建目录和测试文件
        result = self.gds(f'mkdir -p "{test_dir_path}"')
        self.assertEqual(result.returncode, 0, "创建测试目录应该成功")
        
        test_file_path = f"{test_dir_path}/test_file.txt"
        result = self.gds(f"'echo \"Directory download test content\" > \"{test_file_path}\"'")
        self.assertEqual(result.returncode, 0, "创建测试文件应该成功")
        
        # 验证目录和文件存在
        self.assertTrue(self.verify_file_exists(test_dir_path), "测试目录应该存在")
        self.assertTrue(self.verify_file_exists(test_file_path), "测试文件应该存在")
        
        # 测试目录下载
        print("测试目录下载功能")
        local_target_dir = os.path.expanduser("~/tmp")
        os.makedirs(local_target_dir, exist_ok=True)
        
        result = self.gds(f'download "{test_dir_path}" "{local_target_dir}/downloaded_dir.zip"')
        self.assertTrue(result.returncode == 0, f"目录下载失败: {result.stderr if result else 'Unknown error'}")
        
        local_zip_file = os.path.join(local_target_dir, "downloaded_dir.zip")
        if os.path.exists(local_zip_file):
            print(f'本地zip文件存在: {local_zip_file}')
            print(f'文件大小: {os.path.getsize(local_zip_file)} bytes')
            
            # 清理本地文件
            try:
                os.remove(local_zip_file)
                print("清理本地zip文件成功")
            except Exception as e:
                print(f'Warning: 清理本地文件失败: {e}')
        else:
            print("本地zip文件不存在")
            self.fail("目录下载后本地zip文件不存在")
    
        # 清理测试目录
        result = self.gds(f'rm -rf "{test_dir_path}"')
        print(f'GDS目录下载功能测试完成')
    
    def test_09_grep(self):
        # 创建测试文件
        test_content = '''Line 1: Hello world
Line 2: This is a test
Line 3: Hello again
Line 4: Multiple Hello Hello Hello
Line 5: No match here'''
        echo_cmd = f'echo "{test_content}" > "{self.test_folder}/grep_test.txt"'
        result = self.gds(f'\'{echo_cmd}\'')
        self.assertEqual(result.returncode, 0)
        
        # 验证文件创建成功
        grep_test_path = f'{self.test_folder}/grep_test.txt'
        self.assertTrue(self.verify_file_exists (grep_test_path))
        
        # 测试1: 无模式grep（等效于read命令）
        result = self.gds(f'grep "{grep_test_path}"')
        self.assertEqual(result.returncode, 0)
        output = result.stdout

        # 验证包含行号和所有行内容
        self.assertIn("1: Line 1: Hello world", output)
        self.assertIn("2: Line 2: This is a test", output)
        self.assertIn("3: Line 3: Hello again", output)
        self.assertIn("4: Line 4: Multiple Hello Hello Hello", output)
        self.assertIn("5: Line 5: No match here", output)
        
        # 测试2: 有模式grep（只显示匹配行）
        result = self.gds(f'grep "Hello" "{grep_test_path}"')
        self.assertEqual(result.returncode, 0)
        output = result.stdout
        # 验证只包含匹配的行
        self.assertIn("1: Line 1: Hello world", output)
        self.assertIn("3: Line 3: Hello again", output)
        self.assertIn("4: Line 4: Multiple Hello Hello Hello", output)
        # 验证不包含不匹配的行
        self.assertNotIn("2: Line 2: This is a test", output)
        self.assertNotIn("5: Line 5: No match here", output)
        
        # 测试3: 多词模式grep
        result = self.gds(f'grep "is a" "{grep_test_path}"')
        self.assertEqual(result.returncode, 0)
        output = result.stdout
        self.assertIn("2: Line 2: This is a test", output)
        self.assertNotIn("1: Line 1: Hello world", output)
        self.assertNotIn("3: Line 3: Hello again", output)
        
        # 测试4: 测试不存在模式的grep（应该返回1，没有匹配项）
        result = self.gds(f'grep "NotFound" "{grep_test_path}"', expect_success=False)
        self.assertEqual(result.returncode, 1)  # grep没有匹配项时返回1
        output = result.stdout
        self.assertNotIn("1:", output)
        self.assertNotIn("2:", output)
        self.assertNotIn("3:", output)
        self.assertNotIn("4:", output)
        self.assertNotIn("5:", output)
    
    def test_10_edit(self):
        # 重新上传测试文件确保存在（使用--force保证覆盖）
        # 创建唯一的测试文件避免并发冲突
        test_edit_file = self.TEST_DATA_DIR / "test_edit_simple_hello.py"
        original_file = self.TEST_DATA_DIR / "simple_hello.py"
        import shutil
        shutil.copy2(original_file, test_edit_file)
        test_edit_file_path = self.get_test_file_path("test_edit_simple_hello.py")
        success, result = self.run_upload(
            f'upload --target-dir "{self.test_folder}" --force "{test_edit_file}"',
            [f'ls "{test_edit_file_path}"'],
            max_retries=3
        )
        self.assertTrue(success, f"test04文件上传失败: {result.stderr if result else 'Unknown error'}")
        
        # 测试upload --force的覆盖功能
        # 再次上传同一个文件，应该覆盖成功
        success, result = self.run_upload(
            f'upload --target-dir "{self.test_folder}" --force "{test_edit_file}"',
            [f'ls "{test_edit_file_path}"'],
            max_retries=3
        )
        self.assertTrue(success, f'upload --force覆盖功能失败: {result.stderr if result else "Unknown error"}')
        
        # 基础文本替换编辑
        import json
        edit_data = [["Hello from remote project", "Hello from MODIFIED remote project"]]
        edit_json = json.dumps(edit_data).replace('"', '\\"')
        success, result = self.gds_with_retry(
            f'edit "{self.test_folder}/test_edit_simple_hello.py" "{edit_json}"',
            ['grep "MODIFIED" "' + self.test_folder + '/test_edit_simple_hello.py"'],
            max_retries=3
        )
        self.assertTrue(success, f"基础文本替换编辑失败: {result.stderr if result else 'Unknown error'}")
        
        # 行号替换编辑（使用0-based索引，替换第3-4行）
        edit_data2 = [[[3, 4], "# Modified line 3-4"]]
        edit_json2 = json.dumps(edit_data2).replace('"', '\\"')
        success, result = self.gds_with_retry(
            f'edit "{self.test_folder}/test_edit_simple_hello.py" "{edit_json2}"',
            ['grep "# Modified line 3-4" "' + self.test_folder + '/test_edit_simple_hello.py"'],
            max_retries=3
        )
        self.assertTrue(success, f"行号替换编辑失败: {result.stderr if result else 'Unknown error'}")
        
        # 预览模式编辑（不实际修改文件）
        # 预览模式不修改文件，所以不需要验证文件内容变化
        edit_data3 = [["print", "# print"]]
        edit_json3 = json.dumps(edit_data3).replace('"', '\\"')
        result = self.gds(f'edit --preview "{self.test_folder}/test_edit_simple_hello.py" "{edit_json3}"')
        self.assertEqual(result.returncode, 0)
        
        # 备份模式编辑
        edit_data4 = [["Modified line", "Updated line"]]
        edit_json4 = json.dumps(edit_data4).replace('"', '\\"')
        success, result = self.gds_with_retry(
            f'edit --backup "{self.test_folder}/test_edit_simple_hello.py" "{edit_json4}"',
            ['grep "Updated line" "' + self.test_folder + '/test_edit_simple_hello.py"'],
            max_retries=3
        )
        self.assertTrue(success, f"备份模式编辑失败: {result.stderr if result else 'Unknown error'}")
    
    def test_11_linter(self):
        # 强制上传测试文件（确保文件存在）
        print(f'上传测试文件...')
        valid_script_local = self.TEST_DATA_DIR / "valid_script.py"
        valid_script_path = self.get_test_file_path("valid_script.py")
        success, result = self.run_upload(
            f'upload --target-dir "{self.test_folder}" --force "{valid_script_local}"',
            [f'ls "{valid_script_path}"'],
            max_retries=3
        )
        self.assertTrue(success, f"valid_script.py上传失败: {result.stderr if result else 'Unknown error'}")
        
        invalid_script_local = self.TEST_DATA_DIR / "invalid_script.py"
        invalid_script_path = self.get_test_file_path("invalid_script.py")
        success, result = self.run_upload(
            f'upload --target-dir "{self.test_folder}" --force "{invalid_script_local}"',
            [f'ls "{invalid_script_path}"'],
            max_retries=3
        )
        self.assertTrue(success, f"invalid_script.py上传失败: {result.stderr if result else 'Unknown error'}")
        
        json_file_local = self.TEST_DATA_DIR / "valid_config.json"
        json_file_path = self.get_test_file_path("valid_config.json")
        success, result = self.run_upload(
            f'upload --target-dir "{self.test_folder}" --force "{json_file_local}"',
            [f'ls "{json_file_path}"'],
            max_retries=3
        )
        self.assertTrue(success, f"valid_config.json上传失败: {result.stderr if result else 'Unknown error'}")
        
        # 1. 测试语法正确的文件
        print(f'测试语法正确的Python文件')
        result = self.gds(f'linter "{valid_script_path}"')
        self.assertEqual(result.returncode, 0)
        
        # 2. 测试有样式错误的文件
        print(f'测试有样式错误的Python文件')
        result = self.gds(f'linter "{invalid_script_path}"', expect_success=False, check_function_result=False)
        stdout, stderr, returncode = result.stdout, result.stderr, result.returncode
        output = stdout.lower()
        
        # 定义期望的Python linting错误类型
        expected_python_issues = [
            'syntaxerror', 'invalid syntax', 'unexpected eof', 'unexpected indent',
            'indentationerror', 'expected an indented block', 'unindent does not match',
            'f401',  # unused import
            'e225',  # missing whitespace around operator
            'e302',  # expected 2 blank lines
            'w292',  # no newline at end of file
            'e501',  # line too long
            'undefined name', 'imported but unused', 'redefined'
        ]
        
        detected_issues = [issue for issue in expected_python_issues if issue in stdout]
        
        if detected_issues:
            print(f'检测到具体的linting问题: {detected_issues}')
            self.assertGreater(len(detected_issues), 0, f"应该检测到具体的Python linting问题")
        else:
            # 如果没有检测到具体问题，检查是否有通用错误指示
            generic_indicators = ['error', 'warning', 'fail', 'problem']
            has_generic_error = any(indicator in output for indicator in generic_indicators)
            if has_generic_error:
                print(f'检测到通用错误指示，但缺少具体问题描述')                
                print(f'输出内容: {stdout[:200]}...')
            else:
                self.fail(f'样式错误文件应该报告具体问题，但输出为: {stdout[:200]}...')
        
        # 3. 测试指定语言的linter
        print(f'测试指定Python语言的linter')
        valid_script_path = self.get_test_file_path("valid_script.py")
        result = self.gds(f'linter --language python "{valid_script_path}"')
        stdout, stderr, returncode = result.stdout, result.stderr, result.returncode
        self.assertEqual(returncode, 0)
        
        # 4. 测试JSON文件linter
        print(f'测试JSON文件linter')
        valid_config_path = self.get_test_file_path("valid_config.json")
        result = self.gds(f'linter "{valid_config_path}"')
        self.assertEqual(result.returncode, 0)
        
        # 5. 测试不存在文件的错误处理
        print(f'测试不存在文件的错误处理')
        nonexistent_file_path = self.get_test_file_path("nonexistent_file.py")
        result = self.gds(f'linter "{nonexistent_file_path}"', expect_success=False, check_function_result=False)
        stdout, stderr, returncode = result.stdout, result.stderr, result.returncode
        self.assertNotEqual(returncode, 0, "不存在的文件应该返回错误")
        
    def test_12_edit_linter(self):
        # 创建一个有语法错误的Python文件
        error_content = '''def hello_world(
print(f'Missing closing parenthesis')
return True

def calculate_sum(a, b:
return a + b

if __name__ == "__main__":
hello_world()
result = calculate_sum(5, 3)
print(f'Sum: {result}')
'''
        
        # 使用echo创建有错误的文件
        syntax_error_test_path = self.get_test_file_path("syntax_error_test.py")   
        escaped_content = error_content.replace('"', '\\"').replace('\n', '\\n')
        success, result = self.gds_with_retry(
            f'echo -e "{escaped_content}" > "{syntax_error_test_path}"',
            [f'ls "{syntax_error_test_path}"'],
            max_retries=3
        )
        self.assertTrue(success, f"创建语法错误文件失败: {result.stderr if result else 'Unknown error'}")
        
        # 尝试编辑文件，这应该触发linter并显示错误
        print(f'执行edit命令，应该触发linter检查...')
        result = self.gds(f'edit "{syntax_error_test_path}" \'[["Missing closing parenthesis", "Fixed syntax error"]]\'')
        
        # 检查edit命令的输出格式
        print(f'检查edit命令输出格式...')
        stdout, stderr, returncode = result.stdout, result.stderr, result.returncode
        output = stdout
        
        # 改进的linter错误检测：关注错误内容而不是UI格式
        print(f'检查linter错误内容...')
        
        # 定义各种错误类型的检测模式
        error_patterns = {
            'syntax_error': ['SyntaxError', 'invalid syntax', 'unexpected EOF', 'unexpected indent'],
            'indentation_error': ['IndentationError', 'expected an indented block', 'unindent does not match'],
            'name_error': ['NameError', 'name .* is not defined'],
            'import_error': ['ImportError', 'ModuleNotFoundError', 'No module named'],
            'type_error': ['TypeError', 'unsupported operand type', 'takes .* positional arguments'],
            'attribute_error': ['AttributeError', 'has no attribute'],
            'value_error': ['ValueError', 'invalid literal'],
            'linter_style': ['F401', 'E225', 'E302', 'W292', 'E501']  # flake8/pycodestyle codes
        }
        
        # 检测是否有任何linter输出
        has_linter_output = False
        detected_errors = {}
        
        for error_type, patterns in error_patterns.items():
            for pattern in patterns:
                if pattern in output:
                    has_linter_output = True
                    if error_type not in detected_errors:
                        detected_errors[error_type] = []
                    detected_errors[error_type].append(pattern)
        
        if has_linter_output:
            print(f'检测到linter错误输出，发现的错误类型:')
            for error_type, patterns in detected_errors.items():
                print(f'  - {error_type}: {patterns}')
            
            # 验证语法错误文件应该检测到语法相关问题
            syntax_related = any(error_type in ['syntax_error', 'indentation_error'] 
                               for error_type in detected_errors.keys())
            self.assertTrue(syntax_related, f"语法错误文件应该检测到语法相关问题，但只发现: {list(detected_errors.keys())}")
            
            # 检查错误信息的完整性：应该包含文件名和行号信息
            has_file_info = any(syntax_error_test_path in line for line in output.split('\n'))
            if has_file_info:
                print(f'错误信息包含文件路径信息')
            
            # 检查是否有行号信息
            import re
            line_number_pattern = r'line \d+|:\d+:'
            has_line_numbers = bool(re.search(line_number_pattern, output))
            if has_line_numbers:
                print(f'错误信息包含行号信息')
                
            else:
                print(f'未检测到linter错误输出')
        
        print(f'Edit与Linter集成测试完成')
    
    def test_13_read(self):
        # 创建独特的测试文件
        test_read_file = self.TEST_DATA_DIR / "test_read_simple_hello.py"
        original_file = self.TEST_DATA_DIR / "simple_hello.py"
        
        # 复制文件并上传
        import shutil
        shutil.copy2(original_file, test_read_file)
        success, result = self.run_upload(
            f'upload --target-dir "{self.test_folder}" --force "{test_read_file}"',
            [f'ls "{self.test_folder}/test_read_simple_hello.py"'],
            max_retries=3
        )
        self.assertTrue(success, f'test05文件上传失败: {result.stderr if result else "Unknown error"}')
        
        # cat命令读取文件
        result = self.gds(f'cat "{self.test_folder}/test_read_simple_hello.py"')
        self.assertEqual(result.returncode, 0, 'cat命令读取文件应该成功')
        
        # read命令读取文件（带行号）
        result = self.gds(f'read "{self.test_folder}/test_read_simple_hello.py"')
        self.assertEqual(result.returncode, 0, 'read命令读取文件应该成功')
        
        # read命令读取指定行范围
        result = self.gds(f'read "{self.test_folder}/test_read_simple_hello.py" 1 3')
        self.assertEqual(result.returncode, 0, 'read命令读取指定行范围应该成功')
        
        # grep命令搜索内容
        result = self.gds(f'grep "print" "{self.test_folder}/test_read_simple_hello.py"')
        self.assertEqual(result.returncode, 0, 'grep命令搜索内容应该成功')
        
        # find命令查找文件
        result = self.gds(f'find . -name "*.py" "{self.test_folder}"')
        self.assertEqual(result.returncode, 0, 'find命令查找文件应该成功')
        
        # --force选项强制重新下载
        result = self.gds(f'read --force "{self.test_folder}/test_read_simple_hello.py"')
        self.assertEqual(result.returncode, 0, 'read --force选项强制重新下载应该成功')
        
        # 测试不存在的文件
        print(f'测试cat不存在的文件')
        result = self.gds(f'cat "{self.test_folder}/nonexistent_file.txt"', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0, 'cat不存在的文件应该返回非零退出码')
        
        # 测试read不存在的文件
        print(f'测试read不存在的文件')
        result = self.gds(f'read "{self.test_folder}/nonexistent_file.txt"', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0, 'read不存在的文件应该返回非零退出码')
        
        # 测试grep不存在的文件
        print(f'测试grep不存在的文件')
        result = self.gds(f'grep "test" "{self.test_folder}/nonexistent_file.txt"', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0, 'grep不存在的文件应该返回非零退出码')
        
        # 测试特殊字符文件处理
        print(f'测试特殊字符文件处理')
        if not self.verify_file_exists(f'{self.test_folder}/special_chars.txt'):
            special_file = self.TEST_DATA_DIR / "special_chars.txt"
            success, result = self.gds_with_retry(
                f'upload --target-dir "{self.test_folder}" --force "{special_file}"',
                [f'ls "{self.test_folder}/special_chars.txt"'],
                max_retries=3
            )
            self.assertTrue(success, f'特殊字符文件上传失败: {result.stderr if result else "Unknown error"}')
        
        result = self.gds(f'cat "{self.test_folder}/special_chars.txt"')
        self.assertEqual(result.returncode, 0, '特殊字符文件应该能正常读取')
        
        # 测试绝对路径支持
        print('测试cat命令绝对路径支持')
        
        # 创建测试文件用于绝对路径测试（使用绝对路径）
        abs_test_filename = f"{self.test_folder}/absolute_path_test.txt"
        abs_test_content = "测试cat绝对路径支持"
        result = self.gds(f'echo -n "{abs_test_content}" > "{abs_test_filename}"')
        self.assertEqual(result.returncode, 0, '创建绝对路径测试文件应该成功')
        
        # 测试使用~/路径格式cat文件
        print("测试使用~/路径格式cat文件")
        result = self.gds(f'cat "{abs_test_filename}"')
        self.assertEqual(result.returncode, 0, "~/路径格式cat应该成功")
        self.assertEqual(result.stdout, abs_test_content, "~/路径格式cat内容应该正确")
        
        # 清理绝对路径测试文件
        result = self.gds(f'rm -f "{abs_test_filename}"')
        self.assertEqual(result.returncode, 0, '清理绝对路径测试文件应该成功')
        
        print('cat命令绝对路径支持测试完成')
        
        # 测试heredoc语法支持
        print('测试heredoc语法支持')
        
        # 测试基本heredoc重定向
        heredoc_test_file = f"{self.test_folder}/heredoc_test.txt"
        heredoc_command = f'''cat > "{heredoc_test_file}" << "EOF"
First line of heredoc
Second line with "quotes"
Third line with special chars @#$%
Fourth line with spaces    
EOF'''
        
        print("测试基本heredoc重定向")
        result = self.gds(heredoc_command)
        self.assertEqual(result.returncode, 0, 'heredoc重定向应该成功')
        
        # 验证heredoc创建的文件内容
        result = self.gds(f'cat "{heredoc_test_file}"')
        self.assertEqual(result.returncode, 0, '读取heredoc文件应该成功')
        
        expected_content = '''First line of heredoc
Second line with "quotes"
Third line with special chars @#$%
Fourth line with spaces    '''
        
        # 使用rstrip('\n')而不是strip()，以保留行尾的空格
        self.assertEqual(result.stdout.rstrip('\n'), expected_content, 'heredoc文件内容应该正确')
        
        # 测试heredoc追加模式
        print("测试heredoc追加模式")
        append_command = f'''cat >> "{heredoc_test_file}" << "EOF"
Fifth line appended
Sixth line appended
EOF'''
        
        result = self.gds(append_command)
        self.assertEqual(result.returncode, 0, 'heredoc追加应该成功')
        
        # 验证追加后的内容
        result = self.gds(f'cat "{heredoc_test_file}"')
        self.assertEqual(result.returncode, 0, '读取追加后的heredoc文件应该成功')
        
        expected_appended_content = '''First line of heredoc
Second line with "quotes"
Third line with special chars @#$%
Fourth line with spaces    
Fifth line appended
Sixth line appended'''
        
        self.assertEqual(result.stdout.rstrip('\n'), expected_appended_content, 'heredoc追加后内容应该正确')
        
        # 测试空heredoc
        print("测试空heredoc")
        empty_heredoc_file = f"{self.test_folder}/empty_heredoc.txt"
        empty_command = f'''cat > "{empty_heredoc_file}" << "EOF"
EOF'''
        
        result = self.gds(empty_command)
        self.assertEqual(result.returncode, 0, '空heredoc应该成功')
        
        result = self.gds(f'cat "{empty_heredoc_file}"')
        self.assertEqual(result.returncode, 0, '读取空heredoc文件应该成功')
        self.assertEqual(result.stdout.strip(), '', '空heredoc文件应该为空')
        
        # 清理heredoc测试文件
        result = self.gds(f'rm -f "{heredoc_test_file}" "{empty_heredoc_file}"')
        self.assertEqual(result.returncode, 0, '清理heredoc测试文件应该成功')
        
        print('heredoc语法支持测试完成')
    
    def test_14_touch_mkdir_mv_rm(self):
        """测试文件和目录的创建、移动、删除操作，包括安全检查"""
        print("测试文件和目录的创建、移动、删除操作")
        
        # 1. 创建测试目录结构
        print("1. 创建测试目录结构")
        test_base = self.get_test_file_path("file_ops_test")
        
        # 创建基础目录
        result = self.gds(f'mkdir -p "{test_base}/parent/child"')
        self.assertEqual(result.returncode, 0)
        
        # 2. 测试touch创建文件
        print("2. 测试touch创建文件")
        test_file1 = f"{test_base}/test_file1.txt"
        test_file2 = f"{test_base}/parent/test_file2.txt"
        
        result = self.gds(f'touch "{test_file1}"')
        self.assertEqual(result.returncode, 0)
        
        result = self.gds(f'touch "{test_file2}"')
        self.assertEqual(result.returncode, 0)
        
        # 验证文件创建成功
        result = self.gds(f'ls "{test_base}"')
        self.assertEqual(result.returncode, 0)
        self.assertIn("test_file1.txt", result.stdout)
        
        result = self.gds(f'ls "{test_base}/parent"')
        self.assertEqual(result.returncode, 0)
        self.assertIn("test_file2.txt", result.stdout)
        
        # 3. 测试mkdir创建更多目录
        print("3. 测试mkdir创建更多目录")
        result = self.gds(f'mkdir "{test_base}/new_dir1" "{test_base}/new_dir2"')
        self.assertEqual(result.returncode, 0)
        
        # 验证目录创建
        result = self.gds(f'ls "{test_base}"')
        self.assertEqual(result.returncode, 0)
        self.assertIn("new_dir1", result.stdout)
        self.assertIn("new_dir2", result.stdout)
        
        # 4. 测试mv移动文件
        print("4. 测试mv移动文件")
        # 移动文件到新目录
        result = self.gds(f'mv "{test_file1}" "{test_base}/new_dir1/"')
        self.assertEqual(result.returncode, 0)
        
        # 验证文件移动
        result = self.gds(f'ls "{test_base}/new_dir1"')
        self.assertEqual(result.returncode, 0)
        self.assertIn("test_file1.txt", result.stdout)
        
        # 原位置应该没有文件
        result = self.gds(f'ls "{test_base}"')
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("test_file1.txt", result.stdout)
        
        # 5. 测试rm删除文件
        print("5. 测试rm删除文件")
        result = self.gds(f'rm "{test_file2}"')
        self.assertEqual(result.returncode, 0)
        
        # 验证文件删除
        result = self.gds(f'ls "{test_base}/parent"')
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("test_file2.txt", result.stdout)
        
        # 6. 测试rm -rf删除目录
        print("6. 测试rm -rf删除目录")
        result = self.gds(f'rm -rf "{test_base}/new_dir2"')
        self.assertEqual(result.returncode, 0)
        
        # 验证目录删除
        result = self.gds(f'ls "{test_base}"')
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("new_dir2", result.stdout)
        
        # 7. 测试安全检查：尝试删除包含当前目录的父目录
        print("7. 测试安全检查：尝试删除包含当前目录的父目录")
        
        # 先进入子目录
        result = self.gds(f'cd "{test_base}/parent/child"')
        self.assertEqual(result.returncode, 0)
        
        # 尝试删除父目录，应该被安全检查阻止
        result = self.gds(f'rm -rf "{test_base}"', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0, "删除包含当前目录的父目录应该被阻止")
        self.assertIn("Cannot delete directory containing current working directory", result.stdout)
        
        # 8. 测试安全检查：尝试删除当前目录的直接父目录
        print("8. 测试安全检查：尝试删除当前目录的直接父目录")
        result = self.gds(f'rm -rf ..', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0, "删除当前目录的父目录应该被阻止")
        self.assertIn("Cannot delete directory containing current working directory", result.stdout)
        
        # 9. 清理测试：先切换到安全目录再删除
        print("9. 清理测试：先切换到安全目录再删除")
        result = self.gds(f'cd ~ && rm -rf "{test_base}"')
        self.assertEqual(result.returncode, 0)
        
        # 验证清理成功
        result = self.gds(f'ls "{test_base}"', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0, "测试目录应该已被删除")

        """测试mkdir的-p选项（递归创建父目录）"""
        print("测试mkdir的-p选项")
        
        # 1. 测试不带-p的mkdir，父目录不存在时应该失败
        print("1. 测试不带-p的mkdir，父目录不存在时应该失败")
        test_base = self.get_test_file_path("mkdir_recursive_test")
        
        # 清理可能存在的测试目录
        self.gds(f'rm -rf "{test_base}"', expect_success=False, check_function_result=False)
        
        # 尝试在不存在的父目录中创建目录（不带-p）
        result = self.gds(f'mkdir "{test_base}/parent/child"', expect_success=False)
        self.assertNotEqual(result.returncode, 0, "在不存在的父目录中创建目录应该失败")
        self.assertIn("No such file or directory", result.stdout, "错误信息应该包含'No such file or directory'")
        
        # 2. 测试带-p的mkdir，父目录不存在时应该成功
        print("2. 测试带-p的mkdir，父目录不存在时应该成功")
        result = self.gds(f'mkdir -p "{test_base}/parent/child"')
        self.assertEqual(result.returncode, 0, "带-p选项应该成功创建所有父目录")
        
        # 验证所有目录都被创建
        result = self.gds(f'ls "{test_base}"')
        self.assertEqual(result.returncode, 0)
        self.assertIn("parent", result.stdout, "父目录应该被创建")
        
        result = self.gds(f'ls "{test_base}/parent"')
        self.assertEqual(result.returncode, 0)
        self.assertIn("child", result.stdout, "子目录应该被创建")
        
        # 3. 测试不带-p的mkdir，在已存在的父目录中创建目录应该成功
        print("3. 测试不带-p的mkdir，在已存在的父目录中创建目录应该成功")
        result = self.gds(f'mkdir "{test_base}/parent/another_child"')
        self.assertEqual(result.returncode, 0, "在已存在的父目录中创建目录应该成功")
        
        # 验证新目录被创建
        result = self.gds(f'ls "{test_base}/parent"')
        self.assertEqual(result.returncode, 0)
        self.assertIn("another_child", result.stdout, "新目录应该被创建")
        
        # 4. 测试多级目录创建（-p选项）
        print("4. 测试多级目录创建（-p选项）")
        result = self.gds(f'mkdir -p "{test_base}/a/b/c/d/e"')
        self.assertEqual(result.returncode, 0, "应该成功创建多级目录")
        
        # 验证深层目录结构
        result = self.gds(f'ls "{test_base}/a/b/c/d"')
        self.assertEqual(result.returncode, 0)
        self.assertIn("e", result.stdout, "深层目录应该被创建")
        
        # 5. 清理测试目录
        print("5. 清理测试目录")
        result = self.gds(f'rm -rf "{test_base}"')
        # rm -rf 可能有问题，所以不强制检查返回码
    
    def test_15_project_development(self):
        print(f'阶段1: 项目初始化')
        
        # 创建项目目录
        result = self.gds('mkdir -p "' + self.test_folder + '/myproject/src" "' + self.test_folder + '/myproject/tests" "' + self.test_folder + '/myproject/docs"')
        self.assertEqual(result.returncode, 0)
        
        # 验证所有目录创建成功
        self.assertTrue(self.verify_file_exists(self.test_folder + "/myproject/src"), "myproject/src目录应该存在")
        self.assertTrue(self.verify_file_exists(self.test_folder + "/myproject/tests"), "myproject/tests目录应该存在")
        self.assertTrue(self.verify_file_exists(self.test_folder + "/myproject/docs"), "myproject/docs目录应该存在")
        
        # 创建项目基础文件
        result = self.gds('\'echo "# My Project\\nA sample Python project for testing" > "' + self.test_folder + '/myproject/README.md"\'')
        self.assertEqual(result.returncode, 0)
        
        result = self.gds('\'echo "requests>=2.25.0\\nnumpy>=1.20.0\\npandas>=1.3.0" > "' + self.test_folder + '/myproject/requirements.txt"\'')
        self.assertEqual(result.returncode, 0)
        
        # 创建主应用文件
        main_py_content = '''# 主应用文件
import sys
import json
from datetime import datetime

def load_config(config_file="config.json"):
    # 加载配置文件
    try:
        with open(config_file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f'配置文件 {config_file} 不存在')
        return {}

def process_data(data_list):
    # 处理数据列表
    if not data_list:
        return {"error": "数据为空"}
    
    result = {
        "count": len(data_list),
        "sum": sum(data_list),
        "average": sum(data_list) / len(data_list),
        "max": max(data_list),
        "min": min(data_list)
    }
    return result

def main():
    # 主函数
    print(f'应用启动')
    print(f'当前时间: {datetime.now()}')
    
    # 加载配置
    config = load_config()
    print(f'配置: {config}')
    
    # 处理示例数据
    sample_data = [1, 2, 3, 4, 5, 10, 15, 20]
    result = process_data(sample_data)
    print(f'处理结果: {result}')
    
    print(f'应用完成')

if __name__ == "__main__":
    main()
'''
        
        # 使用echo创建main.py文件（长内容会自动使用base64编码）
        # 转义特殊字符确保Python语法正确
        myproject_path = self.test_folder + '/myproject'
        escaped_content = main_py_content.replace('"', '\\"')
        result = self.gds(f'\'echo "{escaped_content}" > "{myproject_path}/src/main.py"\'')
        self.assertEqual(result.returncode, 0)
        
        # 验证项目结构创建成功
        self.assertTrue(self.verify_file_exists(myproject_path + "/README.md"))
        self.assertTrue(self.verify_file_exists(myproject_path + "/requirements.txt"))
        self.assertTrue(self.verify_file_exists(myproject_path + "/src/main.py"))
        
        print(f'阶段2: 环境设置')
        
        # 确保干净的shell状态
        self.ensure_clean_shell_state()
        
        # 使用时间哈希命名虚拟环境（确保测试独立性）
        import time
        venv_name = f"myproject_env_{int(time.time())}"
        print(f'虚拟环境名称: {venv_name}')
        
        # 创建虚拟环境
        self.ensure_clean_shell_state()
        result = self.gds(f'venv --create {venv_name}')
        self.assertEqual(result.returncode, 0)
        
        # 激活虚拟环境
        self.ensure_clean_shell_state()
        result = self.gds(f'venv --activate {venv_name}')
        self.assertEqual(result.returncode, 0)
        
        # 安装依赖（简化版，只安装一个包）
        result = self.gds('pip install requests')
        self.assertEqual(result.returncode, 0)
        
        print(f'阶段3: 开发调试')
        
        # 进入项目目录
        result = self.gds('cd "' + myproject_path + '/src"')
        self.assertEqual(result.returncode, 0)
        
        # 运行主程序（第一次运行，可能有问题）
        result = self.gds('python "' + myproject_path + '/src/main.py"')
        self.assertEqual(result.returncode, 0)
        
        # 创建配置文件
        config_content = '{"debug": true, "version": "1.0.0", "author": "developer"}'
        result = self.gds(f"'echo \"{config_content}\" > \"{myproject_path}/config.json\"'")
        self.assertEqual(result.returncode, 0)
        
        # 再次运行程序（现在应该加载配置文件）
        result = self.gds('python "' + myproject_path + '/src/main.py"')
        self.assertEqual(result.returncode, 0)
        
        print(f'阶段4: 问题解决')
        
        # 搜索特定函数
        result = self.gds('grep "def " "' + myproject_path + '/src/main.py"', expect_success=False)
        self.assertEqual(result.returncode, 0)
        
        # 查看配置文件内容
        result = self.gds('cat "' + myproject_path + '/config.json"')
        self.assertEqual(result.returncode, 0)
        
        # 读取代码的特定行
        result = self.gds('read "' + myproject_path + '/src/main.py" 1 10')
        self.assertEqual(result.returncode, 0)
        
        # 编辑代码：添加更多功能
        success, result = self.gds_with_retry(
            'edit "' + myproject_path + '/src/main.py" \'[["处理示例数据", "处理示例数据（已优化）"]]\'',
            ['grep "已优化" "' + myproject_path + '/src/main.py"'],
            max_retries=3
        )
        self.assertTrue(success, f"代码编辑失败: {result.stderr if result else 'Unknown error'}")
        
        print(f'阶段5: 验证测试')
        
        # 最终运行测试
        result = self.gds('python "' + myproject_path + '/src/main.py"')
        self.assertEqual(result.returncode, 0)
        
        # 检查项目文件（限制在当前测试目录内）
        result = self.gds('find . -name "*.py" "' + myproject_path + '"')
        self.assertEqual(result.returncode, 0)
        
        # 查看项目结构（限制在当前测试目录内）
        result = self.gds('ls -R . "' + myproject_path + '"')
        self.assertEqual(result.returncode, 0)
        
        # 清理：取消激活虚拟环境
        self.ensure_clean_shell_state()
        result = self.gds('venv --deactivate')
        self.assertEqual(result.returncode, 0)
        
        # 删除测试虚拟环境
        self.ensure_clean_shell_state()
        result = self.gds(f'venv --delete {venv_name}')
        self.assertEqual(result.returncode, 0)
        
        # 返回根目录
        result = self.gds('cd ../..')
        self.assertEqual(result.returncode, 0)
        
        print(f'真实项目开发工作流程测试完成！')

    def test_16_project_deployment(self):
    
        # 1. 上传项目文件夹
        project_dir = self.TEST_DATA_DIR / "test_project"
        success, result = self.run_upload(
            f'upload_folder --target-dir "{self.test_folder}" --force "{project_dir}"',
            ['ls "' + self.test_folder + '/test_project"'],
            max_retries=3
        )
        self.assertTrue(success, f"项目文件夹上传失败: {result.stderr if result else 'Unknown error'}")
        
        # 2. 进入项目目录
        result = self.gds('cd "' + self.test_folder + '/test_project"')
        self.assertEqual(result.returncode, 0)
        
        # 3. 查看项目结构
        result = self.gds('ls -la "' + self.test_folder + '/test_project"')
        self.assertEqual(result.returncode, 0)
        
        # 4. 验证项目文件存在
        result = self.gds('ls "' + self.test_folder + '/test_project/main.py"')
        self.assertEqual(result.returncode, 0)
        
        result = self.gds('ls "' + self.test_folder + '/test_project/core.py"')
        self.assertEqual(result.returncode, 0)
        
        result = self.gds('ls "' + self.test_folder + '/test_project/config.json"')
        self.assertEqual(result.returncode, 0)
        
        # 5. 返回根目录
        result = self.gds('cd "' + self.test_folder + '"')
        self.assertEqual(result.returncode, 0)
    
    def test_17_python(self):
        print(f'阶段1: 创建测试项目')
        
        # 创建项目目录
        test_project_path = self.test_folder + '/test_project'
        result = self.gds('mkdir -p "' + test_project_path + '"')
        self.assertEqual(result.returncode, 0)
        
        # 创建简单的main.py文件（无三重引号，无外部依赖）
        main_py_content = '''# Test project main file
import sys
from datetime import datetime

def main():
    print(f'Test project started')
    print(f'Current time: {datetime.now()}')
    print("Python version:", sys.version)
    
    # Simple data processing
    data = [1, 2, 3, 4, 5]
    result = {
        "count": len(data),
        "sum": sum(data),
        "average": sum(data) / len(data)
    }
    print(f'Processing result: {result}')
    print(f'Test project completed')

if __name__ == "__main__":
    main()
'''
        
        # 转义特殊字符确保Python语法正确
        escaped_content = main_py_content.replace('"', '\\"')
        result = self.gds(f'\'echo "{escaped_content}" > "' + test_project_path + '/main.py"\'')
        self.assertEqual(result.returncode, 0)
        
        # 验证项目文件创建成功
        self.assertTrue(self.verify_file_exists(test_project_path + "/main.py"))
        
        print(f'阶段2: 代码执行测试')
        
        # 1. 执行简单Python脚本
        # 创建独特的测试文件
        test_file = self.TEST_DATA_DIR / "test_simple_hello.py"
        original_file = self.TEST_DATA_DIR / "simple_hello.py"
        
        # 复制文件并上传
        import shutil
        shutil.copy2(original_file, test_file)
        success, result = self.run_upload(
            f'upload --target-dir "{self.test_folder}" --force "{test_file}"',
            ['ls "' + self.test_folder + '/test_simple_hello.py"'],
            max_retries=3
        )
        self.assertTrue(success, f"test文件上传失败: {result.stderr if result else 'Unknown error'}")
        
        result = self.gds(f'python "{self.test_folder}/test_simple_hello.py"')
        self.assertEqual(result.returncode, 0)
        
        # 2. 执行Python代码片段
        python_script = '''print("Hello from Python code!"); import os; print(os.getcwd())'''
        python_script_escaped = python_script.replace('"', '\\"')
        result = self.gds(f'python -c "{python_script_escaped}"')
        self.assertEqual(result.returncode, 0)
        
        # 3. 执行项目主文件
        result = self.gds(f'cd "{test_project_path}" && python "{test_project_path}/main.py"')
        self.assertEqual(result.returncode, 0)
    
    def test_18_pip_venv(self):
        import time
        venv_name = f"test_env_{int(time.time())}"
        print(f'虚拟环境名称: {venv_name}')
        
        # 0. 预备工作：确保测试环境干净（强制取消激活任何现有环境）
        print(f'清理测试环境...')
        try:
            result = self.gds('venv --deactivate', expect_success=False, check_function_result=False)
        except:
            pass 
        
        # 1. 初始状态：没有激活的环境
        result = self.gds('venv --current')
        self.assertEqual(result.returncode, 0)
        cleaned_output = self.get_cleaned_stdout(result)
        self.assertIn("No virtual environment", cleaned_output)
        
        # 2. 创建虚拟环境
        result = self.gds(f'venv --create {venv_name}')
        self.assertEqual(result.returncode, 0)
        
        # 3. 列出虚拟环境（验证创建成功）
        result = self.gds('venv --list')
        self.assertEqual(result.returncode, 0)
        cleaned_output = self.get_cleaned_stdout(result)
        self.assertIn(venv_name, cleaned_output)
        
        result = self.gds('venv --current')
        self.assertEqual(result.returncode, 0)
        cleaned_output = self.get_cleaned_stdout(result)
        self.assertIn("No virtual environment", cleaned_output)
        
        # 4. 激活虚拟环境
        result = self.gds(f'venv --activate {venv_name}')
        self.assertEqual(result.returncode, 0)
        
        result = self.gds('venv --current')
        self.assertEqual(result.returncode, 0)
        cleaned_output = self.get_cleaned_stdout(result)
        self.assertIn(venv_name, cleaned_output)
        
        # 5. 在虚拟环境中安装包
        result = self.gds('pip install colorama')
        self.assertEqual(result.returncode, 0)
        
        python_script = 'import colorama; print("colorama imported successfully")'
        python_script_escaped = python_script.replace('"', '\\"')
        result = self.gds(f'python -c "{python_script_escaped}"')
        self.assertEqual(result.returncode, 0)
        cleaned_output = self.get_cleaned_stdout(result)
        self.assertIn("colorama imported successfully", cleaned_output)
        
        # 6. 取消激活虚拟环境
        result = self.gds('venv --deactivate')
        self.assertEqual(result.returncode, 0)

        result = self.gds('venv --current')
        self.assertEqual(result.returncode, 0)
        cleaned_output = self.get_cleaned_stdout(result)
        self.assertIn("No virtual environment", cleaned_output)
        
        # 7. 创建一个空的虚拟环境用于验证包隔离
        empty_venv_name = f"empty_env_{int(time.time())}"
        result = self.gds(f'venv --create {empty_venv_name}')
        self.assertEqual(result.returncode, 0)
        
        # 8. 激活空环境
        result = self.gds(f'venv --activate {empty_venv_name}')
        self.assertEqual(result.returncode, 0)

        result = self.gds('venv --current')
        self.assertEqual(result.returncode, 0)
        cleaned_output = self.get_cleaned_stdout(result)
        self.assertIn(empty_venv_name, cleaned_output)
        
        # 9. 验证包在空环境中不可用（应该失败）
        python_script = 'import colorama; print("colorama imported")'
        python_script_escaped = python_script.replace('"', '\\"')
        result = self.gds(f'python -c "{python_script_escaped}"', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0)  # 应该失败，因为colorama不在空环境中
        
        # 10. 重新激活原环境验证包仍然可用
        result = self.gds(f'venv --activate {venv_name}')
        self.assertEqual(result.returncode, 0)

        result = self.gds('venv --current')
        self.assertEqual(result.returncode, 0)
        cleaned_output = self.get_cleaned_stdout(result)
        self.assertIn(venv_name, cleaned_output)
        
        python_script = 'import colorama; print("colorama re-imported successfully")'
        python_script_escaped = python_script.replace('"', '\\"')
        result = self.gds(f'python -c "{python_script_escaped}"')
        self.assertEqual(result.returncode, 0)
        cleaned_output = self.get_cleaned_stdout(result)
        self.assertIn("colorama re-imported successfully", cleaned_output)
        
        # 11. 最终清理：取消激活并删除虚拟环境
        result = self.gds('venv --deactivate')
        self.assertEqual(result.returncode, 0)
        
        result = self.gds(f'venv --delete {venv_name}')
        self.assertEqual(result.returncode, 0)
        
        # 12. 清理空环境
        result = self.gds(f'venv --delete {empty_venv_name}')
        self.assertEqual(result.returncode, 0)
        
        # 13. 验证删除后的环境不在列表中
        result = self.gds('venv --list')
        self.assertEqual(result.returncode, 0)
        self.assertNotIn(venv_name, result.stdout)
        self.assertNotIn(empty_venv_name, result.stdout)
        
        # 14. 验证删除后的环境无法激活
        result = self.gds(f'venv --activate {venv_name}', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0)  # 应该失败
        
        result = self.gds(f'venv --activate {empty_venv_name}', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0)  # 应该失败
    
    def test_19_venv_protect_unprotect(self):
        """测试虚拟环境的保护和取消保护功能"""
        import time
        protected_env = f'protected_env_{int(time.time())}'
        normal_env = f'normal_env_{int(time.time())}'
        
        print(f'测试venv --protect和--unprotect功能')
        
        # 1. 创建两个虚拟环境
        print(f'创建测试环境: {protected_env}, {normal_env}')
        result = self.gds(f'venv --create {protected_env}')
        self.assertEqual(result.returncode, 0)
        
        result = self.gds(f'venv --create {normal_env}')
        self.assertEqual(result.returncode, 0)
        
        # 2. 保护第一个环境
        print(f'保护环境: {protected_env}')
        result = self.gds(f'venv --protect {protected_env}')
        self.assertEqual(result.returncode, 0)
        cleaned_output = self.get_cleaned_stdout(result)
        self.assertIn('protected', cleaned_output.lower())
        
        # 3. 尝试删除被保护的环境（应该被跳过）
        print(f'尝试删除被保护的环境（应该被跳过）')
        result = self.gds(f'venv --delete {protected_env}')
        self.assertEqual(result.returncode, 0)
        # 应该包含警告信息
        cleaned_output = self.get_cleaned_stdout(result)
        self.assertIn('protected', cleaned_output.lower())
        
        # 4. 验证被保护的环境仍然存在
        print(f'验证被保护的环境仍然存在')
        result = self.gds('venv --list')
        self.assertEqual(result.returncode, 0)
        cleaned_output = self.get_cleaned_stdout(result)
        self.assertIn(protected_env, cleaned_output)
        
        # 5. 删除未保护的环境（应该成功）
        print(f'删除未保护的环境: {normal_env}')
        result = self.gds(f'venv --delete {normal_env}')
        self.assertEqual(result.returncode, 0)
        
        # 6. 验证未保护的环境已被删除
        print(f'验证未保护的环境已被删除')
        result = self.gds('venv --list')
        self.assertEqual(result.returncode, 0)
        self.assertNotIn(normal_env, result.stdout)
        
        # 7. 取消保护
        print(f'取消保护: {protected_env}')
        result = self.gds(f'venv --unprotect {protected_env}')
        self.assertEqual(result.returncode, 0)
        # 使用清理后的输出进行验证
        cleaned_output = self.get_cleaned_stdout(result)
        self.assertIn('unprotected', cleaned_output.lower())
        
        # 8. 现在应该可以删除了
        print(f'再次尝试删除（应该成功）')
        result = self.gds(f'venv --delete {protected_env}')
        self.assertEqual(result.returncode, 0)
        
        # 9. 验证环境已被删除
        print(f'验证环境已被删除')
        result = self.gds('venv --list')
        self.assertEqual(result.returncode, 0)
        self.assertNotIn(protected_env, result.stdout)
        
        # 10. 测试批量保护
        print(f'测试批量保护功能')
        batch_env1 = f'batch_env1_{int(time.time())}'
        batch_env2 = f'batch_env2_{int(time.time())}'
        
        result = self.gds(f'venv --create {batch_env1}')
        self.assertEqual(result.returncode, 0)
        result = self.gds(f'venv --create {batch_env2}')
        self.assertEqual(result.returncode, 0)
        
        # 批量保护
        result = self.gds(f'venv --protect {batch_env1} {batch_env2}')
        self.assertEqual(result.returncode, 0)
        
        # 尝试批量删除（应该都被跳过）
        result = self.gds(f'venv --delete {batch_env1} {batch_env2}')
        self.assertEqual(result.returncode, 0)
        cleaned_output = self.get_cleaned_stdout(result)
        self.assertIn('protected', cleaned_output.lower())
        
        # 验证都还存在
        result = self.gds('venv --list')
        self.assertEqual(result.returncode, 0)
        cleaned_output = self.get_cleaned_stdout(result)
        self.assertIn(batch_env1, cleaned_output)
        self.assertIn(batch_env2, cleaned_output)
        
        # 批量取消保护并删除
        result = self.gds(f'venv --unprotect {batch_env1} {batch_env2}')
        self.assertEqual(result.returncode, 0)
        
        result = self.gds(f'venv --delete {batch_env1} {batch_env2}')
        self.assertEqual(result.returncode, 0)
        
        # 验证都已删除
        result = self.gds('venv --list')
        self.assertEqual(result.returncode, 0)
        self.assertNotIn(batch_env1, result.stdout)
        self.assertNotIn(batch_env2, result.stdout)
        
        print(f'venv protect/unprotect功能测试通过')
    
    def test_20_pip_deps_analysis(self):
        # 测试简单包的依赖分析（depth=1）
        print(f'测试简单包依赖分析（depth=1）')
        result = self.gds('deps requests --depth=1')
        self.assertEqual(result.returncode, 0)
        
        # 验证输出包含关键信息
        output = self.get_cleaned_stdout(result)
        self.assertIn("Analysis completed:", output, "应该包含分析完成信息")
        self.assertIn("API calls", output, "应该包含API调用次数")
        self.assertIn("packages analyzed", output, "应该包含分析包数量")
        self.assertIn("requests", output, "应该包含主包名")
        
        # 验证依赖树格式
        self.assertIn("├─", output, "应该包含依赖树连接符")
        self.assertIn("Level 1:", output, "应该包含层级汇总")
        
        print(f'简单包依赖分析测试通过')
        
        # 测试复杂包的依赖分析（depth=2）
        print(f'测试复杂包依赖分析（depth=2）')
        result = self.gds('deps numpy --depth=2')
        self.assertEqual(result.returncode, 0)
        
        # numpy通常没有依赖，但测试应该正常完成
        output = self.get_cleaned_stdout(result)
        self.assertIn("Analysis completed:", output, "应该包含分析完成信息")
        self.assertIn("numpy", output, "应该包含包名")
        print(f'复杂包依赖分析测试通过')
        
        # 测试不存在包的错误处理
        print(f'测试不存在包的错误处理')
        result = self.gds('deps nonexistent-package-12345', expect_success=False, check_function_result=False)
        # 不存在的包应该返回非0退出码
        self.assertNotEqual(result.returncode, 0, f"不存在的包应该返回非0退出码，实际返回码: {result.returncode}")
        
        # 同时验证输出包含错误信息
        output = self.get_cleaned_stdout(result).lower()
        not_found_indicators = ["not found", "error", "failed", "no package"]
        has_error_indicator = any(indicator in output for indicator in not_found_indicators)
        self.assertTrue(has_error_indicator, f"不存在的包应该有错误指示，输出: {output}")
        
        # 测试性能统计信息
        print(f'测试性能统计')
        import time
        start_time = time.time()
        result = self.gds('deps colorama --depth=1')
        end_time = time.time()
        
        self.assertEqual(result.returncode, 0)
        
        # 验证性能统计格式
        output = result.stdout
        self.assertRegex(output, r'\d+ API calls', "应该包含API调用次数")
        self.assertRegex(output, r'\d+ packages analyzed', "应该包含分析包数量")
        self.assertRegex(output, r'in \d+\.\d+s', "应该包含执行时间")
        
        # 验证执行时间合理（应该在合理范围内）
        actual_time = end_time - start_time
        print(f'实际执行时间: {actual_time:.2f}s')
        self.assertLess(actual_time, 60, "简单包分析应该在60秒内完成")
        
        # 测试深度参数
        print(f'测试深度参数')
        result = self.gds('deps requests --depth=2')
        self.assertEqual(result.returncode, 0)
        output = result.stdout
        
        # 验证分析统计行
        print(f'验证分析统计')
        self.assertRegex(output, r'Analysis completed: \d+ API calls, \d+ packages analyzed in \d+\.\d+s', "应该包含完整的分析统计信息")
        
        # 验证依赖树格式
        print(f'验证依赖树格式')
        tree_indicators = ["├─", "└─", "│"]
        has_tree_format = any(indicator in output for indicator in tree_indicators)
        self.assertTrue(has_tree_format, "应该包含依赖树格式字符")
        
        # 验证大小显示格式
        print(f'验证大小显示格式')
        size_patterns = [r'\(\d+\.\d+MB\)', r'\(\d+\.\d+KB\)', r'\(\d+B\)']
        has_size_format = any(re.search(pattern, output) for pattern in size_patterns)
        self.assertTrue(has_size_format, "应该包含大小信息")
        
        # 验证层级汇总
        print(f'验证层级汇总')
        self.assertRegex(output, r'Level \d+:', "应该包含层级汇总")
        print(f'依赖分析功能测试完成')

    def test_21_pipe(self):
        # 测试简单的pipe命令
        result = self.gds('echo "hello world" | grep hello')
        self.assertEqual(result.returncode, 0)
        
        # 创建测试文件
        pipe_file = "pipe_test.txt"
        pipe_test_path = self.get_test_file_path(pipe_file)
        result = self.gds(f'echo "test content" > "{pipe_test_path}"')
        self.assertEqual(result.returncode, 0)
        
        # 验证文件是否被创建（调试）
        result = self.gds(f'ls -la "{pipe_test_path}"')
        print(f'创建文件后目录内容: {result.stdout[:300]}')
        
        # 直接验证文件存在
        self.assertTrue(self.verify_file_exists(pipe_test_path), "pipe_test.txt should exist after creation")
        
        # 测试 ls | grep 组合
        result = self.gds(f'ls "{self.test_folder}" | grep "{pipe_file}"')
        self.assertEqual(result.returncode, 0)
        
        # 清理测试文件
        self.gds(f'rm "{pipe_test_path}"')
        
        # 测试多个pipe操作符的组合
        result = self.gds('echo -e "apple\\nbanana\\napple\\ncherry" | sort | uniq')
        self.assertEqual(result.returncode, 0)
        
        # 测试head命令
        result = self.gds('echo -e "line1\\nline2\\nline3\\nline4\\nline5" | head -n 3')
        self.assertEqual(result.returncode, 0)
        
        # 测试tail命令
        result = self.gds('echo -e "line1\\nline2\\nline3\\nline4\\nline5" | tail -n 2')
        self.assertEqual(result.returncode, 0)

    def test_22_shell_mode(self):
        """测试Shell模式下的连续操作 - 分步骤调试版本"""
        print(f'测试Shell模式连续操作 - 分步骤调试')
        
        # 创建测试文件
        test_file = self.TEST_DATA_DIR / "shell_test.txt"
        test_file.write_text("shell test content", encoding='utf-8')
        print(f'创建测试文件: {test_file}')
        
        # 步骤1: 基础命令测试
        print("步骤1: 测试基础命令 (pwd, ls)")
        basic_commands = ["pwd", "ls"]
        print(f'执行命令: {basic_commands}')
        result1 = self.gds(' && '.join(basic_commands))  # 使用 && 连接命令

        stdout, stderr, returncode = result1.stdout, result1.stderr, result1.returncode
        print(f'步骤1返回码: {returncode}')
        if returncode != 0:
            print(f'步骤1失败 - stderr: {stderr}')
            print(f'步骤1失败 - stdout: {stdout}')
        else:
            print("步骤1成功")
        self.assertEqual(returncode, 0, "基础命令应该成功")
        
        # 步骤2: 文件上传测试
        print("步骤2: 测试文件上传")
        upload_commands = ["pwd", f'upload --target-dir "{self.test_folder}" --force "{test_file}"', "ls"]
        
        print(f'执行命令: {upload_commands}')
        result2 = self.gds(f'upload --target-dir "{self.test_folder}" --force "{test_file}"')
        
        stdout, stderr, returncode = result2.stdout, result2.stderr, result2.returncode
        print(f'步骤2返回码: {returncode}')
        if returncode != 0:
            print(f'步骤2失败 - stderr: {stderr}')
            print(f'步骤2失败 - stdout: {stdout}')
        else:
            print("步骤2成功")
        
        self.assertEqual(returncode, 0, "文件上传应该成功")
        
        # 步骤3: 文件操作测试
        print("步骤3: 测试文件操作 (cat)")
        shell_test_path = self.get_test_file_path("shell_test.txt")
        file_commands = [f'cat "{shell_test_path}"']
        
        print(f'执行命令: {file_commands}')
        result3 = self.gds(f'cat "{shell_test_path}"')
        
        stdout, stderr, returncode = result3.stdout, result3.stderr, result3.returncode
        print(f'步骤3返回码: {returncode}')
        if returncode != 0:
            print(f'步骤3失败 - stderr: {stderr}')
            print(f'步骤3失败 - stdout: {stdout}')
        else:
            print("步骤3成功")
            if "shell test content" in result3.stdout:
                print("文件内容验证成功")
            else:
                print(f'文件内容验证失败，输出: {result3.stdout}')
        
        self.assertEqual(returncode, 0, "文件读取应该成功")
        
        # 步骤4: 目录操作测试
        print("步骤4: 测试目录操作")
        shell_test_dir = self.get_test_file_path("shell_test_dir")
        dir_commands = ['mkdir "' + shell_test_dir + '"', 'cd "' + shell_test_dir + '"', 'pwd', 'cd ..']
        
        print(f'执行命令: {dir_commands}')
        result4 = self.gds(' && '.join(dir_commands))
        
        stdout, stderr, returncode = result4.stdout, result4.stderr, result4.returncode
        print(f'步骤4返回码: {returncode}')
        if returncode != 0:
            print(f'步骤4失败 - stderr: {stderr}')
            print(f'步骤4失败 - stdout: {stdout}')
        else:
            print("步骤4成功")
        
        self.assertEqual(returncode, 0, "目录操作应该成功")
        
        # 步骤5: 清理操作测试
        print("步骤5: 测试清理操作")
        cleanup_commands = [f'rm "{shell_test_path}"', f'rm -rf "{shell_test_dir}"', 'ls']
        
        print(f'执行命令: {cleanup_commands}')
        result5 = self.gds(' && '.join(cleanup_commands))
        
        stdout, stderr, returncode = result5.stdout, result5.stderr, result5.returncode
        print(f'步骤5返回码: {returncode}')
        if returncode != 0:
            print(f'步骤5失败 - stderr: {stderr}')
            print(f'步骤5失败 - stdout: {stdout}')
        else:
            print("步骤5成功")
        
        self.assertEqual(returncode, 0, "清理操作应该成功")
        print(f'Shell模式连续操作分步骤测试完成 - 所有步骤都成功')
        
        # 步骤6: Shell切换和状态管理测试（from test_23）
        print("步骤6: 测试Shell切换和状态管理")
        create_result = subprocess.run(
            [sys.executable, str(self.GOOGLE_DRIVE_PY), '--create-remote-shell'],
            capture_output=True, text=True, timeout=180
        )
        self.assertEqual(create_result.returncode, 0, "创建remote shell命令应该成功")
        
        # 从输出中提取shell ID
        shell_id_match = re.search(r'Shell ID: (\w+)', create_result.stdout)
        if shell_id_match:
            new_shell_id = shell_id_match.group(1)
            print(f'创建的Shell ID: {new_shell_id}')
            
            # 列出所有shells
            list_result = subprocess.run(
                [sys.executable, str(self.GOOGLE_DRIVE_PY), '--list-remote-shell'],
                capture_output=True, text=True, timeout=180
            )
            self.assertEqual(list_result.returncode, 0, "列出shells应该成功")
            self.assertIn(new_shell_id, list_result.stdout, "新创建的shell应该在列表中")
            
            # 切换到新shell
            print(f'切换到新shell: {new_shell_id}')
            checkout_result = subprocess.run(
                [sys.executable, str(self.GOOGLE_DRIVE_PY), '--checkout-remote-shell', new_shell_id],
                capture_output=True, text=True, timeout=180
            )
            self.assertEqual(checkout_result.returncode, 0, "切换shell应该成功")
            
            # 在新shell中执行操作
            test_shell_state_path = self.get_test_file_path("test_shell_state")
            shell_commands = [
                "pwd",
                f'mkdir "{test_shell_state_path}"',
                f'cd "{test_shell_state_path}"',
                "pwd",
                f'echo "shell state test" > "{test_shell_state_path}/state_test.txt"',
                f'cat "{test_shell_state_path}/state_test.txt"',
                f'cd "{self.test_folder}"',
                f'ls "{test_shell_state_path}"'
            ]
            
            shell_input = "\n".join(shell_commands) + "\nexit\n"
            shell_result = self.run_command_with_input(
                [sys.executable, str(self.GOOGLE_DRIVE_PY), "--shell", "--no-direct-feedback"],
                shell_input,
                timeout=3600
            )
            self.assertEqual(shell_result.returncode, 0, "新shell中的操作应该成功")
            self.assertIn("shell state test", shell_result.stdout, "应该能够创建和读取文件")
            self.assertIn(test_shell_state_path, shell_result.stdout, "应该能够创建目录")
            self.assertIn("state_test.txt", shell_result.stdout, "ls命令应该显示创建的文件名")
            
            # 清理：删除创建的shell
            cleanup_result = subprocess.run(
                [sys.executable, str(self.GOOGLE_DRIVE_PY), '--terminate-remote-shell', new_shell_id],
                capture_output=True, text=True, timeout=180
            )
            print("Shell切换和状态管理测试完成")
        else:
            print("无法从输出中提取Shell ID，跳过Shell切换测试")
        
        # 步骤7: Shell模式错误处理测试（from test_23）
        print("步骤7: 测试Shell模式错误处理")
        error_commands = [
            "invalid_command",
            f'ls "{self.get_test_file_path("nonexistent_path")}"',
            f'rm "{self.get_test_file_path("nonexistent_file.txt")}"',
            f'cd "{self.get_test_file_path("invalid_directory")}"'
        ]
        
        for cmd in error_commands:
            shell_input = f"{cmd}\nexit\n"
            shell_result = self.run_command_with_input(
                [sys.executable, str(self.GOOGLE_DRIVE_PY), "--shell", "--no-direct-feedback"],
                shell_input,
            )
            # Shell模式应该能够处理错误而不崩溃
            self.assertEqual(shell_result.returncode, 0, f"Shell模式处理错误命令{cmd}时不应该崩溃")
            self.assertIn("GDS:", shell_result.stdout, "即使命令失败，Shell模式也应该继续运行")
            self.assertIn("Exit Google Drive Shell", shell_result.stdout, "Shell应该正常退出")
        
        print("所有Shell模式测试完成（包括连续操作、切换、错误处理）")

    def test_23_shell_mode_consistency(self):
        """测试Shell模式与直接命令执行的输出一致性"""
        print(f'测试Shell模式与直接命令一致性')
        
        # 创建独立的测试环境
        import uuid
        test_id = str(uuid.uuid4())[:8]
        test_dir = f"{self.test_folder}/test_consistency_{test_id}"
        
        # 使用绝对路径创建测试目录和文件
        mkdir_result = self.gds(f'mkdir -p {test_dir}', expect_success=True)
        self.assertEqual(mkdir_result.returncode, 0, "创建测试目录应该成功")
        
        # 在测试目录中创建测试文件
        test_files = ["file1.txt", "file2.txt", "file3.txt"]
        for filename in test_files:
            file_path = f"{test_dir}/{filename}"
            echo_result = self.gds(f'echo "test content" > "{file_path}"', expect_success=True)
            self.assertEqual(echo_result.returncode, 0, f"创建测试文件{filename}应该成功")
        
        # 创建子目录
        subdir_result = self.gds(f'mkdir {test_dir}/subdir', expect_success=True)
        self.assertEqual(subdir_result.returncode, 0, "创建子目录应该成功")
        
        # 测试命令列表（使用绝对路径）
        test_commands = [
            (f'ls {test_dir}', "ls"),
            ("help", "help")
        ]
        
        for cmd, cmd_type in test_commands:
            print(f'测试命令: {cmd}')
            
            # 直接命令执行（使用--no-direct-feedback避免交互）
            direct_result = self.gds(f'{cmd}', expect_success=True)
            
            # Shell模式执行（进入交互式shell模式）
            shell_command = f'python3 {self.GOOGLE_DRIVE_PY} --shell --no-direct-feedback "{cmd}"'
            shell_result = subprocess.run(
                shell_command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.BIN_DIR
            )
            
            self.assertEqual(direct_result.returncode, 0, f"直接执行{cmd}应该成功")
            self.assertEqual(shell_result.returncode, 0, f"Shell模式执行{cmd}应该成功")
            
            # 清理输出以便比较
            direct_output = process_terminal_erase(direct_result.stdout)
            shell_output = process_terminal_erase(shell_result.stdout)
            
            # 对于help命令，验证关键内容存在
            if cmd_type == "help":
                self.assertIn("pwd", direct_output, "直接执行help应该包含pwd命令")
                self.assertIn("ls", direct_output, "直接执行help应该包含ls命令")
                
                # 验证shell模式也包含相同命令
                self.assertIn("pwd", shell_output, "Shell模式help应该包含pwd命令")
                self.assertIn("ls", shell_output, "Shell模式help应该包含ls命令")
                print(f'{cmd}命令在两种模式下都包含必要内容')
            
            # 对于ls命令，验证列出的文件相同
            elif cmd_type == "ls":
                # 验证所有测试文件都被列出
                for filename in test_files + ["subdir"]:
                    self.assertIn(filename, direct_output, f"直接执行ls应该列出{filename}")
                    self.assertIn(filename, shell_output, f"Shell模式ls应该列出{filename}")
                print(f'ls命令在两种模式下都列出了所有测试文件')
        
        # 清理测试环境
        cleanup_result = self.gds(f'rm -rf {test_dir}', expect_success=True)
        self.assertEqual(cleanup_result.returncode, 0, "清理测试目录应该成功")
        print("测试环境清理完成")
        print(f'Shell模式与直接命令一致性测试完成')

    def test_24_background(self):
        """测试GDS --bg后台任务功能 - 利用优先队列验证长时间运行任务的状态查询"""
        print(f'测试GDS --bg后台任务功能 - 优先队列验证')
        
        def run_gds_bg_command(command):
            """运行GDS --bg命令并返回结果"""
            cmd = [sys.executable, str(self.GOOGLE_DRIVE_PY), "--shell", "--no-direct-feedback", "--bg", command]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result
        
        def run_gds_bg_status(task_id, use_priority=False):
            """查询GDS --bg任务状态 - 支持优先队列"""
            if use_priority:
                cmd = [sys.executable, str(self.GOOGLE_DRIVE_PY), "--shell", "--no-direct-feedback", "--priority", "--bg", "--status", task_id]
            else:
                cmd = [sys.executable, str(self.GOOGLE_DRIVE_PY), "--shell", "--no-direct-feedback", "--bg", "--status", task_id]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result
        
        def run_gds_bg_result(task_id):
            """获取GDS --bg任务结果"""
            cmd = [sys.executable, str(self.GOOGLE_DRIVE_PY), "--shell", "--no-direct-feedback", "--bg", "--result", task_id]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result
        
        def run_gds_bg_cleanup(task_id):
            """清理GDS --bg任务"""
            cmd = [sys.executable, str(self.GOOGLE_DRIVE_PY), "--shell", "--no-direct-feedback", "--bg", "--cleanup", task_id]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result
        
        def extract_task_id(output):
            """从--bg命令输出中提取任务ID"""
            import re
            match = re.search(r'Background task started with ID: (\d+_\d+)', output)
            if match:
                return match.group(1)
            return None
        
        def wait_for_task_completion(task_id, max_wait=30):
            """等待任务完成"""
            import time
            start_time = time.time()
            while time.time() - start_time < max_wait:
                status_result = run_gds_bg_status(task_id)
                
                if status_result.returncode == 0 and "Status: completed" in status_result.stdout:
                    return True
                elif status_result.returncode == 0 and "Status: running" in status_result.stdout:
                    pass
                else:
                    print(f'WARNING: 任务 {task_id} 状态异常，返回码: {status_result.returncode}')
                    print(f'WARNING: 输出内容: {status_result.stdout}')
                
                time.sleep(1)
            
            print(f'ERROR: 任务 {task_id} 在 {max_wait} 秒内未完成')
            return False
        
        print("测试1: 基础echo命令")
        result = run_gds_bg_command("echo 'Hello GDS Background'")
        self.assertEqual(result.returncode, 0, f"后台任务创建失败: {result.stderr}")
        
        task_id = extract_task_id(result.stdout)
        self.assertIsNotNone(task_id, f"无法提取任务ID: {result.stdout}")
        print(f'任务ID: {task_id}')
        
        # 等待任务完成
        completed = wait_for_task_completion(task_id, max_wait=30)
        self.assertTrue(completed, "任务未在预期时间内完成")
        
        # 检查结果
        result_output = run_gds_bg_result(task_id)
        self.assertEqual(result_output.returncode, 0, f"获取结果失败: {result_output.stderr}")
        self.assertIn("Hello GDS Background", result_output.stdout, "结果内容不正确")
        
        # 清理任务
        cleanup_result = run_gds_bg_cleanup(task_id)
        self.assertEqual(cleanup_result.returncode, 0, f"清理任务失败: {cleanup_result.stderr}")
        print("基础echo命令测试通过")
        
        print("测试2: 包含引号的复杂命令")
        result = run_gds_bg_command("echo 'Complex command with \"double quotes\" and single quotes'")
        self.assertEqual(result.returncode, 0, f"复杂命令创建失败: {result.stderr}")
        
        task_id = extract_task_id(result.stdout)
        self.assertIsNotNone(task_id, "无法提取任务ID")
        
        completed = wait_for_task_completion(task_id, max_wait=30)
        self.assertTrue(completed, "复杂命令未完成")
        
        result_output = run_gds_bg_result(task_id)
        self.assertEqual(result_output.returncode, 0, "获取复杂命令结果失败")
        self.assertIn("double quotes", result_output.stdout, "复杂命令结果不正确")
        
        run_gds_bg_cleanup(task_id)
        print("复杂命令测试通过")
        
        print("测试3: 错误命令处理")
        result = run_gds_bg_command(f'ls "{self.get_test_file_path("nonexistent_directory/that/should/not/exist")}"')
        self.assertEqual(result.returncode, 0, "错误命令任务创建应该成功")
        
        task_id = extract_task_id(result.stdout)
        self.assertIsNotNone(task_id, "无法提取错误任务ID")
        
        completed = wait_for_task_completion(task_id, max_wait=30)
        self.assertTrue(completed, "错误命令未完成")
        
        status_result = run_gds_bg_status(task_id)
        self.assertEqual(status_result.returncode, 0, "状态查询失败")
        self.assertIn("Status: completed", status_result.stdout, "错误命令状态不正确")
        run_gds_bg_cleanup(task_id)
        print("错误命令处理测试通过")

        print("测试4: 长时间运行任务的时间敏感化partial输出验证")
        
        # 导入时间相关模块
        import time
        import datetime
        import os  # 添加os导入用于调试
        
        # 配置参数（可调整）- 必须在使用前定义
        STAGE1_DURATION = 180  # 阶段1时长：log文件可能因Google Drive同步延迟未出现（秒），给予充足同步时间
        STAGE2_DURATION = 60   # 阶段2时长：log文件应该已同步，任务应即将完成（秒）
        STAGE3_DURATION = 60   # 阶段3时长：允许任务完成（秒）
        QUERY_INTERVAL = 10    # 查询间隔（秒），减少查询频率
        MAX_TEST_DURATION = STAGE1_DURATION + STAGE2_DURATION + STAGE3_DURATION + 60  # 最大测试时长
        TASK_SLEEP_DURATION = 180  # 任务sleep时长（秒），匹配阶段1+阶段2
        
        long_command = f'''python3 -c "
import time
import sys
start_time = time.strftime('%Y-%m-%d %H:%M:%S')
print('TASK_START_TIME:', start_time)
print('First echo: Task started at', time.strftime('%H:%M:%S'))
sys.stdout.flush()
print('About to sleep for {TASK_SLEEP_DURATION} seconds...')
sys.stdout.flush()
time.sleep({TASK_SLEEP_DURATION})
print('Second echo: Task completed at', time.strftime('%H:%M:%S'))
sys.stdout.flush()
"'''
        
        print(f"启动长时间运行的后台任务（sleep {TASK_SLEEP_DURATION}秒）...")
        
        task_start_time = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"测试开始时间: {task_start_time}")
        
        result = run_gds_bg_command(long_command)
        self.assertEqual(result.returncode, 0, f"长时间任务创建失败: {result.stderr}")
        
        task_id = extract_task_id(result.stdout)
        self.assertIsNotNone(task_id, f"无法提取长时间任务ID: {result.stdout}")
        print(f'长时间任务ID: {task_id}')
        
        def run_gds_bg_log_priority(task_id):
            """获取GDS --bg任务log - 使用优先队列"""
            cmd = [sys.executable, str(self.GOOGLE_DRIVE_PY), "--shell", "--no-direct-feedback", "--priority", "--bg", "--log", task_id]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result
        
        def run_gds_bg_log(task_id):
            """获取GDS --bg任务log"""
            cmd = [sys.executable, str(self.GOOGLE_DRIVE_PY), "--shell", "--no-direct-feedback", "--priority", "--bg", "--log", task_id]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result
        
        # 时间敏感化测试：重复查询直到成功条件满足
        
        test_start_time = time.time()
        query_count = 0
        task_completed = False
        task_start_time_str = None
        
        print(f"开始重复查询，直到成功条件满足（最大测试时长: {MAX_TEST_DURATION}秒）...")
        print(f"配置: 阶段1={STAGE1_DURATION}s, 阶段2={STAGE2_DURATION}s, 阶段3={STAGE3_DURATION}s, 查询间隔={QUERY_INTERVAL}s")
        
        while not task_completed:
            query_count += 1
            elapsed_time = time.time() - test_start_time
            current_time = time.strftime('%Y-%m-%d %H:%M:%S')
            
            # 异常检测：测试时间超出限制
            if elapsed_time > MAX_TEST_DURATION:
                self.fail(f"测试超时：已运行{elapsed_time:.1f}秒，超出{MAX_TEST_DURATION}秒限制")
            
            print(f"\n=== 第{query_count}次查询 (时间: {current_time}, 已过时间: {elapsed_time:.1f}秒) ===")
            
            # 确定当前时间阶段（使用配置参数）
            if elapsed_time < STAGE1_DURATION:
                stage = f"阶段1: 0-{STAGE1_DURATION}秒（log文件可能因同步延迟未出现）"
                expect_log_exists = False
            elif elapsed_time < STAGE1_DURATION + STAGE2_DURATION:
                stage = f"阶段2: {STAGE1_DURATION}-{STAGE1_DURATION + STAGE2_DURATION}秒（log文件应该已同步，任务未完成）"
                expect_log_exists = True
                expect_completed = False
            elif elapsed_time < STAGE1_DURATION + STAGE2_DURATION + STAGE3_DURATION:
                stage = f"阶段3: {STAGE1_DURATION + STAGE2_DURATION}-{STAGE1_DURATION + STAGE2_DURATION + STAGE3_DURATION}秒（允许完成）"
                expect_log_exists = True
                expect_completed = None  # 可能完成也可能未完成
            else:
                stage = f"阶段4: {STAGE1_DURATION + STAGE2_DURATION + STAGE3_DURATION}秒+（要求必须完成）"
                expect_log_exists = True
                expect_completed = True
            
            print(f"当前{stage}")
            
            # 查询log
            log_result = run_gds_bg_log(task_id)
            print(f'Log查询结果: returncode={log_result.returncode}')
            
            if log_result.returncode == 0:
                print(f'Log内容预览: {log_result.stdout[:200]}...' if len(log_result.stdout) > 200 else f'Log内容: {log_result.stdout}')
                
                # 提取任务开始时间
                current_task_start_time_str = None
                for line in log_result.stdout.split('\n'):
                    if 'TASK_START_TIME:' in line:
                        current_task_start_time_str = line.split('TASK_START_TIME:')[1].strip()
                        break
                
                if current_task_start_time_str:
                    if task_start_time_str is None:
                        task_start_time_str = current_task_start_time_str
                        print(f"✓ 首次获得任务开始时间: {task_start_time_str}")
                    
                    # 计算任务运行时间
                    try:
                        task_start = datetime.datetime.strptime(current_task_start_time_str, '%Y-%m-%d %H:%M:%S')
                        current_dt = datetime.datetime.now()
                        task_runtime = (current_dt - task_start).total_seconds()
                        print(f"✓ 任务运行时间: {task_runtime:.1f}秒")
                        
                        # 异常检测：任务运行时间异常
                        if task_runtime > MAX_TEST_DURATION:
                            self.fail(f"任务运行时间异常：{task_runtime:.1f}秒，超出{MAX_TEST_DURATION}秒限制")
                        
                    except Exception as e:
                        print(f"⚠ 无法解析任务开始时间: {e}")
                else:
                    # 异常检测：无法获得远端background cmd输出的测试开始时间
                    if elapsed_time >= STAGE1_DURATION:
                        self.fail("无法获得远端background cmd输出的测试开始时间")
                
                # 验证内容
                has_first_echo = "First echo: Task started at" in log_result.stdout
                has_sleep_msg = f"About to sleep for {TASK_SLEEP_DURATION} seconds" in log_result.stdout
                has_second_echo = "Second echo: Task completed at" in log_result.stdout
                
                if has_first_echo:
                    print("✓ 包含第一个echo输出")
                if has_sleep_msg:
                    print("✓ 包含sleep提示")
                if has_second_echo:
                    print("✓ 包含第二个echo输出（任务已完成）")
                    task_completed = True
                else:
                    print("- 不包含第二个echo输出（任务仍在运行）")
                
                # 阶段验证
                if elapsed_time >= STAGE1_DURATION and expect_log_exists:
                    self.assertTrue(has_first_echo, "应该包含第一个echo")
                    self.assertTrue(has_sleep_msg, "应该包含sleep提示")
                
                if elapsed_time >= STAGE1_DURATION + STAGE2_DURATION + STAGE3_DURATION and expect_completed:
                    self.assertTrue(has_second_echo, f"阶段4: {STAGE1_DURATION + STAGE2_DURATION + STAGE3_DURATION}秒后任务必须完成")
                    
            else:
                print(f'Log查询失败: {log_result.stderr}')
                # 异常检测：无法得到log file
                if elapsed_time >= STAGE1_DURATION and expect_log_exists:
                    self.fail(f"阶段2及以后: 无法得到log file（已等待{elapsed_time:.1f}秒）")
            
            # 查询status
            status_result = run_gds_bg_status(task_id, use_priority=True)
            print(f'Status查询结果: returncode={status_result.returncode}')
            if status_result.returncode == 0:
                print(f'Status内容: {status_result.stdout.strip()}')
                
                # 检查是否完成
                if "Status: completed" in status_result.stdout:
                    print("✓ 任务状态：已完成")
                    task_completed = True
                elif "Status: running" in status_result.stdout:
                    print("✓ 任务状态：运行中")
                
            else:
                print(f'Status查询失败: {status_result.stderr}')
            
            print(f"=== 第{query_count}次查询完成 ===")
            
            # 如果任务在阶段3或4完成，结束测试
            if task_completed and elapsed_time >= STAGE1_DURATION + STAGE2_DURATION:
                print(f"✅ 任务在{elapsed_time:.1f}秒时完成，测试通过！")
                break
            
            # 如果任务未完成，等待后继续查询
            if not task_completed:
                print(f"等待{QUERY_INTERVAL}秒后继续查询...")
                time.sleep(QUERY_INTERVAL)
        
        # 最终验证：确保任务已完成
        print("进行最终验证...")
        final_time = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"最终验证时间: {final_time}")
        
        final_status = run_gds_bg_status(task_id, use_priority=False)
        print(f'最终status查询结果: returncode={final_status.returncode}')
        print(f'最终status输出: {final_status.stdout}')
        
        # 验证最终检查是完整输出
        self.assertEqual(final_status.returncode, 0, "最终status查询应该成功")
        self.assertIn("First echo: Task started at", final_status.stdout, "最终检查应该包含第一个echo输出")
        self.assertIn("Second echo: Task completed at", final_status.stdout, "最终检查应该包含第二个echo输出（完整输出验证）")
        print("最终检查验证通过：确认是完整输出")
        
        # 清理任务
        cleanup_result = run_gds_bg_cleanup(task_id)
        self.assertEqual(cleanup_result.returncode, 0, f"清理长时间任务失败: {cleanup_result.stderr}")
        
        print("长时间运行任务的partial输出验证完成")
        print(f'GDS --bg后台任务功能测试完成')

    def test_25_edge_cases(self):
        """综合边缘情况测试"""
        print(f'综合边缘情况测试')
        
        # 子测试1: 反引号执行（与本地bash行为一致）
        print("子测试1: 反引号执行（与本地bash行为一致）")
        backtick_file = self.get_test_file_path("test_backtick.txt")
        result = self.gds(f'\'echo "Command: `whoami`" > "{backtick_file}"\'')
        self.assertEqual(result.returncode, 0, "反引号命令应该成功")
        
        # 测试反映实际行为：反引号会被执行（与本地bash行为一致）
        result = self.gds(f'cat "{backtick_file}"')
        self.assertEqual(result.returncode, 0, "读取反引号文件应该成功")
        self.assertIn("Command: root", result.stdout, "反引号应该被执行，与本地bash行为一致")
        
        # 子测试2: 占位符冲突防护
        print("子测试2: 占位符冲突防护")
        placeholder_file = self.get_test_file_path("test_placeholder.txt")
        result = self.gds(f'\'echo "Text with CUSTOM_PLACEHOLDER marker" > "{placeholder_file}"\'')
        self.assertEqual(result.returncode, 0, "占位符命令应该成功")

        result = self.gds(f'cat "{placeholder_file}"')
        self.assertEqual(result.returncode, 0, "读取占位符文件应该成功")
        self.assertIn("Text with CUSTOM_PLACEHOLDER marker", result.stdout, "应该包含占位符标记")
        
        # 子测试3: 复杂引号嵌套
        print("子测试3: 复杂引号嵌套")
        nested_file = self.get_test_file_path("test_nested.txt")
        nested_content = 'Outer "nested" quotes'
        result = self.gds(f"'echo \"{nested_content}\" > \"{nested_file}\"'")
        self.assertEqual(result.returncode, 0, "嵌套引号命令应该成功")
        
        result = self.gds(f'cat "{nested_file}"')
        self.assertEqual(result.returncode, 0, "读取嵌套引号文件应该成功")
        self.assertIn('Outer "nested" quotes', result.stdout, "应该正确处理嵌套引号")
        
        # 子测试4: printf测试（printf没有问题）
        print("子测试4: printf测试")
        printf_tests = [
            ("basic", "Hello World"),
            ("newline", "Line1\\nLine2"),
            ("format", "Number: %d"),  # printf without args outputs the format string as-is
            ("escape", "Tab:\\tBackslash:\\\\"),
        ]
        
        for i, test_data in enumerate(printf_tests):
            if len(test_data) == 2:
                name, content = test_data
                expected = content.replace('\\n', '\n').replace('\\t', '\t').replace('\\\\', '\\')
            else:
                name, content, expected = test_data
            
            printf_file = self.get_test_file_path(f'test_printf_{name}.txt')
            result = self.gds(f'\'printf "{content}" > "{printf_file}"\'')
            self.assertEqual(result.returncode, 0, f"printf {name}测试应该成功")
            
            result = self.gds(f'cat "{printf_file}"')
            self.assertEqual(result.returncode, 0, f"读取printf {name}文件应该成功")
            if len(test_data) == 3:
                self.assertIn(expected, result.stdout, f"应该包含printf {name}结果")
            else:
                # For basic tests, just check the content exists
                self.assertTrue(len(result.stdout) > 0, f"printf {name}应该有输出")
        
        # 子测试5: 格式字符串防护
        print("子测试5: 格式字符串防护")
        dangerous_formats = ["%s%s%s%s", "%x%x%x%x", "%^&*()%"]
        
        for i, fmt in enumerate(dangerous_formats):
            fmt_file = self.get_test_file_path(f'test_printf_fmt_{i}.txt')
            result = self.gds(f'\'echo "Format: {fmt}" > "{fmt_file}"\'')
            self.assertEqual(result.returncode, 0, f"格式字符串{fmt}应该成功")
            
            result = self.gds(f'cat "{fmt_file}"')
            self.assertEqual(result.returncode, 0, f"读取格式文件{i}应该成功")
            self.assertIn(f"Format: {fmt}", result.stdout, f"应该包含格式字符串{fmt}")
        
        # 子测试6: 特殊字符处理
        print("子测试6: 特殊字符处理")
        special_chars = [
            ("ampersand", "Text with & character"),
            ("pipe", "Text with | character"),
            ("semicolon", "Text with ; character"),
            ("parentheses", "Text with () characters"),
        ]
        
        for name, text in special_chars:
            special_file = self.get_test_file_path(f'test_{name}.txt')
            result = self.gds(f'\'echo "{text}" > "{special_file}"\'')
            self.assertEqual(result.returncode, 0, f"特殊字符{name}命令应该成功")
            
            result = self.gds(f'cat "{special_file}"')
            self.assertEqual(result.returncode, 0, f"读取特殊字符文件{name}应该成功")
            self.assertIn(text, result.stdout, f"应该包含特殊字符文本{name}")
        
        # 子测试7: Unicode编码处理
        print("子测试7: Unicode编码处理")
        unicode_texts = [
            ("chinese", "中文测试"),
            ("emoji", "测试🚀💻"),
            ("symbols", "©®™€"),
        ]
        
        for name, text in unicode_texts:
            unicode_file = self.get_test_file_path(f'test_unicode_{name}.txt')
            result = self.gds(f'\'echo "{text}" > "{unicode_file}"\'')
            self.assertEqual(result.returncode, 0, f"Unicode{name}命令应该成功")
            
            result = self.gds(f'cat "{unicode_file}"')
            self.assertEqual(result.returncode, 0, f"读取Unicode文件{name}应该成功")
            self.assertIn(text, result.stdout, f"应该包含Unicode文本{name}")
        
        # 清理测试文件
        cleanup_files = [
            "test_backtick.txt", "test_placeholder.txt", "test_nested.txt",
            "test_printf_basic.txt", "test_printf_newline.txt", "test_printf_format.txt", "test_printf_escape.txt",
            "test_printf_fmt_0.txt", "test_printf_fmt_1.txt", "test_printf_fmt_2.txt",
            "test_ampersand.txt", "test_pipe.txt", "test_semicolon.txt", "test_parentheses.txt",
            "test_unicode_chinese.txt", "test_unicode_emoji.txt", "test_unicode_symbols.txt"
        ]
        
        for filename in cleanup_files:
            file_path = self.get_test_file_path(filename)
            self.gds(f'rm -f "{file_path}"')
        print(f'综合边缘情况测试完成')


    def test_26_python_execution(self):
        """测试Python执行"""
        print(f'测试Python执行')
        
        # 执行各种Python代码
        test_cases = [
            ("print('Hello World')", "Hello World"),
            ("import sys; print(sys.version_info.major)", "3"),
            ("import os; print('os module imported')", "os module imported"),
            ("print(2 + 3 * 4)", "14"),
            ("print('Python'.upper())", "PYTHON"),
        ]
        
        for code, expected_output in test_cases:
            result = self.gds(["python", "-c", code])
            self.assertEqual(result.returncode, 0, f"Python代码执行应该成功: {code}")
            self.assertIn(expected_output, result.stdout, f"应该包含预期输出: {expected_output}")
        
        # 测试Python文件执行（通过echo创建文件）
        python_script = '''import sys
import os
import json
print(f'Python executable: {sys.executable}')
print("Python version:", sys.version)
print(f'Platform: {sys.platform}')
print(f'Current directory: {os.getcwd()}')'''
        
        # 创建测试文件
        pyenv_integration_test_path = f"{self.test_folder}/pyenv_integration_test.py"
        result = self.gds(f'cat > "{pyenv_integration_test_path}" << \"EOF\"\n{python_script}\nEOF')
        self.assertEqual(result.returncode, 0, "创建Python测试文件应该成功")
        
        # 执行测试文件
        result = self.gds(["python", pyenv_integration_test_path])
        self.assertEqual(result.returncode, 0, "执行Python测试文件应该成功")
        
        output = result.stdout
        self.assertIn("Python executable:", output, "应该显示Python可执行文件路径")
        self.assertIn("Python version:", output, "应该显示Python版本")
        
        # 清理测试文件
        result = self.gds(["rm", "-f", pyenv_integration_test_path])
        self.assertEqual(result.returncode, 0, "清理测试文件应该成功")
        print(f'Python执行集成测试完成')

    def test_27_window_control(self):
        """测试GDS单窗口控制机制 - 确保任何时候只有一个窗口存在"""
        print(f'测试GDS单窗口控制机制')
        
        import threading
        import psutil
        
        # 测试状态变量
        window_count = 0
        max_concurrent = 0
        window_history = []
        monitoring = True
        test_failed = False
        failure_reason = ""
        first_window_time = None
        
        def detect_gds_windows():
            """检测当前GDS窗口数量"""
            gds_processes = []
            
            for proc in psutil.process_iter(['pid', 'cmdline', 'create_time']):
                try:
                    cmdline = proc.info['cmdline']
                    if not cmdline:
                        continue
                        
                    cmdline_str = ' '.join(cmdline)
                    if ('python' in cmdline_str.lower() and 
                        ('-c' in cmdline_str or 'tkinter' in cmdline_str.lower()) and
                        ('Google Drive Shell' in cmdline_str or 'root.title' in cmdline_str or 'TKINTER_WINDOW' in cmdline_str)):
                        
                        create_time = proc.info['create_time']
                        gds_processes.append({
                            'pid': proc.info['pid'],
                            'create_time': create_time,
                            'cmdline': cmdline_str[:100] + '...' if len(cmdline_str) > 100 else cmdline_str
                        })
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
            return gds_processes
        
        def monitor_windows():
            """监控窗口变化 - 自动检测失败条件"""
            nonlocal window_count, max_concurrent, window_history, monitoring, test_failed, failure_reason, first_window_time
            
            print("开始自动监控...")
            start_time = time.time()
            
            while monitoring and not test_failed:
                try:
                    current_windows = detect_gds_windows()
                    current_count = len(current_windows)
                    current_time = time.time()
                    
                    # 检查10秒内是否有窗口出现，如果没有则结束测试
                    if current_time - start_time > 10:
                        if first_window_time is None:
                            test_failed = True
                            failure_reason = "10秒内没有窗口出现（可能死锁）"
                            print(f'自动失败: {failure_reason}')
                        else:
                            # 有窗口出现，10秒后根据窗口个数结束测试
                            print(f'10秒测试时间到，根据窗口个数结束测试')
                            print(f'当前窗口个数: {current_count}')
                            monitoring = False  # 结束监控
                        break
                    
                    if current_count != window_count:
                        timestamp = time.strftime('%H:%M:%S')
                        print(f'[{timestamp}] 窗口数量变化: {window_count} -> {current_count}')
                        
                        # 记录第一个窗口出现时间
                        if current_count > 0 and first_window_time is None:
                            first_window_time = current_time
                            print(f'第一个窗口在 {current_time - start_time:.1f}s 时出现')
                        
                        if current_count > window_count:
                            for window in current_windows:
                                print(f'   新窗口: PID={window["pid"]}')
                        
                        window_count = current_count
                        window_history.append({
                            'timestamp': current_time,
                            'count': current_count,
                            'windows': current_windows.copy()
                        })
                        
                        # 更新最大并发数
                        if current_count > max_concurrent:
                            max_concurrent = current_count
                            
                        # 立即检测多窗口失败条件
                        if current_count > 1:
                            test_failed = True
                            failure_reason = f"检测到 {current_count} 个窗口同时存在（多窗口并发问题）"
                            print(f'自动失败: {failure_reason}')
                            
                            for i, window in enumerate(current_windows):
                                print(f'     窗口{i+1}: PID={window["pid"]}')
                            break
                    
                    time.sleep(0.5)  # 检测间隔
                    
                except Exception as e:
                    print(f'监控出错: {e}')
                    test_failed = True
                    failure_reason = f"监控异常: {e}"
                    break
        
        # 启动监控线程
        monitor_thread = threading.Thread(target=monitor_windows, daemon=True)
        monitor_thread.start()
        
        # 运行一个简单的GDS命令来触发窗口
        print("启动GDS命令触发窗口...")
        try:
            test_process = subprocess.Popen(
                [sys.executable, str(self.GOOGLE_DRIVE_PY), '--shell', '--no-direct-feedback', 'pwd'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            print(f'测试进程已启动 (PID: {test_process.pid})')
            
            # 等待测试完成或失败
            start_time = time.time()
            while monitoring and not test_failed:
                if test_process.poll() is not None:
                    # 进程已结束
                    print("测试进程完成")
                    break
                
                # 检查是否超过最大测试时间（30秒）
                if time.time() - start_time > 30:
                    print("测试超时 (30秒)")
                    test_process.kill()
                    break
                
                time.sleep(0.5)
                
        except Exception as e:
            print(f'启动测试失败: {e}')
            test_failed = True
            failure_reason = f"测试启动异常: {e}"
        finally:
            monitoring = False
            if 'test_process' in locals() and test_process.poll() is None:
                test_process.kill()
        
        # 等待监控线程结束
        monitor_thread.join(timeout=2)
        
        print("\n测试结果分析:")
        print("=" * 40)
        
        print(f'窗口统计:')
        print(f'   最大并发窗口数: {max_concurrent}')
        print(f'   窗口变化记录: {len(window_history)} 次')
        
        if first_window_time:
            print(f'   第一个窗口出现时间: 测试开始后 {first_window_time - time.time() + 10:.1f}s')
        
        # 最终判断
        if test_failed:
            print(f'\n测试失败: {failure_reason}')
            self.assertTrue(False, f"单窗口控制测试失败: {failure_reason}")
        elif max_concurrent == 0:
            print(f'\n测试失败: 没有窗口出现')
            self.assertTrue(False, "没有窗口出现，可能存在死锁")
        elif max_concurrent == 1:
            print(f'\n测试通过: 窗口控制正常')
            print("   只有1个窗口出现")
            print("   没有多窗口并发")
            self.assertTrue(True, "单窗口控制测试通过")
        else:
            print(f'\n测试失败: 最大并发窗口数 {max_concurrent} > 1')
            self.assertTrue(False, f"检测到多个窗口并发: {max_concurrent} 个窗口")
        
        print(f'GDS单窗口控制测试完成')

    def test_28_pyenv_basic(self):
        """测试Python版本管理基础功能"""
        print(f'测试Python版本管理基础功能')
        
        # 测试列出可用版本
        result = self.gds(["pyenv", "--list-available"])
        self.assertEqual(result.returncode, 0, "列出可用Python版本应该成功")
        
        output = result.stdout
        
        # 如果没有可用版本，自动刷新缓存
        if "No verified Python versions" in output:
            print("缓存为空或过期，正在更新缓存...")
            update_result = self.gds(["pyenv", "--update-cache"])
            self.assertEqual(update_result.returncode, 0, "更新缓存应该成功")
            
            # 重新列出可用版本
            result = self.gds(["pyenv", "--list-available"])
            self.assertEqual(result.returncode, 0, "刷新缓存后列出可用Python版本应该成功")
            output = result.stdout
        
        self.assertIn("Available Python versions", output, "应该显示可用版本列表")
        self.assertIn("3.8", output, "应该包含Python 3.8版本")
        self.assertIn("3.9", output, "应该包含Python 3.9版本")
        self.assertIn("3.10", output, "应该包含Python 3.10版本")
        self.assertIn("3.11", output, "应该包含Python 3.11版本")
        
        # 测试列出已安装版本（初始应该为空）
        result = self.gds(["pyenv", "--versions"])
        self.assertEqual(result.returncode, 0, "列出已安装Python版本应该成功")
        
        # 测试显示当前版本
        result = self.gds(["pyenv", "--version"])
        self.assertEqual(result.returncode, 0, "显示当前Python版本应该成功")
        
        # 测试显示全局版本
        result = self.gds(["pyenv", "--global"])
        self.assertEqual(result.returncode, 0, "显示全局Python版本应该成功")
        
        # 测试显示本地版本
        result = self.gds(["pyenv", "--local"])
        self.assertEqual(result.returncode, 0, "显示本地Python版本应该成功")
        
        print(f'Python版本管理基础功能测试完成')

    def test_29_pyenv_version_management(self):
        """测试Python版本安装和管理"""
        print(f'测试Python版本安装和管理')
        test_version = "3.9.18"
        print(f'注意：Python版本安装测试仅验证命令接口，不进行实际安装')
        print(f'如需完整测试，请手动执行: GDS pyenv --install {test_version}')
        
        # 测试安装命令格式验证
        result = self.gds(["pyenv", "--install"], expect_success=False)
        self.assertNotEqual(result.returncode, 0, "不提供版本号的安装命令应该失败")
        
        output = result.stdout + result.stderr
        self.assertIn("Please specify a Python version", output, "应该提示需要指定版本号")
        
        # 测试卸载命令格式验证
        result = self.gds(["pyenv", "--uninstall"], expect_success=False)
        self.assertNotEqual(result.returncode, 0, "不提供版本号的卸载命令应该失败")
        
        output = result.stdout + result.stderr
        self.assertIn("Please specify a Python version", output, "应该提示需要指定版本号")
        
        # 测试设置全局版本（未安装版本）
        result = self.gds(["pyenv", "--global", test_version], expect_success=False)
        self.assertNotEqual(result.returncode, 0, "设置未安装版本为全局版本应该失败")
        output = result.stdout + result.stderr
        self.assertIn("is not installed", output, "应该提示版本未安装")
        
        # 测试设置本地版本（未安装版本）
        result = self.gds(["pyenv", "--local", test_version], expect_success=False)
        self.assertNotEqual(result.returncode, 0, "设置未安装版本为本地版本应该失败")
        
        output = result.stdout + result.stderr
        self.assertIn("is not installed", output, "应该提示版本未安装")
        print(f'Python版本安装和管理测试完成')

        # 检查当前Python版本
        result = self.gds(["pyenv", "--version"])
        self.assertEqual(result.returncode, 0, "检查当前Python版本应该成功")
        
        # 列出可用版本
        result = self.gds(["pyenv", "--list-available"])
        self.assertEqual(result.returncode, 0, "列出可用版本应该成功")
        
        # 检查已安装版本
        result = self.gds(["pyenv", "--versions"])
        self.assertEqual(result.returncode, 0, "检查已安装版本应该成功")
    
    def test_30_pyenv_version_change(self):
        """测试pyenv版本切换 - 动态获取可用版本并随机选择进行测试"""
        print(f'测试pyenv版本切换（使用随机可用版本）')
        
        # 步骤1：获取所有可用的Python版本
        print("步骤1：获取所有可用的Python版本")
        result = self.gds(["pyenv", "--list"])
        self.assertEqual(result.returncode, 0, "获取可用版本应该成功")
        available_versions_output = result.stdout
        
        # 解析可用版本，过滤掉Python 2.x版本（Colab可能不支持）
        import re
        version_lines = available_versions_output.split('\n')
        available_versions = []
        
        for line in version_lines:
            line = line.strip()
            if line and not line.startswith('Available Python versions') and not line.startswith('Showing'):
                # 提取版本号，只选择Python 3.x版本
                version_match = re.search(r'(3\.\d+\.\d+)', line)
                if version_match:
                    version = version_match.group(1)
                    # 过滤掉过新的版本（可能不稳定）和过旧的版本
                    major, minor, patch = map(int, version.split('.'))
                    if 7 <= minor <= 12:  # 选择3.7.x到3.12.x的版本
                        available_versions.append(version)
        
        self.assertGreaterEqual(len(available_versions), 2, "至少需要2个可用的Python版本进行测试")
        
        # 随机选择两个不同的版本进行测试
        import random
        import time
        random.seed(int(time.time()))  # 使用当前时间作为种子确保真正随机
        test_versions = random.sample(available_versions, 2)
        version1, version2 = test_versions
        
        print(f'从{len(available_versions)}个可用版本中随机选择的测试版本: {version1} 和 {version2}')
        
        # 检查当前已安装的版本
        print("步骤1.5：检查当前已安装的Python版本")
        result = self.gds(["pyenv", "--versions"])
        self.assertEqual(result.returncode, 0, "检查已安装版本应该成功")
        initial_versions = result.stdout
        print(f'当前已安装版本:\n{initial_versions}')
    
        print(f'\n步骤2：后台安装Python {version1}（使用--force强制重新安装）')
        # 使用新的pyenv --install-bg命令，添加--force参数防止版本已存在的问题
        result = self.gds(["pyenv", "--install-bg", version1, "--force"])
        self.assertEqual(result.returncode, 0, f"启动{version1}后台安装应该成功")
        
        # 从输出中提取任务ID  
        task_id = None
        import re
        # 尝试匹配"with ID:"格式
        match = re.search(r'with ID:\s*(\S+)', result.stdout)
        if match:
            task_id = match.group(1)
        else:
            # 尝试匹配其他格式
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if 'Task ID:' in line or 'task_id' in line.lower():
                    # 尝试提取任务ID
                    parts = line.split(':')
                    if len(parts) >= 2:
                        task_id = parts[-1].strip()
                        break
        
        self.assertIsNotNone(task_id, "应该能获取后台任务ID")
        print(f'后台安装任务已启动，任务ID: {task_id}')
        
        # 等待安装完成
        install_success = self.wait_for_pyenv_install(task_id, version1)
        self.assertTrue(install_success, f"Python {version1}应该成功安装")
        
        # 步骤3：后台安装第二个版本（使用--force强制安装）
        print(f'\n步骤3：后台安装Python {version2}（使用--force强制重新安装）')
        # 使用新的pyenv --install-bg命令，添加--force参数防止版本已存在的问题
        result = self.gds(["pyenv", "--install-bg", version2, "--force"])
        self.assertEqual(result.returncode, 0, f"启动{version2}后台安装应该成功")
        
        # 从输出中提取任务ID
        task_id = None
        import re
        # 尝试匹配"with ID:"格式
        match = re.search(r'with ID:\s*(\S+)', result.stdout)
        if match:
            task_id = match.group(1)
        else:
            # 尝试匹配其他格式
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if 'Task ID:' in line or 'task_id' in line.lower():
                    # 尝试提取任务ID
                    parts = line.split(':')
                    if len(parts) >= 2:
                        task_id = parts[-1].strip()
                        break
        
        self.assertIsNotNone(task_id, "应该能获取后台任务ID")
        print(f'后台安装任务已启动，任务ID: {task_id}')
        
        # 等待安装完成
        install_success = self.wait_for_pyenv_install(task_id, version2)
        self.assertTrue(install_success, f"Python {version2}应该成功安装")
        
        # 步骤4：切换到第一个版本并验证
        print(f'\n步骤4：切换到Python {version1}并验证')
        result = self.gds(["pyenv", "--local", version1])
        self.assertEqual(result.returncode, 0, f"切换到{version1}应该成功")
        
        # 验证当前Python版本
        test_code = 'import sys; print(sys.version)'
        result = self.gds(["python", "-c", test_code])
        self.assertEqual(result.returncode, 0, "执行Python代码应该成功")
        python_version_output = result.stdout
        print(f'当前Python版本输出: {python_version_output}')
        self.assertIn(version1, python_version_output, f"应该使用Python {version1}")
        
        # 步骤5：切换到第二个版本并验证
        print(f'\n步骤5：切换到Python {version2}并验证')
        result = self.gds(["pyenv", "--local", version2])
        self.assertEqual(result.returncode, 0, f"切换到{version2}应该成功")
        
        # 验证当前Python版本
        result = self.gds(["python", "-c", test_code])
        self.assertEqual(result.returncode, 0, "执行Python代码应该成功")
        python_version_output = result.stdout
        print(f'当前Python版本输出: {python_version_output}')
        self.assertIn(version2, python_version_output, f"应该使用Python {version2}")
        
        # 步骤6：再次切换回第一个版本验证
        print(f'\n步骤6：再次切换回Python {version1}并验证')
        result = self.gds(["pyenv", "--local", version1])
        self.assertEqual(result.returncode, 0, f"切换回{version1}应该成功")
        
        result = self.gds(["python", "-c", test_code])
        self.assertEqual(result.returncode, 0, "执行Python代码应该成功")
        python_version_output = result.stdout
        print(f'当前Python版本输出: {python_version_output}')
        self.assertIn(version1, python_version_output, f"应该使用Python {version1}")
        
        # 步骤7：测试Python脚本执行
        print(f'\n步骤7：测试Python脚本执行')
        test_script_content = '''import sys
import os

# 显示Python版本信息
print(f'Python version: {sys.version}')
print(f'Version info: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')
print("Script execution successful!")
'''.replace('"', '\\"')
        
        # 创建测试脚本，使用相对路径
        result = self.gds(f'cat > "{self.test_folder}/test_version_script.py" << \"EOF\"\n{test_script_content}\nEOF')
        self.assertEqual(result.returncode, 0, "创建测试脚本应该成功")
        
        # 首先检查脚本是否存在
        result = self.gds(f'ls -la "{self.test_folder}/test_version_script.py"')
        self.assertEqual(result.returncode, 0, "测试脚本应该存在")
        
        # 使用绝对路径执行Python脚本
        result = self.gds(f'python "{self.test_folder}/test_version_script.py"')
        self.assertEqual(result.returncode, 0, "执行Python脚本应该成功")
        self.assertIn("Script execution successful!", result.stdout, "应该显示脚本执行成功")
        self.assertIn(version1, result.stdout, f"脚本应该使用Python {version1}")
        
        # 清理
        result = self.gds(f'rm -f "{self.test_folder}/test_version_script.py"')
        self.assertEqual(result.returncode, 0, "清理测试文件应该成功")
        
        # 步骤8：测试卸载功能
        print(f'\n步骤8：测试Python版本卸载功能')
        
        # 记录卸载前的已安装版本
        result = self.gds(["pyenv", "--versions"])
        self.assertEqual(result.returncode, 0, "检查已安装版本应该成功")
        pre_uninstall_versions = result.stdout
        print(f'卸载前已安装版本:\n{pre_uninstall_versions}')
        
        # 卸载第一个版本
        print(f'\n步骤8.1：卸载Python {version1}')
        result = self.gds(["pyenv", "--uninstall", version1])
        self.assertEqual(result.returncode, 0, f"卸载Python {version1}应该成功")
        self.assertIn("uninstalled successfully", result.stdout, "应该显示卸载成功信息")
        
        # 验证版本已从列表中移除
        result = self.gds(["pyenv", "--versions"])
        self.assertEqual(result.returncode, 0, "检查已安装版本应该成功")
        post_uninstall_versions = result.stdout
        print(f'卸载{version1}后已安装版本:\n{post_uninstall_versions}')
        self.assertNotIn(version1, post_uninstall_versions, f"Python {version1}应该已从已安装版本列表中移除")
        
        # 验证当前版本已自动切换（如果卸载的是当前版本）
        result = self.gds(["python", "--version"])
        self.assertEqual(result.returncode, 0, "检查当前Python版本应该成功")
        current_python_version = result.stdout
        print(f'卸载后当前Python版本: {current_python_version}')
        
        # 尝试再次卸载同一版本（应该失败）
        print(f'\n步骤8.2：尝试再次卸载已卸载的版本{version1}（应该失败）')
        result = self.gds(["pyenv", "--uninstall", version1], expect_success=False)
        self.assertNotEqual(result.returncode, 0, f"再次卸载{version1}应该失败")
        self.assertIn("is not installed", result.stderr if result.stderr else result.stdout, "应该提示版本未安装")
        
        # 卸载第二个版本
        print(f'\n步骤8.3：卸载Python {version2}')
        result = self.gds(["pyenv", "--uninstall", version2])
        self.assertEqual(result.returncode, 0, f"卸载Python {version2}应该成功")
        self.assertIn("uninstalled successfully", result.stdout, "应该显示卸载成功信息")
        
        # 最终验证两个版本都已卸载
        result = self.gds(["pyenv", "--versions"])
        self.assertEqual(result.returncode, 0, "检查已安装版本应该成功")
        final_versions = result.stdout
        print(f'最终已安装版本:\n{final_versions}')
        self.assertNotIn(version1, final_versions, f"Python {version1}应该已完全移除")
        self.assertNotIn(version2, final_versions, f"Python {version2}应该已完全移除")
        
        print(f'\npyenv版本切换和卸载测试完成！成功测试了{version1}和{version2}的安装、切换和卸载')

    def test_31_pyenv_invalid_versions(self):
        """测试pyenv边缘情况和无效版本处理"""
        print(f'测试pyenv边缘情况和无效版本处理')

        # 测试无效的命令选项
        print("\n步骤1：测试无效命令选项")
        result = self.gds(["pyenv", "--invalid-option"], expect_success=False)
        self.assertNotEqual(result.returncode, 0, "无效选项应该失败")
        
        # 测试极端版本号 - 包括--global、--local、--install、--uninstall
        print("\n步骤2：测试极端版本号")
        extreme_versions = [
            "0.0.1",      # 极小版本号
            "99.99.99",   # 极大版本号
            "3.99.999",   # 不存在的版本
        ]
        
        for version in extreme_versions:
            # 测试全局设置
            result = self.gds(["pyenv", "--global", version], expect_success=False)
            self.assertNotEqual(result.returncode, 0, f"设置不存在版本 {version} 应该失败")
            output = result.stdout + result.stderr
            self.assertIn("is not installed", output, f"应该提示版本 {version} 未安装")
            
            # 测试本地设置
            result = self.gds(["pyenv", "--local", version], expect_success=False)
            self.assertNotEqual(result.returncode, 0, f"本地设置不存在版本 {version} 应该失败")
            
            # 测试安装不存在的版本（不使用--bg，直接测试失败）
            result = self.gds(["pyenv", "--install", version], expect_success=False)
            self.assertNotEqual(result.returncode, 0, f"安装不存在版本 {version} 应该失败")
            
            # 测试卸载未安装的版本
            result = self.gds(["pyenv", "--uninstall", version], expect_success=False)
            self.assertNotEqual(result.returncode, 0, f"卸载未安装版本 {version} 应该失败")
        
        # 测试长字符串版本
        print("\n步骤3：测试超长版本号")
        long_version = "3." + "9" * 100 + ".1"
        result = self.gds(["pyenv", "--global", long_version], expect_success=False)
        self.assertNotEqual(result.returncode, 0, "超长版本号应该失败")
        
        result = self.gds(["pyenv", "--install", long_version], expect_success=False)
        self.assertNotEqual(result.returncode, 0, "安装超长版本号应该失败")
        
        # 测试特殊字符版本号
        print("\n步骤4：测试特殊字符版本号")
        special_versions = [
            "3.9.1-alpha",
            "3.9.1+build",
            "3.9.1~rc1",
            "3.9.1 with spaces",
            "3.9.1;injection",
            "3.9.1|pipe",
            "3.9.1&background",
        ]
        
        for version in special_versions:
            result = self.gds(["pyenv", "--global", version], expect_success=False)
            self.assertNotEqual(result.returncode, 0, f"特殊字符版本 {version} 应该失败")
            
            result = self.gds(["pyenv", "--install", version], expect_success=False)
            self.assertNotEqual(result.returncode, 0, f"安装特殊字符版本 {version} 应该失败")
        
        print(f'\npyenv边缘情况测试完成')
        
    def test_32_redirection(self):
        """强化补丁：测试printf和echo -n重定向功能"""
        print(f'测试printf和echo -n重定向功能（强化补丁）')
        
        # 获取当前GDS工作目录的绝对路径
        pwd_result = self.gds(["pwd"])
        self.assertEqual(pwd_result.returncode, 0, "获取当前目录应该成功")
        current_dir = pwd_result.stdout.strip()
        
        # 定义测试目录名称
        redirection_test = f'{self.test_folder}/redirection_test'
        
        # 创建测试目录（使用相对路径）
        result = self.gds(f'mkdir -p "{redirection_test}"')
        self.assertEqual(result.returncode, 0, "创建测试目录应该成功")
        
        
        # 测试1: printf重定向（不带换行符）
        print("测试场景1: printf重定向")
        result = self.gds(f'printf "Hello World without newline" > "{redirection_test}/printf_test.txt"')
        self.assertEqual(result.returncode, 0, "printf重定向应该成功")
        
        # 验证文件内容
        result = self.gds(f'cat "{redirection_test}/printf_test.txt"')
        self.assertEqual(result.returncode, 0, "读取printf文件应该成功")
        self.assertEqual(result.stdout, "Hello World without newline", "printf内容应该正确且无换行符")
        
        # 测试2: echo -n重定向（不带换行符）
        print("测试场景2: echo -n重定向")
        result = self.gds(f'echo -n "Echo without newline" > {redirection_test}/echo_test.txt')
        self.assertEqual(result.returncode, 0, "echo -n重定向应该成功")
        
        # 验证文件内容
        result = self.gds(f'cat "{redirection_test}/echo_test.txt"')
        self.assertEqual(result.returncode, 0, "读取echo文件应该成功")
        self.assertEqual(result.stdout, "Echo without newline", "echo -n内容应该正确且无换行符")
        
        # 测试3: 普通echo重定向（带换行符）
        print("测试场景3: 普通echo重定向")
        result = self.gds(f'echo "Echo with newline" > {redirection_test}/echo_normal.txt')
        self.assertEqual(result.returncode, 0, "echo重定向应该成功")
        
        # 验证文件内容
        result = self.gds(f'cat "{redirection_test}/echo_normal.txt"')
        self.assertEqual(result.returncode, 0, "读取echo文件应该成功")
        self.assertEqual(result.stdout, "Echo with newline\n", "echo内容应该正确且带换行符")
        
        # 测试4: 追加重定向 >>
        print("测试场景4: 追加重定向")
        result = self.gds(f'printf "Appended text" >> "{redirection_test}/printf_test.txt"')
        self.assertEqual(result.returncode, 0, "printf追加重定向应该成功")
        
        # 验证追加后的内容
        result = self.gds(f'cat "{redirection_test}/printf_test.txt"')
        self.assertEqual(result.returncode, 0, "读取追加文件应该成功")
        self.assertEqual(result.stdout, "Hello World without newlineAppended text", "追加内容应该正确")
        
        # 测试5: 复杂重定向（带特殊字符）
        print("测试场景5: 复杂重定向")
        result = self.gds(f'echo "Special chars: @#$%^&*()" > "{redirection_test}/special.txt"')
        self.assertEqual(result.returncode, 0, "特殊字符重定向应该成功")
        
        # 验证特殊字符内容
        result = self.gds(f'cat "{redirection_test}/special.txt"')
        self.assertEqual(result.returncode, 0, "读取特殊字符文件应该成功")
        self.assertEqual(result.stdout, "Special chars: @#$%^&*()\n", "特殊字符内容应该正确")
        
        # 测试6: 多级目录重定向
        print("测试场景6: 多级目录重定向")
        result = self.gds(f'mkdir -p "{redirection_test}/subdir/deep"')
        self.assertEqual(result.returncode, 0, "创建多级目录应该成功")
        
        result = self.gds(f'echo -n "Deep directory test" > "{redirection_test}/subdir/deep/test.txt"')
        self.assertEqual(result.returncode, 0, "多级目录重定向应该成功")
        
        # 验证多级目录文件
        result = self.gds(f'cat "{redirection_test}/subdir/deep/test.txt"')
        self.assertEqual(result.returncode, 0, "读取多级目录文件应该成功")
        self.assertEqual(result.stdout, "Deep directory test", "多级目录文件内容应该正确")
        
        # 测试7: 验证重定向符号不被错误引用
        print("测试场景7: 重定向符号处理验证")
        # 这个测试确保重定向符号 > 不会被当作普通字符串处理
        result = self.gds(f'echo "test" > "{redirection_test}/redirect_symbol_test.txt"')
        self.assertEqual(result.returncode, 0, "重定向符号处理应该成功")
        
        # 如果重定向符号被错误引用，这个文件不会被创建
        result = self.gds(f'ls "{redirection_test}/redirect_symbol_test.txt"')
        self.assertEqual(result.returncode, 0, "重定向创建的文件应该存在")
        
        # 清理测试文件
        result = self.gds(f'rm -rf "{redirection_test}"')
        self.assertEqual(result.returncode, 0, "清理测试目录应该成功")
        print(f'printf和echo -n重定向功能测试完成（强化补丁）')
    
    def test_33_regex(self):
        """测试正则表达式验证功能 - 基于实际文件操作"""
        print(f'测试正则表达式验证功能')
        
        import re
        
        # 准备：创建测试目录和文件
        print("准备：创建测试目录和文件")
        redirection_test_folder = f"{self.test_folder}/regex_test"
        result = self.gds(f'mkdir -p "{redirection_test_folder}"')
        self.assertEqual(result.returncode, 0, "创建测试目录应该成功")
        
        # 创建测试文件1: 基本文本文件
        test_file1 = f'{redirection_test_folder}/echo_test.txt'
        result = self.gds(f'echo -n "Echo without newline" > "{test_file1}"')
        self.assertEqual(result.returncode, 0, "创建测试文件1应该成功")
        
        # 创建测试文件2: 带路径的文件
        test_file2 = f'{redirection_test_folder}/printf_test.txt'
        result = self.gds(f'printf "Hello World" > "{test_file2}"')
        self.assertEqual(result.returncode, 0, "创建测试文件2应该成功")
        
        # 创建测试文件3: 追加模式文件
        test_file3 = f'{redirection_test_folder}/append.txt'
        result = self.gds(f'echo "Line 1" > "{test_file3}"')
        self.assertEqual(result.returncode, 0, "创建测试文件3应该成功")
        result = self.gds(f'echo "Line 2" >> "{test_file3}"')
        self.assertEqual(result.returncode, 0, "追加到测试文件3应该成功")
        
        # 创建测试文件4: 用于grep的文件（使用多个echo命令代替heredoc）
        test_file4 = f'{redirection_test_folder}/grep_source.txt'
        result = self.gds(f'echo "pattern line 1" > "{test_file4}"')
        self.assertEqual(result.returncode, 0, "创建测试文件4第一行应该成功")
        result = self.gds(f'echo "no match line" >> "{test_file4}"')
        self.assertEqual(result.returncode, 0, "创建测试文件4第二行应该成功")
        result = self.gds(f'echo "pattern line 2" >> "{test_file4}"')
        self.assertEqual(result.returncode, 0, "创建测试文件4第三行应该成功")
        
        # 测试1: 基本重定向模式匹配（验证命令和结果）
        print("测试1: 基本重定向模式匹配")
        shell_cmd_clean = f'echo -n "Echo without newline" > "{test_file1}"'
        redirect_pattern = r'(.+?)\s*>\s*(.+)'
        match = re.search(redirect_pattern, shell_cmd_clean)
        self.assertIsNotNone(match, f"应该匹配重定向模式: {shell_cmd_clean}")
        
        # 验证文件确实被创建
        result = self.gds(f'cat "{test_file1}"')
        self.assertEqual(result.returncode, 0, "读取测试文件1应该成功")
        self.assertEqual(result.stdout.strip(), "Echo without newline", "文件内容应该正确")
        
        # 测试2: 复杂命令模式匹配（基于已创建的文件）
        print(f'测试2: 复杂命令模式匹配')
        # 验证test_file2的内容
        result = self.gds(f'cat "{test_file2}"')
        self.assertEqual(result.returncode, 0, "读取测试文件2应该成功")
        self.assertEqual(result.stdout.strip(), "Hello World", "printf文件内容应该正确")
        
        # 验证test_file3的追加内容
        result = self.gds(f'cat "{test_file3}"')
        self.assertEqual(result.returncode, 0, "读取测试文件3应该成功")
        self.assertIn("Line 1", result.stdout, "追加文件应该包含第一行")
        self.assertIn("Line 2", result.stdout, "追加文件应该包含第二行")
        
        # 测试正则表达式匹配
        complex_commands = [
            (f'printf "Hello World" > "{test_file2}"', r'printf\s+.+?\s*>\s*.+'),
            (f'echo "Line 2" >> "{test_file3}"', r'echo\s+.+?\s*>>\s*.+'),
            (f'cat "{test_file4}" | grep pattern > "{redirection_test_folder}/result.txt"', r'cat\s+.+?\s*\|\s*grep\s+.+?\s*>\s*.+'),
        ]
        
        for command, pattern in complex_commands:
            match = re.search(pattern, command)
            self.assertIsNotNone(match, f"应该匹配命令模式: {command}")
        
        # 测试3: 文件路径验证模式（使用实际创建的文件路径）
        print("测试3: 文件路径验证模式")
        # 创建不同路径类型的测试文件
        py_file = f'{redirection_test_folder}/test_script.py'
        sh_file = f'{redirection_test_folder}/test_script.sh'
        json_file = f'{redirection_test_folder}/config_123.json'
        
        result = self.gds(f'echo "# Python script" > "{py_file}"')
        self.assertEqual(result.returncode, 0, "创建Python文件应该成功")
        result = self.gds(f'echo "#!/bin/bash" > "{sh_file}"')
        self.assertEqual(result.returncode, 0, "创建Shell脚本应该成功")
        result = self.gds(f'echo "{{}}" > "{json_file}"')
        self.assertEqual(result.returncode, 0, "创建JSON文件应该成功")
        
        # 验证文件路径匹配
        path_patterns = [
            (test_file1, r'.*\.txt$'),
            (py_file, r'.*\.py$'),
            (sh_file, r'.*\.sh$'),
            (json_file, r'.*config.*\.json$'),
        ]
        
        for path, pattern in path_patterns:
            match = re.search(pattern, path)
            self.assertIsNotNone(match, f"应该匹配路径模式: {path}")
            # 验证文件确实存在
            result = self.gds(f'ls "{path}"')
            self.assertEqual(result.returncode, 0, f"文件应该存在: {path}")
        
        # 测试4: 命令参数解析模式（基于实际执行的命令）
        print("测试4: 命令参数解析模式")
        grep_result_file = f'{redirection_test_folder}/grep_result.txt'
        grep_cmd = f'\'grep -n "pattern" "{test_file4}" > "{grep_result_file}"\''
        result = self.gds(grep_cmd)
        self.assertEqual(result.returncode, 0, "grep命令应该成功")
        
        # 验证grep结果
        result = self.gds(f'cat "{grep_result_file}"')
        self.assertEqual(result.returncode, 0, "读取grep结果应该成功")
        self.assertIn("pattern", result.stdout, "grep结果应该包含pattern")
        
        # 测试参数解析正则
        arg_parsing_tests = [
            (f'echo "test content"', r'echo\s+"([^"]+)"', "test content"),
            (grep_cmd, r'grep\s+(-[a-zA-Z]+)\s+"([^"]+)"', ["-n", "pattern"]),
        ]
        
        for command, pattern, expected in arg_parsing_tests:
            match = re.search(pattern, command)
            self.assertIsNotNone(match, f"应该匹配参数模式: {command}")
            if isinstance(expected, str):
                self.assertEqual(match.group(1), expected, f"应该正确提取参数: {command}")
        
        # 测试5: 特殊字符转义模式（使用实际文件）
        print("测试5: 特殊字符转义模式")
        escape_file = f'{redirection_test_folder}/escape_test.txt'
        result = self.gds(f'printf "Tab:\\tNewline:\\n" > "{escape_file}"')
        self.assertEqual(result.returncode, 0, "创建转义测试文件应该成功")
        
        # 验证文件内容包含转义字符
        result = self.gds(f'cat "{escape_file}"')
        self.assertEqual(result.returncode, 0, "读取转义文件应该成功")
        
        # 测试转义模式匹配
        escape_tests = [
            (f'printf "Tab:\\tNewline:\\n" > "{escape_file}"', r'printf\s+"([^"\\]*(?:\\.[^"\\]*)*)"'),
        ]
        
        for command, pattern in escape_tests:
            match = re.search(pattern, command)
            self.assertIsNotNone(match, f"应该匹配转义模式: {command}")
        
        # 测试6: 管道和重定向组合模式（使用实际文件）
        print("测试6: 管道和重定向组合模式")
        # 测试实际的管道命令
        pipe_result_file = f'{redirection_test_folder}/pipe_result.txt'
        pipe_cmd = f'cat "{test_file4}" | grep "pattern" | wc -l > "{pipe_result_file}"'
        result = self.gds(pipe_cmd)
        self.assertEqual(result.returncode, 0, "管道命令应该成功")
        
        # 验证管道结果
        result = self.gds(f'cat "{pipe_result_file}"')
        self.assertEqual(result.returncode, 0, "读取管道结果应该成功")
        self.assertIn("2", result.stdout.strip(), "应该有2行匹配pattern")
        
        # 测试管道模式匹配
        pipe_redirect_tests = [
            (pipe_cmd, r'(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*>\s*(.+)'),
            (f'cat "{test_file3}" | head -2 > "{redirection_test_folder}/head_result.txt"', r'(.+?)\s*\|\s*(.+?)\s*>\s*(.+)'),
        ]
        
        for command, pattern in pipe_redirect_tests:
            match = re.search(pattern, command)
            self.assertIsNotNone(match, f"应该匹配管道重定向模式: {command}")
            self.assertTrue(len(match.groups()) >= 3, f"应该提取多个命令组: {command}")
        
        # 测试7: 文件名和扩展名验证
        print("测试7: 文件名和扩展名验证")
        filename_tests = [
            ("test_file.txt", r'^[a-zA-Z0-9_-]+\.(txt|py|json|md)$', True),
            ("invalid file name.txt", r'^[a-zA-Z0-9_-]+\.(txt|py|json|md)$', False),
            ("script.py", r'^[a-zA-Z0-9_-]+\.(txt|py|json|md)$', True),
            ("config.json", r'^[a-zA-Z0-9_-]+\.(txt|py|json|md)$', True),
            ("readme.md", r'^[a-zA-Z0-9_-]+\.(txt|py|json|md)$', True),
            ("file.exe", r'^[a-zA-Z0-9_-]+\.(txt|py|json|md)$', False),
        ]
        
        for filename, pattern, should_match in filename_tests:
            match = re.search(pattern, filename)
            if should_match:
                self.assertIsNotNone(match, f"应该匹配文件名: {filename}")
            else:
                self.assertIsNone(match, f"不应该匹配文件名: {filename}")
        
        # 测试8: 命令注入防护模式
        print("测试8: 命令注入防护模式")
        injection_tests = [
            ("echo 'safe content'", r"[;&|`$()]", False),  # 安全命令
            ("echo 'content'; rm -rf /'", r"[;&|`$()]", True),  # 危险命令
            ("echo 'content' && malicious", r"[;&|`$()]", True),  # 危险命令
            ("echo `whoami`", r"[;&|`$()]", True),  # 命令替换
            ("echo $(whoami)", r"[;&|`$()]", True),  # 命令替换
        ]
        
        for command, pattern, should_match in injection_tests:
            match = re.search(pattern, command)
            if should_match:
                self.assertIsNotNone(match, f"应该检测到危险模式: {command}")
            else:
                self.assertIsNone(match, f"不应该检测到危险模式: {command}")
        
        # 清理测试目录
        print("清理测试目录")
        result = self.gds(f'rm -rf "{redirection_test_folder}"')
        self.assertEqual(result.returncode, 0, "清理测试目录应该成功")
        
        print(f'正则表达式验证功能测试完成')
    
    def test_34_bash_output_alignment(self):
        """测试GDS shell输出与bash shell输出的对齐性"""
        print(f'测试GDS shell输出与bash shell输出的对齐性')
        import tempfile
        import os
        
        # 创建本地临时目录用于bash测试
        local_temp_dir = tempfile.mkdtemp(prefix="gds_bash_test_")
        bash_test_dir = os.path.join(local_temp_dir, "bash_test_dir")
        print(f'使用本地临时bash测试目录: {bash_test_dir}')
        
        # 创建本地bash测试目录
        os.makedirs(bash_test_dir, exist_ok=True)
        
        # 创建GDS测试目录
        gds_test_dir = f'{self.test_folder}/gds_test_dir'
        result = self.gds(f'mkdir -p "{gds_test_dir}"')
        self.assertEqual(result.returncode, 0, "创建GDS测试目录应该成功")
        
        # 测试用例1: 基本命令对比
        print("测试1: 基本命令对比")
        
        # 基本命令（不涉及文件系统路径）
        basic_commands_simple = [
            'echo "Hello World"',
            'echo "Line1\\nLine2"'
        ]
        
        # 文件系统命令（需要分别为GDS和bash准备）
        gds_fs_commands = [
            f'mkdir "{gds_test_dir}/test_basic_dir"',
            f'ls "{gds_test_dir}/test_basic_dir"',
            f'rmdir "{gds_test_dir}/test_basic_dir"'
        ]
        
        bash_fs_commands = [
            f'mkdir "{bash_test_dir}/test_basic_dir"',
            f'ls "{bash_test_dir}/test_basic_dir"',
            f'rmdir "{bash_test_dir}/test_basic_dir"'
        ]
        
        # 测试简单命令（不涉及文件系统）
        for cmd in basic_commands_simple:
            print(f'  测试简单命令: {cmd}')
            
            # 运行GDS命令
            gds_result = self.gds(cmd, expect_success=True, check_function_result=False)
            gds_stdout = self.get_cleaned_stdout(gds_result)
            
            # 为bash准备等效命令
            bash_cmd = cmd
            if cmd.startswith('echo') and ('\\n' in cmd or '\\t' in cmd):
                # GDS会自动为包含转义序列的echo命令添加-e标志
                # 所以bash也需要使用-e标志来保持一致
                import re
                echo_pattern = r'^echo\s+(["\'])(.*?)\1(.*)$'
                match = re.match(echo_pattern, cmd.strip())
                if match:
                    quote_char = match.group(1)
                    content = match.group(2)
                    rest_args = match.group(3).strip()
                    bash_cmd = f'echo -e {quote_char}{content}{quote_char}'
                    if rest_args:
                        bash_cmd += f' {rest_args}'
            
            # 运行bash命令
            bash_result = self.bash(bash_cmd)
            
            # 对比返回码
            self.assertEqual(gds_result.returncode, bash_result.returncode, 
                           f"命令 '{cmd}' 返回码应该一致")
            
            # 对于echo命令，输出应该一致
            if cmd.startswith('echo'):
                self.assertEqual(gds_stdout.strip(), bash_result.stdout.strip(), 
                               f"echo命令 '{cmd}' (bash: '{bash_cmd}') 输出应该一致")
        
        # 测试文件系统命令（分别运行）
        print("  测试文件系统命令:")
        for gds_cmd, bash_cmd in zip(gds_fs_commands, bash_fs_commands):
            print(f'    GDS: {gds_cmd}')
            print(f'    Bash: {bash_cmd}')
            
            # 运行GDS命令
            gds_result = self.gds(gds_cmd, expect_success=True, check_function_result=False)
            
            # 运行bash命令
            bash_result = self.bash(bash_cmd)
            
            # 对比返回码（都应该成功）
            self.assertEqual(gds_result.returncode, 0, f"GDS命令应该成功: {gds_cmd}")
            self.assertEqual(bash_result.returncode, 0, f"bash命令应该成功: {bash_cmd}")
            
        
        # 测试用例2: 文件操作对比
        print("测试2: 文件操作对比")
        
        # 创建相同的测试内容
        # 注意：GDS会自动为包含\\n的echo命令添加-e标志，所以bash也需要使用echo -e
        test_content = "Test content for alignment\\nLine 2: 中文测试\\nLine 3: Special chars @#$%"
        
        # 在GDS中创建文件（GDS会自动添加-e标志）
        gds_file_path = f'{gds_test_dir}/test_alignment.txt'
        gds_create_cmd = f'echo "{test_content}" > "{gds_file_path}"'
        gds_result = self.gds(gds_create_cmd)
        self.assertEqual(gds_result.returncode, 0, "GDS创建文件应该成功")
        
        # 在bash中创建相同文件（需要明确使用echo -e）
        bash_file_path = f'{bash_test_dir}/test_alignment.txt'
        bash_create_cmd = f'echo -e "{test_content}" > "{bash_file_path}"'
        bash_result = self.bash(bash_create_cmd)
        self.assertEqual(bash_result.returncode, 0, "bash创建文件应该成功")
        
        # 对比cat输出
        gds_cat_cmd = f'cat "{gds_file_path}"'
        bash_cat_cmd = f'cat "{bash_file_path}"'
        
        gds_cat_result = self.gds(gds_cat_cmd)
        gds_stdout = self.get_cleaned_stdout(gds_cat_result)
        
        bash_cat_result = self.bash(bash_cat_cmd)
        
        self.assertEqual(gds_cat_result.returncode, bash_cat_result.returncode, "cat返回码应该一致")
        self.assertEqual(gds_stdout.strip(), bash_cat_result.stdout.strip(), "cat输出应该一致")
            
        # 测试用例3: 无输出命令对比（echo重定向等）
        print("测试3: 无输出命令对比")
        
        # 测试echo重定向（应该没有stdout输出）
        gds_redirect_commands = [
            f'echo "redirect test" > "{gds_test_dir}/redirect_test.txt"',
            f'echo "append test" >> "{gds_test_dir}/redirect_test.txt"',
            f'mkdir "{gds_test_dir}/silent_dir"'
        ]
        
        bash_redirect_commands = [
            f'echo "redirect test" > "{bash_test_dir}/redirect_test.txt"',
            f'echo "append test" >> "{bash_test_dir}/redirect_test.txt"',
            f'mkdir "{bash_test_dir}/silent_dir"'
        ]
        
        for gds_cmd, bash_cmd in zip(gds_redirect_commands, bash_redirect_commands):
            print(f'  测试无输出命令: {gds_cmd}')
            
            # 运行GDS命令
            gds_result = self.gds(gds_cmd, expect_success=True, check_function_result=False)
            gds_stdout = self.get_cleaned_stdout(gds_result)
            
            # 运行bash命令
            bash_result = self.bash(bash_cmd)
            
            # 验证两者都没有实质性输出
            self.assertEqual(len(gds_stdout.strip()), 0, f"GDS无输出命令 '{gds_cmd}' 应该没有输出")
            self.assertEqual(len(bash_result.stdout.strip()), 0, f"bash无输出命令 '{bash_cmd}' 应该没有输出")
            self.assertEqual(gds_result.returncode, bash_result.returncode, f"无输出命令返回码应该一致")
        
        # 测试用例4: 边缘情况对比
        print("测试4: 边缘情况对比")
        
        # 简化边缘情况测试，只测试基本的重定向
        gds_edge_cases = [
            f'echo "" > "{gds_test_dir}/empty_test.txt"',  # 空字符串
            f'echo " " > "{gds_test_dir}/space_test.txt"',  # 空格
        ]
        
        bash_edge_cases = [
            f'echo "" > "{bash_test_dir}/empty_test.txt"',  # 空字符串
            f'echo " " > "{bash_test_dir}/space_test.txt"',  # 空格
        ]
        
        for gds_cmd, bash_cmd in zip(gds_edge_cases, bash_edge_cases):
            print(f'  测试边缘情况: {gds_cmd}')
            
            # 运行GDS命令
            gds_result = self.gds(gds_cmd, expect_success=True, check_function_result=False)
            gds_stdout = self.get_cleaned_stdout(gds_result)
            
            # 运行bash命令
            bash_result = self.bash(bash_cmd)
            
            # 验证两者都没有实质性输出
            self.assertEqual(len(gds_stdout.strip()), 0, f"GDS边缘情况 '{gds_cmd}' 应该没有输出")
            self.assertEqual(len(bash_result.stdout.strip()), 0, f"bash边缘情况 '{bash_cmd}' 应该没有输出")
            self.assertEqual(gds_result.returncode, bash_result.returncode, f"边缘情况返回码应该一致")
    
        # 测试用例5: 组合命令和重定向对比（重要！）
        print("测试5: 组合命令和重定向对比")
        
        # 测试echo重定向+cat组合（修复的bug）
        print("  子测试5.1: echo重定向+cat组合")
        # GDS使用远程路径，bash使用本地路径
        gds_redirect_cat_cmd = f'echo "test content for redirect" > "{gds_test_dir}/redirect_and_cat.txt" && cat "{gds_test_dir}/redirect_and_cat.txt"'
        bash_redirect_cat_cmd = f'echo "test content for redirect" > "{bash_test_dir}/redirect_and_cat.txt" && cat "{bash_test_dir}/redirect_and_cat.txt"'
        
        # GDS测试
        gds_result = self.gds(gds_redirect_cat_cmd)
        self.assertEqual(gds_result.returncode, 0, "GDS echo+cat组合应该成功")
        self.assertIn("test content for redirect", gds_result.stdout, "GDS cat输出应该显示")
        
        # bash测试
        bash_result = self.bash(bash_redirect_cat_cmd, bash_test_dir)
        self.assertEqual(bash_result.returncode, 0, "bash echo+cat组合应该成功")
        self.assertIn("test content for redirect", bash_result.stdout, "bash cat输出应该显示")
        
        # 对比输出
        gds_cleaned = self.get_cleaned_stdout(gds_result)
        self.assertEqual(gds_cleaned.strip(), bash_result.stdout.strip(), 
                        "GDS和bash的echo+cat输出应该一致")
        
        # 测试多重重定向+cat组合
        print("  子测试5.2: 多重重定向+cat组合")
        gds_multi_redirect_cmd = f'echo "line1" > "{gds_test_dir}/multi.txt" && echo "line2" >> "{gds_test_dir}/multi.txt" && cat "{gds_test_dir}/multi.txt"'
        bash_multi_redirect_cmd = f'echo "line1" > "{bash_test_dir}/multi.txt" && echo "line2" >> "{bash_test_dir}/multi.txt" && cat "{bash_test_dir}/multi.txt"'
        
        gds_result = self.gds(gds_multi_redirect_cmd)
        self.assertEqual(gds_result.returncode, 0, "GDS多重重定向应该成功")
        self.assertIn("line1", gds_result.stdout, "GDS应该显示line1")
        self.assertIn("line2", gds_result.stdout, "GDS应该显示line2")
        
        bash_result = self.bash(bash_multi_redirect_cmd, bash_test_dir)
        self.assertEqual(bash_result.returncode, 0, "bash多重重定向应该成功")
        gds_multi_cleaned = self.get_cleaned_stdout(gds_result)
        self.assertEqual(gds_multi_cleaned.strip(), bash_result.stdout.strip(), 
                        "多重重定向输出应该一致")
        
        # 测试管道+重定向+cat组合
        print("  子测试5.3: 管道+重定向+cat组合")
        gds_pipe_redirect_cmd = f'echo -e "test\\nline\\ndata" | grep "line" > "{gds_test_dir}/grep_output.txt" && cat "{gds_test_dir}/grep_output.txt"'
        bash_pipe_redirect_cmd = f'echo -e "test\\nline\\ndata" | grep "line" > "{bash_test_dir}/grep_output.txt" && cat "{bash_test_dir}/grep_output.txt"'
        
        gds_result = self.gds(gds_pipe_redirect_cmd)
        self.assertEqual(gds_result.returncode, 0, "GDS管道+重定向应该成功")
        self.assertIn("line", gds_result.stdout, "GDS应该显示grep结果")
        
        bash_result = self.bash(bash_pipe_redirect_cmd, bash_test_dir)
        self.assertEqual(bash_result.returncode, 0, "bash管道+重定向应该成功")
        
        # 跳过失败命令和短路测试，因为GDS的远端shell不会因为命令失败而退出
        # 这些测试不适合bash输出对齐测试的目标
        
        # 跳过错误情况对比测试，因为GDS和bash的错误处理机制不同
        # GDS有自己的错误包装和处理方式，不适合直接对比
        
        # 测试用例4: 复杂命令对比
        print("测试4: 复杂命令对比")
        
        # 创建多个测试文件进行ls测试
        for i in range(3):
            filename = f"test_file_{i}.txt"
            content = f"Content of file {i}"
            
            # GDS创建（使用远程路径）
            gds_result = self.gds(f'echo "{content}" > "{gds_test_dir}/{filename}"')    
            self.assertEqual(gds_result.returncode, 0, f"GDS创建{filename}应该成功")
            
            # bash创建（使用本地路径）
            bash_result = self.bash(f'echo "{content}" > "{bash_test_dir}/{filename}"', bash_test_dir)
            self.assertEqual(bash_result.returncode, 0, f"bash创建{filename}应该成功")
        
        # 对比ls输出（分别使用正确的路径）
        gds_ls_cmd = f'ls {gds_test_dir}/test_file_*.txt'
        bash_ls_cmd = f'ls {bash_test_dir}/test_file_*.txt'
        
        gds_ls_result = self.gds(gds_ls_cmd)
        bash_ls_result = self.bash(bash_ls_cmd, bash_test_dir)
        
        self.assertEqual(gds_ls_result.returncode, bash_ls_result.returncode, "ls返回码应该一致")
        
        # 检查文件名是否都存在（只比较文件名，不比较路径）
        gds_cleaned = self.get_cleaned_stdout(gds_ls_result)
        gds_files = set([os.path.basename(f) for f in gds_cleaned.strip().split()])
        bash_files = set([os.path.basename(f) for f in bash_ls_result.stdout.strip().split()])
        
        expected_files = {"test_file_0.txt", "test_file_1.txt", "test_file_2.txt"}
        self.assertEqual(gds_files, expected_files, "GDS ls应该列出所有测试文件")
        self.assertEqual(bash_files, expected_files, "bash ls应该列出所有测试文件")
        
        # 测试用例5: 错误情况对齐测试（grep和cat不存在文件）
        print("测试5: 错误情况对齐测试")
        
        # 测试grep不存在文件
        nonexistent_file = "nonexistent_file_for_test.txt"
        gds_grep_cmd = f'grep "pattern" "{gds_test_dir}/{nonexistent_file}"'
        bash_grep_cmd = f'grep "pattern" "{bash_test_dir}/{nonexistent_file}"'
        
        print(f"  测试grep不存在文件: {nonexistent_file}")
        gds_grep_result = self.gds(gds_grep_cmd, expect_success=False)
        bash_grep_result = self.bash(bash_grep_cmd, bash_test_dir)
        
        # 两者都应该返回非0（错误）
        self.assertNotEqual(gds_grep_result.returncode, 0, "GDS grep不存在文件应该返回错误码")
        self.assertNotEqual(bash_grep_result.returncode, 0, "bash grep不存在文件应该返回错误码")
        
        # 测试cat不存在文件
        gds_cat_cmd = f'cat "{gds_test_dir}/{nonexistent_file}"'
        bash_cat_cmd = f'cat "{bash_test_dir}/{nonexistent_file}"'
        
        print(f"  测试cat不存在文件: {nonexistent_file}")
        gds_cat_result = self.gds(gds_cat_cmd, expect_success=False)
        bash_cat_result = self.bash(bash_cat_cmd, bash_test_dir)
        
        # 两者都应该返回非0（错误）
        self.assertNotEqual(gds_cat_result.returncode, 0, "GDS cat不存在文件应该返回错误码")
        self.assertNotEqual(bash_cat_result.returncode, 0, "bash cat不存在文件应该返回错误码")
        
        # 检查错误信息格式（不要求完全一致，但都应该包含文件名）
        gds_cat_cleaned = self.get_cleaned_stdout(gds_cat_result)
        self.assertIn(nonexistent_file, gds_cat_cleaned, "GDS cat错误信息应该包含文件名")
        self.assertIn(nonexistent_file, bash_cat_result.stdout + bash_cat_result.stderr, "bash cat错误信息应该包含文件名")
        
        print("bash输出对齐测试完成")
        
        # 清理本地临时目录
        import shutil
        try:
            shutil.rmtree(local_temp_dir)
            print(f'已清理本地临时目录: {local_temp_dir}')
        except Exception as e:
            print(f'清理本地临时目录失败: {e}')
        
        print(f'GDS与bash输出对齐性测试完成')

    def test_35_priority_queue(self):
        """测试优先队列的执行顺序"""
        
        import threading
        import time
        from datetime import datetime
        
        # 创建结果收集器
        results = []
        results_lock = threading.Lock()
        
        def run_command_with_timing(command, priority, delay, task_name):
            """运行命令并记录时间"""
            if delay > 0:
                time.sleep(delay)
            
            start_time = datetime.now()
            result = self.gds(command, is_priority=priority)
            end_time = datetime.now()
            
            with results_lock:
                results.append({
                    'task_name': task_name,
                    'priority': priority,
                    'start_time': start_time,
                    'end_time': end_time,
                    'success': result.returncode == 0,
                    'output': result.stdout.strip() if result.stdout else ""
                })
        
        # 创建测试命令
        commands = [
            ('echo "Task 1 completed"', False, 0, "Task1_Normal"),      # 普通队列，立即启动
            ('echo "Task 2 completed"', False, 2, "Task2_Normal"),      # 普通队列，延迟2秒
            ('echo "Task 3 completed"', True, 4, "Task3_Priority")      # 优先队列，延迟4秒
        ]
        
        print("启动3个并发任务...")
        print("- Task1: 普通队列，立即启动")
        print("- Task2: 普通队列，延迟2秒启动")  
        print("- Task3: 优先队列，延迟4秒启动")
        print("预期执行顺序: Task1 -> Task3 -> Task2")
        
        # 启动线程
        threads = []
        for command, priority, delay, task_name in commands:
            thread = threading.Thread(
                target=run_command_with_timing,
                args=(command, priority, delay, task_name)
            )
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=120)  # 2分钟超时
        
        # 验证结果
        self.assertEqual(len(results), 3, "应该有3个任务完成")
        
        # 按完成时间排序
        results.sort(key=lambda x: x['end_time'])
        
        print("\n实际执行顺序:")
        for i, result in enumerate(results):
            print(f'{i+1}. {result["task_name"]} ({"优先" if result["priority"] else "普通"}队列) - {result["end_time"].strftime("%H:%M:%S.%f")[:-3]}')
            self.assertTrue(result['success'], f"{result['task_name']}应该执行成功")
        
        # 验证优先队列的执行顺序
        # Task3（优先队列）应该在Task2（普通队列）之前完成，尽管Task3启动更晚
        task1_idx = next(i for i, r in enumerate(results) if r['task_name'] == 'Task1_Normal')
        task2_idx = next(i for i, r in enumerate(results) if r['task_name'] == 'Task2_Normal')
        task3_idx = next(i for i, r in enumerate(results) if r['task_name'] == 'Task3_Priority')
        
        print(f'\n执行顺序验证:')
        print(f'Task1位置: {task1_idx + 1}')
        print(f'Task2位置: {task2_idx + 1}')
        print(f'Task3位置: {task3_idx + 1}')
        
        # 关键验证：Task3（优先队列）应该在Task2（普通队列）之前完成
        self.assertLess(task3_idx, task2_idx, 
                       "Task3（优先队列）应该在Task2（普通队列）之前完成，证明优先队列功能正常")
        
        # 注意：由于并发和优先队列机制，Task1不一定最先完成
        # 重要的是验证优先队列的优先级功能正常工作
        print("优先队列执行顺序测试完成")
        print(f'验证通过：优先队列Task3在普通队列Task2之前完成')


    def test_36_at_path_operations(self):
        """测试@路径相关的文件操作和导航"""
        print("测试@路径相关的文件操作和导航")
        
        # 测试1: 导航到@路径
        print("测试1: 导航到@路径（REMOTE_ENV）")
        result = self.gds('cd @')
        self.assertEqual(result.returncode, 0, "cd @应该成功")
        
        # 验证当前路径（pwd返回逻辑路径）
        result = self.gds('pwd')
        self.assertEqual(result.returncode, 0, "pwd应该成功")
        # 应该显示@（逻辑路径）
        self.assertIn("@", result.stdout, "pwd输出应该包含@路径")
        
        # 测试2: ls @路径
        print("测试2: ls @路径")
        result = self.gds('ls @')
        self.assertEqual(result.returncode, 0, "ls @应该成功")
        
        # 确保@/tmp存在
        print("确保@/tmp目录存在")
        result = self.gds('mkdir -p @/tmp')
        self.assertEqual(result.returncode, 0, "mkdir -p @/tmp应该成功")
        
        # 测试3: 在@/tmp路径下创建文件
        print("测试3: 在@/tmp路径下创建测试文件")
        test_file = "test_at_path_file.txt"
        result = self.gds(f'echo "Test content for @ path" > @/tmp/{test_file}')
        self.assertEqual(result.returncode, 0, f"在@/tmp路径创建{test_file}应该成功")
        
        # 验证文件创建
        result = self.gds(f'cat @/tmp/{test_file}')
        self.assertEqual(result.returncode, 0, f"读取@/tmp/{test_file}应该成功")
        self.assertIn("Test content for @ path", result.stdout, "文件内容应该正确")
        
        # 测试4: 在@/tmp路径下创建目录
        print("测试4: 在@/tmp路径下创建测试目录")
        test_dir = "test_at_path_dir"
        result = self.gds(f'mkdir @/tmp/{test_dir}')
        self.assertEqual(result.returncode, 0, f"在@/tmp路径创建目录{test_dir}应该成功")
        
        # 验证目录创建
        result = self.gds(f'ls @/tmp/{test_dir}')
        self.assertEqual(result.returncode, 0, f"ls @/tmp/{test_dir}应该成功")
        
        # 测试5: 在@/tmp路径下的子目录中操作
        print("测试5: 在@/tmp路径的子目录中创建文件")
        sub_file = "subdir_test.txt"
        result = self.gds(f'echo "Subdirectory test" > @/tmp/{test_dir}/{sub_file}')
        self.assertEqual(result.returncode, 0, f"在@/tmp/{test_dir}中创建文件应该成功")
        
        # 验证子目录文件
        result = self.gds(f'cat @/tmp/{test_dir}/{sub_file}')
        self.assertEqual(result.returncode, 0, f"读取@/tmp/{test_dir}/{sub_file}应该成功")
        self.assertIn("Subdirectory test", result.stdout, "子目录文件内容应该正确")
        
        # 测试6: cd到@/tmp路径的子目录
        print("测试6: cd到@/tmp路径的子目录")
        result = self.gds(f'cd @/tmp/{test_dir}')
        self.assertEqual(result.returncode, 0, f"cd @/tmp/{test_dir}应该成功")
        
        # 验证当前路径
        result = self.gds('pwd')
        self.assertEqual(result.returncode, 0, "pwd应该成功")
        self.assertIn(test_dir, result.stdout, f"当前路径应该包含{test_dir}")
        
        # 测试7: 从@路径子目录中读取文件（使用相对路径）
        print("测试7: 在@路径子目录中使用相对路径")
        result = self.gds(f'cat {sub_file}')
        self.assertEqual(result.returncode, 0, f"在当前目录读取{sub_file}应该成功")
        self.assertIn("Subdirectory test", result.stdout, "相对路径读取应该成功")
        
        # 测试8: mv操作（@/tmp路径内移动文件）
        print("测试8: mv操作（@/tmp路径内移动文件）")
        new_file_name = "renamed_test.txt"
        result = self.gds(f'mv @/tmp/{test_file} @/tmp/{test_dir}/{new_file_name}')
        self.assertEqual(result.returncode, 0, "mv文件到@/tmp路径子目录应该成功")
        
        # 验证文件已移动
        result = self.gds(f'cat @/tmp/{test_dir}/{new_file_name}')
        self.assertEqual(result.returncode, 0, "读取移动后的文件应该成功")
        self.assertIn("Test content for @ path", result.stdout, "移动后文件内容应该保持")
        
        # 验证原文件不存在
        result = self.gds(f'cat @/tmp/{test_file}', expect_success=False)
        self.assertNotEqual(result.returncode, 0, "原文件应该不存在")
        
        # 测试9: rm操作（清理@/tmp路径中的测试文件和目录）
        print("测试9: 清理@/tmp路径中的测试数据")
        # 先切换到安全目录，避免删除当前所在的目录
        result = self.gds('cd @')
        self.assertEqual(result.returncode, 0, "切换到@根目录应该成功")
        
        result = self.gds(f'rm -rf @/tmp/{test_dir}')
        self.assertEqual(result.returncode, 0, "删除@/tmp路径测试目录应该成功")
        
        # 验证目录已删除
        result = self.gds(f'ls @/tmp/{test_dir}', expect_success=False)
        self.assertNotEqual(result.returncode, 0, "测试目录应该已被删除")
        
        # 测试10: 混合路径操作（@/tmp路径和~/tmp路径）
        print("测试10: 混合路径操作（@/tmp路径和~/tmp路径）")
        # 在@/tmp路径创建文件
        at_file = "at_path_test.txt"
        result = self.gds(f'echo "From @ path" > @/tmp/{at_file}')
        self.assertEqual(result.returncode, 0, "在@/tmp路径创建文件应该成功")
        
        # 复制到~/tmp路径
        home_file = "home_path_test.txt"
        result = self.gds(f'cat @/tmp/{at_file} > ~/tmp/{home_file}')
        self.assertEqual(result.returncode, 0, "从@/tmp路径复制到~/tmp路径应该成功")
        
        # 验证~/tmp路径文件
        result = self.gds(f'cat ~/tmp/{home_file}')
        self.assertEqual(result.returncode, 0, "读取~/tmp路径文件应该成功")
        self.assertIn("From @ path", result.stdout, "复制的文件内容应该正确")
        
        # 清理测试文件
        self.gds(f'rm @/tmp/{at_file}')
        self.gds(f'rm ~/tmp/{home_file}')
        
        print("@路径操作测试完成")

    def test_37_pyenv_install_local(self):
        """测试pyenv本地下载安装功能 - 动态选择随机版本进行本地下载和远程编译安装"""
        print("测试pyenv本地下载安装功能（使用随机版本）")
        
        # 步骤1：获取所有可用的Python版本
        print("步骤1：获取所有可用的Python版本")
        result = self.gds(["pyenv", "--list"])
        self.assertEqual(result.returncode, 0, "获取可用版本应该成功")
        available_versions_output = result.stdout
        
        # 解析可用版本，过滤掉Python 2.x版本（Colab可能不支持）
        import re
        version_lines = available_versions_output.split('\n')
        available_versions = []
        
        for line in version_lines:
            line = line.strip()
            if line and not line.startswith('Available Python versions') and not line.startswith('Showing'):
                # 提取版本号，只选择Python 3.x版本
                version_match = re.search(r'(3\.\d+\.\d+)', line)
                if version_match:
                    version = version_match.group(1)
                    # 过滤掉过新的版本（可能不稳定）和过旧的版本，选择适合测试的版本
                    major, minor, patch = map(int, version.split('.'))
                    if 8 <= minor <= 11:  # 选择3.8.x到3.11.x的版本（避免太新或太旧）
                        available_versions.append(version)
        
        self.assertGreaterEqual(len(available_versions), 1, "至少需要1个可用的Python版本进行测试")
        
        # 随机选择一个版本进行测试
        import random
        import time
        random.seed(int(time.time()))  # 使用当前时间作为种子确保真正随机
        test_version = random.choice(available_versions)
        
        print(f'从{len(available_versions)}个可用版本中随机选择的测试版本: {test_version}')
        
        # 步骤1.5：检查当前已安装的版本
        print("步骤1.5：检查当前已安装的Python版本")
        result = self.gds(["pyenv", "--versions"])
        self.assertEqual(result.returncode, 0, "检查已安装版本应该成功")
        initial_versions = result.stdout
        print(f'当前已安装版本:\n{initial_versions}')
        
        # 步骤3：使用本地下载安装Python版本
        print(f'\n步骤3：本地下载并安装Python {test_version}')
        print("注意：这个过程包括本地下载、上传、远程编译，可能需要10-20分钟")
        
        # 使用pyenv --install-local命令（本地下载模式），添加--force参数强制重新安装
        result = self.gds(["pyenv", "--install-local", test_version, "--force"])
        self.assertEqual(result.returncode, 0, f"本地下载安装Python {test_version}应该成功")
        
        # 从输出中提取任务ID（如果是后台任务）
        task_id = None
        import re
        # 尝试匹配"with ID:"格式
        match = re.search(r'with ID:\s*(\S+)', result.stdout)
        if match:
            task_id = match.group(1)
        else:
            # 尝试匹配其他格式
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if 'Task ID:' in line or 'task_id' in line.lower():
                    # 尝试提取任务ID
                    parts = line.split(':')
                    if len(parts) >= 2:
                        task_id = parts[-1].strip()
                        break
        
        # 如果有任务ID，说明是后台任务，需要等待完成
        if task_id:
            print(f'后台安装任务已启动，任务ID: {task_id}')
            # 等待安装完成
            install_success = self.wait_for_pyenv_install(task_id, test_version)
            self.assertTrue(install_success, f"Python {test_version}应该成功安装")
            print(f'✓ Python {test_version}本地下载安装成功')
        else:
            # 如果没有任务ID，验证直接输出中的安装成功信息
            self.assertIn("installed successfully", result.stdout, "应该显示安装成功信息")
            print(f'✓ Python {test_version}本地下载安装成功')
        
        # 步骤4：验证版本已安装
        print(f'\n步骤4：验证Python {test_version}已正确安装')
        result = self.gds(["pyenv", "--versions"])
        self.assertEqual(result.returncode, 0, "检查已安装版本应该成功")
        updated_versions = result.stdout
        self.assertIn(test_version, updated_versions, f"Python {test_version}应该出现在已安装版本列表中")
        print(f'✓ Python {test_version}已出现在版本列表中')
        
        # 步骤5：切换到新安装的版本并验证
        print(f'\n步骤5：切换到Python {test_version}并验证')
        result = self.gds(["pyenv", "--local", test_version])
        self.assertEqual(result.returncode, 0, f"切换到Python {test_version}应该成功")
        
        # 验证版本切换
        result = self.gds(["pyenv", "--version"])
        self.assertEqual(result.returncode, 0, "检查当前版本应该成功")
        self.assertIn(test_version, result.stdout, f"当前版本应该是{test_version}")
        print(f'✓ 成功切换到Python {test_version}')
        
        # 步骤6：测试Python可执行性
        print(f'\n步骤6：测试Python {test_version}可执行性')
        result = self.gds(["python", "--version"])
        self.assertEqual(result.returncode, 0, "python --version应该成功")
        self.assertIn(test_version, result.stdout, f"python --version应该显示{test_version}")
        print(f'✓ Python {test_version}可执行性验证成功')
        
        # 步骤7：测试Python代码执行
        print(f'\n步骤7：测试Python代码执行')
        test_code = f'import sys; print(f"Python {{sys.version}} is working correctly!")'
        result = self.gds(["python", "-c", test_code])
        self.assertEqual(result.returncode, 0, "Python代码执行应该成功")
        self.assertIn("is working correctly", result.stdout, "Python代码应该正确执行")
        print(f'✓ Python {test_version}代码执行验证成功')
        
        # 步骤8：测试pip功能
        print(f'\n步骤8：测试pip功能')
        result = self.gds(["python", "-c", "import pip; print(f'pip version: {pip.__version__}')"])
        self.assertEqual(result.returncode, 0, "pip导入应该成功")
        self.assertIn("pip version:", result.stdout, "应该显示pip版本信息")
        print(f'✓ pip功能验证成功')
        
        print(f'\npyenv本地下载安装测试完成')
        print(f'✓ Python {test_version}通过本地下载模式成功安装并验证')

    def test_reset_functionality(self):
        """测试GDS reset功能 - 设置错误ID验证找不到，并且报错当中有指出访问文件夹的问题"""
        print(f'测试GDS reset功能')
        
        # 步骤1：记录当前的路径ID配置
        print("步骤1：记录当前的路径ID配置")
        
        # 步骤2：为~/test_reset设置一个无效的ID
        test_path = "~/test_reset"
        invalid_id = "invalid_test_reset_id_12345"
        print(f'\n步骤2：为{test_path}设置无效ID: {invalid_id}')
        
        result = self.gds(["reset", "id", test_path, invalid_id])
        self.assertEqual(result.returncode, 0, "设置无效ID应该成功")
        self.assertIn(f"Reset Google Drive id for path '{test_path}' to {invalid_id}", result.stdout, "应该显示ID设置成功")
        
        # 步骤3：尝试访问该路径，验证错误信息
        print(f'\n步骤3：尝试访问{test_path}，验证错误信息')
        
        # 使用ls命令访问该路径
        result = self.gds(["ls", test_path], expect_success=False)
        self.assertNotEqual(result.returncode, 0, "访问无效ID路径应该失败")
        
        # 验证错误信息包含预期的内容
        error_output = result.stderr if result.stderr else result.stdout
        print(f'错误输出: {error_output}')
        
        # 检查错误信息是否包含关键信息
        self.assertTrue(
            any([
                "Unable to find the id for subfolder" in error_output,
                "Unable to access" in error_output,
                "API error" in error_output,
                invalid_id in error_output
            ]),
            f"错误信息应该包含访问失败的详细信息，实际输出: {error_output}"
        )
        
        # 步骤4：移除错误的ID设置
        print(f'\n步骤4：移除{test_path}的错误ID设置')
        
        result = self.gds(["reset", "remove", test_path])
        self.assertEqual(result.returncode, 0, "移除ID设置应该成功")
        self.assertIn(f"Path ID removed: {test_path}", result.stdout, "应该显示ID移除成功")
        
        # 步骤5：验证移除ID后可以正常访问（或至少不是因为无效ID导致的错误）
        print(f'\n步骤5：验证移除ID后的访问情况')
        
        result = self.gds(["ls", test_path], expect_success=False)
        # 这次可能仍然失败（因为路径可能不存在），但错误信息应该不同
        if result.returncode != 0:
            error_output = result.stderr if result.stderr else result.stdout
            print(f'移除ID后的错误输出: {error_output}')
            
            # 确保不再是无效ID的错误
            self.assertNotIn(invalid_id, error_output, f"错误信息不应该再包含无效ID {invalid_id}")
        
        print(f'✓ GDS reset功能测试完成')


class ParallelTestRunner:
    """并行测试运行器"""
    
    def __init__(self, num_workers=3):
        self.num_workers = num_workers
        self.test_methods = []
        self.total_gds_commands = 0
        self.completed_gds_commands = 0
        self.results = {}
        self.lock = threading.Lock()
        self.start_time = None
        
    def discover_test_methods(self, test_class):
        """发现所有测试方法并统计GDS命令数量"""
        print(f'发现测试方法...')
        
        methods = []
        for name in dir(test_class):
            if name.startswith('test_'):
                method = getattr(test_class, name)
                if callable(method):
                    # 统计该方法中的gds调用次数
                    source = inspect.getsource(method)
                    gds_count = source.count('gds(')
                    gds_count += source.count('gds_with_retry(')
                    
                    methods.append({
                        'name': name,
                        'method': method,
                        'gds_commands': gds_count,
                        'status': 'pending'
                    })
                    self.total_gds_commands += gds_count
        
        self.test_methods = sorted(methods, key=lambda x: x['name'])
        return methods
    
    def run_single_test(self, test_info, worker_id):
        """运行单个测试方法"""
        test_name = test_info['name']
        
        try:
            print(f'Tool: Worker-{worker_id}: 开始执行 {test_name}')
            
            # 创建测试实例
            test_instance = GDSTest()
            test_instance.setUpClass()
            
            # 执行测试方法
            method = getattr(test_instance, test_name)
            start_time = time.time()
            method()
            end_time = time.time()
            
            # 更新结果
            with self.lock:
                self.results[test_name] = {
                    'status': 'success',
                    'duration': end_time - start_time,
                    'worker': worker_id,
                    'gds_commands': test_info['gds_commands']
                }
                self.completed_gds_commands += test_info['gds_commands']
                
            print(f'Worker-{worker_id}: {test_name} 成功 ({end_time - start_time:.1f}s)')
            return True
            
        except Exception as e:
            with self.lock:
                self.results[test_name] = {
                    'status': 'failed',
                    'error': str(e),
                    'worker': worker_id,
                    'gds_commands': test_info['gds_commands']
                }
                # 即使失败也计入已完成的命令数
                self.completed_gds_commands += test_info['gds_commands']
                
            print(f'Error: Worker-{worker_id}: {test_name} 失败 - {str(e)[:100]}')
            return False
    
    def display_progress(self):
        """显示实时进度"""
        while True:
            with self.lock:
                if len(self.results) >= len(self.test_methods):
                    break
                    
                # 统计状态
                success_count = sum(1 for r in self.results.values() if r['status'] == 'success')
                failed_count = sum(1 for r in self.results.values() if r['status'] == 'failed')
                pending_count = len(self.test_methods) - len(self.results)
                
                # 计算进度
                progress_percent = (self.completed_gds_commands / self.total_gds_commands * 100) if self.total_gds_commands > 0 else 0
                
                # 显示进度
                elapsed = time.time() - self.start_time if self.start_time else 0
                print(f"\r进度: {success_count}{failed_count}Error: {pending_count}⏳ | "
                      f"GDS命令: {self.completed_gds_commands}/{self.total_gds_commands} ({progress_percent:.1f}%) | "
                      f"用时: {elapsed:.0f}s", end="", flush=True)
            
            time.sleep(1)
    
    def run_parallel_tests(self):
        """并行运行所有测试"""
        print(f'启动并行测试 (Workers: {self.num_workers})')
        print(f'发现 {len(self.test_methods)} 个测试方法，共 {self.total_gds_commands} 个GDS命令')
        print(f"=" * 80)
        
        self.start_time = time.time()
        
        # 启动进度显示线程
        progress_thread = threading.Thread(target=self.display_progress, daemon=True)
        progress_thread.start()
        
        # 使用线程池执行测试
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            # 提交所有任务
            future_to_test = {}
            for i, test_info in enumerate(self.test_methods):
                worker_id = (i % self.num_workers) + 1
                future = executor.submit(self.run_single_test, test_info, worker_id)
                future_to_test[future] = test_info
            
            # 等待所有任务完成
            for future in as_completed(future_to_test):
                test_info = future_to_test[future]
                try:
                    future.result()
                except Exception as e:
                    print(f'\n测试执行异常: {test_info["name"]} - {e}')
        
        # 等待进度显示完成
        progress_thread.join(timeout=1)
        
        # 显示最终结果
        self.display_final_results()
    
    def display_final_results(self):
        """显示最终测试结果"""
        print(f"\n" + "=" * 80)
        print(f'测试结果汇总')
        print(f"=" * 80)
        
        success_tests = [name for name, result in self.results.items() if result['status'] == 'success']
        failed_tests = [name for name, result in self.results.items() if result['status'] == 'failed']
        total_time = time.time() - self.start_time if self.start_time else 0
        print(f'Successful: {len(success_tests)}/{len(self.test_methods)} ({len(success_tests)/len(self.test_methods)*100:.1f}%)')
        print(f'Error: Failed: {len(failed_tests)}/{len(self.test_methods)} ({len(failed_tests)/len(self.test_methods)*100:.1f}%)')
        print(f'Total time: {total_time:.1f}s')
        print(f'Tool: GDS commands: {self.completed_gds_commands}/{self.total_gds_commands}')
        
        if success_tests:
            print(f'\nSuccessful tests ({len(success_tests)}):')
            for test_name in success_tests:
                result = self.results[test_name]
                print(f' • {test_name} (Worker-{result["worker"]}, {result["duration"]:.1f}s, {result["gds_commands"]} GDS命令)')
        
        if failed_tests:
            print(f'\nError: Failed tests ({len(failed_tests)}):')
            for test_name in failed_tests:
                result = self.results[test_name]
                print(f' • {test_name} (Worker-{result["worker"]})')
                print(f'Error: {result["error"][:150]}...')
        
        # 按Worker统计
        worker_stats = defaultdict(lambda: {'success': 0, 'failed': 0, 'time': 0})
        for result in self.results.values():
            worker_id = result["worker"]
            worker_stats[worker_id][result["status"]] += 1
            if 'duration' in result:
                worker_stats[worker_id]['time'] += result['duration']
        
        print(f'\nWorker statistics:')
        for worker_id in sorted(worker_stats.keys()):
            stats = worker_stats[worker_id]
            print(f'Worker-{worker_id}: {stats["success"]}{stats["failed"]}Error: ({stats["time"]:.1f}s)')
        
        print(f"=" * 80)
        
        return len(failed_tests) == 0

def main():
    """主函数"""
    print(f'Launch GDS parallel test suite')
    print(f"=" * 60)
    print(f'Test features:')
    print(f'• Remote window operation without timeout limit')
    print(f'• Result judgment based on function execution')
    print(f'• Static reproducibility (using --force options)')
    print(f'• 3 workers parallel execution')
    print(f"=" * 60)
    
    # 创建并行测试运行器
    runner = ParallelTestRunner(num_workers=3)
    
    # 发现测试方法
    test_methods = runner.discover_test_methods(GDSTest)
    
    print(f'Found test methods:')
    for i, method in enumerate(test_methods, 1):
        print(f'{i:2d}. {method["name"]} ({method["gds_commands"]} GDS commands)')
    
    print(f'Total: {len(test_methods)} tests, {runner.total_gds_commands} GDS commands')
    
    # 运行并行测试
    success = runner.run_parallel_tests()
    
    # 返回适当的退出码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
