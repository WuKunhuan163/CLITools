#!/usr/bin/env python3
"""
测试indicator清理功能的专用脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from _UNITTEST.test_gds import GDSTest

def test_indicator_cleanup():
    """测试indicator清理功能"""
    
    # 创建测试实例
    test_instance = GDSTest()
    GDSTest.setUpClass()
    test_instance.setUp()
    
    print("=== 测试indicator清理功能 ===")
    
    # 测试用例1: 简单echo命令
    print("\n测试1: 简单echo命令")
    test_content = "Echo stdout test content"
    result = test_instance._run_gds_command(f"echo '{test_content}'")
    
    print(f"返回码: {result.returncode}")
    print(f"Raw stdout: {repr(result.stdout)}")
    print(f"Raw stderr: {repr(result.stderr)}")
    
    # 添加处理后的可读输出
    readable_stdout = test_instance._process_terminal_erase(result.stdout)
    print(f"Raw stdout (readable): {repr(readable_stdout)}")
    
    # 测试清理函数
    print("\n测试清理函数:")
    cleaned_stdout = test_instance._process_terminal_erase(result.stdout)
    print(f"Cleaned stdout: {repr(cleaned_stdout)}")
    print(f"Cleaned stdout (显示): '{cleaned_stdout}'")
    
    # 检查是否还有转义序列
    has_escape = '\x1b[K' in cleaned_stdout or '\r' in cleaned_stdout
    print(f"是否还有转义序列: {has_escape}")
    
    # 测试用例2: 带重定向的命令
    print("\n测试2: 带重定向的echo命令")
    test_file = test_instance._get_test_file_path("indicator_test.txt")
    result2 = test_instance._run_gds_command(f"echo '{test_content}' > '{test_file}'")
    
    print(f"返回码: {result2.returncode}")
    print(f"Raw stdout: {repr(result2.stdout)}")
    print(f"Raw stderr: {repr(result2.stderr)}")
    
    # 添加处理后的可读输出
    readable_stdout2 = test_instance._process_terminal_erase(result2.stdout)
    print(f"Raw stdout (readable): {repr(readable_stdout2)}")
    
    # 测试清理函数
    print("\n测试清理函数:")
    cleaned_stdout2 = test_instance._process_terminal_erase(result2.stdout)
    print(f"Cleaned stdout: {repr(cleaned_stdout2)}")
    print(f"Cleaned stdout (显示): '{cleaned_stdout2}'")
    
    # 检查是否还有转义序列
    has_escape2 = '\x1b[K' in cleaned_stdout2 or '\r' in cleaned_stdout2
    print(f"是否还有转义序列: {has_escape2}")
    
    # 测试用例3: 手动构造包含indicator的字符串
    print("\n测试3: 手动构造的indicator字符串")
    test_strings = [
        '\n\x1b[KEcho stdout test content\n',
        '\r\x1b[K⏳ Waiting for result ...\r\x1b[KActual content\n',
        '⏳ Processing\r\x1b[K\n\x1b[KDone\n',
        'Line1\n\x1b[K⏳ Progress\r\x1b[KLine2\n'
    ]
    
    for i, test_str in enumerate(test_strings, 1):
        print(f"\n测试字符串 {i}:")
        print(f"原始: {repr(test_str)}")
        cleaned = test_instance._process_terminal_erase(test_str)
        print(f"清理后: {repr(cleaned)}")
        print(f"显示: '{cleaned}'")
        
        # 检查是否还有转义序列
        has_escape = '\x1b[K' in cleaned or '\r' in cleaned
        print(f"是否还有转义序列: {has_escape}")
        if has_escape:
            print("❌ 清理不完整")
        else:
            print("✅ 清理成功")

if __name__ == '__main__':
    test_indicator_cleanup()
