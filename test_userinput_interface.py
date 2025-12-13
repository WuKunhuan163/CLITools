#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试USERINPUT_TKINTER接口调用
模仿GOOGLE_DRIVE的GDS direct feedback功能
"""

import subprocess
import sys
import os
import time
import json

def call_userinput_interface(title=None, timeout=180):
    """
    调用USERINPUT_TKINTER接口获取用户反馈
    
    Args:
        title: 窗口标题
        timeout: 超时时间
    
    Returns:
        dict: 包含success, result, window_id的结果
    """
    try:
        print(f"🚀 调用USERINPUT接口 (标题: {title}, 超时: {timeout}秒)")
        
        # 构建命令
        cmd = [os.path.join(os.getcwd(), "USERINPUT_TKINTER")]
        if timeout != 180:
            cmd.extend(["--timeout", str(timeout)])
        
        # 调用USERINPUT_TKINTER
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout + 30
        )
        
        if result.returncode == 0:
            output = result.stdout.strip()
            
            # 解析输出
            lines = output.split('\n')
            window_id = None
            user_feedback = []
            
            for line in lines:
                if line.startswith('Window ID:'):
                    window_id = line.replace('Window ID:', '').strip()
                else:
                    user_feedback.append(line)
            
            feedback_text = '\n'.join(user_feedback).strip()
            
            return {
                'success': True,
                'window_id': window_id,
                'result': feedback_text,
                'length': len(feedback_text)
            }
        else:
            return {
                'success': False,
                'error': f"退出代码: {result.returncode}",
                'stderr': result.stderr
            }
            
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': f"接口调用超时 ({timeout + 30}秒)"
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"接口调用异常: {e}"
        }

def simulate_gds_direct_feedback():
    """模拟GDS direct feedback功能"""
    print("=== 模拟GDS Direct Feedback功能 ===")
    print("这是一个模拟Google Drive Shell中direct feedback的示例")
    print()
    
    # 模拟一些GDS操作
    print("📁 模拟GDS操作:")
    print("  > gds ls")
    print("  文件1.txt")
    print("  文件2.pdf") 
    print("  文件夹A/")
    print()
    
    print("  > gds upload 本地文件.txt")
    print("  ✅ 上传完成")
    print()
    
    # 请求用户反馈
    print("🤖 AI助手: 操作已完成，请提供您的反馈或下一步指令")
    
    # 调用USERINPUT接口
    feedback_result = call_userinput_interface(
        title="GDS Direct Feedback",
        timeout=120
    )
    
    # 处理反馈结果
    if feedback_result['success']:
        print(f"\n✅ 成功获取用户反馈:")
        print(f"   Window ID: {feedback_result['window_id']}")
        print(f"   反馈长度: {feedback_result['length']} 字符")
        print(f"   反馈内容:")
        print(f"   {'-' * 40}")
        print(f"   {feedback_result['result']}")
        print(f"   {'-' * 40}")
        
        # 模拟根据反馈执行下一步操作
        print(f"\n🔄 根据用户反馈执行后续操作...")
        print(f"   (这里会根据用户反馈内容执行相应的GDS命令)")
        
    else:
        print(f"\n❌ 获取用户反馈失败:")
        print(f"   错误: {feedback_result.get('error', '未知错误')}")

def test_multiple_interface_calls():
    """测试多次接口调用"""
    print("\n=== 测试多次接口调用 ===")
    
    scenarios = [
        {"title": "测试场景1", "timeout": 30},
        {"title": "测试场景2", "timeout": 45},
        {"title": "测试场景3", "timeout": 60}
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n📝 场景 {i}: {scenario['title']}")
        
        choice = input(f"是否测试场景 {i}? (y/N): ").strip().lower()
        if choice != 'y':
            print("跳过此场景")
            continue
        
        result = call_userinput_interface(
            title=scenario['title'],
            timeout=scenario['timeout']
        )
        
        if result['success']:
            print(f"✅ 场景 {i} 成功: {result['length']} 字符")
        else:
            print(f"❌ 场景 {i} 失败: {result['error']}")

def main():
    """主测试函数"""
    print("USERINPUT_TKINTER 接口测试")
    print("=" * 50)
    
    print("请选择测试类型:")
    print("1. 模拟GDS Direct Feedback")
    print("2. 测试多次接口调用")
    print("3. 简单接口调用测试")
    
    choice = input("请输入选择 (1-3): ").strip()
    
    if choice == "1":
        simulate_gds_direct_feedback()
    elif choice == "2":
        test_multiple_interface_calls()
    elif choice == "3":
        print("\n=== 简单接口调用测试 ===")
        result = call_userinput_interface(
            title="接口测试",
            timeout=120
        )
        print(f"\n测试结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    else:
        print("无效选择")
        return False
    
    return True

if __name__ == "__main__":
    main()