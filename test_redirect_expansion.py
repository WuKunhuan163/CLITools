#!/usr/bin/env python3
"""
测试重定向路径展开的问题
"""

import subprocess
import os
import re

def test_redirect_expansion(cmd):
    """模拟expand_paths_with_bash中的重定向处理逻辑"""
    print(f"\n=== 测试命令: {cmd} ===")
    
    # 步骤1: 获取主命令展开
    try:
        result = subprocess.run(
            ['bash', '-x', '-c', cmd],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=os.path.expanduser('~/tmp')
        )
        
        print(f"主命令bash -x结果:")
        print(f"  stdout: '{result.stdout}'")
        print(f"  stderr: '{result.stderr}'")
        
        # 提取主命令
        expanded_main = None
        if result.stderr:
            lines = result.stderr.strip().split('\n')
            for line in lines:
                if line.startswith('+ '):
                    expanded_main = line[2:]
                    break
        
        print(f"  展开的主命令: {expanded_main}")
        
        # 步骤2: 检测重定向
        redirect_operators = ['>', '>>', '<', '2>', '2>>', '&>', '&>>', '2>&1', '|']
        redirect_part = ""
        
        for op in redirect_operators:
            if op in cmd:
                op_index = cmd.find(op)
                redirect_part = cmd[op_index:]
                print(f"  发现重定向: {redirect_part}")
                
                # 提取重定向路径
                redirect_path_match = re.search(r'[><|&]\s*(.+?)(?:\s+[><|&]|$)', redirect_part)
                if redirect_path_match:
                    redirect_path = redirect_path_match.group(1).strip()
                    print(f"  重定向路径: '{redirect_path}'")
                    
                    # 对重定向路径进行展开 - 这里是问题所在！
                    echo_cmd = f'echo {redirect_path}'
                    print(f"  用于展开的echo命令: {echo_cmd}")
                    
                    redirect_expand_result = subprocess.run(
                        ['bash', '-x', '-c', echo_cmd],
                        capture_output=True,
                        text=True,
                        timeout=2,
                        cwd=os.path.expanduser('~/tmp')
                    )
                    
                    print(f"  重定向展开结果:")
                    print(f"    stdout: '{redirect_expand_result.stdout}'")
                    print(f"    stderr: '{redirect_expand_result.stderr}'")
                    
                    if redirect_expand_result.stderr:
                        redirect_lines = redirect_expand_result.stderr.strip().split('\n')
                        for line in redirect_lines:
                            if line.startswith('+ echo '):
                                expanded_redirect_path = line[7:].strip()
                                print(f"    展开的重定向路径: '{expanded_redirect_path}'")
                                
                                # 替换
                                new_redirect_part = redirect_part.replace(redirect_path, expanded_redirect_path)
                                print(f"    替换后的重定向: {new_redirect_part}")
                                
                                # 最终结果
                                final_cmd = expanded_main + ' ' + new_redirect_part if expanded_main else cmd
                                print(f"  最终命令: {final_cmd}")
                                return final_cmd
                break
        
        return expanded_main or cmd
        
    except Exception as e:
        print(f"错误: {e}")
        return cmd

def main():
    """测试各种重定向情况"""
    
    os.makedirs(os.path.expanduser('~/tmp'), exist_ok=True)
    
    test_cases = [
        'echo "Hello" > ~/test.txt',
        'echo -e "Line1\\nLine2\\nLine3" > ~/test.txt',
        'echo "Test with spaces" > ~/test file.txt',
        'echo -e "Line1\\nLine2" > "~/test with quotes.txt"',
    ]
    
    for cmd in test_cases:
        test_redirect_expansion(cmd)

if __name__ == "__main__":
    main()
