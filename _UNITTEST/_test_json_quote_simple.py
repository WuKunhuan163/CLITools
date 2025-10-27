#!/usr/bin/env python3
"""
简单的JSON引号问题测试脚本
不依赖GDS测试框架，直接调用GDS命令
"""

import subprocess
import os

def test_json_quote_issue():
    """测试JSON引号问题"""
    print("=== 简单的JSON引号问题测试 ===")
    
    # 测试1: 直接echo JSON到stdout
    print("\n测试1: 直接echo JSON到stdout")
    json_content = "{'name': 'test', 'value': 123}"
    cmd = f'python3 GOOGLE_DRIVE.py --shell --no-direct-feedback "echo \\"{json_content}\\""'
    
    print(f"执行命令: {cmd}")
    print(f"期望输出: {json_content}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, 
                              cwd='/Users/wukunhuan/.local/bin', timeout=60)
        print(f"返回码: {result.returncode}")
        
        if result.returncode == 0:
            actual_output = result.stdout.strip()
            print(f"实际输出: {actual_output}")
            
            # 检查引号是否丢失
            if json_content in actual_output:
                print("✅ JSON引号保留正常")
            elif "name" in actual_output and "test" in actual_output:
                if "'" in actual_output:
                    print("✅ 引号存在，但格式可能不同")
                else:
                    print("❌ 引号丢失！")
                    print(f"丢失引号的输出: {actual_output}")
            else:
                print("❌ 输出内容不匹配")
        else:
            print("❌ 命令执行失败")
            print(f"错误输出: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("❌ 命令执行超时")
    except Exception as e:
        print(f"❌ 异常: {e}")
    
    # 测试2: 使用单引号包围JSON
    print("\n测试2: 使用单引号包围JSON")
    cmd2 = f"python3 GOOGLE_DRIVE.py --shell --no-direct-feedback \"echo '{json_content}'\""
    
    print(f"执行命令: {cmd2}")
    
    try:
        result2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True, 
                               cwd='/Users/wukunhuan/.local/bin', timeout=60)
        print(f"返回码: {result2.returncode}")
        
        if result2.returncode == 0:
            actual_output2 = result2.stdout.strip()
            print(f"实际输出: {actual_output2}")
            
            if json_content in actual_output2:
                print("✅ JSON引号保留正常")
            else:
                print("❌ 输出不匹配")
        else:
            print("❌ 命令执行失败")
            
    except Exception as e:
        print(f"❌ 异常: {e}")

if __name__ == '__main__':
    test_json_quote_issue()
