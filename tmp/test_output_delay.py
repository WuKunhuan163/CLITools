#!/usr/bin/env python3
"""
验证Google Drive vs /tmp的输出延迟
测试后台进程输出的可见性
"""

import subprocess
import time
import os

def test_output_delay():
    """测试输出延迟"""
    
    # 测试用的两个路径
    drive_log = "/content/drive/MyDrive/REMOTE_ROOT/tmp/test_drive_delay.log"
    tmp_log = "/tmp/test_tmp_delay.log"
    
    print("="*70)
    print("🧪 测试后台进程输出延迟")
    print("="*70)
    print()
    
    # 确保目录存在
    os.makedirs("/content/drive/MyDrive/REMOTE_ROOT/tmp", exist_ok=True)
    
    # 清理旧文件
    for f in [drive_log, tmp_log]:
        if os.path.exists(f):
            os.remove(f)
    
    # Test 1: Google Drive路径
    print("[Test 1] 输出到Google Drive路径")
    print(f"  路径: {drive_log}")
    print("  启动后台进程...")
    
    # 创建后台脚本：每秒输出一行
    script_drive = f"""
#!/bin/bash
for i in {{1..5}}; do
    echo "[Drive] Output line $i at $(date +%H:%M:%S)"
    sleep 1
done
"""
    
    with open("/tmp/test_drive.sh", "w") as f:
        f.write(script_drive)
    os.chmod("/tmp/test_drive.sh", 0o755)
    
    # 启动后台进程
    subprocess.Popen(["/bin/bash", "/tmp/test_drive.sh"], 
                     stdout=open(drive_log, "w"), 
                     stderr=subprocess.STDOUT)
    
    # 每秒检查文件大小
    print("  检查输出可见性:")
    for i in range(6):
        time.sleep(1)
        if os.path.exists(drive_log):
            size = os.path.getsize(drive_log)
            print(f"    {i+1}秒后: {size} bytes")
            if size > 0 and i == 0:
                print("      ✅ 1秒内可见！")
        else:
            print(f"    {i+1}秒后: 文件不存在")
    
    # 读取最终内容
    time.sleep(1)
    if os.path.exists(drive_log):
        with open(drive_log, "r") as f:
            content = f.read()
        print(f"  最终输出:")
        for line in content.strip().split('\n'):
            print(f"    {line}")
    print()
    
    # Test 2: /tmp路径
    print("[Test 2] 输出到/tmp路径")
    print(f"  路径: {tmp_log}")
    print("  启动后台进程...")
    
    script_tmp = f"""
#!/bin/bash
for i in {{1..5}}; do
    echo "[TMP] Output line $i at $(date +%H:%M:%S)"
    sleep 1
done
"""
    
    with open("/tmp/test_tmp.sh", "w") as f:
        f.write(script_tmp)
    os.chmod("/tmp/test_tmp.sh", 0o755)
    
    # 启动后台进程
    subprocess.Popen(["/bin/bash", "/tmp/test_tmp.sh"], 
                     stdout=open(tmp_log, "w"), 
                     stderr=subprocess.STDOUT)
    
    # 每秒检查文件大小
    print("  检查输出可见性:")
    for i in range(6):
        time.sleep(1)
        if os.path.exists(tmp_log):
            size = os.path.getsize(tmp_log)
            print(f"    {i+1}秒后: {size} bytes")
            if size > 0 and i == 0:
                print("      ✅ 1秒内可见！")
        else:
            print(f"    {i+1}秒后: 文件不存在")
    
    # 读取最终内容
    time.sleep(1)
    if os.path.exists(tmp_log):
        with open(tmp_log, "r") as f:
            content = f.read()
        print(f"  最终输出:")
        for line in content.strip().split('\n'):
            print(f"    {line}")
    print()
    
    # Test 3: 带flush的Drive输出
    print("[Test 3] Drive路径 + Python flush")
    drive_log_flush = "/content/drive/MyDrive/REMOTE_ROOT/tmp/test_drive_flush.log"
    print(f"  路径: {drive_log_flush}")
    print("  启动后台进程...")
    
    script_flush = f"""
import sys
import time
for i in range(1, 6):
    print(f"[Drive+Flush] Output line {{i}} at {{time.strftime('%H:%M:%S')}}", flush=True)
    sys.stdout.flush()  # 强制刷新
    time.sleep(1)
"""
    
    with open("/tmp/test_flush.py", "w") as f:
        f.write(script_flush)
    
    # 启动后台进程
    subprocess.Popen(["python3", "/tmp/test_flush.py"], 
                     stdout=open(drive_log_flush, "w"), 
                     stderr=subprocess.STDOUT)
    
    # 每秒检查文件大小
    print("  检查输出可见性:")
    for i in range(6):
        time.sleep(1)
        if os.path.exists(drive_log_flush):
            size = os.path.getsize(drive_log_flush)
            print(f"    {i+1}秒后: {size} bytes")
            if size > 0 and i == 0:
                print("      ✅ 1秒内可见！")
        else:
            print(f"    {i+1}秒后: 文件不存在")
    
    # 读取最终内容
    time.sleep(1)
    if os.path.exists(drive_log_flush):
        with open(drive_log_flush, "r") as f:
            content = f.read()
        print(f"  最终输出:")
        for line in content.strip().split('\n'):
            print(f"    {line}")
    print()
    
    # 总结
    print("="*70)
    print("📊 结论")
    print("="*70)
    print()
    print("如果你看到：")
    print("  • Google Drive路径：多秒后才有输出 ❌")
    print("  • /tmp路径：1秒内就有输出 ✅")
    print("  • Drive+flush：可能改善，但仍不如/tmp")
    print()
    print("这证明：后台任务日志应该写入/tmp，而不是Google Drive")
    print()
    
    # 清理
    print("清理测试文件...")
    for f in [drive_log, tmp_log, drive_log_flush, 
              "/tmp/test_drive.sh", "/tmp/test_tmp.sh", "/tmp/test_flush.py"]:
        try:
            if os.path.exists(f):
                os.remove(f)
        except:
            pass
    print("✅ 清理完成")

if __name__ == '__main__':
    test_output_delay()

