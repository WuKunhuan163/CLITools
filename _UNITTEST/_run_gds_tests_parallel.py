#!/usr/bin/env python3
"""
GDS测试并行运行脚本
使用BACKGROUND_CMD批量运行GDS单元测试，支持指定ID范围，控制并发数
"""

import os
import sys
import time
import subprocess
import json
import argparse
from pathlib import Path

# 完整的GDS测试列表（从0开始编号）
#从test_gds.py当中自动寻找所有GDSTest下方，test_开头的测试用例函数，并添加到ALL_GDS_TESTS列表中
ALL_GDS_TESTS = []
import test_gds
for name in dir(test_gds.GDSTest):
    if name.startswith('test_'):
        ALL_GDS_TESTS.append(f"test_gds.GDSTest.{name}")

def get_running_background_processes():
    """获取当前运行中的后台进程数量"""
    try:
        result = subprocess.run(
            ["../BACKGROUND_CMD", "--status", "--json"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            running_processes = [proc for proc in data.get('processes', []) 
                               if proc.get('status') == 'running']
            running_count = len(running_processes)
            return running_count
        return 0
    except Exception as e:
        print(f"Error getting background processes: {e}")
        return 1

def start_test(test_name):
    """启动一个测试"""
    # 创建输出文件名
    test_short_name = test_name.split('.')[-1]
    output_file = f"_TEMP/{test_short_name}_output.txt"
    
    # 确保_TEMP目录存在
    _TEMP_dir = Path(__file__).parent / "_TEMP"
    _TEMP_dir.mkdir(exist_ok=True)
    
    # 修改命令以重定向输出到文件
    cmd = f'cd {Path(__file__).parent} && /usr/bin/python3 -m unittest {test_name} -v > {output_file} 2>&1'
    
    try:
        result = subprocess.run(
            ["../BACKGROUND_CMD", cmd],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            if "Process started: PID" in output:
                pid = output.split("PID ")[1].split(",")[0]
                print(f"Started {test_short_name} (PID: {pid}) -> {output_file}")
                return int(pid), output_file
            else:
                print(f"Unexpected output from BACKGROUND_CMD: {output}")
                return None, None
        print(f"Failed to start {test_name}: {result.stderr}")
        return None, None
    except Exception as e:
        print(f"Error starting {test_name}: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def list_tests():
    """列出所有测试及其ID"""
    print("📋 GDS Test List (ID: Test Name)")
    print("=" * 60)
    for i, test in enumerate(ALL_GDS_TESTS):
        test_name = test.split('.')[-1]  # 只显示测试方法名
        print(f"{i:2d}: {test_name}")
    print(f"\nTotal: {len(ALL_GDS_TESTS)} tests")

def run_tests_range(start_id, end_id, max_concurrent=3):
    """运行指定范围的测试"""
    if start_id < 0 or end_id >= len(ALL_GDS_TESTS) or start_id > end_id:
        print(f"❌ Invalid range: {start_id}-{end_id}. Valid range: 0-{len(ALL_GDS_TESTS)-1}")
        return
    
    test_queue = ALL_GDS_TESTS[start_id:end_id+1]
    
    print(f"🚀 Running tests {start_id}-{end_id} ({len(test_queue)} tests)")
    print(f"⚡ Max concurrent: {max_concurrent}")
    print("=" * 60)
    
    completed_tests = []
    failed_tests = []
    running_pids = {}  # {pid: (test_name, output_file)}
    test_results = {}  # {test_name: {"status": "pass/fail", "output_file": "path", "content": "..."}}
    last_progress_msg = ""  # 跟踪上次的进度消息，避免重复打印
    
    while test_queue or running_pids:
        # 启动新测试（如果有空闲槽位）
        while len(running_pids) < max_concurrent and test_queue:
            test_name = test_queue.pop(0)
            print(f"Attempting to start {test_name.split('.')[-1]}")
            pid, output_file = start_test(test_name)
            if pid:
                running_pids[pid] = (test_name, output_file)
                print(f"Successfully started {test_name.split('.')[-1]} with PID {pid}")
            else:
                failed_tests.append(test_name)
                print(f"Failed to start {test_name.split('.')[-1]}")
        
        # 检查已完成的测试
        completed_pids = []
        for pid, (test_name, output_file) in running_pids.items():
            try:
                result = subprocess.run(
                    ["../BACKGROUND_CMD", "--status", str(pid), "--json"],
                    capture_output=True,
                    text=True,
                    cwd=Path(__file__).parent
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    if data.get('success') and data.get('status', {}).get('status') == 'completed':
                        completed_pids.append(pid)
                        completed_tests.append(test_name)
                        
                        # 读取测试结果
                        test_short_name = test_name.split('.')[-1]
                        output_path = Path(__file__).parent / output_file
                        test_content = ""
                        test_status = "unknown"
                        
                        try:
                            if output_path.exists():
                                test_content = output_path.read_text(encoding='utf-8')
                                # 简单判断测试是否通过
                                if "OK" in test_content and "FAILED" not in test_content:
                                    test_status = "pass"
                                elif "FAILED" in test_content or "ERROR" in test_content:
                                    test_status = "fail"
                                else:
                                    test_status = "unknown"
                            else:
                                test_content = "Output file not found"
                                test_status = "fail"
                        except Exception as e:
                            test_content = f"Error reading output: {e}"
                            test_status = "fail"
                        
                        test_results[test_name] = {
                            "status": test_status,
                            "output_file": output_file,
                            "content": test_content
                        }
                        
                        status_icon = "✅" if test_status == "pass" else "❌" if test_status == "fail" else "❓"
                        print(f"{status_icon} Completed {test_short_name} (PID: {pid}) - {test_status.upper()}")
            except Exception:
                pass
        
        # 移除已完成的进程
        for pid in completed_pids:
            del running_pids[pid]
        
        # 显示进度（只在变化时打印，避免重复）
        total = len(ALL_GDS_TESTS[start_id:end_id+1])
        done = len(completed_tests) + len(failed_tests)
        running = len(running_pids)  # 使用测试套件跟踪的进程数量
        remaining = len(test_queue)
        
        # 添加debug信息
        progress_msg = f"Progress: {done}/{total} done, {running} running, {remaining} queued"
        debug_msg = f"running_pids={list(running_pids.keys())}"
        
        # 只在进度消息发生变化时打印
        if progress_msg != last_progress_msg:
            print(progress_msg)
            print(debug_msg)  
            last_progress_msg = progress_msg
        
        if running_pids or test_queue:
            time.sleep(5)  # 等待5秒再检查
    
    # 最终报告
    print(f"\n{'='*60}")
    print(f"Test execution completed!")
    
    # 统计结果
    passed_tests = [name for name, result in test_results.items() if result["status"] == "pass"]
    failed_test_results = [name for name, result in test_results.items() if result["status"] == "fail"]
    unknown_tests = [name for name, result in test_results.items() if result["status"] == "unknown"]
    
    print(f"Passed: {len(passed_tests)}")
    print(f"Failed: {len(failed_test_results) + len(failed_tests)}")
    print(f"Unknown: {len(unknown_tests)}")
    
    # 显示失败的测试详情
    all_failed = failed_tests + failed_test_results
    if all_failed:
        print(f"\nFailed tests:")
        for test in all_failed:
            test_short = test.split('.')[-1]
            print(f"  - {test_short}")
            if test in test_results:
                output_file = test_results[test]["output_file"]
                print(f"    {output_file}")
    
    # 显示通过的测试
    if passed_tests:
        print(f"\nPassed tests:")
        for test in passed_tests:
            test_short = test.split('.')[-1]
            output_file = test_results[test]["output_file"]
            print(f"  - {test_short} ({output_file})")
    
    print(f"\nAll test outputs saved in _TEMP/ folder")
    print(f"Use '../BACKGROUND_CMD --status' to see process details")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='GDS并行测试运行器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 run_gds_tests_parallel.py --list                    # 列出所有测试
  python3 run_gds_tests_parallel.py --range 0 4               # 运行测试0-4 (5个测试)
  python3 run_gds_tests_parallel.py --range 10 14 --max 2     # 运行测试10-14，最大并发2
        """
    )
    
    parser.add_argument('--list', action='store_true', help='列出所有测试及其ID')
    parser.add_argument('--range', nargs=2, type=int, metavar=('START', 'END'), 
                       help='指定测试ID范围 (包含START和END)')
    parser.add_argument('--max', type=int, default=3, metavar='N',
                       help='最大并发数 (默认: 3)')
    
    args = parser.parse_args()
    
    if args.list:
        list_tests()
    elif args.range:
        start_id, end_id = args.range
        run_tests_range(start_id, end_id, args.max)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
