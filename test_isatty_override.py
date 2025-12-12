#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：研究覆盖isatty(0)=False的可能性
尝试多种方法使标准输入在非TTY环境中表现为TTY
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

def test_original_isatty():
    """测试原始的isatty状态"""
    print("=== 原始isatty状态 ===")
    print(f"os.isatty(0): {os.isatty(0)}")
    print(f"sys.stdin.isatty(): {sys.stdin.isatty()}")
    print(f"sys.stdin: {sys.stdin}")
    print(f"sys.stdin.fileno(): {sys.stdin.fileno()}")
    return os.isatty(0)

def test_monkey_patch_os_isatty():
    """测试猴子补丁覆盖os.isatty"""
    print("\n=== 测试猴子补丁覆盖os.isatty ===")
    
    # 保存原始函数
    original_isatty = os.isatty
    
    # 创建覆盖函数
    def fake_isatty(fd):
        print(f"[FAKE] isatty({fd}) called, returning True")
        return True
    
    # 应用猴子补丁
    os.isatty = fake_isatty
    
    print(f"覆盖后 os.isatty(0): {os.isatty(0)}")
    print(f"但是 sys.stdin.isatty(): {sys.stdin.isatty()}")
    
    # 测试input()是否工作
    try:
        print("尝试使用input()...")
        # 设置短超时来避免无限等待
        import signal
        def timeout_handler(signum, frame):
            raise TimeoutError("Input timeout")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(2)  # 2秒超时
        
        try:
            result = input("请输入内容: ")
            signal.alarm(0)
            print(f"成功获取输入: {result}")
            success = True
        except EOFError:
            print("仍然收到EOFError")
            success = False
        except TimeoutError:
            print("输入超时（预期行为）")
            success = False
        finally:
            signal.alarm(0)
    except Exception as e:
        print(f"input()测试失败: {e}")
        success = False
    
    # 恢复原始函数
    os.isatty = original_isatty
    
    return success

def test_monkey_patch_sys_stdin():
    """测试覆盖sys.stdin.isatty方法"""
    print("\n=== 测试覆盖sys.stdin.isatty方法 ===")
    
    # 保存原始方法
    original_method = sys.stdin.isatty
    
    # 创建覆盖方法
    def fake_stdin_isatty():
        print("[FAKE] sys.stdin.isatty() called, returning True")
        return True
    
    # 应用覆盖
    sys.stdin.isatty = fake_stdin_isatty
    
    print(f"覆盖后 sys.stdin.isatty(): {sys.stdin.isatty()}")
    print(f"但是 os.isatty(0): {os.isatty(0)}")
    
    # 测试input()
    try:
        import signal
        def timeout_handler(signum, frame):
            raise TimeoutError("Input timeout")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(2)
        
        try:
            result = input("请输入内容: ")
            signal.alarm(0)
            print(f"成功获取输入: {result}")
            success = True
        except EOFError:
            print("仍然收到EOFError")
            success = False
        except TimeoutError:
            print("输入超时（预期行为）")
            success = False
        finally:
            signal.alarm(0)
    except Exception as e:
        print(f"input()测试失败: {e}")
        success = False
    
    # 恢复原始方法
    sys.stdin.isatty = original_method
    
    return success

def test_create_fake_tty():
    """测试创建伪TTY"""
    print("\n=== 测试创建伪TTY ===")
    
    try:
        import pty
        import select
        
        # 创建伪终端
        master, slave = pty.openpty()
        
        print(f"创建伪TTY: master={master}, slave={slave}")
        print(f"os.isatty(master): {os.isatty(master)}")
        print(f"os.isatty(slave): {os.isatty(slave)}")
        
        # 尝试替换stdin
        original_stdin = sys.stdin
        sys.stdin = os.fdopen(slave, 'r')
        
        print(f"替换后 sys.stdin.isatty(): {sys.stdin.isatty()}")
        
        # 测试是否能工作
        # 向master写入数据
        os.write(master, b"test input\n")
        
        # 从slave读取
        if select.select([slave], [], [], 1)[0]:
            data = os.read(slave, 1024)
            print(f"从伪TTY读取到: {data}")
            success = True
        else:
            print("伪TTY读取超时")
            success = False
        
        # 恢复stdin
        sys.stdin = original_stdin
        
        # 关闭伪终端
        os.close(master)
        os.close(slave)
        
        return success
        
    except ImportError:
        print("pty模块不可用")
        return False
    except Exception as e:
        print(f"伪TTY测试失败: {e}")
        return False

