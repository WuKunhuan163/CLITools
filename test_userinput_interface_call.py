#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试USERINPUT接口调用
"""

import sys
import os

def test_userinput_interface():
    """测试USERINPUT接口是否能正确工作"""
    
    print("=== 测试USERINPUT接口调用 ===")
    
    try:
        # 添加USERINPUT.py所在目录到Python路径
        userinput_dir = '/Users/wukunhuan/.local/bin'
        if userinput_dir not in sys.path:
            sys.path.insert(0, userinput_dir)
        
        print("1. 导入USERINPUT模块...")
        # 导入USERINPUT模块
        import importlib.util
        spec = importlib.util.spec_from_file_location("userinput_module", "/Users/wukunhuan/.local/bin/USERINPUT.py")
        userinput_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(userinput_module)
        
        print("2. 模块导入成功!")
        
        print("3. 调用get_user_input_tkinter接口...")
        print("   - 窗口应该弹出并显示文本框")
        print("   - 请在文本框中输入一些测试内容")
        print("   - 点击'提交'按钮")
        
        # 调用接口
        result = userinput_module.get_user_input_tkinter(
            title='接口测试窗口 - 请输入测试内容',
            timeout=60,
            max_retries=3
        )
        
        print(f"4. 接口调用完成!")
        print(f"   - 返回结果: {repr(result)}")
        print(f"   - 结果类型: {type(result)}")
        print(f"   - 结果长度: {len(result) if result else 0}")
        
        if result:
            print(f"✅ 接口调用成功! 获得用户输入: {result}")
            return True
        else:
            print(f"接口调用失败! 没有获得用户输入")
            return False
            
    except Exception as e:
        print(f"接口调用异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_userinput_interface()
    if success:
        print("\n🎉 USERINPUT接口测试通过!")
    else:
        print("\n💥 USERINPUT接口测试失败!")
