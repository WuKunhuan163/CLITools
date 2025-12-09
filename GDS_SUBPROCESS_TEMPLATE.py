#!/usr/bin/env python3
"""
GDS Subprocess Execution Template
用于在本地Python中通过subprocess执行GDS窗口命令
"""

import subprocess
import sys
import json

def execute_gds_command(gds_command: str, timeout: int = 300) -> dict:
    """
    执行GDS命令并返回结果
    
    Args:
        gds_command: GDS命令字符串，例如 "ls", "pip install requests"
        timeout: 超时时间（秒），默认300秒
        
    Returns:
        dict: {
            "success": bool,
            "exit_code": int,
            "stdout": str,
            "stderr": str,
            "error": str (if failed)
        }
    """
    try:
        # 构建完整命令
        # 注意：GDS路径应该是绝对路径
        google_drive_path = "/Users/wukunhuan/.local/bin/GOOGLE_DRIVE.py"
        
        # 方法1：使用--shell直接执行
        full_command = [
            sys.executable,  # 使用当前Python解释器
            google_drive_path,
            "--shell",
            gds_command
        ]
        
        print(f"Executing: {' '.join(full_command)}")
        
        # 执行命令
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
        
    except subprocess.TimeoutExpired as e:
        return {
            "success": False,
            "exit_code": -1,
            "stdout": e.stdout.decode() if e.stdout else "",
            "stderr": e.stderr.decode() if e.stderr else "",
            "error": f"Command timeout after {timeout} seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": "",
            "error": str(e)
        }


def execute_gds_raw_command(raw_command: str, timeout: int = 300) -> dict:
    """
    执行GDS --raw-command（用于执行bash脚本）
    
    Args:
        raw_command: 原始bash命令字符串
        timeout: 超时时间（秒）
        
    Returns:
        dict: 同上
    """
    try:
        google_drive_path = "/Users/wukunhuan/.local/bin/GOOGLE_DRIVE.py"
        
        # 使用--raw-command需要特别注意引号转义
        full_command = [
            sys.executable,
            google_drive_path,
            "--shell",
            "--raw-command",
            raw_command  # subprocess会自动处理引号
        ]
        
        print(f"Executing raw command: {raw_command[:100]}...")
        
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
        
    except subprocess.TimeoutExpired as e:
        return {
            "success": False,
            "exit_code": -1,
            "stdout": e.stdout.decode() if e.stdout else "",
            "stderr": e.stderr.decode() if e.stderr else "",
            "error": f"Command timeout after {timeout} seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": "",
            "error": str(e)
        }


# ============= 使用示例 =============

if __name__ == "__main__":
    print("=" * 70)
    print("GDS Subprocess Template - Usage Examples")
    print("=" * 70)
    print()
    
    # 示例1：简单的GDS命令
    print("Example 1: Simple GDS command (ls)")
    result = execute_gds_command("ls")
    print(f"Success: {result['success']}")
    print(f"Exit code: {result['exit_code']}")
    print(f"Output: {result['stdout'][:200]}")
    print()
    
    # 示例2：GDS pip命令
    print("Example 2: GDS pip list")
    result = execute_gds_command("pip list")
    print(f"Success: {result['success']}")
    print(f"Output: {result['stdout'][:200]}")
    print()
    
    # 示例3：Raw command（bash脚本）
    print("Example 3: Raw command (bash)")
    bash_script = """
echo 'Testing bash execution'
python3 --version
pip --version 2>&1 || echo 'pip not available'
"""
    result = execute_gds_raw_command(bash_script.strip())
    print(f"Success: {result['success']}")
    print(f"Output: {result['stdout'][:200]}")
    print()
    
    # 示例4：带引号的复杂命令
    print("Example 4: Complex command with quotes")
    complex_cmd = 'echo "Test: special chars @#$%"'
    result = execute_gds_raw_command(complex_cmd)
    print(f"Success: {result['success']}")
    print(f"Output: {result['stdout']}")
    print()
    
    # 示例5：多行Python脚本（通过raw command）
    print("Example 5: Multi-line Python script")
    python_script = '''python3 << 'EOF'
import sys
print(f"Python version: {sys.version}")
print("Script executed successfully")
EOF'''
    result = execute_gds_raw_command(python_script)
    print(f"Success: {result['success']}")
    print(f"Output: {result['stdout']}")
    print()
    
    print("=" * 70)
    print("Template ready for use!")
    print("=" * 70)

