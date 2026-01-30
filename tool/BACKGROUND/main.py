#!/usr/bin/env python3
import os
import sys
import json
import argparse
import tempfile
from pathlib import Path

# Use resolve() to get the actual location of the script
current_dir = Path(__file__).resolve().parent
# project_root is two levels up: tool/BACKGROUND -> tool -> root
project_root = current_dir.parent.parent

# Add the directory containing 'proj' to sys.path
sys.path.append(str(current_dir))

# Localization setup
# import shared utils from the shared root logic
try:
    from logic.lang.utils import get_translation
    from logic.utils import get_display_width, truncate_to_display_width, format_table, get_logic_dir
    from logic.config import get_color
except ImportError:
    def get_color(name, default="\033[0m"): return default
    def get_translation(d, k, default): return default
    def get_display_width(s): return len(s)
    def truncate_to_display_width(s, w): return s[:w]
    def format_table(h, r, **kwargs): return "\n".join([" | ".join(h)] + [" | ".join(map(str, row)) for row in r]), None
    def get_logic_dir(d): return d / "logic"

RESET = get_color("RESET", "\033[0m")
GREEN = get_color("GREEN", RESET)
BOLD = get_color("BOLD", RESET)
BLUE = get_color("BLUE", RESET)
RED = get_color("RED", RESET)

TOOL_INTERNAL = get_logic_dir(current_dir)

def _(key, default):
    return get_translation(str(TOOL_INTERNAL), key, default)

