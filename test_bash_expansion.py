#!/usr/bin/env python3
"""
测试bash -x -c的路径展开和引号处理
探索echo命令中双引号和转义序列的处理问题
"""

import subprocess
import os

def test_bash_expansion(cmd, description):
    """测试bash -x -c的展开效果"""
    print(f"\n=== {description} ===")
    print(f"输入命令: {cmd}")
    
    try:
        # 在~/tmp中执行，避免在项目目录创建文件
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
        
        # 提取bash -x的展开结果
        if result.stderr:
            lines = result.stderr.strip().split('\n')
            for line in lines:
                if line.startswith('+ '):
                    expanded = line[2:]  # 去掉"+ "前缀
                    print(f"展开结果: {expanded}")
                    return expanded
        
        return None
        
    except Exception as e:
        print(f"错误: {e}")
        return None

def main():
    """测试各种命令的bash展开"""
    
    # 确保~/tmp目录存在
    os.makedirs(os.path.expanduser('~/tmp'), exist_ok=True)
    
    test_cases = [
        # 基本路径展开
        ("mkdir -p ~/test", "基本路径展开"),
        
        # echo命令 - 简单情况
        ("echo 'Hello World'", "echo简单字符串"),
        
        # echo命令 - 双引号
        ('echo "Hello World"', "echo双引号字符串"),
        
        # echo命令 - 转义序列
        ('echo -e "Line1\\nLine2\\nLine3"', "echo转义序列"),
        
        # echo命令 - 重定向
        ("echo 'Hello' > ~/test.txt", "echo重定向"),
        
        # echo命令 - 双引号+重定向
        ('echo "Hello" > ~/test.txt', "echo双引号重定向"),
        
        # echo命令 - 转义序列+重定向
        ('echo -e "Line1\\nLine2\\nLine3" > ~/test.txt', "echo转义序列重定向"),
        
        # 复杂情况 - 单引号包围
        ("'echo -e \"Line1\\nLine2\\nLine3\" > ~/test.txt'", "单引号包围整个命令"),
        
        # 测试不同的转义方式
        ('echo -e Line1\\nLine2\\nLine3', "无引号转义序列"),
        
        # 测试路径在不同位置
        ("echo 'test' > ~/output.txt && cat ~/output.txt", "多命令路径展开"),
    ]
    
    results = []
    
    for cmd, desc in test_cases:
        expanded = test_bash_expansion(cmd, desc)
        results.append((cmd, expanded, desc))
    
    # 总结结果
    print("\n" + "="*60)
    print("总结:")
    print("="*60)
    
    for original, expanded, desc in results:
        print(f"\n{desc}:")
        print(f"  原始: {original}")
        print(f"  展开: {expanded}")
        
        # 分析问题
        if expanded and original != expanded:
            if '"' in original and '"' not in expanded:
                print("  ⚠️  双引号被去掉了")
            if '\\n' in original and '\\n' not in expanded:
                print("  ⚠️  转义序列被处理了")
            if '~' in original and '~' not in expanded:
                print("  ✅ 路径展开正常")

if __name__ == "__main__":
    main()
