#!/usr/bin/env python3
import os
import sys
import json
import argparse
from pathlib import Path

# Use resolve() to get the actual location of the script
current_dir = Path(__file__).resolve().parent
# project_root is two levels up: tool/BACKGROUND -> tool -> root
project_root = current_dir.parent.parent

# Add the directory containing 'proj' to sys.path
sys.path.append(str(current_dir))

# Localization setup
# import shared utils from the shared root proj
try:
    from proj.language_utils import get_translation, get_display_width, truncate_to_display_width
except ImportError:
    def get_translation(d, k, default): return default
    def get_display_width(s): return len(s)
    def truncate_to_display_width(s, w): return s[:w]

TOOL_PROJ_DIR = current_dir / "proj"

def _(key, default):
    return get_translation(str(TOOL_PROJ_DIR), key, default)

from proj.manager import ProcessManager

def main():
    """主函数"""
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
                    
                    # Try to get terminal width
                    try:
                        terminal_width = os.get_terminal_size().columns
                    except (AttributeError, OSError):
                        terminal_width = 80
                    
                    # Translated headers
                    status_label = _("status", "Status")
                    runtime_label = _("runtime", "Runtime")
                    command_label = _("command", "Command")
                    
                    # Column widths - adjust based on terminal width
                    if terminal_width < 50:
                        pid_col_width = 8
                        status_col_width = 8
                        runtime_col_width = 8
                    else:
                        pid_col_width = 12
                        status_col_width = 12
                        runtime_col_width = 12
                    
                    sep_width = 3 # " | "
                    
                    # Calculate available width for command
                    fixed_width = pid_col_width + sep_width + status_col_width + sep_width + runtime_col_width + sep_width
                    
                    if terminal_width > fixed_width + 10:
                        cmd_width = terminal_width - fixed_width
                    elif terminal_width > fixed_width:
                        cmd_width = terminal_width - fixed_width
                    else:
                        # Terminal is extremely narrow, we might have to clip even the fixed columns
                        cmd_width = 0
                    
                    total_table_width = fixed_width + (cmd_width + sep_width if cmd_width > 0 else 0)
                    # For simple display, just use the terminal_width if total is too small
                    total_table_width = min(total_table_width, terminal_width)
                    
                    print("-" * total_table_width)
                    
                    # Manual alignment for localized headers
                    pid_header = "PID: ID"
                    pid_header = truncate_to_display_width(pid_header, pid_col_width)
                    pid_header = pid_header + " " * (pid_col_width - get_display_width(pid_header))
                    
                    status_header = truncate_to_display_width(status_label, status_col_width)
                    status_header = status_header + " " * (status_col_width - get_display_width(status_header))
                    
                    runtime_header = truncate_to_display_width(runtime_label, runtime_col_width)
                    runtime_header = runtime_header + " " * (runtime_col_width - get_display_width(runtime_header))
                    
                    header = f"{pid_header} | {status_header} | {runtime_header}"
                    if cmd_width > 0:
                        header += f" | {command_label}"
                    
                    # Final clipping of the header row
                    print(truncate_to_display_width(header, total_table_width))
                    print("-" * total_table_width)
                    
                    for proc in processes:
                        # Translate status
                        status_val = proc['status']
                        translated_status = status_val
                        if status_val == 'active':
                            translated_status = _("status_active", "active")
                        elif status_val == 'completed':
                            translated_status = _("status_completed", "completed")
                        elif status_val == 'failed':
                            translated_status = _("status_failed", "failed")
                        elif status_val == 'unknown':
                            translated_status = _("status_unknown", "unknown")
                        
                        # Pad PID, translated status and runtime
                        pid_val = f"PID: {proc['pid']}"
                        pid_display = truncate_to_display_width(pid_val, pid_col_width)
                        pid_display = pid_display + " " * (pid_col_width - get_display_width(pid_display))
                        
                        status_display = truncate_to_display_width(translated_status, status_col_width)
                        status_display = status_display + " " * (status_col_width - get_display_width(status_display))
                        
                        runtime_display = truncate_to_display_width(proc['runtime'], runtime_col_width)
                        runtime_display = runtime_display + " " * (runtime_col_width - get_display_width(runtime_display))
                        
                        row = f"{pid_display} | {status_display} | {runtime_display}"
                        if cmd_width > 0:
                            cmd_display = truncate_to_display_width(proc['command'], cmd_width)
                            row += f" | {cmd_display}"
                        
                        # Final clipping of the row
                        print(truncate_to_display_width(row, total_table_width))
                    print("-" * total_table_width)
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
        
        elif args.wait is not None:
            finished = manager.wait_for_process(args.wait)
            if args.json:
                print(json.dumps({'success': finished, 'action': 'wait', 'pid': args.wait}))
            elif finished:
                print(_("wait_finished", "Process {pid} finished").format(pid=args.wait))
            else:
                print(_("wait_timeout", "Timed out waiting for process {pid}").format(pid=args.wait))
        
        elif args.cleanup:
            count = manager.cleanup_all()
            if args.json:
                print(json.dumps({'success': True, 'action': 'cleanup', 'cleaned_count': count}))
            else:
                print(f"Cleaned up {count} process records")
        
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
