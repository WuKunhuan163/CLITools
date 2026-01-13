#!/usr/bin/env python3
"""
ALIAS.py - Permanent Shell Alias Creation Tool
Creates permanent aliases in shell configuration files
"""

import os
import sys
import re
from pathlib import Path
from typing import List

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

def update_shell_configs():
    """更新shell配置文件（source所有配置文件）"""
    config_files = get_config_files()
    
    success_count = 0
    for config_file in config_files:
        try:
            import subprocess
            result = subprocess.run(
                ["bash", "-c", f"source {str(config_file)}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                success_count += 1
                print(f"Updated: {config_file}")
            else:
                print(f"Error: Failed to update {config_file}: {result.stderr}")
        except Exception as e:
            print(f"Error: Error updating {config_file}: {e}")
    
    if success_count > 0:
        print(f"Successfully updated {success_count} configuration files!")
        print(f"Changes should now be active in your current shell.")
    else:
        print(f"Error:  Failed to update any configuration files.")
    
    return success_count > 0


def get_config_files() -> List[Path]:
    """获取shell配置文件路径"""
    home = Path.home()
    return [
        home / ".bash_profile",
        home / ".bashrc", 
        home / ".zshrc"
    ]


def validate_alias_name(alias_name: str) -> tuple[bool, str]:
    """验证别名名称是否有效"""
    if not alias_name:
        return False, "Alias name cannot be empty"
    
    if alias_name == "ALIAS":
        return False, "Alias name cannot be 'ALIAS'"
    
    if re.search(r'\s', alias_name):
        return False, "Alias name cannot contain spaces"
    
    # 检查是否包含特殊字符
    if re.search(r'[;&|<>(){}[\]$`"\'\\]', alias_name):
        return False, "Alias name contains invalid characters"
    
    return True, ""

def check_existing_alias(alias_name: str, config_file: Path) -> bool:
    """检查别名是否已存在于配置文件中"""
    if not config_file.exists():
        return False
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找现有的别名定义
        pattern = rf'^alias\s+{re.escape(alias_name)}\s*='
        return bool(re.search(pattern, content, re.MULTILINE))
    except Exception:
        return False

def remove_existing_alias(alias_name: str, config_file: Path) -> bool:
    """从配置文件中移除现有的别名"""
    if not config_file.exists():
        return True
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 过滤掉现有的别名行
        pattern = rf'^alias\s+{re.escape(alias_name)}\s*='
        new_lines = [line for line in lines if not re.match(pattern, line)]
        
        with open(config_file, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        return True
    except Exception as e:
        print(f"Error removing existing alias from {config_file}: {e}")
        return False

def add_alias_to_file(alias_name: str, alias_command: str, config_file: Path) -> bool:
    """向配置文件添加别名"""
    try:
        # 如果文件不存在，创建它
        if not config_file.exists():
            config_file.touch()
        
        # 移除现有的别名（如果存在）
        if check_existing_alias(alias_name, config_file):
            remove_existing_alias(alias_name, config_file)
        
        # 添加新的别名
        # 根据命令内容选择合适的引号
        if "'" in alias_command:
            alias_line = f'alias {alias_name}="{alias_command}"\n'
        else:
            alias_line = f"alias {alias_name}='{alias_command}'\n"
        
        with open(config_file, 'a', encoding='utf-8') as f:
            f.write(alias_line)
        
        return True
    except Exception as e:
        print(f"Error adding alias to {config_file}: {e}")
        return False

def create_alias(alias_name: str, alias_command: str) -> int:
    """创建别名"""
    
    # 验证别名名称
    valid, error_msg = validate_alias_name(alias_name)
    if not valid:
        print(f"Error: {error_msg}")
        return 1
    
    # 获取配置文件
    config_files = get_config_files()
    
    # 处理结果
    results = []
    success_count = 0
    
    for config_file in config_files:
        file_existed = config_file.exists()
        had_existing_alias = check_existing_alias(alias_name, config_file)
        
        if add_alias_to_file(alias_name, alias_command, config_file):
            success_count += 1
            results.append({
                "file": str(config_file),
                "success": True,
                "created_file": not file_existed,
                "updated_existing": had_existing_alias
            })
        else:
            results.append({
                "file": str(config_file),
                "success": False,
                "error": "Failed to add alias"
            })
    
    print(f"Creating alias: {alias_name} -> {alias_command}")
    print()
    
    for result in results:
        if result["success"]:
            status = "✅"
            if result.get("created_file"):
                status += f" Created file and added alias: {result['file']}"
            elif result.get("updated_existing"):
                status += f" Updated existing alias in: {result['file']}"
            else:
                status += f" Added alias to: {result['file']}"
            print(status)
        else:
            print(f"Error: Failed to update: {result['file']}")
    
    print()
    if success_count > 0:
        print(f"Alias created successfully!")
        print(f"Alias will be available in new terminal sessions")
        print(f"Note: Current session may need manual source or restart for aliases")
    else:
        print(f"Error:  Failed to create alias in any configuration file")
    
    return 0 if success_count > 0 else 1

def remove_alias_from_all_files(alias_name: str) -> int:
    """从所有配置文件中移除别名"""
    config_files = get_config_files()
    removed_count = 0
    results = []

    for config_file in config_files:
        if remove_existing_alias(alias_name, config_file):
            removed_count += 1
            results.append({
                "file": str(config_file),
                "success": True,
                "alias_name": alias_name
            })
        else:
            results.append({
                "file": str(config_file),
                "success": False,
                "error": "Failed to remove alias"
            })

    print(f"Removing alias: {alias_name}")
    print()
    for result in results:
        if result["success"]:
            print(f"Removed alias '{alias_name}' from {result['file']}")
        else:
            print(f"Error: Failed to remove alias '{alias_name}' from {result['file']}: {result['error']}")
    print()
    if removed_count > 0:
        print(f"Alias removed successfully!")
    else:
        print(f"Error:  Alias not found in any configuration file.")
    
    return 0 if removed_count > 0 else 1

def show_help():
    """显示帮助信息"""
    help_text = """ALIAS - Permanent Shell Alias Creation Tool

Usage: ALIAS <alias_name> <alias_command>

Arguments:
  alias_name      The short name for the alias (cannot be 'ALIAS')
  alias_command   The command that the alias will execute

Options:
  --help, -h      Show this help message
  --remove, --undo, -r  Remove an existing alias
  --update        Update shell configuration files (source all config files)

Examples:
  ALIAS ll "ls -la"                    # Create alias for detailed listing
  ALIAS gs "git status"                # Create alias for git status
  ALIAS python python3                 # Create alias for python3
  ALIAS mydir "cd ~/my-project"        # Create alias for changing directory
  ALIAS serve "python -m http.server"  # Create alias for local server
  ALIAS --remove ll                     # Remove the 'll' alias
  ALIAS --undo gs                       # Remove the 'gs' alias
  ALIAS --update                        # Update shell configuration files

Notes:
  - Alias names cannot contain spaces or special characters
  - Alias commands with spaces should be quoted
  - Aliases are added to ~/.bash_profile, ~/.bashrc, and ~/.zshrc
  - Existing aliases with the same name will be updated
  - Use 'source ~/.bashrc' (or similar) to activate aliases immediately

This tool will:
1. Validate the alias name
2. Add the alias to shell configuration files
3. Handle existing aliases by updating them
4. Provide instructions for immediate activation"""
    
    print(help_text)

def main():
    """主函数"""
    args = sys.argv[1:]
    
    if len(args) == 0:
        print(f"Error: No arguments provided")
        print(f"Usage: ALIAS <alias_name> <alias_command>")
        print(f"Use --help for more information")
        return 1
    
    if args[0] in ['--help', '-h']:
        show_help()
        return 0
    
    # 处理移除别名
    if args[0] in ['--remove', '--undo', '-r']:
        if len(args) != 2:
            print(f"Error: --remove/--undo requires exactly one argument: alias_name")
            print(f"Usage: ALIAS --remove <alias_name>")
            print(f"       ALIAS --undo <alias_name>")
            return 1
        
        alias_name = args[1]
        return remove_alias_from_all_files(alias_name)
    
    # 处理更新配置文件
    if args[0] == '--update':
        if len(args) != 1:
            print(f"Error: --update does not take any arguments")
            print(f"Usage: ALIAS --update")
            return 1
        
        print(f"Updating shell configuration files...")
        success = update_shell_configs()
        return 0 if success else 1
    
    if len(args) != 2:
        print(f"Error: Exactly two arguments required: alias_name and alias_command")
        print(f"Usage: ALIAS <alias_name> <alias_command>")
        print(f"Use --help for more information")
        return 1
    
    alias_name = args[0]
    alias_command = args[1]
    
    return create_alias(alias_name, alias_command)

if __name__ == "__main__":
    sys.exit(main())
