#!/usr/bin/env python3
"""
测试转义序列在bash -x中的处理问题
"""

import subprocess
import os

def test_bash_with_escapes(cmd):
    """测试bash -x对转义序列的处理"""
    print(f"\n=== 测试: {cmd} ===")
    
    try:
        result = subprocess.run(
            ['bash', '-x', '-c', cmd],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=os.path.expanduser('~/tmp')
        )
        
        print(f"返回码: {result.returncode}")
        print(f"stdout: '{result.stdout}'")
        print(f"stderr: '{result.stderr}'")
        
        # 提取展开结果
        if result.stderr:
            lines = result.stderr.strip().split('\n')
            for line in lines:
                if line.startswith('+ '):
                    expanded = line[2:]
                    print(f"展开结果: '{expanded}'")
                    
                    # 检查转义序列
                    if '\\n' in cmd and '\\n' not in expanded:
                        print("⚠️  转义序列被破坏了！")
                    elif '\\n' in cmd and '\\n' in expanded:
                        print("✅ 转义序列保持完整")
                    
                    return expanded
        
        return None
        
    except Exception as e:
        print(f"错误: {e}")
        return None

def main():
    """测试不同的转义序列情况"""
    
    os.makedirs(os.path.expanduser('~/tmp'), exist_ok=True)
    
    # 测试不同的引号和转义组合
    test_cases = [
        # 原始的有问题的命令
        'echo -e Line1\\nLine2\\nLine3 > ~/debug_test.txt',
        
        # 尝试不同的引号保护
        'echo -e "Line1\\nLine2\\nLine3" > ~/debug_test.txt',
        'echo -e \'Line1\\nLine2\\nLine3\' > ~/debug_test.txt',
        
        # 双重转义
        'echo -e "Line1\\\\nLine2\\\\nLine3" > ~/debug_test.txt',
        
        # 测试单独的转义序列
        'echo -e Line1\\nLine2',
        'echo -e "Line1\\nLine2"',
        'echo -e \'Line1\\nLine2\'',
        
        # 测试其他转义序列
        'echo -e "Line1\\tTab\\nNewline"',
    ]
    
    for cmd in test_cases:
        test_bash_with_escapes(cmd)

if __name__ == "__main__":
    main()
