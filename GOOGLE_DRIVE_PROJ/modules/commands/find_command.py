"""
Find command - 文件查找功能
从text_operations.py迁移而来
"""


class FindCommand:
    """文件查找命令"""
    
    def __init__(self, main_instance):
        self.main_instance = main_instance
        self.drive_service = main_instance.drive_service
    

    def parse_find_args(self, args):
        """解析find命令参数"""
        try:
            args_list = list(args)
            
            # 默认值
            path = "."
            pattern = "*"
            case_sensitive = True
            file_type = None  # None=both, "f"=files, "d"=directories
            
            i = 0
            while i < len(args_list):
                arg = args_list[i]
                
                if arg == "-name" and i + 1 < len(args_list):
                    pattern = args_list[i + 1]
                    case_sensitive = True
                    i += 2
                elif arg == "-iname" and i + 1 < len(args_list):
                    pattern = args_list[i + 1]
                    case_sensitive = False
                    i += 2
                elif arg == "-type" and i + 1 < len(args_list):
                    file_type = args_list[i + 1]
                    if file_type not in ["f", "d"]:
                        return {"success": False, "error": "无效的文件类型，使用 'f' (文件) 或 'd' (目录)"}
                    i += 2
                elif not arg.startswith("-"):
                    # 这是路径参数
                    path = arg
                    i += 1
                else:
                    i += 1
            
            return {
                "success": True,
                "path": path,
                "pattern": pattern,
                "case_sensitive": case_sensitive,
                "file_type": file_type
            }
            
        except Exception as e:
            return {"success": False, "error": f"参数解析错误: {e}"}

    def recursive_find(self, search_path, pattern, case_sensitive=True, file_type=None):
        """
        递归查找匹配的文件和目录
        
        Args:
            search_path: 搜索路径
            pattern: 搜索模式（支持通配符）
            case_sensitive: 是否大小写敏感
            file_type: 文件类型过滤 ("f" for files, "d" for directories, None for both)
        
        Returns:
            dict: {"success": bool, "files": list, "error": str}
        """
        try:
            import fnmatch
            
            # 使用统一的路径解析接口
            current_shell = self.main_instance.get_current_shell()
            search_path = self.main_instance.path_resolver.resolve_remote_absolute_path(search_path, current_shell)
            
            # 生成远程find命令
            find_cmd_parts = ["find", f'"{search_path}"']
            
            # 添加文件类型过滤
            if file_type == "f":
                find_cmd_parts.append("-type f")
            elif file_type == "d":
                find_cmd_parts.append("-type d")
            
            # 添加名称模式
            if case_sensitive:
                find_cmd_parts.append(f'-name "{pattern}"')
            else:
                find_cmd_parts.append(f'-iname "{pattern}"')
            
            find_command = " ".join(find_cmd_parts)
            
            # 执行远程find命令
            result = self.main_instance.execute_command_interface("bash", ["-c", find_command])
            
            if result.get("success"):
                stdout = result.get("stdout", "").strip()
                if stdout:
                    # 分割输出为文件路径列表
                    files = [line.strip() for line in stdout.split("\n") if line.strip()]
                    return {
                        "success": True,
                        "files": files
                    }
                else:
                    return {
                        "success": True,
                        "files": []
                    }
            else:
                return {
                    "success": False,
                    "error": f"Remote find command failed: {result.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error executing find: {e}"
            }

    def cmd_find(self, *args):
        """
        GDS find命令实现，类似bash find
        
        用法:
            find [path] -name [pattern]
            find [path] -iname [pattern]  # 大小写不敏感
            find [path] -type f -name [pattern]  # 只查找文件
            find [path] -type d -name [pattern]  # 只查找目录
        
        Args:
            *args: 命令参数
            
        Returns:
            dict: 查找结果
        """
        try:
            if not args:
                return {
                    "success": False,
                    "error": "用法: find [path] -name [pattern] 或 find [path] -type [f|d] -name [pattern]"
                }
            
            # 解析参数
            parsed_args = self.parse_find_args(args)
            if not parsed_args["success"]:
                return parsed_args
            
            search_path = parsed_args["path"]
            pattern = parsed_args["pattern"]
            case_sensitive = parsed_args["case_sensitive"]
            file_type = parsed_args["file_type"]  # "f" for files, "d" for directories, None for both
            
            # 递归搜索文件
            results = self.recursive_find(search_path, pattern, case_sensitive, file_type)
            
            if results["success"]:
                found_files = results["files"]
                
                # 格式化输出
                output_lines = []
                for file_path in sorted(found_files):
                    output_lines.append(file_path)
                
                return {
                    "success": True,
                    "files": found_files,
                    "count": len(found_files),
                    "output": "\n".join(output_lines) if output_lines else "No files found matching the pattern."
                }
            else:
                return results
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Find command error: {e}"
            }