from logic.manager import ProcessManager

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description=_('tool_BACKGROUND_desc', 'BACKGROUND - 安全的后台进程管理工具'),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_('tool_epilog_example', """
示例:
  BACKGROUND "sleep 60"                    # 使用默认zsh运行命令
  BACKGROUND "ls -la" --shell bash         # 使用bash运行命令
  BACKGROUND --list                        # 列出所有活跃进程
  BACKGROUND --kill 12345                  # 终止指定进程
  BACKGROUND --cleanup                     # 清理所有进程
  BACKGROUND --wait 12345                  # 等待进程结束
  BACKGROUND --max-processes 500           # 设置最大进程数
        """)
    )
    
    # 位置参数
    parser.add_argument('command_args', nargs=argparse.REMAINDER, help=_('command_args_help', '要在后台执行的命令'))
    
    # 可选参数
    parser.add_argument('--shell', choices=['zsh', 'bash'], default='zsh',
                       help=_('shell_help', '使用的shell类型 (默认: zsh)'))
    parser.add_argument('--max-processes', type=int, default=1000,
                       help=_('max_processes_help', '最大同时运行进程数 (默认: 1000)'))
    parser.add_argument('--log-dir', default=None,
                       help=_('log_dir_help', '日志文件目录 (默认: tool/BACKGROUND/data/logs)'))
    parser.add_argument('--max-log-files', type=int, default=1000,
                       help=_('max_log_files_help', '最大保留日志文件数 (默认: 1000)'))
    parser.add_argument('--no-alias', action='store_true',
                       help=_('no_alias_help', '不解析shell别名'))

    # 操作参数
    parser.add_argument('--list', action='store_true',
                       help=_('list_help', '列出所有活跃的后台进程'))
    parser.add_argument('--status', nargs='?', const='all', metavar='PID',
                       help=_('status_help', '查询指定PID进程的状态, 无参数时列出所有进程（等同于--list）'))
    parser.add_argument('--result', type=int, metavar='PID',
                       help=_('result_help', '获取指定PID进程的执行结果'))
    parser.add_argument('--log', type=int, metavar='PID',
                       help=_('log_help', '查看指定PID进程의日志'))
    parser.add_argument('--kill', type=int, metavar='PID',
                       help=_('kill_help', '终止指定PID的进程'))
    parser.add_argument('--force-kill', type=int, metavar='PID',
                       help=_('force_kill_help', '强制终止指定PID的进程'))
    parser.add_argument('--cleanup', action='store_true',
                       help=_('cleanup_help', '清理所有管理的后台进程'))
    parser.add_argument('--wait', type=int, metavar='PID',
                       help=_('wait_help', '等待指定PID的进程结束'))
    
    # JSON输出
    parser.add_argument('--json', action='store_true',
                       help=_('json_help', '以JSON格式输出结果'))
    
    args, unknown_args = parser.parse_known_args()
    
    # 创建进程管理器
    manager = ProcessManager(
        max_processes=args.max_processes,
        log_dir=args.log_dir,
        max_log_files=args.max_log_files
    )

    try:
        if args.list:
            processes = manager.list_processes()
            if args.json:
                print(json.dumps({'success': True, 'processes': processes, 'total_count': len(processes)}, indent=2))
            else:
                if processes:
                    print("\n" + _("all_processes", "All processes ({count}):").format(count=len(processes)))
                    
                    try:
                        terminal_width = os.get_terminal_size().columns
                    except (AttributeError, OSError):
                        terminal_width = 80
                    
                    # Translated headers
                    status_label = _("status", "Status")
                    runtime_label = _("runtime", "Runtime")
                    command_label = _("command", "Command")
                    pid_label = _("pid", "PID")
                    
                    headers = [pid_label, status_label, runtime_label, command_label]
                    table_rows = []
                    
                    for proc in processes:
                        # Translate status with colors
                        status_val = proc['status']
                        if status_val in ['active', 'running', 'sleeping']:
                            label = _("status_active", "running")
                            translated_status = f"{BLUE}{BOLD}{label}{RESET}"
                        elif status_val == 'completed':
                            label = _("status_completed", "completed")
                            translated_status = f"{GREEN}{BOLD}{label}{RESET}"
                        else:
                            # failed, unknown, etc.
                            status_key = f"status_{status_val}"
                            label = _(status_key, status_val)
                            translated_status = f"{RED}{BOLD}{label}{RESET}"
                        
                        table_rows.append([
                            str(proc['pid']),
                            translated_status,
                            proc['runtime'],
                            proc['command']
                        ])

                    # Prioritize PID column for full display
                    table_str, report_path = format_table(
                        headers, table_rows, 
                        max_width=terminal_width, 
                        save_dir="background", 
                        full_display_cols=[pid_label]
                    )
                    print(table_str + "\n")
                    
                    if report_path:
                        # Full report is always saved to report_path by format_table if truncated
                        if "..." in table_str: # Simple way to check truncation
                            print(_("full_report_saved", "Full report saved to: {path}").format(path=report_path))
                        
                        # Always print for tests
                        print(f"BACKGROUND_REPORT_PATH: {report_path}")
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
                # Use the same logic as --list
                args.list = True
                # Fall through to the next logic block? No, it's already inside if/elif.
                # I'll just copy the logic or refactor.
                processes = manager.list_processes()
                if args.json:
                    print(json.dumps({'success': True, 'action': 'status_all', 'processes': processes, 'total_count': len(processes)}, indent=2))
                else:
                    if processes:
                        print("\n" + _("all_processes", "All processes ({count}):").format(count=len(processes)))
                        
                        try:
                            terminal_width = os.get_terminal_size().columns
                        except (AttributeError, OSError):
                            terminal_width = 80
                        
                        # Translated headers
                        status_label = _("status", "Status")
                        runtime_label = _("runtime", "Runtime")
                        command_label = _("command", "Command")
                        pid_label = _("pid", "PID")
                        
                        headers = [pid_label, status_label, runtime_label, command_label]
                        table_rows = []
                        
                        for proc in processes:
                            # Translate status with colors
                            status_val = proc['status']
                            if status_val in ['active', 'running', 'sleeping']:
                                label = _("status_active", "running")
                                translated_status = f"{BLUE}{BOLD}{label}{RESET}"
                            elif status_val == 'completed':
                                label = _("status_completed", "completed")
                                translated_status = f"{GREEN}{BOLD}{label}{RESET}"
                            else:
                                # failed, unknown, etc.
                                status_key = f"status_{status_val}"
                                label = _(status_key, status_val)
                                translated_status = f"{RED}{BOLD}{label}{RESET}"
                            
                            table_rows.append([
                                str(proc['pid']),
                                translated_status,
                                proc['runtime'],
                                proc['command']
                            ])

                        table_str, report_path = format_table(
                            headers, 
                            table_rows, 
                            max_width=terminal_width, 
                            save_dir="background",
                            full_display_cols=[pid_label]
                        )
                        print(table_str + "\n")
                        
                        if report_path:
                            if "..." in table_str:
                                print(_("full_report_saved", "Full report saved to: {path}").format(path=report_path))
                            print(f"BACKGROUND_REPORT_PATH: {report_path}")
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
                        label = _("label_process_started", "Process started")
                        full_msg = _("process_started", "Process started: PID {pid}, Log: {log_file}").format(pid=pid, log_file=log_file)
                        if full_msg.startswith(label):
                            print(f"{BLUE}{BOLD}{label}{RESET}" + full_msg[len(label):])
                        else:
                            print(full_msg)
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
