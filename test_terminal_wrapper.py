#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：创建终端包装器，作为输入指令的中介
将指令发送到系统终端窗口并获取反馈
"""

import os
import sys
import subprocess
import tempfile
import time
import threading
import signal
from pathlib import Path

class TerminalWrapper:
    def __init__(self):
        self.temp_dir = Path.home() / "tmp" / "terminal_wrapper"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.command_file = None
        self.output_file = None
        self.is_running = False
        
    def create_command_files(self, session_id=None):
        """创建命令和输出文件"""
        if not session_id:
            session_id = f"session_{int(time.time())}"
        
        self.command_file = self.temp_dir / f"{session_id}_command.txt"
        self.output_file = self.temp_dir / f"{session_id}_output.txt"
        
        # 创建空文件
        self.command_file.touch()
        self.output_file.touch()
        
        return self.command_file, self.output_file
    
    def create_terminal_script(self, command_file, output_file):
        """创建在终端中运行的监控脚本"""
        script_content = f'''#!/bin/bash
# 终端包装器监控脚本
# 监控命令文件: {command_file}
# 输出文件: {output_file}

echo "=== 终端包装器已启动 ==="
echo "监控命令文件: {command_file}"
echo "输出文件: {output_file}"
echo "请保持此终端窗口开启..."
echo ""

# 监控循环
while true; do
    if [ -f "{command_file}" ] && [ -s "{command_file}" ]; then
        echo "检测到新命令..."
        
        # 读取命令
        command=$(cat "{command_file}")
        echo "执行命令: $command"
        echo "----------------------------------------"
        
        # 清空命令文件
        > "{command_file}"
        
        # 执行命令并将输出写入输出文件
        {{
            echo "=== 命令执行开始 ==="
            echo "命令: $command"
            echo "时间: $(date)"
            echo "----------------------------------------"
            
            # 执行命令
            eval "$command" 2>&1
            exit_code=$?
            
            echo "----------------------------------------"
            echo "退出代码: $exit_code"
            echo "执行完成时间: $(date)"
            echo "=== 命令执行结束 ==="
            echo ""
        }} >> "{output_file}"
        
        echo "命令执行完成，输出已写入文件"
        echo ""
    fi
    
    sleep 1
done
'''
        
        script_file = self.temp_dir / "terminal_monitor.sh"
        with open(script_file, 'w') as f:
            f.write(script_content)
        
        os.chmod(script_file, 0o755)
        return script_file
    
    def start_terminal_wrapper(self):
        """启动终端包装器"""
        print("=== 启动终端包装器 ===")
        
        # 创建文件
        command_file, output_file = self.create_command_files()
        print(f"命令文件: {command_file}")
        print(f"输出文件: {output_file}")
        
        # 创建监控脚本
        script_file = self.create_terminal_script(command_file, output_file)
        print(f"监控脚本: {script_file}")
        
        # 在新终端窗口中启动脚本
        try:
            if sys.platform == 'darwin':  # macOS
                # 使用AppleScript在新Terminal窗口中运行脚本
                applescript = f'''
                tell application "Terminal"
                    activate
                    set newTab to do script "{script_file}"
                end tell
                '''
                result = subprocess.run(['osascript', '-e', applescript], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    print("✅ 成功在Terminal中启动监控脚本")
                    self.is_running = True
                    return True
                else:
                    print(f"❌ 启动Terminal失败: {result.stderr}")
                    return False
            
            elif sys.platform == 'linux':  # Linux
                # 尝试多个终端模拟器
                terminals = ['gnome-terminal', 'xterm', 'konsole', 'xfce4-terminal']
                for terminal in terminals:
                    try:
                        subprocess.run([terminal, '-e', str(script_file)], 
                                     check=True, capture_output=True)
                        print(f"✅ 成功在{terminal}中启动监控脚本")
                        self.is_running = True
                        return True
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue
                
                print("❌ 未找到可用的终端模拟器")
                return False
            
            else:  # Windows
                subprocess.run(['cmd', '/c', 'start', 'cmd', '/k', str(script_file)], 
                             check=True)
                print("✅ 成功在CMD中启动监控脚本")
                self.is_running = True
                return True
                
        except Exception as e:
            print(f"❌ 启动终端包装器失败: {e}")
            return False
    
    def send_command(self, command, timeout=30):
        """发送命令到终端并等待结果"""
        if not self.is_running or not self.command_file:
            print("❌ 终端包装器未运行")
            return None
        
        print(f"发送命令: {command}")
        
        # 清空输出文件
        with open(self.output_file, 'w') as f:
            f.write("")
        
        # 写入命令
        with open(self.command_file, 'w') as f:
            f.write(command)
        
        # 等待输出
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.output_file.exists() and self.output_file.stat().st_size > 0:
                # 等待一下确保输出完整
                time.sleep(1)
                
                # 读取输出
                try:
                    with open(self.output_file, 'r') as f:
                        output = f.read()
                    
                    if output.strip():
                        print(f"✅ 收到输出 ({len(output)} 字符)")
                        return output
                except Exception as e:
                    print(f"读取输出失败: {e}")
            
            time.sleep(0.5)
        
        print(f"❌ 命令执行超时 ({timeout}秒)")
        return None
    
    def test_interactive_input(self, timeout=60):
        """测试交互式输入"""
        print("\n=== 测试交互式输入 ===")
        
        # 创建一个需要用户输入的Python脚本
        input_script = self.temp_dir / "test_input.py"
        with open(input_script, 'w') as f:
            f.write('''#!/usr/bin/env python3
import sys
print("请输入您的反馈:")
try:
    user_input = input("> ")
    print(f"您输入了: {user_input}")
    print("输入测试完成")
except Exception as e:
    print(f"输入失败: {e}")
''')
        
        os.chmod(input_script, 0o755)
        
        # 发送命令
        command = f"python3 {input_script}"
        result = self.send_command(command, timeout)
        
        return result
    
    def cleanup(self):
        """清理临时文件"""
        try:
            if self.temp_dir.exists():
                for file in self.temp_dir.iterdir():
                    file.unlink()
                self.temp_dir.rmdir()
            print("✅ 清理完成")
        except Exception as e:
            print(f"清理失败: {e}")

def test_terminal_wrapper():
    """测试终端包装器"""
    print("测试终端包装器功能")
    print("=" * 50)
    
    wrapper = TerminalWrapper()
    
    try:
        # 启动包装器
        if not wrapper.start_terminal_wrapper():
            print("❌ 无法启动终端包装器")
            return False
        
        print("\n等待5秒让终端启动...")
        time.sleep(5)
        
        # 测试简单命令
        print("\n=== 测试简单命令 ===")
        result1 = wrapper.send_command("echo 'Hello from terminal wrapper!'", timeout=10)
        if result1:
            print("简单命令测试成功")
        else:
            print("简单命令测试失败")
        
        # 测试复杂命令
        print("\n=== 测试复杂命令 ===")
        result2 = wrapper.send_command("ls -la | head -5", timeout=10)
        if result2:
            print("复杂命令测试成功")
        else:
            print("复杂命令测试失败")
        
        # 询问是否测试交互式输入
        print(f"\n{'='*50}")
        choice = input("是否测试交互式输入? (需要手动在Terminal中输入) (y/N): ").strip().lower()
        
        if choice == 'y':
            print("请切换到Terminal窗口并按照提示输入...")
            result3 = wrapper.test_interactive_input(timeout=60)
            if result3:
                print("交互式输入测试成功")
                print(f"结果:\n{result3}")
            else:
                print("交互式输入测试失败")
        else:
            print("跳过交互式输入测试")
            result3 = "跳过"
        
        # 总结结果
        print(f"\n{'='*50}")
        print("测试结果总结:")
        print(f"  简单命令: {'✅ 成功' if result1 else '❌ 失败'}")
        print(f"  复杂命令: {'✅ 成功' if result2 else '❌ 失败'}")
        print(f"  交互输入: {'✅ 成功' if result3 and result3 != '跳过' else '⏭️ 跳过' if result3 == '跳过' else '❌ 失败'}")
        
        return True
        
    except KeyboardInterrupt:
        print("\n用户中断测试")
        return False
    except Exception as e:
        print(f"测试过程中出错: {e}")
        return False
    finally:
        # 清理
        print("\n清理资源...")
        wrapper.cleanup()

def main():
    """主函数"""
    print("终端包装器测试脚本")
    print("=" * 50)
    
    try:
        success = test_terminal_wrapper()
        return success
    except KeyboardInterrupt:
        print("\n\n用户中断")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)