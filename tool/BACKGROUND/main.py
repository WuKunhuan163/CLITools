#!/usr/bin/env python3
import os
import sys
import json
import argparse
from pathlib import Path

# Add the directory containing 'proj' to sys.path
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir))

# Localization setup
project_root = current_dir.parent.parent
python_tool_dir = project_root / "tool" / "PYTHON"
if python_tool_dir.exists():
    sys.path.insert(0, str(python_tool_dir))

try:
    from proj.language_utils import get_translation
except ImportError:
    def get_translation(d, k, default): return default

# Restore sys.path order for local imports
if python_tool_dir.exists():
    sys.path.pop(0)

TOOL_PROJ_DIR = current_dir / "proj"

def _(key, default):
    return get_translation(str(TOOL_PROJ_DIR), key, default)

from proj.manager import ProcessManager

def main():
    """主函数"""
    print(f"DEBUG: BACKGROUND main running with sys.path: {sys.path}")
    parser = argparse.ArgumentParser(
        description='BACKGROUND - 安全的后台进程管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  BACKGROUND "sleep 60"                    # 使用默认zsh运行命令
  BACKGROUND "ls -la" --shell bash         # 使用bash运行命令
  BACKGROUND --list                        # 列出所有活跃进程
  BACKGROUND --kill 12345                  # 终止指定进程
  BACKGROUND --cleanup                     # 清理所有进程
  BACKGROUND --wait 12345                  # 等待进程结束
  BACKGROUND --max-processes 500           # 设置最大进程数
        """
    )
    
    # 位置参数
    parser.add_argument('command_args', nargs=argparse.REMAINDER, help='要在后台执行的命令')
    
    # 可选参数
    parser.add_argument('--shell', choices=['zsh', 'bash'], default='zsh',
                       help='使用的shell类型 (默认: zsh)')
    parser.add_argument('--max-processes', type=int, default=1000,
                       help='最大同时运行进程数 (默认: 1000)')
    parser.add_argument('--log-dir', default='~/tmp/background_logs',
                       help='日志文件目录 (默认: ~/tmp/background_logs)')
    parser.add_argument('--no-alias', action='store_true',
                       help='不解析shell别名')
    
    # 操作参数
    parser.add_argument('--list', action='store_true',
                       help='列出所有活跃的后台进程')
    parser.add_argument('--status', nargs='?', const='all', metavar='PID',
                       help='查询指定PID进程的状态，无参数时列出所有进程（等同于--list）')
    parser.add_argument('--result', type=int, metavar='PID',
                       help='获取指定PID进程的执行结果')
    parser.add_argument('--log', type=int, metavar='PID',
                       help='查看指定PID进程的日志')
    parser.add_argument('--kill', type=int, metavar='PID',
                       help='终止指定PID的进程')
    parser.add_argument('--force-kill', type=int, metavar='PID',
                       help='强制终止指定PID的进程')
    parser.add_argument('--cleanup', action='store_true',
                       help='清理所有管理的后台进程')
    parser.add_argument('--wait', type=int, metavar='PID',
                       help='等待指定PID的进程结束')
    
    # JSON输出
    parser.add_argument('--json', action='store_true',
                       help='以JSON格式输出结果')
    
    args, unknown_args = parser.parse_known_args()
    
    # 创建进程管理器
    manager = ProcessManager(
        max_processes=args.max_processes,
        log_dir=args.log_dir
    )
    
    try:
        if args.list:
            processes = manager.list_processes()
            if args.json:
                print(json.dumps({'success': True, 'processes': processes, 'total_count': len(processes)}, indent=2))
            else:
                if processes:
                    print("\n" + _("active_processes", "Active processes ({count}):").format(count=len(processes)))
                    print("-" * 80)
                    for proc in processes:
                        cmd_display = proc['command'][:20] + "..." if len(proc['command']) > 20 else proc['command']
                        print(f"PID: {proc['pid']:<8} | Status: {proc['status']:<10} | Runtime: {proc['runtime']:<10} | Command: {cmd_display}")
                    print("-" * 80)
                else:
                    print(_("no_active_processes", "No active processes"))
        
        elif args.kill is not None:
            success = manager.kill_process(args.kill)
            if args.json:
                print(json.dumps({'success': success, 'action': 'kill', 'pid': args.kill}))
            elif success:
                print(_("process_terminated", "Process {pid} terminated").format(pid=args.kill))
        
        elif args.force_kill is not None:
            success = manager.kill_process(args.force_kill, force=True)
            if args.json:
                print(json.dumps({'success': success, 'action': 'force_kill', 'pid': args.force_kill}))
            elif success:
                print(_("process_force_killed", "Process {pid} force-killed").format(pid=args.force_kill))
        
        elif args.status is not None:
            if args.status == 'all':
                processes = manager.list_processes()
                if args.json:
                    print(json.dumps({'success': True, 'action': 'status_all', 'processes': processes, 'total_count': len(processes)}, indent=2))
                else:
                    if processes:
                        print("\n" + _("active_processes", "Active processes ({count}):").format(count=len(processes)))
                        print("-" * 80)
                        for proc in processes:
                            cmd_display = proc['command'][:20] + "..." if len(proc['command']) > 20 else proc['command']
                            print(f"PID: {proc['pid']:<8} | Status: {proc['status']:<10} | Runtime: {proc['runtime']:<10} | Command: {cmd_display}")
                        print("-" * 80)
                    else:
                        print(_("no_active_processes", "No active background processes"))
            else:
                try:
                    pid = int(args.status)
                    status = manager.get_process_status(pid)
                    if status:
                        if args.json:
                            print(json.dumps({'success': True, 'action': 'status', 'status': status}))
                        else:
                            print(f"Process {pid} Status:")
                            print(f"  Command: {status['command']}")
                            print(f"  Status: {status['status']}")
                            print(f"  Runtime: {status['runtime']}")
                            print(f"  Log file: {status['log_file']}")
                    else:
                        if args.json:
                            print(json.dumps({'success': False, 'action': 'status', 'error': f'Process {pid} not found'}))
                        else:
                            print(_("process_not_found", "Error: Process {pid} not found").format(pid=pid))
                        sys.exit(1)
                except ValueError:
                    print(f"Error: Invalid PID: {args.status}")
                    sys.exit(1)
        
        elif args.result is not None:
            result = manager.get_process_result(args.result)
            if result is not None:
                if args.json:
                    print(json.dumps({'success': True, 'action': 'result', 'pid': args.result, 'output': result}))
                else:
                    print(result)
            else:
                if args.json:
                    print(json.dumps({'success': False, 'action': 'result', 'error': f'Process {args.result} not found'}))
                else:
                    print(f"Error: Process {args.result} not found")
                sys.exit(1)
        
        elif args.log is not None:
            log_content = manager.get_process_log(args.log)
            if log_content is not None:
                if args.json:
                    print(json.dumps({'success': True, 'action': 'log', 'pid': args.log, 'content': log_content}))
                else:
                    print(log_content)
            else:
                if args.json:
                    print(json.dumps({'success': False, 'action': 'log', 'error': f'Process {args.log} not found'}))
                else:
                    print(f"Error: Process {args.log} not found")
                sys.exit(1)
        
        elif args.cleanup:
            count = manager.cleanup_all()
            if args.json:
                print(json.dumps({'success': True, 'action': 'cleanup', 'cleaned_count': count}))
            else:
                print(f"Cleaned up {count} process records")
        
        elif args.wait is not None:
            finished = manager.wait_for_process(args.wait)
            if args.json:
                print(json.dumps({'success': finished, 'action': 'wait', 'pid': args.wait}))
            elif finished:
                print(_("wait_finished", "Process {pid} finished").format(pid=args.wait))
            else:
                print(_("wait_timeout", "Timed out waiting for process {pid}").format(pid=args.wait))
        
        elif args.command_args or unknown_args:
            all_args = (args.command_args or []) + (unknown_args or [])
            if all_args:
                full_command = ' '.join(all_args)
                result = manager.create_process(full_command, shell=args.shell, resolve_aliases=not args.no_alias)
                if result:
                    pid, log_file = result
                    if args.json:
                        print(json.dumps({'success': True, 'action': 'create', 'pid': pid, 'log_file': log_file, 'command': full_command}))
                    else:
                        print(_("process_started", "Process started: PID {pid}, Log: {log_file}").format(pid=pid, log_file=log_file))
                else:
                    if args.json:
                        print(json.dumps({'success': False, 'action': 'create', 'error': 'Failed to create process'}))
                    else:
                        print("Error: Failed to create process")
                    sys.exit(1)
            else:
                parser.print_help()
        
        else:
            parser.print_help()
            
    except KeyboardInterrupt:
        print("\nOperation interrupted by user")
        sys.exit(1)
    except Exception as e:
        if args.json:
            print(json.dumps({'success': False, 'error': str(e)}))
        else:
            print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

