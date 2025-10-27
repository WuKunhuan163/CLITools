#!/usr/bin/env python3
"""测试process_terminal_erases函数的终端转义序列处理能力"""

import sys
sys.path.insert(0, '/Users/wukunhuan/.local/bin')

from GOOGLE_DRIVE_PROJ.modules.command_executor import CommandExecutor

def test_terminal_escape_sequences():
    """测试各种终端转义序列的处理"""
    
    # 创建一个CommandExecutor实例（需要main_instance参数）
    class MockMainInstance:
        pass
    
    executor = CommandExecutor(main_instance=MockMainInstance())
    
    # 测试用例列表：(输入, 期望输出, 说明)
    test_cases = [
        # 回车符测试
        ("Hello\rWorld", "World", "回车符覆盖前面内容"),
        ("Loading...\rDone!", "Done!", "进度指示器被覆盖"),
        ("Line1\rLine2\rLine3", "Line3", "多个回车符，保留最后一个"),
        
        # 退格符测试
        ("Hello\b\b\bWorld", "HeWorld", "退格符删除字符"),
        ("Test\b\b\b\babc", "abc", "退格全部删除后重新输入"),
        ("\bHello", "Hello", "开头的退格符被忽略"),
        
        # ANSI颜色代码测试
        ("\033[31mRed Text\033[0m", "Red Text", "ANSI颜色代码（八进制）"),
        ("\x1b[32mGreen\x1b[0m", "Green", "ANSI颜色代码（十六进制）"),
        ("\033[1;34mBold Blue\033[0m", "Bold Blue", "组合ANSI代码"),
        
        # 光标移动测试
        ("Text\033[2AUp", "TextUp", "光标上移"),
        ("Text\033[10;20HMove", "TextMove", "光标定位"),
        ("Text\x1b[5CRight", "TextRight", "光标右移"),
        
        # 清屏序列测试
        ("Text\033[2JClear", "TextClear", "清屏代码"),
        ("Text\033[HHome", "TextHome", "光标归位"),
        ("Text\033[KErase", "TextErase", "清除到行尾"),
        
        # 响铃符测试
        ("Hello\aWorld", "HelloWorld", "响铃符（\\a）"),
        ("Test\x07End", "TestEnd", "响铃符（\\x07）"),
        
        # 制表符测试
        ("Col1\tCol2\tCol3", "Col1    Col2    Col3", "制表符转空格"),
        
        # 混合测试
        ("Loading\r\033[32m✓\033[0m Done", "✓ Done", "进度指示器+颜色代码"),
        ("Progress: 50%\rProgress: 100%", "Progress: 100%", "进度条更新"),
        # 注意：ANSI序列应该在退格符处理之前被移除，所以退格数应该基于可见字符数
        # "\033[31mError\033[0m" -> "Error" (5个可见字符)，然后5个退格符删除所有字符
        # 实际上这个场景很少见，因为终端通常先处理ANSI再处理退格
        # 更现实的测试：直接在可见文本上使用退格
        ("Error\b\b\b\b\b\033[32mFixed\033[0m", "Fixed", "退格+颜色组合"),
        
        # 空字符串测试
        ("", "", "空字符串"),
        (None, "", "None输入"),
        
        # 多行测试
        ("Line1\nLine2\rUpdated2", "Line1\nUpdated2", "多行+回车"),
        ("A\033[31mRed\033[0m\nB\x1b[32mGreen\x1b[0m", "ARed\nBGreen", "多行+颜色"),
    ]
    
    print("🧪 测试 process_terminal_erases 函数\n")
    print("=" * 80)
    
    passed = 0
    failed = 0
    failed_cases = []
    
    for input_text, expected, description in test_cases:
        result = executor.process_terminal_erases(input_text)
        
        if result == expected:
            passed += 1
            status = "✅ PASS"
        else:
            failed += 1
            status = "❌ FAIL"
            failed_cases.append((input_text, expected, result, description))
        
        print(f"\n{status}")
        print(f"  说明: {description}")
        print(f"  输入: {repr(input_text)}")
        print(f"  期望: {repr(expected)}")
        if result != expected:
            print(f"  实际: {repr(result)}")
    
    print("\n" + "=" * 80)
    print(f"\n📊 测试结果: {passed}/{len(test_cases)} 通过")
    
    if failed > 0:
        print(f"\n❌ {failed} 个测试失败:")
        for input_text, expected, result, description in failed_cases:
            print(f"\n  {description}")
            print(f"    输入: {repr(input_text)}")
            print(f"    期望: {repr(expected)}")
            print(f"    实际: {repr(result)}")
        return 1
    else:
        print("✅ 所有测试通过！")
        return 0

if __name__ == '__main__':
    try:
        sys.exit(test_terminal_escape_sequences())
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
