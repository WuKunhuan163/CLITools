"""
Grep command handler for GDS.
"""

from typing import List
from .base_command import BaseCommand

class GrepCommand(BaseCommand):
    """Handler for grep commands."""
    
    @property
    def command_name(self) -> str:
        return "grep"
    
    def validate_args(self, args: List[str]) -> bool:
        """Validate grep command arguments."""
        if len(args) < 1:
            self.print_error("grep command needs at least a file name")
            return False
        return True
    
    def show_help(self):
        """显示grep命令帮助信息"""
        print("GDS Grep Command Help")
        print("=" * 50)
        print()
        print("USAGE:")
        print("  GDS grep <pattern> <file>           # Search for pattern in file")
        print("  GDS grep <file>                     # Display file contents (no pattern)")
        print("  GDS grep --help                     # Show this help")
        print()
        print("DESCRIPTION:")
        print("  Search for text patterns in files in the remote environment.")
        print("  Without a pattern, displays the entire file (equivalent to read/cat).")
        print()
        print("EXAMPLES:")
        print("  GDS grep 'import' script.py         # Find lines with 'import'")
        print("  GDS grep 'TODO' *.py                # Search in multiple files")
        print("  GDS grep script.py                  # Display entire file")
        print()
        print("RELATED COMMANDS:")
        print("  GDS find --help                     # Search for files")
        print("  GDS cat --help                      # Display file contents")
        print("  GDS read --help                     # Read file contents")
    
    def execute(self, cmd: str, args: List[str], **kwargs) -> int:
        """Execute grep command."""
        # 检查是否请求帮助
        if '--help' in args or '-h' in args:
            self.show_help()
            return 0

        # 处理参数解析
        if len(args) == 1:
            # 只有一个参数，视为文件名，模式为空（等效于read）
            pattern = ""
            filenames = args
        elif '.' in args[-1] and not args[-1].startswith('.'):
            # 最后一个参数是文件名，前面的是模式
            filenames = [args[-1]]
            pattern = ' '.join(args[:-1])
        else:
            # 传统处理：第一个参数是模式，其余是文件名
            pattern = args[0]
            filenames = args[1:]
        
        # 移除pattern的外层引号（如果存在）
        if pattern.startswith('"') and pattern.endswith('"'):
            pattern = pattern[1:-1]
        elif pattern.startswith("'") and pattern.endswith("'"):
            pattern = pattern[1:-1]
        
        # 检查是否为无模式的grep（等效于read）
        if not pattern or pattern.strip() == "":
            # 无模式grep，等效于read命令
            for filename in filenames:
                cat_result = self.shell.cmd_cat(filename)
                if cat_result.get("success"):
                    content = cat_result["output"]
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        print(f"{i}: {line}")
                else:
                    self.print_error(f"无法读取文件: {filename}")
            return 0
        
        # 有模式的grep，只显示匹配行
        result = self.shell.cmd_grep(pattern, *filenames)
        if result.get("success", False):
            result_data = result.get("result", {})
            
            has_file_errors = False
            has_matches = False
            
            for filename, file_result in result_data.items():
                if "error" in file_result:
                    self.print_error(f"{filename}: {file_result['error']}")
                    has_file_errors = True
                else:
                    occurrences = file_result.get("occurrences", {})
                    if occurrences:
                        has_matches = True
                        # 获取文件内容用于显示匹配行
                        cat_result = self.shell.cmd_cat(filename)
                        if cat_result.get("success"):
                            lines = cat_result["output"].split('\n')
                            for line_num in sorted(occurrences.keys()):
                                if 1 <= line_num <= len(lines):
                                    print(f"{line_num:3}: {lines[line_num-1]}")
                        else:
                            self.print_error(f"无法读取文件内容: {filename}")
            
            # 按照bash grep的标准行为返回退出码
            if has_file_errors:
                return 2  # 文件错误（如文件不存在）
            elif not has_matches:
                return 1  # 没有匹配项
            else:
                return 0  # 有匹配项
        else:
            self.print_error(result.get("error", "Grep命令执行失败"))
            return 1


    def cmd_grep(self, pattern, *filenames):
        """grep命令 - 在文件中搜索模式，支持多文件和regex"""
        import re
        
        try:
            if not pattern:
                return {"success": False, "error": "请指定搜索模式"}
            
            if not filenames:
                return {"success": False, "error": "请指定要搜索的文件"}
            
            # 编译正则表达式
            try:
                regex = re.compile(pattern)
            except re.error as e:
                return {"success": False, "error": f"无效的正则表达式: {e}"}
            
            result = {}
            
            for filename in filenames:
                # 获取文件内容（使用grep作为命令名用于错误信息）
                cat_result = self.shell.cmd_cat(filename, "grep")
                if not cat_result["success"]:
                    result[filename] = {
                        "local_file": None,
                        "occurrences": [],
                        "error": cat_result["error"]
                    }
                    continue
                
                content = cat_result["output"]
                lines = content.split('\n')
                
                # 搜索匹配的位置
                occurrences = {}
                for line_num, line in enumerate(lines, 1):
                    line_matches = []
                    for match in regex.finditer(line):
                        line_matches.append(match.start())
                    if line_matches:
                        occurrences[line_num] = line_matches
                
                # 转换为所需格式: {line_num: [positions]}
                formatted_occurrences = occurrences
                
                # 获取本地缓存文件路径
                local_file = self.main_instance.cache_manager.get_local_cache_path(filename)
                
                result[filename] = {
                    "local_file": local_file,
                    "occurrences": formatted_occurrences
                }
            
            return {"success": True, "result": result}
                
        except Exception as e:
            return {"success": False, "error": f"Grep command failed: {str(e)}"}
