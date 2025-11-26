#!/usr/bin/env python3
"""
在Google Colab测试Python 3.9.0编译
复制这个脚本内容到Colab cell运行
"""

import subprocess
import time
import os
import tempfile
import shutil

def test_python_390_on_colab():
    """在Colab测试Python 3.9.0编译"""
    
    print("="*70)
    print("🧪 在Google Colab测试Python 3.9.0编译")
    print("="*70)
    
    # 检查是否在Colab环境
    try:
        import google.colab
        print("✅ 确认在Google Colab环境")
    except:
        print("⚠️  警告：不在Colab环境")
    
    print()
    
    # 显示系统信息
    print("📊 系统信息:")
    subprocess.run(['uname', '-a'])
    subprocess.run(['gcc', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = subprocess.run(['gcc', '--version'], capture_output=True, text=True)
    print(f"GCC: {result.stdout.split('\\n')[0]}")
    print(f"CPU: {os.cpu_count()} cores")
    print()
    
    version = "3.9.0"
    start_time = time.time()
    
    # 源码包路径
    source_tgz = f"/content/drive/MyDrive/REMOTE_ENV/python_test/Python-{version}.tgz"
    
    # 检查文件是否存在
    if not os.path.exists(source_tgz):
        print(f"❌ 源码包不存在: {source_tgz}")
        print(f"   请确保已上传到Google Drive")
        return False
    
    file_size = os.path.getsize(source_tgz)
    print(f"✅ 找到源码包: {file_size / 1024 / 1024:.1f} MB")
    print()
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix='python_390_test_', dir='/tmp')
    print(f"📁 临时目录: {temp_dir}")
    print()
    
    try:
        # 1. 复制源码包
        print(f"[1/6] 📋 复制源码包...")
        start_step = time.time()
        shutil.copy2(source_tgz, temp_dir)
        elapsed = time.time() - start_step
        print(f"      ✅ 复制完成: {elapsed:.1f}s")
        print()
        
        # 2. 解压
        print(f"[2/6] 📦 解压...")
        start_step = time.time()
        result = subprocess.run(
            ['tar', '-xzf', f'{temp_dir}/Python-{version}.tgz', '-C', temp_dir],
            capture_output=True,
            text=True,
            timeout=60
        )
        elapsed = time.time() - start_step
        
        if result.returncode != 0:
            print(f"      ❌ 解压失败")
            print(f"      {result.stderr}")
            return False
        
        print(f"      ✅ 解压完成: {elapsed:.1f}s")
        print()
        
        source_dir = f'{temp_dir}/Python-{version}'
        install_dir = f'{temp_dir}/install'
        
        # 3. Configure
        print(f"[3/6] ⚙️  Configure（预计1-2分钟）...")
        start_step = time.time()
        
        result = subprocess.run(
            ['./configure', f'--prefix={install_dir}'],
            cwd=source_dir,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        elapsed = time.time() - start_step
        
        if result.returncode != 0:
            print(f"      ❌ Configure失败 ({elapsed:.1f}s)")
            print(f"      错误信息:")
            print(result.stderr[-500:])
            return False
        
        print(f"      ✅ Configure成功: {elapsed:.1f}s")
        print()
        
        # 4. Make
        print(f"[4/6] 🔨 Make -j{os.cpu_count()}（预计3-8分钟）...")
        start_step = time.time()
        
        result = subprocess.run(
            ['make', f'-j{os.cpu_count()}'],
            cwd=source_dir,
            capture_output=True,
            text=True,
            timeout=600
        )
        
        elapsed = time.time() - start_step
        
        # 检查segfault
        if 'Segmentation fault' in result.stderr:
            print(f"      ❌ 编译segfault ({elapsed:.1f}s)")
            return False
        
        if result.returncode != 0:
            print(f"      ❌ Make失败 ({elapsed:.1f}s)")
            print(f"      错误信息:")
            print(result.stderr[-500:])
            return False
        
        print(f"      ✅ Make成功: {elapsed:.1f}s ({elapsed/60:.1f}分钟)")
        print()
        
        # 5. Make install
        print(f"[5/6] 📦 Make install...")
        start_step = time.time()
        
        result = subprocess.run(
            ['make', 'install'],
            cwd=source_dir,
            capture_output=True,
            text=True,
            timeout=180
        )
        
        elapsed = time.time() - start_step
        print(f"      ✅ Install完成: {elapsed:.1f}s")
        print()
        
        # 6. 测试执行
        print(f"[6/6] 🧪 测试执行...")
        
        bin_dir = f'{install_dir}/bin'
        python_exe = None
        
        if os.path.exists(bin_dir):
            files = os.listdir(bin_dir)
            for fname in files:
                if fname.startswith('python3.') and '-' not in fname:
                    python_exe = f'{bin_dir}/{fname}'
                    break
            
            if not python_exe and os.path.exists(f'{bin_dir}/python3'):
                python_exe = f'{bin_dir}/python3'
        
        if not python_exe or not os.path.exists(python_exe):
            print(f"      ❌ Python可执行文件未找到")
            return False
        
        # --version测试
        result = subprocess.run(
            [python_exe, '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            print(f"      ❌ --version失败")
            return False
        
        version_output = result.stdout.strip() or result.stderr.strip()
        print(f"      ✅ 版本检查: {version_output}")
        
        # 代码执行测试
        result = subprocess.run(
            [python_exe, '-c', 'import sys; print(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} 可执行")'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            print(f"      ❌ 代码执行失败")
            return False
        
        print(f"      ✅ {result.stdout.strip()}")
        
        # 成功！
        total_elapsed = time.time() - start_time
        print()
        print("="*70)
        print(f"🎉 Python {version} 在Colab编译成功！")
        print(f"⏱️  总耗时: {total_elapsed:.1f}s ({total_elapsed/60:.1f}分钟)")
        print("="*70)
        
        return True
        
    except subprocess.TimeoutExpired as e:
        elapsed = time.time() - start_time
        print(f"❌ 超时: {e}")
        print(f"已耗时: {elapsed:.1f}s")
        return False
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ 错误: {e}")
        print(f"已耗时: {elapsed:.1f}s")
        return False
    finally:
        # 清理
        print()
        print(f"🧹 清理临时目录: {temp_dir}")
        try:
            shutil.rmtree(temp_dir)
            print("✅ 清理完成")
        except:
            print("⚠️  清理失败")

if __name__ == '__main__':
    # 确保Google Drive已挂载
    if not os.path.exists('/content/drive'):
        print("⚠️  请先挂载Google Drive:")
        print("    from google.colab import drive")
        print("    drive.mount('/content/drive')")
    else:
        success = test_python_390_on_colab()
        
        if success:
            print("\n✅ 结论: Python 3.9.0 在Google Colab (Ubuntu 22.04) 上可以成功编译安装")
        else:
            print("\n❌ 结论: Python 3.9.0 在Google Colab上编译失败")

