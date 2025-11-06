#!/usr/bin/env python3
"""
测试undo_local_path_user_expansion函数的接口测试
"""

import sys
import os
sys.path.append('/Users/wukunhuan/.local/bin/GOOGLE_DRIVE_PROJ')

from modules.path_resolver import PathResolver

def test_undo_expansion():
    """测试undo_local_path_user_expansion函数"""
    
    # 创建PathResolver实例
    resolver = PathResolver(None)  # main_instance为None用于测试
    
    # 获取home目录用于构造测试用例
    home_dir = os.path.expanduser("~")
    
    test_cases = [
        # 基本情况
        ("~/test.txt", "~/test.txt"),
        
        # 被bash展开的路径（这是函数要处理的主要情况）
        (f"{home_dir}/test.txt", "~/test.txt"),
        (f"{home_dir}", "~"),
        
        # 命令中的路径
        (f"echo hello > {home_dir}/test.txt", "echo hello > ~/test.txt"),
        
        # 带引号的命令（关键测试用例）
        (f'echo "hello world" > {home_dir}/test.txt', 'echo "hello world" > ~/test.txt'),
        (f'echo -e "Line1\\nLine2" > {home_dir}/test.txt', 'echo -e "Line1\\nLine2" > ~/test.txt'),
        
        # 混合情况
        (f"cp {home_dir}/source.txt ~/dest.txt", "cp ~/source.txt ~/dest.txt"),
        
        # 不应该被改变的情况
        ("echo 'hello world'", "echo 'hello world'"),
        ("/other/path/file.txt", "/other/path/file.txt"),
        ("relative/path/file.txt", "relative/path/file.txt"),
    ]
    
    print("测试undo_local_path_user_expansion函数:")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for i, (input_cmd, expected) in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {input_cmd}")
        print(f"期望: {expected}")
        
        try:
            result = resolver.undo_local_path_user_expansion(input_cmd)
            print(f"实际: {result}")
            
            if result == expected:
                print("✅ 通过")
                passed += 1
            else:
                print("❌ 失败")
                failed += 1
        except Exception as e:
            print(f"❌ 异常: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    
    return failed == 0

if __name__ == "__main__":
    success = test_undo_expansion()
    sys.exit(0 if success else 1)