def test_subprocess_with_pty():
    """测试使用pty的子进程"""
    print("\n=== 测试使用pty的子进程 ===")
    
    try:
        import pty
        
        # 创建一个简单的输入测试脚本
        test_script = '''
import sys
import os
print(f"子进程中 os.isatty(0): {os.isatty(0)}")
print(f"子进程中 sys.stdin.isatty(): {sys.stdin.isatty()}")
try:
    result = input("子进程请输入: ")
    print(f"子进程收到输入: {result}")
except Exception as e:
    print(f"子进程输入失败: {e}")
'''
        
        # 使用pty.spawn运行脚本
        def read_and_write(fd):
            # 向子进程发送输入
            os.write(fd, b"test from parent\\n")
            
            # 读取输出
            try:
                data = os.read(fd, 1024)
                print(f"从子进程读取: {data.decode()}")
                return True
            except:
                return False
        
        print("启动带pty的子进程...")
        result = pty.spawn([sys.executable, '-c', test_script], read_and_write)
        
        return result == 0
        
    except ImportError:
        print("pty模块不可用")
        return False
    except Exception as e:
        print(f"pty子进程测试失败: {e}")
        return False

def test_redirect_from_file():
    """测试从文件重定向输入"""
    print("\n=== 测试从文件重定向输入 ===")
    
    try:
        # 创建临时输入文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("line1\nline2\nline3\n")
            temp_file = f.name
        
        # 创建测试脚本
        test_script = f'''
import sys
import os
print(f"重定向后 os.isatty(0): {{os.isatty(0)}}")
print(f"重定向后 sys.stdin.isatty(): {{sys.stdin.isatty()}}")
try:
    while True:
        line = input("请输入: ")
        print(f"收到: {{line}}")
except EOFError:
    print("输入结束")
except Exception as e:
    print(f"输入失败: {{e}}")
'''
        
        # 运行脚本，重定向输入
        result = subprocess.run(
            [sys.executable, '-c', test_script],
            stdin=open(temp_file, 'r'),
            capture_output=True,
            text=True,
            timeout=5
        )
        
        print(f"退出代码: {result.returncode}")
        print(f"输出: {result.stdout}")
        if result.stderr:
            print(f"错误: {result.stderr}")
        
        # 清理
        os.unlink(temp_file)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"文件重定向测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("测试覆盖isatty(0)=False的各种方法")
    print("=" * 50)
    
    results = {}
    
    # 测试原始状态
    original_is_tty = test_original_isatty()
    results['original_tty'] = original_is_tty
    
    # 如果已经是TTY，跳过测试
    if original_is_tty:
        print("\n当前已经是TTY环境，无需测试覆盖方法")
        return results
    
    # 测试各种覆盖方法
    results['monkey_patch_os'] = test_monkey_patch_os_isatty()
    results['monkey_patch_stdin'] = test_monkey_patch_sys_stdin()
    results['fake_tty'] = test_create_fake_tty()
    results['subprocess_pty'] = test_subprocess_with_pty()
    results['file_redirect'] = test_redirect_from_file()
    
    # 总结结果
    print("\n" + "=" * 50)
    print("测试结果总结:")
    for method, success in results.items():
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  {method}: {status}")
    
    # 结论
    print("\n结论:")
    if any(results.values()):
        successful_methods = [k for k, v in results.items() if v]
        print(f"可行的方法: {', '.join(successful_methods)}")
    else:
        print("所有方法都失败了，无法在非TTY环境中模拟TTY行为")
    
    return results

if __name__ == "__main__":
    main()