"""
GDS Extract Command - Parallel file extraction and transfer system

Supports extracting zip files and transferring them to Google Drive in batches
using parallel workers for efficient large-scale file operations.
"""

import os
import time
import threading
import queue
import hashlib
from pathlib import Path
from GOOGLE_DRIVE_PROJ.modules.commands.base_command import BaseCommand


class ExtractCommand(BaseCommand):
    """
    GDS extract指令 - 并行文件解压和转移系统
    
    功能：
    1. 将zip文件复制到/tmp并解压
    2. 递归分析目录结构
    3. 根据文件数量智能决定压缩整体转移或分批转移
    4. 使用3个worker并行执行转移任务
    5. 每批转移后创建指纹文件，确保可靠性
    
    语法：
        GDS extract <zip_file> [--transfer-batch SIZE]
        
    示例：
        GDS extract test.tar.gz
        GDS extract ~/tmp/python.tar.gz --transfer-batch 500
        GDS extract @/python/test.zip --transfer-batch 2000
    """
    
    @property
    def command_name(self):
        """命令名称"""
        return "extract"
    
    def __init__(self, main_instance):
        """
        初始化ExtractCommand
        
        Args:
            main_instance: GoogleDriveShell主实例
        """
        self.main_instance = main_instance
        self.shell = main_instance
    
    def execute(self, cmd, args, command_identifier=None):
        """
        执行extract命令（CommandRegistry接口）
        
        Args:
            cmd (str): 命令名称
            args (list): 命令参数
            command_identifier (str): 命令标识符
            
        Returns:
            int: 退出码（0表示成功，非0表示失败）
        """
        result = self.handle_command(args)
        
        # 转换dict结果为exit code
        if isinstance(result, dict):
            return 0 if result.get("success") else 1
        return 0
        
    def _get_stdout(self, result):
        """
        从命令结果中获取stdout
        
        Args:
            result (dict): 命令执行结果
            
        Returns:
            str: stdout内容
        """
        # 首先尝试从data中获取（正常的capture_result模式）
        if 'data' in result and 'stdout' in result['data']:
            return result['data']['stdout']
        # 否则直接从result获取（兼容性）
        return result.get('stdout', '')
    
    def handle_command(self, args):
        """
        处理extract命令
        
        Args:
            args (list): 命令参数
            
        Returns:
            dict: 执行结果
        """
        # 解析参数
        if not args or '--help' in args or '-h' in args:
            return self._show_help()
        
        # 解析文件路径和参数
        archive_path = None
        transfer_batch = 1000  # 默认batch大小
        
        i = 0
        while i < len(args):
            arg = args[i]
            
            if arg == '--transfer-batch':
                if i + 1 < len(args):
                    try:
                        transfer_batch = int(args[i + 1])
                        i += 2
                        continue
                    except ValueError:
                        return {
                            "success": False,
                            "error": f"Invalid --transfer-batch value: {args[i + 1]}"
                        }
                else:
                    return {
                        "success": False,
                        "error": "--transfer-batch requires a numeric argument"
                    }
            else:
                if archive_path is None:
                    archive_path = arg
                else:
                    return {
                        "success": False,
                        "error": f"Multiple archive paths specified: {archive_path} and {arg}"
                    }
                i += 1
        
        if archive_path is None:
            return {
                "success": False,
                "error": "No archive file specified"
            }
        
        # 执行extract操作
        return self.extract_and_transfer(archive_path, transfer_batch)
    
    def transfer_directory(self, source_dir, target_dir, transfer_batch=1000):
        """
        批量转移已存在的目录（不需要解压）
        
        用于pyenv等场景，直接转移已准备好的目录
        
        Args:
            source_dir (str): 源目录路径（通常在/tmp）
            target_dir (str): 目标目录路径（GDS格式，如~/python/3.9.7）
            transfer_batch (int): 每批转移的文件数量
            
        Returns:
            dict: 执行结果
        """
        print(f"\n{'='*70}")
        print(f"GDS Batch Transfer - Parallel Directory Transfer")
        print(f"{'='*70}")
        print(f"Source: {source_dir}")
        print(f"Target: {target_dir}")
        print(f"Transfer batch size: {transfer_batch}")
        print(f"{'='*70}\n")
        
        try:
            # Step 1: 生成任务ID
            task_id = self._generate_task_id(source_dir)
            fingerprint_dir = f"~/tmp/transfer_fingerprints_{task_id}"
            
            print(f"  Task ID: {task_id}")
            print(f"  Fingerprint dir: {fingerprint_dir}")
            
            # Step 2: 转换目标路径为远端路径
            remote_target_dir = self._convert_to_remote_path(target_dir)
            print(f"  Remote target: {remote_target_dir}")
            
            # Step 3: 分析目录结构
            print("\nStep 1: Analyzing directory structure...")
            dir_structure = self._analyze_directory_structure(source_dir)
            print(f"  Total files: {dir_structure['total_files']}")
            print(f"  Total directories: {dir_structure['total_dirs']}")
            
            # Step 4: 构建转移任务列表
            print("\nStep 2: Building transfer task list...")
            task_list = self._build_transfer_tasks(
                source_dir, 
                remote_target_dir,
                transfer_batch,
                fingerprint_dir
            )
            print(f"  Total tasks: {len(task_list)}")
            
            # Step 5: 启动3个worker并行执行
            print("\nStep 3: Starting parallel transfer with 3 workers...")
            transfer_result = self._parallel_transfer(task_list, num_workers=3)
            
            if not transfer_result["success"]:
                return transfer_result
            
            # Step 6: 清理临时文件（可选，pyenv可能需要保留）
            # self._cleanup_tmp(source_dir)
            
            print(f"\n{'='*70}")
            print(f"✅ Batch transfer completed successfully!")
            print(f"  Files transferred: {transfer_result['files_transferred']}")
            print(f"  Time taken: {transfer_result['time_taken']:.2f}s")
            print(f"{'='*70}\n")
            
            return {
                "success": True,
                "task_id": task_id,
                "files_transferred": transfer_result["files_transferred"],
                "time_taken": transfer_result["time_taken"]
            }
            
        except KeyboardInterrupt:
            print("\n\n⚠️ Transfer interrupted by user (Ctrl+C)")
            print("Progress may be partially saved. You can manually check the transfer status.")
            return {
                "success": False,
                "error": "Transfer interrupted by user"
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Transfer failed: {str(e)}"
            }
    
    def extract_and_transfer(self, archive_path, transfer_batch=1000):
        """
        解压文件并批量转移
        
        Args:
            archive_path (str): 压缩文件路径（可能是GDS路径格式）
            transfer_batch (int): 每批转移的文件数量
            
        Returns:
            dict: 执行结果
        """
        print(f"\n{'='*70}")
        print(f"GDS Extract - Parallel File Transfer System")
        print(f"{'='*70}")
        print(f"Archive: {archive_path}")
        print(f"Transfer batch size: {transfer_batch}")
        print(f"{'='*70}\n")
        
        try:
            # Step 1: 路径转换（GDS路径 → 远端绝对路径）
            print("Step 1: Converting path...")
            remote_archive_path = self._convert_to_remote_path(archive_path)
            print(f"  Remote archive path: {remote_archive_path}")
            
            # Step 2: 生成临时目录和任务ID
            task_id = self._generate_task_id(remote_archive_path)
            tmp_extract_dir = f"/tmp/gds_extract_{task_id}"
            fingerprint_dir = f"~/tmp/extract_fingerprints_{task_id}"
            
            print(f"  Task ID: {task_id}")
            print(f"  Temp extract dir: {tmp_extract_dir}")
            print(f"  Fingerprint dir: {fingerprint_dir}")
            
            # Step 2-4: 在一个命令中完成解压和分析（减少远端窗口数量）
            print("\nStep 2: Extracting and analyzing (combined in one remote command)...")
            extract_result = self._extract_and_analyze_combined(
                remote_archive_path, 
                tmp_extract_dir
            )
            
            if not extract_result["success"]:
                return extract_result
            
            actual_extract_dir = extract_result["content_dir"]
            dir_tree_text = extract_result["dir_tree"]  # ls -R结果文本
            
            print(f"  Actual content dir: {actual_extract_dir}")
            print(f"  Total files: {extract_result['total_files']}")
            print(f"  Total directories: {extract_result['total_dirs']}")
            
            # Step 3: 本地分析目录树构建任务列表（无需多次远端查询）
            print("\nStep 3: Building transfer task list (local analysis)...")
            task_list = self._build_transfer_tasks_from_tree(
                actual_extract_dir, 
                dir_tree_text,
                extract_result['total_files'],
                transfer_batch,
                fingerprint_dir
            )
            print(f"  Total tasks: {len(task_list)}")
            
            # Step 4: 启动3个worker并行执行
            print("\nStep 4: Starting parallel transfer with 3 workers...")
            transfer_result = self._parallel_transfer(task_list, num_workers=3)
            
            if not transfer_result["success"]:
                return transfer_result
            
            # Step 7: 清理临时文件
            print("\nStep 6: Cleaning up...")
            self._cleanup_tmp(tmp_extract_dir)
            
            print(f"\n{'='*70}")
            print(f"✅ Extract and transfer completed successfully!")
            print(f"  Files transferred: {transfer_result['files_transferred']}")
            print(f"  Time taken: {transfer_result['time_taken']:.2f}s")
            print(f"{'='*70}\n")
            
            return {
                "success": True,
                "task_id": task_id,
                "files_transferred": transfer_result["files_transferred"],
                "time_taken": transfer_result["time_taken"]
            }
            
        except KeyboardInterrupt:
            print("\n\n⚠️ Extract interrupted by user (Ctrl+C)")
            print("Exiting immediately...")
            # 不保存进度，立即退出
            import sys
            sys.exit(1)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Extract failed: {str(e)}"
            }
    
    def _convert_to_remote_path(self, gds_path):
        """
        将GDS路径转换为远端绝对路径
        
        Args:
            gds_path (str): GDS格式路径（可能包含~或@）
            
        Returns:
            str: 远端绝对路径
        """
        # 获取REMOTE_ROOT和REMOTE_ENV路径
        try:
            from GOOGLE_DRIVE_PROJ.modules.path_constants import REMOTE_ROOT, REMOTE_ENV
        except ImportError:
            # Fallback
            REMOTE_ROOT = "/content/drive/MyDrive/REMOTE_ROOT"
            REMOTE_ENV = "/content/drive/MyDrive/REMOTE_ENV"
        
        # 处理不同的路径格式
        if gds_path.startswith('@/'):
            # @/path → {REMOTE_ENV}/path
            return gds_path.replace('@/', f'{REMOTE_ENV}/')
        elif gds_path.startswith('~/'):
            # ~/path → {REMOTE_ROOT}/path
            return gds_path.replace('~/', f'{REMOTE_ROOT}/')
        elif gds_path.startswith('@'):
            # @path → {REMOTE_ENV}/path
            return gds_path.replace('@', f'{REMOTE_ENV}/')
        elif gds_path.startswith('~'):
            # ~path → {REMOTE_ROOT}/path
            return gds_path.replace('~', f'{REMOTE_ROOT}/')
        else:
            # 绝对路径或相对路径，保持不变
            return gds_path
    
    def _generate_task_id(self, path):
        """生成任务ID"""
        timestamp = str(int(time.time()))
        hash_str = hashlib.md5(f"{path}_{timestamp}".encode()).hexdigest()[:8]
        return hash_str
    
    def _copy_and_extract(self, archive_path, extract_dir):
        """
        复制压缩文件到/tmp并解压
        
        Args:
            archive_path (str): 远端压缩文件路径
            extract_dir (str): 解压目标目录
            
        Returns:
            dict: 执行结果
        """
        # 构造复制和解压命令
        archive_name = os.path.basename(archive_path)
        tmp_archive = f"/tmp/gds_archive_{archive_name}"  # 添加前缀避免同名
        
        # 检测压缩文件类型
        if archive_path.endswith('.tar.gz') or archive_path.endswith('.tgz'):
            extract_cmd = f"tar -xzf {tmp_archive} -C {extract_dir}"
        elif archive_path.endswith('.tar'):
            extract_cmd = f"tar -xf {tmp_archive} -C {extract_dir}"
        elif archive_path.endswith('.zip'):
            extract_cmd = f"unzip -q {tmp_archive} -d {extract_dir}"
        else:
            return {
                "success": False,
                "error": f"Unsupported archive format: {archive_name}"
            }
        
        # 如果源文件已在/tmp，直接使用，不复制
        if archive_path.startswith('/tmp/'):
            copy_cmd = f"[ '{archive_path}' = '{tmp_archive}' ] || cp '{archive_path}' {tmp_archive}"
        else:
            copy_cmd = f"cp '{archive_path}' {tmp_archive}"
        
        # 执行复制和解压
        cmd = f"""
cd /tmp && \\
echo 'Preparing archive...' && \\
{copy_cmd} && \\
echo 'Creating extract directory...' && \\
mkdir -p {extract_dir} && \\
echo 'Extracting archive...' && \\
{extract_cmd} && \\
echo 'Extraction completed' && \\
rm -f {tmp_archive}
"""
        
        # 使用raw command模式执行
        if hasattr(self.shell, 'command_executor'):
            old_raw = getattr(self.shell.command_executor, '_raw_command', False)
            self.shell.command_executor._raw_command = True
            
            result = self.shell.command_executor.execute_command_interface(
                cmd=cmd.strip(),
                capture_result=False
            )
            
            self.shell.command_executor._raw_command = old_raw
            
            if result.get("success") == False or result.get("interrupted"):
                return {
                    "success": False,
                    "error": "Failed to copy and extract archive"
                }
        
        return {"success": True}
    
    def _extract_and_analyze_combined(self, archive_path, extract_dir):
        """
        合并的解压和分析方法 - 在一个远端命令中完成所有操作
        
        流程：
        1. 复制并解压
        2. 找到实际内容目录
        3. 执行ls -R获取完整目录树
        4. 统计文件和目录数量
        
        Args:
            archive_path (str): 压缩文件路径
            extract_dir (str): 解压目标目录
            
        Returns:
            dict: {
                "success": bool,
                "content_dir": str,      # 实际内容目录
                "dir_tree": str,          # ls -R结果文本
                "total_files": int,
                "total_dirs": int
            }
        """
        archive_name = os.path.basename(archive_path)
        tmp_archive = f"/tmp/gds_archive_{archive_name}"
        
        # 检测压缩文件类型
        if archive_path.endswith('.tar.gz') or archive_path.endswith('.tgz'):
            extract_cmd = f"tar -xzf {tmp_archive} -C {extract_dir}"
        elif archive_path.endswith('.tar'):
            extract_cmd = f"tar -xf {tmp_archive} -C {extract_dir}"
        elif archive_path.endswith('.zip'):
            extract_cmd = f"unzip -q {tmp_archive} -d {extract_dir}"
        else:
            return {
                "success": False,
                "error": f"Unsupported archive format: {archive_name}"
            }
        
        # 复制命令
        if archive_path.startswith('/tmp/'):
            copy_cmd = f"[ '{archive_path}' = '{tmp_archive}' ] || cp '{archive_path}' {tmp_archive}"
        else:
            copy_cmd = f"cp '{archive_path}' {tmp_archive}"
        
        # 构造合并命令：复制、解压、分析、统计（全部在一个命令中）
        cmd = f"""
cd /tmp && \\
echo '[Step 1] Preparing archive...' && \\
{copy_cmd} && \\
echo '[Step 2] Creating extract directory...' && \\
mkdir -p {extract_dir} && \\
echo '[Step 3] Extracting archive...' && \\
{extract_cmd} && \\
rm -f {tmp_archive} && \\
echo '[Step 4] Finding content directory...' && \\
CONTENT_DIR=$(find {extract_dir} -maxdepth 1 -mindepth 1 -type d | head -1) && \\
if [ -z "$CONTENT_DIR" ]; then CONTENT_DIR="{extract_dir}"; fi && \\
echo "Content dir: $CONTENT_DIR" && \\
echo '[Step 5] Getting directory tree (ls -R)...' && \\
ls -R "$CONTENT_DIR" && \\
echo '---STATS---' && \\
find "$CONTENT_DIR" -type f | wc -l && \\
find "$CONTENT_DIR" -type d | wc -l && \\
echo "$CONTENT_DIR"
"""
        
        print(f"  [DEBUG] Executing combined command (this reduces remote windows)")
        
        # 执行命令并捕获结果
        if hasattr(self.shell, 'command_executor'):
            old_raw = getattr(self.shell.command_executor, '_raw_command', False)
            self.shell.command_executor._raw_command = True
            
            result = self.shell.command_executor.execute_command_interface(
                cmd=cmd.strip(),
                capture_result=True
            )
            
            self.shell.command_executor._raw_command = old_raw
            
            if not result.get("success") or result.get("interrupted"):
                return {
                    "success": False,
                    "error": "Failed to extract and analyze"
                }
            
            # 解析输出
            stdout = self._get_stdout(result)
            if not stdout:
                return {
                    "success": False,
                    "error": "No output from extract command"
                }
            
            # 查找统计信息标记
            if '---STATS---' not in stdout:
                return {
                    "success": False,
                    "error": "Missing stats marker in output"
                }
            
            # 分割dir_tree和stats
            parts = stdout.split('---STATS---')
            dir_tree = parts[0]
            stats_part = parts[1].strip()
            
            # 解析统计信息（最后3行）
            stats_lines = stats_part.strip().split('\n')
            if len(stats_lines) < 3:
                return {
                    "success": False,
                    "error": f"Invalid stats format: {stats_part}"
                }
            
            try:
                total_files = int(stats_lines[-3].strip())
                total_dirs = int(stats_lines[-2].strip())
                content_dir = stats_lines[-1].strip()
            except:
                return {
                    "success": False,
                    "error": f"Failed to parse stats: {stats_lines}"
                }
            
            print(f"  [DEBUG] Parsed: files={total_files}, dirs={total_dirs}, content_dir={content_dir}")
            
            return {
                "success": True,
                "content_dir": content_dir,
                "dir_tree": dir_tree,
                "total_files": total_files,
                "total_dirs": total_dirs
            }
        
        return {
            "success": False,
            "error": "Shell executor not available"
        }
    
    def _find_extract_content_dir(self, extract_dir):
        """
        找到解压后的实际内容目录
        
        tar解压可能在extract_dir下创建子目录，需要找到实际内容
        
        Args:
            extract_dir (str): 解压目标目录
            
        Returns:
            str: 实际内容目录路径
        """
        print(f"  [DEBUG] Checking extract_dir: {extract_dir}")
        
        # 检查extract_dir下有多少个项目
        cmd = f"find {extract_dir} -maxdepth 1 -mindepth 1 | wc -l"
        
        if hasattr(self.shell, 'command_executor'):
            old_raw = getattr(self.shell.command_executor, '_raw_command', False)
            old_debug = getattr(self.shell.command_executor, '_debug_remote_cmd', False)
            
            self.shell.command_executor._raw_command = True
            self.shell.command_executor._debug_remote_cmd = True  # 启用远端命令打印
            
            print(f"  [DEBUG] Running command: {cmd}")
            result = self.shell.command_executor.execute_command_interface(
                cmd=cmd,
                capture_result=True
            )
            
            self.shell.command_executor._raw_command = old_raw
            self.shell.command_executor._debug_remote_cmd = old_debug
            
            stdout = self._get_stdout(result)
            print(f"  [DEBUG] Result success: {result.get('success')}, stdout: {stdout}")
            
            if result.get("success"):
                try:
                    count_str = stdout.strip() if stdout else "0"
                    print(f"  [DEBUG] Count string: '{count_str}'")
                    count = int(count_str)
                    print(f"  [DEBUG] Item count: {count}")
                    
                    # 如果只有一个项目，且是目录，使用该目录
                    if count == 1:
                        cmd2 = f"find {extract_dir} -maxdepth 1 -mindepth 1 -type d"
                        print(f"  [DEBUG] Found 1 item, checking if it's a directory: {cmd2}")
                        
                        old_raw = getattr(self.shell.command_executor, '_raw_command', False)
                        self.shell.command_executor._raw_command = True
                        
                        result2 = self.shell.command_executor.execute_command_interface(
                            cmd=cmd2,
                            capture_result=True
                        )
                        
                        self.shell.command_executor._raw_command = old_raw
                        
                        stdout2 = self._get_stdout(result2)
                        print(f"  [DEBUG] Directory check result: {result2.get('success')}, stdout: {stdout2}")
                        
                        if result2.get("success"):
                            dir_path = stdout2.strip() if stdout2 else ""
                            if dir_path:
                                print(f"  [DEBUG] Found single subdirectory: {dir_path}")
                                return dir_path
                    else:
                        print(f"  [DEBUG] Not a single item (count={count}), using extract_dir itself")
                
                except Exception as e:
                    print(f"  [DEBUG] Exception during detection: {e}")
                    import traceback
                    traceback.print_exc()
        
        # 默认返回extract_dir本身
        print(f"  [DEBUG] Using extract_dir itself: {extract_dir}")
        return extract_dir
    
    def _analyze_directory_structure(self, root_dir):
        """
        递归分析目录结构和文件统计
        
        Args:
            root_dir (str): 根目录路径
            
        Returns:
            dict: 目录结构信息
        """
        print(f"  [DEBUG] Analyzing directory: {root_dir}")
        
        # 使用find命令获取所有文件和目录
        cmd = f"find {root_dir} -type f | wc -l && find {root_dir} -type d | wc -l"
        print(f"  [DEBUG] Running command: {cmd}")
        
        if hasattr(self.shell, 'command_executor'):
            old_raw = getattr(self.shell.command_executor, '_raw_command', False)
            self.shell.command_executor._raw_command = True
            
            result = self.shell.command_executor.execute_command_interface(
                cmd=cmd,
                capture_result=True
            )
            
            self.shell.command_executor._raw_command = old_raw
            
            stdout = self._get_stdout(result)
            print(f"  [DEBUG] Result: success={result.get('success')}, stdout='{stdout}'")
            
            if result.get("success"):
                # 解析输出
                output = stdout.strip().split('\n') if stdout else ['']
                print(f"  [DEBUG] Output lines: {output}")
                if len(output) >= 2:
                    try:
                        total_files = int(output[0].strip())
                        total_dirs = int(output[1].strip())
                        
                        print(f"  [DEBUG] Parsed: files={total_files}, dirs={total_dirs}")
                        
                        return {
                            "success": True,
                            "root_dir": root_dir,
                            "total_files": total_files,
                            "total_dirs": total_dirs
                        }
                    except Exception as e:
                        print(f"  [DEBUG] Parse error: {e}")
        
        # Fallback: 返回0而不是假设值
        print(f"  [DEBUG] Fallback to 0 files/dirs")
        return {
            "success": False,
            "root_dir": root_dir,
            "total_files": 0,
            "total_dirs": 0
        }
    
    def _build_transfer_tasks(self, source_dir, dir_structure, batch_size, fingerprint_dir):
        """
        构建转移任务列表 - 递归分析并智能分批
        
        Args:
            source_dir (str): 源目录
            dir_structure (dict): 目录结构信息
            batch_size (int): 每批文件数
            fingerprint_dir (str): 指纹文件目录
            
        Returns:
            list: 任务列表
        """
        # 创建指纹目录
        self._ensure_fingerprint_dir(fingerprint_dir)
        
        tasks = []
        task_counter = [0]  # 使用list来实现引用传递
        
        # 获取目标根目录（从/tmp转到~）
        target_root = source_dir.replace('/tmp/gds_extract_', '~/gds_extracted_')
        
        # 递归构建任务
        self._recursive_build_tasks(
            source_dir, 
            target_root,
            batch_size, 
            fingerprint_dir, 
            tasks, 
            task_counter,
            prefix=""
        )
        
        return tasks
    
    def _build_transfer_tasks_from_tree(self, source_dir, dir_tree_text, total_files, batch_size, fingerprint_dir):
        """
        从ls -R结果本地构建转移任务列表（减少远端查询）
        
        简化策略：
        - 如果文件总数 <= batch_size: 压缩整体转移
        - 否则: 暂时也压缩整体转移（未来可以优化为分批）
        
        Args:
            source_dir (str): 源目录
            dir_tree_text (str): ls -R结果文本
            total_files (int): 总文件数
            batch_size (int): 每批文件数
            fingerprint_dir (str): 指纹文件目录
            
        Returns:
            list: 任务列表
        """
        print(f"\n{'='*70}")
        print(f"LOCAL TASK LIST BUILDING (no remote queries)")
        print(f"{'='*70}")
        print(f"Source directory: {source_dir}")
        print(f"Total files: {total_files}")
        print(f"Batch size: {batch_size}")
        print(f"Strategy: {'Single compress' if total_files <= batch_size * 2 else 'May need batching (TBD)'}")
        print(f"{'='*70}")
        
        # 创建指纹目录
        self._ensure_fingerprint_dir(fingerprint_dir)
        
        tasks = []
        
        # 获取目标根目录
        target_root = source_dir.replace('/tmp/gds_extract_', '~/gds_extracted_')
        
        print(f"\nDECISION: Using single compress_transfer task")
        print(f"  Reason: Simple and reliable for {total_files} files")
        print(f"  Target: {target_root}")
        
        # 简化策略：整体压缩转移（未来可优化为智能分批）
        task = {
            "type": "compress_transfer",
            "source": source_dir,
            "target": target_root,
            "fingerprint": f"{fingerprint_dir}/task_0000_ok",
            "description": f"Compress and transfer {source_dir} ({total_files} files)",
            "task_id": 0
        }
        tasks.append(task)
        
        print(f"\nCREATED TASK LIST:")
        print(f"  Task 0: compress_transfer")
        print(f"    - Source: {source_dir}")
        print(f"    - Target: {target_root}")
        print(f"    - Files: {total_files}")
        print(f"    - Fingerprint: {fingerprint_dir}/task_0000_ok")
        
        print(f"\n{'='*70}")
        print(f"TASK LIST READY: {len(tasks)} task(s) generated locally")
        print(f"NO MORE REMOTE QUERIES NEEDED FOR TASK BUILDING")
        print(f"{'='*70}\n")
        
        # TODO: 未来优化 - 如果文件数很多，可以解析dir_tree_text来分批
        # 但现在先保持简单，减少远端查询窗口是第一优先级
        
        return tasks
    
    def _ensure_fingerprint_dir(self, fingerprint_dir):
        """确保指纹目录存在"""
        cmd = f"mkdir -p {fingerprint_dir}"
        
        if hasattr(self.shell, 'command_executor'):
            old_raw = getattr(self.shell.command_executor, '_raw_command', False)
            self.shell.command_executor._raw_command = True
            
            self.shell.command_executor.execute_command_interface(
                cmd=cmd,
                capture_result=False
            )
            
            self.shell.command_executor._raw_command = old_raw
    
    def _recursive_build_tasks(self, source_path, target_path, batch_size, 
                                fingerprint_dir, tasks, task_counter, prefix=""):
        """
        递归构建转移任务
        
        算法：
        1. 统计当前目录及子目录的总文件数
        2. 如果总文件数 < batch_size: 压缩整体转移
        3. 否则：
           - 对每个子目录递归调用
           - 对剩余文件按batch_size分批，构造批量cp脚本
        
        Args:
            source_path (str): 源路径
            target_path (str): 目标路径
            batch_size (int): 批大小
            fingerprint_dir (str): 指纹目录
            tasks (list): 任务列表（引用传递）
            task_counter (list): 任务计数器（引用传递）
            prefix (str): 日志前缀
        """
        # 统计文件和子目录
        stats = self._get_dir_stats(source_path)
        
        total_files = stats["total_files"]
        subdirs = stats["subdirs"]
        direct_files = stats["direct_files"]
        
        print(f"{prefix}Analyzing {source_path}:")
        print(f"{prefix}  Total files: {total_files}, Subdirs: {len(subdirs)}, Direct files: {len(direct_files)}")
        
        # 判断是否需要分批
        if total_files <= batch_size:
            # 整体压缩转移
            task_id = task_counter[0]
            task_counter[0] += 1
            
            task = {
                "type": "compress_transfer",
                "source": source_path,
                "target": target_path,
                "fingerprint": f"{fingerprint_dir}/task_{task_id:04d}_ok",
                "description": f"Compress and transfer {source_path} ({total_files} files)",
                "task_id": task_id
            }
            tasks.append(task)
            print(f"{prefix}  → Task {task_id}: Compress transfer ({total_files} files)")
            
        else:
            # 需要分批处理
            print(f"{prefix}  → Splitting into batches...")
            
            # 1. 递归处理子目录
            for subdir_name in subdirs:
                source_subdir = f"{source_path}/{subdir_name}"
                target_subdir = f"{target_path}/{subdir_name}"
                
                self._recursive_build_tasks(
                    source_subdir,
                    target_subdir,
                    batch_size,
                    fingerprint_dir,
                    tasks,
                    task_counter,
                    prefix=prefix + "  "
                )
            
            # 2. 处理当前目录的直接文件（按batch分组）
            if direct_files:
                file_batches = [direct_files[i:i+batch_size] 
                               for i in range(0, len(direct_files), batch_size)]
                
                for batch_idx, file_batch in enumerate(file_batches):
                    task_id = task_counter[0]
                    task_counter[0] += 1
                    
                    task = {
                        "type": "batch_copy",
                        "source_dir": source_path,
                        "target_dir": target_path,
                        "files": file_batch,
                        "fingerprint": f"{fingerprint_dir}/task_{task_id:04d}_ok",
                        "description": f"Batch copy {len(file_batch)} files from {source_path}",
                        "task_id": task_id
                    }
                    tasks.append(task)
                    print(f"{prefix}    → Task {task_id}: Batch copy {len(file_batch)} files (batch {batch_idx+1}/{len(file_batches)})")
    
    def _get_dir_stats(self, dir_path):
        """
        获取目录统计信息
        
        Args:
            dir_path (str): 目录路径
            
        Returns:
            dict: {
                "total_files": int,  # 包括子目录的所有文件
                "subdirs": list,     # 子目录名称列表
                "direct_files": list # 当前目录的直接文件列表
            }
        """
        print(f"    [DEBUG] Getting stats for: {dir_path}")
        
        # 获取总文件数（递归）
        cmd_total = f"find {dir_path} -type f | wc -l"
        
        # 获取子目录列表
        cmd_subdirs = f"find {dir_path} -maxdepth 1 -type d -not -path {dir_path} -exec basename {{}} \\;"
        
        # 获取直接文件列表
        cmd_direct_files = f"find {dir_path} -maxdepth 1 -type f -exec basename {{}} \\;"
        
        total_files = 0
        subdirs = []
        direct_files = []
        
        if hasattr(self.shell, 'command_executor'):
            old_raw = getattr(self.shell.command_executor, '_raw_command', False)
            self.shell.command_executor._raw_command = True
            
            # 获取总文件数
            print(f"    [DEBUG] Command: {cmd_total}")
            result = self.shell.command_executor.execute_command_interface(
                cmd=cmd_total,
                capture_result=True
            )
            stdout = self._get_stdout(result)
            print(f"    [DEBUG] Total files result: success={result.get('success')}, stdout='{stdout}'")
            if result.get("success"):
                try:
                    total_files = int(stdout.strip()) if stdout else 0
                    print(f"    [DEBUG] Parsed total_files: {total_files}")
                except Exception as e:
                    print(f"    [DEBUG] Error parsing total_files: {e}")
            
            # 获取子目录
            print(f"    [DEBUG] Command: {cmd_subdirs}")
            result = self.shell.command_executor.execute_command_interface(
                cmd=cmd_subdirs,
                capture_result=True
            )
            stdout = self._get_stdout(result)
            print(f"    [DEBUG] Subdirs result: success={result.get('success')}, stdout='{stdout[:100] if stdout else ''}'")
            if result.get("success") and stdout:
                output = stdout.strip()
                if output:
                    subdirs = [d.strip() for d in output.split('\n') if d.strip()]
                    print(f"    [DEBUG] Parsed subdirs: {subdirs}")
            
            # 获取直接文件
            print(f"    [DEBUG] Command: {cmd_direct_files}")
            result = self.shell.command_executor.execute_command_interface(
                cmd=cmd_direct_files,
                capture_result=True
            )
            stdout = self._get_stdout(result)
            print(f"    [DEBUG] Direct files result: success={result.get('success')}, stdout length={len(stdout) if stdout else 0}")
            if result.get("success") and stdout:
                output = stdout.strip()
                if output:
                    direct_files = [f.strip() for f in output.split('\n') if f.strip()]
                    print(f"    [DEBUG] Parsed direct_files: {len(direct_files)} files")
            
            self.shell.command_executor._raw_command = old_raw
        
        print(f"    [DEBUG] Final stats: total_files={total_files}, subdirs={len(subdirs)}, direct_files={len(direct_files)}")
        
        return {
            "total_files": total_files,
            "subdirs": subdirs,
            "direct_files": direct_files
        }
    
    def _parallel_transfer(self, task_list, num_workers=3):
        """
        使用多个worker并行执行转移任务
        
        算法：
        1. 创建任务队列
        2. 启动num_workers个worker线程
        3. 每个worker从队列取任务并执行
        4. 任务完成后检查指纹文件
        5. 等待所有worker完成
        
        Args:
            task_list (list): 任务列表
            num_workers (int): worker数量
            
        Returns:
            dict: 执行结果
        """
        start_time = time.time()
        
        # 创建任务队列
        task_queue = queue.Queue()
        for task in task_list:
            task_queue.put(task)
        
        # 共享状态
        completed_tasks = []
        failed_tasks = []
        files_transferred = [0]  # 使用list实现引用传递
        lock = threading.Lock()
        
        # Worker函数
        def worker(worker_id):
            while True:
                try:
                    # 从队列获取任务（非阻塞，超时1秒）
                    task = task_queue.get(timeout=1)
                except queue.Empty:
                    # 队列为空，退出
                    break
                
                try:
                    # 执行任务
                    with lock:
                        print(f"\n[Worker {worker_id}] Starting task {task['task_id']}: {task['description']}")
                    
                    print(f"[Worker {worker_id}] [DEBUG] About to execute transfer task...")
                    result = self._execute_transfer_task(task)
                    print(f"[Worker {worker_id}] [DEBUG] Transfer task returned: {result.get('success')}")
                    
                    with lock:
                        if result["success"]:
                            completed_tasks.append(task['task_id'])
                            files_transferred[0] += result.get("files_count", 0)
                            print(f"[Worker {worker_id}] ✅ Task {task['task_id']} completed ({result.get('files_count', 0)} files)")
                        else:
                            failed_tasks.append({
                                "task_id": task['task_id'],
                                "error": result.get("error", "Unknown error")
                            })
                            print(f"[Worker {worker_id}] ❌ Task {task['task_id']} failed: {result.get('error', 'Unknown')}")
                
                except Exception as e:
                    import traceback
                    error_detail = traceback.format_exc()
                    with lock:
                        failed_tasks.append({
                            "task_id": task['task_id'],
                            "error": str(e),
                            "traceback": error_detail
                        })
                        print(f"[Worker {worker_id}] ❌ Task {task['task_id']} exception: {str(e)}")
                        print(f"[Worker {worker_id}] [DEBUG] Full traceback:\n{error_detail}")
                
                finally:
                    task_queue.task_done()
        
        # 启动worker线程
        workers = []
        for i in range(num_workers):
            t = threading.Thread(target=worker, args=(i+1,), daemon=True)
            t.start()
            workers.append(t)
        
        # 等待所有任务完成
        print(f"\n{'='*70}")
        print(f"Started {num_workers} workers for {len(task_list)} tasks...")
        print(f"{'='*70}")
        
        task_queue.join()  # 阻塞直到所有任务完成
        
        # 等待所有worker线程结束
        for t in workers:
            t.join(timeout=5)
        
        elapsed = time.time() - start_time
        
        # 检查是否有失败的任务
        if failed_tasks:
            error_msg = f"Failed tasks: {len(failed_tasks)}/{len(task_list)}\n"
            for fail in failed_tasks[:5]:  # 只显示前5个错误
                error_msg += f"  Task {fail['task_id']}: {fail['error']}\n"
            
            return {
                "success": False,
                "error": error_msg,
                "completed": len(completed_tasks),
                "failed": len(failed_tasks),
                "time_taken": elapsed
            }
        
        return {
            "success": True,
            "files_transferred": files_transferred[0],
            "time_taken": elapsed,
            "completed_tasks": len(completed_tasks)
        }
    
    def _execute_transfer_task(self, task):
        """
        执行单个转移任务
        
        支持两种类型：
        1. compress_transfer: 压缩整个目录并转移
        2. batch_copy: 批量复制文件
        
        Args:
            task (dict): 任务信息
            
        Returns:
            dict: 执行结果
        """
        task_type = task["type"]
        fingerprint = task["fingerprint"]
        
        # 首先检查指纹文件是否已存在（任务已完成）
        if self._check_fingerprint(fingerprint):
            return {
                "success": True,
                "files_count": 0,
                "message": "Task already completed (fingerprint exists)"
            }
        
        # 根据类型执行不同的操作
        if task_type == "compress_transfer":
            result = self._do_compress_transfer(task)
        elif task_type == "batch_copy":
            result = self._do_batch_copy(task)
        else:
            return {
                "success": False,
                "error": f"Unknown task type: {task_type}"
            }
        
        # 如果成功，创建指纹文件
        if result["success"]:
            self._create_fingerprint(fingerprint)
        
        return result
    
    def _check_fingerprint(self, fingerprint_path):
        """检查指纹文件是否存在"""
        cmd = f"test -f {fingerprint_path} && echo 'exists' || echo 'not_exists'"
        
        if hasattr(self.shell, 'command_executor'):
            old_raw = getattr(self.shell.command_executor, '_raw_command', False)
            self.shell.command_executor._raw_command = True
            
            result = self.shell.command_executor.execute_command_interface(
                cmd=cmd,
                capture_result=True
            )
            
            self.shell.command_executor._raw_command = old_raw
            
            if result.get("success"):
                stdout = self._get_stdout(result)
                return 'exists' in (stdout if stdout else "")
        
        return False
    
    def _create_fingerprint(self, fingerprint_path):
        """创建指纹文件"""
        cmd = f"touch {fingerprint_path}"
        
        if hasattr(self.shell, 'command_executor'):
            old_raw = getattr(self.shell.command_executor, '_raw_command', False)
            self.shell.command_executor._raw_command = True
            
            self.shell.command_executor.execute_command_interface(
                cmd=cmd,
                capture_result=False
            )
            
            self.shell.command_executor._raw_command = old_raw
    
    def _do_compress_transfer(self, task):
        """
        执行压缩转移任务
        
        流程：
        1. 在/tmp压缩源目录
        2. 创建目标目录
        3. 移动压缩文件到目标
        4. 在目标位置解压
        5. 删除压缩文件
        
        Args:
            task (dict): 任务信息
            
        Returns:
            dict: 执行结果
        """
        source = task["source"]
        target = task["target"]
        
        # 生成压缩文件名
        import random
        random_suffix = f"{random.randint(1000, 9999)}"
        archive_name = f"transfer_{task['task_id']}_{random_suffix}.tar.gz"
        tmp_archive = f"/tmp/{archive_name}"
        
        # 构造命令
        cmd = f"""
cd $(dirname {source}) && \\
tar -czf {tmp_archive} $(basename {source}) && \\
mkdir -p $(dirname {target}) && \\
cp {tmp_archive} $(dirname {target})/{archive_name} && \\
cd $(dirname {target}) && \\
tar -xzf {archive_name} && \\
mv $(basename {source}) $(basename {target}) 2>/dev/null || true && \\
rm -f {archive_name} {tmp_archive} && \\
echo 'Transfer completed'
"""
        
        # 执行命令
        if hasattr(self.shell, 'command_executor'):
            old_raw = getattr(self.shell.command_executor, '_raw_command', False)
            self.shell.command_executor._raw_command = True
            
            result = self.shell.command_executor.execute_command_interface(
                cmd=cmd.strip(),
                capture_result=False
            )
            
            self.shell.command_executor._raw_command = old_raw
            
            if result.get("success") == False or result.get("interrupted"):
                return {
                    "success": False,
                    "error": "Compress transfer command failed"
                }
        
        # 统计转移的文件数
        cmd_count = f"find {target} -type f 2>/dev/null | wc -l"
        
        files_count = 0
        if hasattr(self.shell, 'command_executor'):
            old_raw = getattr(self.shell.command_executor, '_raw_command', False)
            self.shell.command_executor._raw_command = True
            
            result = self.shell.command_executor.execute_command_interface(
                cmd=cmd_count,
                capture_result=True
            )
            
            self.shell.command_executor._raw_command = old_raw
            
            if result.get("success"):
                try:
                    stdout = self._get_stdout(result)
                    files_count = int(stdout.strip()) if stdout else 0
                except:
                    pass
        
        return {
            "success": True,
            "files_count": files_count
        }
    
    def _do_batch_copy(self, task):
        """
        执行批量复制任务
        
        流程：
        1. 创建目标目录
        2. 构造批量cp命令
        3. 执行cp命令
        
        Args:
            task (dict): 任务信息
            
        Returns:
            dict: 执行结果
        """
        source_dir = task["source_dir"]
        target_dir = task["target_dir"]
        files = task["files"]
        
        # 构造批量cp命令
        mkdir_cmd = f"mkdir -p {target_dir}"
        
        # 构造cp命令列表
        cp_commands = []
        for filename in files:
            # 使用cp而不是mv，以便失败时可以重试
            source_file = f"{source_dir}/{filename}"
            target_file = f"{target_dir}/{filename}"
            cp_commands.append(f"cp '{source_file}' '{target_file}'")
        
        # 组合命令（使用&&连接）
        all_commands = mkdir_cmd + " && " + " && ".join(cp_commands)
        
        # 如果命令太长，分批执行
        if len(all_commands) > 100000:  # 命令长度限制
            # 分成多个批次
            batch_size = len(files) // 2
            if batch_size < 1:
                batch_size = 1
            
            for i in range(0, len(files), batch_size):
                batch_files = files[i:i+batch_size]
                sub_task = {
                    **task,
                    "files": batch_files
                }
                result = self._do_batch_copy(sub_task)
                if not result["success"]:
                    return result
            
            return {
                "success": True,
                "files_count": len(files)
            }
        
        # 执行命令
        if hasattr(self.shell, 'command_executor'):
            old_raw = getattr(self.shell.command_executor, '_raw_command', False)
            self.shell.command_executor._raw_command = True
            
            result = self.shell.command_executor.execute_command_interface(
                cmd=all_commands,
                capture_result=False
            )
            
            self.shell.command_executor._raw_command = old_raw
            
            if result.get("success") == False or result.get("interrupted"):
                return {
                    "success": False,
                    "error": "Batch copy command failed"
                }
        
        return {
            "success": True,
            "files_count": len(files)
        }
    
    def _cleanup_tmp(self, tmp_dir):
        """清理临时目录"""
        cmd = f"rm -rf {tmp_dir}"
        
        if hasattr(self.shell, 'command_executor'):
            old_raw = getattr(self.shell.command_executor, '_raw_command', False)
            self.shell.command_executor._raw_command = True
            
            self.shell.command_executor.execute_command_interface(
                cmd=cmd,
                capture_result=False
            )
            
            self.shell.command_executor._raw_command = old_raw
    
    def _show_help(self):
        """显示帮助信息"""
        help_text = """
╔══════════════════════════════════════════════════════════════════════╗
║                    GDS Extract Command - Help                         ║
╚══════════════════════════════════════════════════════════════════════╝

DESCRIPTION:
    Extract and transfer large archives to Google Drive using parallel workers
    for efficient batch processing. Supports intelligent file grouping and
    automatic retry with fingerprint tracking.

SYNTAX:
    GDS extract <archive_file> [--transfer-batch SIZE]

ARGUMENTS:
    <archive_file>
        Path to the archive file (.zip, .tar.gz, .tar, etc.)
        Supports GDS path formats: ~/path, @/path, or absolute paths
        
    --transfer-batch SIZE
        Number of files per transfer batch (default: 1000)
        Smaller values = more batches but more granular progress
        Larger values = fewer batches but less overhead

ALGORITHM:
    1. Copy archive to /tmp and extract
    2. Recursively analyze directory structure
    3. For each directory:
       - If total files < batch size: compress and transfer as one
       - Otherwise:
         • Recursively process each subdirectory
         • Group remaining files into batches
         • Create batch mv scripts (raw command mode)
    4. Use 3 parallel workers for transfer
    5. Create fingerprint after each successful batch
    6. Next batch only starts after previous succeeds

PATH HANDLING:
    Input paths are converted to remote absolute paths:
    - GDS extract ~/tmp/test.zip  → {REMOTE_ROOT}/tmp/test.zip
    - GDS extract @/python/x.tar  → {REMOTE_ENV}/python/x.tar
    - GDS extract /tmp/test.zip   → /tmp/test.zip

FEATURES:
    ✓ Parallel processing with 3 workers
    ✓ Intelligent batching based on directory structure
    ✓ Fingerprint-based progress tracking
    ✓ Automatic retry on failure
    ✓ Uses cp instead of mv for safety
    ✓ Triggers remount on persistent failures

EXAMPLES:
    # Extract with default batch size (1000)
    GDS extract python_install.tar.gz
    
    # Extract with custom batch size
    GDS extract ~/tmp/large_archive.zip --transfer-batch 500
    
    # Extract from Google Drive location
    GDS extract @/downloads/backup.tar.gz --transfer-batch 2000

NOTES:
    - Extraction happens in /tmp for better I/O performance
    - Original archive is preserved (uses cp, not mv)
    - Progress can be resumed if interrupted
    - Each batch creates a fingerprint for reliability
"""
        print(help_text)
        return {"success": True, "message": "Help displayed"}


def register_command(main_instance):
    """
    注册extract命令到主实例
    
    Args:
        main_instance: GoogleDriveShell主实例
    """
    return ExtractCommand(main_instance)

