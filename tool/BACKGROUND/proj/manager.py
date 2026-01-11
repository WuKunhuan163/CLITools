import os
import sys
import json
import time
import shlex
import signal
import psutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class ProcessManager:
    """后台进程管理器"""
    
    def __init__(self, max_processes: int = 1000, log_dir: str = "~/tmp/background_cmd_logs"):
        self.max_processes = max_processes
        self.log_dir = Path(os.path.expanduser(log_dir))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 进程状态文件
        self.state_file = self.log_dir / "processes.json"
        self.processes: Dict[str, Dict] = {}
        
        # 加载现有进程状态
        self.load_state()
        
        # 清理已死亡的进程
        self.cleanup_dead_processes()
    
    def load_state(self):
        """从文件加载进程状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.processes = data.get('processes', {})
            except (json.JSONDecodeError, FileNotFoundError):
                self.processes = {}
    
    def save_state(self):
        """保存进程状态到文件"""
        data = {
            'processes': self.processes,
            'last_updated': datetime.now().isoformat()
        }
        with open(self.state_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def cleanup_dead_processes(self):
        """更新已死亡进程的状态，但保留记录"""
        updated = False
        for pid_str, proc_info in self.processes.items():
            try:
                pid = int(pid_str)
                # 检查进程是否还存在且创建时间匹配
                if psutil.pid_exists(pid):
                    proc = psutil.Process(pid)
                    if abs(proc.create_time() - proc_info['start_time']) < 1.0:
                        continue  # 进程仍然有效
                
                # 进程已死亡或PID被重用，标记为已完成但保留记录
                if proc_info.get('status') != 'completed':
                    proc_info['status'] = 'completed'
                    proc_info['end_time'] = datetime.now().isoformat()
                    updated = True
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
                # 进程已死亡，标记为已完成但保留记录
                if proc_info.get('status') != 'completed':
                    proc_info['status'] = 'completed'
                    proc_info['end_time'] = datetime.now().isoformat()
                    updated = True
        
        if updated:
            self.save_state()
    
    def resolve_shell_aliases(self, command: str, shell: str) -> str:
        """解析shell别名"""
        # 获取命令的第一部分
        try:
            cmd_parts = shlex.split(command)
            if not cmd_parts:
                return command
            
            first_cmd = cmd_parts[0]
            
            # 跳过shell内置命令，这些命令不需要别名解析
            shell_builtins = {
                'cd', 'pwd', 'echo', 'printf', 'test', '[', 'exit', 'return',
                'source', '.', 'exec', 'eval', 'set', 'unset', 'export',
                'alias', 'unalias', 'history', 'jobs', 'bg', 'fg', 'kill',
                'wait', 'read', 'shift', 'getopts', 'break', 'continue',
                'if', 'then', 'else', 'elif', 'fi', 'case', 'esac',
                'for', 'while', 'until', 'do', 'done', 'function'
            }
            
            if first_cmd in shell_builtins:
                return command
            
        except ValueError:
            # 如果shlex.split失败，直接返回原命令
            return command
        
        if shell == 'zsh':
            # 使用交互式zsh来解析别名，先尝试alias命令，再尝试which
            resolve_cmd = f'zsh -i -c "alias {shlex.quote(first_cmd)} 2>/dev/null | cut -d= -f2- | tr -d \"\\047\" || which {shlex.quote(first_cmd)} 2>/dev/null || echo {shlex.quote(first_cmd)}"'
        elif shell == 'bash':
            # 使用交互式bash来解析别名，先尝试alias命令，再尝试which
            resolve_cmd = f'bash -i -c "alias {shlex.quote(first_cmd)} 2>/dev/null | cut -d= -f2- | tr -d \"\\047\" || which {shlex.quote(first_cmd)} 2>/dev/null || echo {shlex.quote(first_cmd)}"'
        else:
            return command
        
        try:
            result = subprocess.run(resolve_cmd, shell=True, capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                resolved_cmd = result.stdout.strip()
                
                # 检查resolved_cmd是否包含"built-in"等字样，如果是则跳过替换
                if 'built-in' in resolved_cmd.lower() or 'shell function' in resolved_cmd.lower():
                    return command
                
                # 处理别名替换
                if resolved_cmd != first_cmd:
                    # 如果是路径形式的命令，直接替换第一个参数
                    if resolved_cmd.startswith('/') or resolved_cmd.startswith('./'):
                        cmd_parts[0] = resolved_cmd
                        return ' '.join(shlex.quote(part) for part in cmd_parts)
                    # 如果是别名（包含空格），替换整个命令的第一部分
                    elif ' ' in resolved_cmd:
                        # 解析别名命令
                        try:
                            alias_parts = shlex.split(resolved_cmd)
                            # 用别名替换原命令的第一部分，保留原命令的其他参数
                            new_cmd_parts = alias_parts + cmd_parts[1:]
                            # 不要对整个命令进行quote，而是直接拼接
                            return ' '.join(new_cmd_parts)
                        except ValueError:
                            # 如果别名解析失败，回退到原命令
                            return command
                    
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass
        
        return command
    
    def create_process(self, command: str, shell: str = 'zsh', 
                      resolve_aliases: bool = True) -> Optional[Tuple[int, str]]:
        """创建后台进程"""
        
        # 检查进程数量限制
        if len(self.processes) >= self.max_processes:
            print(f"Error: Maximum process limit reached ({self.max_processes})")
            return None
        
        # 清理死亡进程
        self.cleanup_dead_processes()
        
        # 解析别名
        if resolve_aliases:
            command = self.resolve_shell_aliases(command, shell)
        
        # 创建日志文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        log_filename = f"bg_cmd_{timestamp}.log"
        log_file = self.log_dir / log_filename
        
        try:
            # 根据shell类型创建进程
            if shell == 'zsh':
                shell_cmd = ['zsh', '-c', command]
            elif shell == 'bash':
                shell_cmd = ['bash', '-c', command]
            else:
                print(f"Error: Unsupported shell type: {shell}")
                return None
            
            # 创建新会话组，避免信号传播
            with open(log_file, 'w') as log_f:
                process = subprocess.Popen(
                    shell_cmd,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    # preexec_fn=os.setsid is deprecated, using start_new_session=True instead
                    start_new_session=True,
                    cwd=os.getcwd(),
                    env=os.environ.copy()
                )
            
            # 获取进程信息
            psutil_proc = psutil.Process(process.pid)
            start_time = psutil_proc.create_time()
            
            # 记录进程信息
            self.processes[str(process.pid)] = {
                'command': command,
                'shell': shell,
                'start_time': start_time,
                'log_file': str(log_file),
                'cwd': os.getcwd(),
                'created_at': datetime.now().isoformat(),
                'status': 'running'  # 初始状态为运行中
            }
            
            # 保存状态
            self.save_state()
            
            return process.pid, str(log_file)
            
        except Exception as e:
            print(f"Error: Failed to create process - {e}")
            # 清理可能创建的空日志文件
            if log_file.exists() and log_file.stat().st_size == 0:
                log_file.unlink(missing_ok=True)
            return None
    
    def list_processes(self) -> List[Dict]:
        """列出所有进程（包括已完成的）"""
        self.cleanup_dead_processes()
        
        all_processes = []
        for pid_str, proc_info in self.processes.items():
            pid = int(pid_str)
            
            # 如果进程已标记为完成，直接使用保存的信息
            if proc_info.get('status') == 'completed':
                start_time = datetime.fromtimestamp(proc_info['start_time'])
                end_time_str = proc_info.get('end_time')
                if end_time_str:
                    end_time = datetime.fromisoformat(end_time_str)
                    runtime = end_time - start_time
                else:
                    runtime = datetime.now() - start_time
                
                all_processes.append({
                    'pid': pid,
                    'command': proc_info['command'],
                    'shell': proc_info['shell'],
                    'status': 'completed',
                    'cpu_percent': 0.0,
                    'memory_mb': 0.0,
                    'runtime': str(runtime).split('.')[0],  # 去掉微秒
                    'log_file': proc_info['log_file'],
                    'cwd': proc_info['cwd']
                })
                continue
            
            try:
                proc = psutil.Process(pid)
                
                # 获取当前状态
                status = proc.status()
                cpu_percent = proc.cpu_percent()
                memory_mb = proc.memory_info().rss / (1024 * 1024)
                
                # 计算运行时间
                start_time = datetime.fromtimestamp(proc_info['start_time'])
                runtime = datetime.now() - start_time
                
                all_processes.append({
                    'pid': pid,
                    'command': proc_info['command'],
                    'shell': proc_info['shell'],
                    'status': status,
                    'cpu_percent': cpu_percent,
                    'memory_mb': memory_mb,
                    'runtime': str(runtime).split('.')[0],  # 去掉微秒
                    'log_file': proc_info['log_file'],
                    'cwd': proc_info['cwd']
                })
                
            except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
                # 进程不存在，标记为完成
                proc_info['status'] = 'completed'
                proc_info['end_time'] = datetime.now().isoformat()
                self.save_state()
                
                start_time = datetime.fromtimestamp(proc_info['start_time'])
                runtime = datetime.now() - start_time
                
                all_processes.append({
                    'pid': pid,
                    'command': proc_info['command'],
                    'shell': proc_info['shell'],
                    'status': 'completed',
                    'cpu_percent': 0.0,
                    'memory_mb': 0.0,
                    'runtime': str(runtime).split('.')[0],  # 去掉微秒
                    'log_file': proc_info['log_file'],
                    'cwd': proc_info['cwd']
                })
        
        return all_processes
    
    def kill_process(self, pid: int, force: bool = False) -> bool:
        """终止指定进程"""
        pid_str = str(pid)
        
        if pid_str not in self.processes:
            print(f"Error: Process {pid} not in managed list")
            return False
        
        try:
            proc = psutil.Process(pid)
            
            if force:
                proc.kill()  # SIGKILL
                signal_type = "SIGKILL"
            else:
                proc.terminate()  # SIGTERM
                signal_type = "SIGTERM"
            
            # 等待进程结束
            try:
                proc.wait(timeout=5)
            except psutil.TimeoutExpired:
                if not force:
                    proc.kill()
                    proc.wait(timeout=3)
            
            # 从管理列表中移除
            del self.processes[pid_str]
            self.save_state()
            
            return True
            
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            # 从管理列表中移除（进程可能已经死亡）
            if pid_str in self.processes:
                del self.processes[pid_str]
                self.save_state()
            return False
    
    def cleanup_all(self) -> int:
        """清理所有管理的进程"""
        pids = list(self.processes.keys())
        
        for pid_str in pids:
            pid = int(pid_str)
            proc_info = self.processes[pid_str]
            
            # 只对仍在运行的进程尝试终止
            if proc_info.get('status') != 'completed':
                try:
                    if psutil.pid_exists(pid):
                        proc = psutil.Process(pid)
                        # 检查进程是否匹配（防止PID重用）
                        if abs(proc.create_time() - proc_info['start_time']) < 1.0:
                            self.kill_process(pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass  # 进程已经不存在，无需终止
            
            # 删除记录
            if pid_str in self.processes:
                del self.processes[pid_str]
        
        # 保存状态
        self.save_state()
        return len(pids)  # 返回清理的总记录数
    
    def get_process_status(self, pid: int) -> Optional[Dict]:
        """获取指定进程的详细状态"""
        pid_str = str(pid)
        if pid_str not in self.processes:
            return None
        
        proc_info = self.processes[pid_str]
        
        # 如果进程已标记为完成，直接返回完成状态
        if proc_info.get('status') == 'completed':
            start_time = datetime.fromtimestamp(proc_info['start_time'])
            end_time_str = proc_info.get('end_time')
            if end_time_str:
                end_time = datetime.fromisoformat(end_time_str)
                runtime = end_time - start_time
            else:
                runtime = datetime.now() - start_time
            
            return {
                'pid': pid,
                'command': proc_info['command'],
                'shell': proc_info['shell'],
                'status': 'completed',
                'cpu_percent': 0.0,
                'memory_mb': 0.0,
                'runtime': str(runtime).split('.')[0],  # 去掉微秒
                'start_time': start_time.isoformat(),
                'end_time': end_time_str,
                'log_file': proc_info['log_file'],
                'cwd': proc_info['cwd'],
                'is_running': False
            }
        
        try:
            proc = psutil.Process(pid)
            
            # 检查进程是否匹配（防止PID重用）
            if abs(proc.create_time() - proc_info['start_time']) > 1.0:
                # PID被重用，标记为完成
                proc_info['status'] = 'completed'
                proc_info['end_time'] = datetime.now().isoformat()
                self.save_state()
                return self.get_process_status(pid)  # 递归调用返回完成状态
            
            # 获取当前状态
            status = proc.status()
            cpu_percent = proc.cpu_percent()
            memory_mb = proc.memory_info().rss / (1024 * 1024)
            
            # 计算运行时间
            start_time = datetime.fromtimestamp(proc_info['start_time'])
            runtime = datetime.now() - start_time
            
            return {
                'pid': pid,
                'command': proc_info['command'],
                'shell': proc_info['shell'],
                'status': status,
                'cpu_percent': cpu_percent,
                'memory_mb': memory_mb,
                'runtime': str(runtime).split('.')[0],  # 去掉微秒
                'start_time': start_time.isoformat(),
                'log_file': proc_info['log_file'],
                'cwd': proc_info['cwd'],
                'is_running': status in ['running', 'sleeping']
            }
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # 进程已死亡，标记为完成
            proc_info['status'] = 'completed'
            proc_info['end_time'] = datetime.now().isoformat()
            self.save_state()
            return self.get_process_status(pid)  # 递归调用返回完成状态
    
    def get_process_result(self, pid: int) -> Optional[str]:
        """获取进程的执行结果（从日志文件）"""
        status = self.get_process_status(pid)
        if not status:
            return None
        
        log_file = Path(status['log_file'])
        if not log_file.exists():
            return "Log file not found"
        
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                if not content.strip():
                    if status['is_running']:
                        return "Process is still running, no output yet"
                    else:
                        return "Process completed with no output"
                return content
        except Exception as e:
            return f"Error reading log file: {e}"
    
    def get_process_log(self, pid: int) -> Optional[str]:
        """获取进程的日志内容（与get_process_result相同，但语义不同）"""
        return self.get_process_result(pid)

