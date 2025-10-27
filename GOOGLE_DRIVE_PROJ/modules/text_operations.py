
import json
import hashlib
import time

class TextOperations:
    """
    Text file editing and content operations
    """
    
    def __init__(self, drive_service, main_instance):
        self.drive_service = drive_service
        self.main_instance = main_instance
    
    def cmd_download(self, *args, **kwargs):
        """Delegate to file_core for download operations"""
        # Import FileCore for download operations
        from .file_core import FileCore
        file_core = FileCore(self.drive_service, self.main_instance)
        return file_core.cmd_download(*args, **kwargs)
    
    def cmd_upload(self, *args, **kwargs):
        """Delegate to file_core for upload operations"""
        # Import FileCore for upload operations
        from .file_core import FileCore
        file_core = FileCore(self.drive_service, self.main_instance)
        return file_core.cmd_upload(*args, **kwargs)

    def _create_text_file(self, filename, content):
        """通过远程命令创建文本文件"""
        try:
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell"}
            
            # 构建远程echo命令
            remote_absolute_path = self.main_instance.resolve_remote_absolute_path(filename, current_shell)
            
            # 使用base64编码来完全避免引号和特殊字符问题
            import base64
            content_bytes = content.encode('utf-8')
            content_base64 = base64.b64encode(content_bytes).decode('ascii')
            
            # 构建远程命令 - 使用base64解码避免所有引号问题
            remote_command = f'echo "{content_base64}" | base64 -d > "{remote_absolute_path}"'
            
            # 使用远程命令执行接口
            result = self.main_instance.execute_command_interface("bash", ["-c", remote_command])
            
            if result.get("success"):
                # 验证文件是否真的被创建了
                verification_result = self.main_instance.verify_creation_with_ls(
                    filename, current_shell, creation_type="file")
                
                if verification_result.get("success", False):
                    return {
                        "success": True,
                        "filename": filename,
                        "message": f"File created: {filename}"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"File create verification failed: {verification_result.get('error', 'Unknown verification error')}"
                    }
            else:
                # 优先使用用户提供的错误信息
                error_msg = result.get('error_info') or result.get('error') or 'Unknown error'
                return {
                    "success": False,
                    "error": f"Create file failed: {error_msg}"
                }
                
        except Exception as e:
            return {"success": False, "error": f"Create file failed: {e}"}

    def cmd_cat(self, filename):
        """cat命令 - 显示文件内容"""
        try:
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API service not initialized"}
                
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell, please create or switch to a shell"}
            
            if not filename:
                return {"success": False, "error": "Please specify the file to view"}
            
            # 查找文件
            file_info = self._find_file(filename, current_shell)
            if not file_info:
                # 将本地路径转换为远程路径格式以便在错误消息中正确显示
                converted_filename = self.main_instance.path_resolver._convert_local_path_to_remote(filename)
                return {"success": False, "error": f"File or directory does not exist: {converted_filename}"}
            
            # 检查是否为文件
            if file_info['mimeType'] == 'application/vnd.google-apps.folder':
                return {"success": False, "error": f"cat: {filename}: Is a directory"}
            
            # 下载并读取文件内容
            try:
                import io
                from googleapiclient.http import MediaIoBaseDownload
                
                request = self.drive_service.service.files().get_media(fileId=file_info['id'])
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                
                content = fh.getvalue().decode('utf-8', errors='replace')
                return {"success": True, "output": content, "filename": filename}
                
            except Exception as e:
                return {"success": False, "error": f"无法读取文件内容: {e}"}
                
        except Exception as e:
            return {"success": False, "error": f"执行cat命令时出错: {e}"}

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
                # 获取文件内容
                cat_result = self.cmd_cat(filename)
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

    def _find_file(self, filepath, current_shell):
        """查找文件，支持路径解析"""
        try:
            # 如果包含路径分隔符，需要解析路径
            if '/' in filepath:
                # 分离目录和文件名
                dir_path, filename = filepath.rsplit('/', 1)
                
                # 解析目录路径
                target_folder_id, _ = self.main_instance.resolve_path(dir_path, current_shell)
                if not target_folder_id:
                    return None
            else:
                # 在当前目录查找
                filename = filepath
                target_folder_id = current_shell.get("current_folder_id", self.main_instance.REMOTE_ROOT_FOLDER_ID)
            
            # 列出目标目录内容
            files_result = self.drive_service.list_files(folder_id=target_folder_id, max_results=100)
            if not files_result['success']:
                return None
            
            # 查找匹配的文件
            for file in files_result['files']:
                if file['name'] == filename:
                    return file
            
            return None
            
        except Exception:
            return None

    def _parse_find_args(self, args):
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

    def _recursive_find(self, search_path, pattern, case_sensitive=True, file_type=None):
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
            parsed_args = self._parse_find_args(args)
            if not parsed_args["success"]:
                return parsed_args
            
            search_path = parsed_args["path"]
            pattern = parsed_args["pattern"]
            case_sensitive = parsed_args["case_sensitive"]
            file_type = parsed_args["file_type"]  # "f" for files, "d" for directories, None for both
            
            # 递归搜索文件
            results = self._recursive_find(search_path, pattern, case_sensitive, file_type)
            
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

    def cmd_edit_online(self, filename, replacement_spec, preview=False, backup=False):
        """
        在线edit命令 - 完全在远端操作，不需要download/upload
        
        Args:
            filename (str): 要编辑的文件名
            replacement_spec (str): 替换规范，支持多种格式
            preview (bool): 预览模式，只显示修改结果不实际保存
            backup (bool): 是否创建备份文件
            
        Returns:
            dict: 编辑结果
        """
        import json
        import hashlib
        import time
        
        try:
            
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell"}
            
            # 1. 解析替换规范
            try:
                replacements = json.loads(replacement_spec)
                if not isinstance(replacements, list):
                    return {"success": False, "error": "Replacement specification must be an array"}
                # Debug output removed for cleaner interface
                pass
            except json.JSONDecodeError as e:
                return {"success": False, "error": f"JSON parsing failed: {e}"}
            
            # 2. 生成远端脚本来执行编辑操作
            script_hash = hashlib.md5(f"{filename}_{time.time()}".encode()).hexdigest()[:8]
            script_filename = f"edit_script_{script_hash}.py"
            
            # 创建Python脚本来处理编辑
            edit_script = self._generate_online_edit_script(filename, replacements, preview, backup)
            
            # 3. 解析远程绝对路径
            remote_absolute_path = self.main_instance.resolve_remote_absolute_path(filename, current_shell)
            
            # 4. 直接在远程执行编辑操作（不需要上传脚本）
            result = self._execute_online_editremote_absolute_path, replacements, preview, backup)
            
            # Return result without debug output for cleaner interface
            
            return result
            
        except Exception as e:
            return {"success": False, "error": f"Edit operation failed: {str(e)}"}

    def _generate_online_edit_script(self, filename, replacements, preview, backup):
        """生成在线编辑的Python脚本"""
        # 使用字符串拼接而不是f-string来避免花括号转义问题
        script = '''#!/usr/bin/env python3
import json
import sys
import os
from datetime import datetime
import difflib

def main():
    filename = "''' + filename + '''"
    replacements = ''' + json.dumps(replacements) + '''
    preview = ''' + str(preview) + '''
    backup = ''' + str(backup) + '''
    
    try:
        # 1. 读取文件内容
        if not os.path.exists(filename):
            print(json.dumps({"success": False, "error": f"File not found: {filename}"}))
            return 1
            
        with open(filename, 'r', encoding='utf-8') as f:
            original_lines = f.readlines()
        
        # 2. 解析和执行替换操作
        modified_lines = original_lines.copy()
        parsed_replacements = []
        
        for i, replacement in enumerate(replacements):
            if not isinstance(replacement, list) or len(replacement) != 2:
                print(json.dumps({"success": False, "error": f"Replacement {i+1} has incorrect format"}))
                return 1
                
            source, target = replacement
            
            if isinstance(source, list) and len(source) == 2:
                start_line, end_line = source
                
                if isinstance(start_line, int) and isinstance(end_line, int):
                    # 行号替换
                    start_idx = start_line
                    end_idx = end_line
                    
                    if start_idx < 0 or start_idx >= len(original_lines) or end_idx >= len(original_lines) or start_idx > end_idx:
                        print(json.dumps({"success": False, "error": f"Line range error: [{start_line}, {end_line}]"}))
                        return 1
                    
                    parsed_replacements.append({
                        "type": "line_range",
                        "start_idx": start_idx,
                        "end_idx": end_idx,
                        "new_content": target
                    })
            elif isinstance(source, str):
                # 文本替换
                parsed_replacements.append({
                    "type": "text_search", 
                    "old_text": source,
                    "new_text": target
                })
        
        # 3. 执行替换操作
        # 按行号倒序处理行替换
        line_replacements = [r for r in parsed_replacements if r["type"] == "line_range"]
        line_replacements.sort(key=lambda x: x["start_idx"], reverse=True)
        
        for replacement in line_replacements:
            start_idx = replacement["start_idx"]
            end_idx = replacement["end_idx"]
            new_content = replacement["new_content"]
            
            # 处理换行符
            if new_content:
                new_lines = [new_content + '\n']
                modified_lines[start_idx:end_idx + 1] = new_lines
            else:
                # 删除行
                modified_lines[start_idx:end_idx + 1] = []
        
        # 处理文本替换
        text_replacements = [r for r in parsed_replacements if r["type"] == "text_search"]
        if text_replacements:
            file_content = "".join(modified_lines)
            for replacement in text_replacements:
                file_content = file_content.replace(replacement["old_text"], replacement["new_text"])
            modified_lines = file_content.splitlines(keepends=True)
        
        # 4. 生成diff
        diff_lines = list(difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile='original',
            tofile='modified',
            lineterm=''
        ))
        
        # 5. 保存文件（如果不是预览模式）
        if not preview:
            # 创建备份
            if backup:
                backup_filename = f"{filename}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                with open(backup_filename, 'w', encoding='utf-8') as f:
                    f.writelines(original_lines)
            
            # 写入修改后的文件
            with open(filename, 'w', encoding='utf-8') as f:
                f.writelines(modified_lines)
        
        # 6. 返回结果
        result = {
            "success": True,
            "filename": filename,
            "original_lines": len(original_lines),
            "modified_lines": len(modified_lines),
            "replacements_applied": len(parsed_replacements),
            "diff_lines": diff_lines,
            "mode": "preview" if preview else "edit",
            "backup_created": backup and not preview
        }
        
        print(json.dumps(result))
        return 0
        
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1

if __name__ == "__main__":
    sys.exit(main())
'''
        return script

    def _execute_online_editself, filename, replacements, preview, backup):
        """直接在远程执行编辑操作，不需要上传脚本"""
        try:
            import base64
            
            # 创建Python脚本内容
            script_content = f"""
import json
import os
import sys
from datetime import datetime
import difflib

def main():
    filename = {json.dumps(filename)}
    replacements = {json.dumps(replacements)}
    preview = {preview}
    backup = {backup}
    
    try:
        # 1. 读取文件内容
        if not os.path.exists(filename):
            print(json.dumps({{"success": False, "error": f"File not found: {{filename}}"}}))
            return 1
            
        with open(filename, 'r', encoding='utf-8') as f:
            original_lines = f.readlines()
        
        # 2. 解析和执行替换操作
        modified_lines = original_lines.copy()
        parsed_replacements = []
        
        for i, replacement in enumerate(replacements):
            if not isinstance(replacement, list) or len(replacement) != 2:
                print(json.dumps({{"success": False, "error": f"Replacement {{i+1}} has incorrect format"}}))
                return 1
                
            source, target = replacement
            
            if isinstance(source, list) and len(source) == 2:
                start_line, end_line = source
                
                if isinstance(start_line, int) and isinstance(end_line, int):
                    # 行号替换
                    start_idx = start_line
                    end_idx = end_line
                    
                    if start_idx < 0 or start_idx >= len(original_lines) or end_idx >= len(original_lines) or start_idx > end_idx:
                        print(json.dumps({{"success": False, "error": f"Line range error: [{{start_line}}, {{end_line}}]"}}))
                        return 1
                    
                    parsed_replacements.append({{"type": "line_range", "start_idx": start_idx, "end_idx": end_idx, "target": target}})
                    
                    # 执行替换
                    for j in range(start_idx, end_idx + 1):
                        modified_lines[j] = target + "\\n" if not target.endswith("\\n") else target
                        
                else:
                    print(json.dumps({{"success": False, "error": f"Invalid line numbers: {{source}}"}}))
                    return 1
                    
            else:
                # 字符串替换
                if not isinstance(source, str):
                    print(json.dumps({{"success": False, "error": f"Source must be string or [start_line, end_line]: {{source}}"}}))
                    return 1
                    
                # 查找并替换字符串
                found = False
                for j, line in enumerate(modified_lines):
                    if source in line:
                        modified_lines[j] = line.replace(source, target)
                        found = True
                        parsed_replacements.append({{"type": "string", "line_idx": j, "source": source, "target": target}})
                        break
                
                if not found:
                    print(json.dumps({{"success": False, "error": f"String not found: {{source}}"}}))
                    return 1
        
        # 3. 生成diff
        diff_lines = []
        for line in difflib.unified_diff(
            [line.rstrip('\\n') for line in original_lines],
            [line.rstrip('\\n') for line in modified_lines],
            fromfile=f"{{filename}} (original)",
            tofile=f"{{filename}} (modified)",
            lineterm=''
        ):
            diff_lines.append(line)
        
        # 4. 创建备份（如果需要且不是预览模式）
        backup_file = None
        if backup and not preview:
            backup_file = f"{{filename}}.backup.{{datetime.now().strftime('%Y%m%d_%H%M%S')}}"
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.writelines(original_lines)
        
        # 5. 写入修改后的内容（如果不是预览模式）
        if not preview:
            with open(filename, 'w', encoding='utf-8') as f:
                f.writelines(modified_lines)
        
        # 6. 返回结果
        result = {{"success": True, "replacements_made": len(parsed_replacements), "diff_lines": diff_lines, "backup_file": backup_file, "preview": preview, "mode": "preview" if preview else "edit"}}
        
        print(json.dumps(result))
        return 0
        
    except Exception as e:
        print(json.dumps({{"success": False, "error": str(e)}}))
        return 1

if __name__ == "__main__":
    sys.exit(main())
"""
            
            # 使用base64编码来避免引号问题
            script_b64 = base64.b64encode(script_content.encode('utf-8')).decode('ascii')
            
            # 执行远程Python代码
            command = f"python3 -c \"import base64; exec(base64.b64decode('{script_b64}').decode('utf-8'))\""
            execute_result = self.main_instance.remote_commands.execute_command(command)
            
            if execute_result.get("success"):
                # 解析脚本输出 - 从data.stdout中获取
                data = execute_result.get("data", {})
                output = data.get("stdout", "").strip()
                try:
                    result = json.loads(output)
                    
                    # 格式化diff输出用于显示
                    if result.get("success") and result.get("diff_lines"):
                        diff_lines = result["diff_lines"]
                        
                        # 过滤diff输出，只显示有意义的行
                        filtered_lines = []
                        for line in diff_lines:
                            if line.startswith(('---', '+++', '@@')) or line.startswith(('+', '-', ' ')):
                                filtered_lines.append(line)
                        
                        if filtered_lines:
                            # 计算文件总行数以确定行号宽度
                            # 从@@行中提取最大行号来估算文件大小
                            max_line_num = 0
                            for line in filtered_lines:
                                if line.startswith('@@'):
                                    import re
                                    # 提取新文件的起始行号和行数
                                    match = re.search(r'@@ -\d+,\d+ \+(\d+),(\d+) @@', line)
                                    if match:
                                        start_line = int(match.group(1))
                                        line_count = int(match.group(2))
                                        # 估算最大行号
                                        max_line_num = max(max_line_num, start_line + line_count - 1)
                            
                            # 如果无法从@@行获取，使用默认宽度
                            if max_line_num == 0:
                                max_line_num = 999  # 默认3位数
                            
                            width = len(str(max_line_num))  # 计算行号宽度
                            
                            # 添加行号并简化文件路径显示
                            simplified_lines = []
                            current_line_num = 1
                            
                            for line in filtered_lines:
                                if line.startswith('---') or line.startswith('+++'):
                                    # 只显示文件名，不显示完整路径
                                    if '/' in line:
                                        parts = line.split('/')
                                        filename_only = parts[-1].split()[0]  # 获取文件名，去掉后面的标记
                                        prefix = line.split()[0]  # --- 或 +++
                                        suffix = ' '.join(line.split()[1:])  # 获取后面的部分
                                        # 重新构建，只保留文件名
                                        if '(original)' in suffix:
                                            simplified_line = f"{prefix} {filename_only} (original)"
                                        elif '(modified)' in suffix:
                                            simplified_line = f"{prefix} {filename_only} (modified)"
                                        else:
                                            simplified_line = f"{prefix} {filename_only}"
                                        simplified_lines.append(simplified_line)
                                    else:
                                        simplified_lines.append(line)
                                elif line.startswith('@@'):
                                    # 解析行号信息
                                    # 格式: @@ -start,count +start,count @@
                                    import re
                                    match = re.search(r'@@ -\d+,\d+ \+(\d+),\d+ @@', line)
                                    if match:
                                        current_line_num = int(match.group(1))
                                    simplified_lines.append(line)
                                elif line.startswith('-'):
                                    # 删除的行，添加空格使其与有行号的行对齐
                                    spaces = ' ' * (width + 2)  # width + ': ' 的长度
                                    simplified_lines.append(f"{spaces}{line}")
                                elif line.startswith('+'):
                                    # 新增的行，添加行号（使用动态宽度）
                                    simplified_lines.append(f"{current_line_num:{width}}: {line}")
                                    current_line_num += 1
                                elif line.startswith(' '):
                                    # 上下文行，添加行号（使用动态宽度）
                                    simplified_lines.append(f"{current_line_num:{width}}: {line}")
                                    current_line_num += 1
                                else:
                                    simplified_lines.append(line)
                            
                            diff_output = "\n".join(simplified_lines)
                            result["diff_output"] = diff_output
                        else:
                            result["diff_output"] = "No changes detected"
                    
                    return result
                    
                except json.JSONDecodeError as e:
                    return {"success": False, "error": f"Invalid script output: {output}"}
            else:
                return {"success": False, "error": f"Script execution failed: {execute_result.get('error')}"}
                
        except Exception as e:
            return {"success": False, "error": f"Direct execution failed: {str(e)}"}

    def cmd_edit(self, filename, replacement_spec, preview=False, backup=False):
        """
        GDS edit命令 - 支持多段文本同步替换的文件编辑功能
        
        使用在线编辑模式，完全在远端操作，避免download/upload
        
        Args:
            filename (str): 要编辑的文件名
            replacement_spec (str): 替换规范，支持多种格式
            preview (bool): 预览模式，只显示修改结果不实际保存
            backup (bool): 是否创建备份文件
            
        Returns:
            dict: 编辑结果
            
        支持的替换格式:
        1. 行号替换: '[[[1, 2], "new content"], [[5, 7], "another content"]]'
        2. 文本搜索替换: '[["old text", "new text"], ["another old", "another new"]]'
        3. 混合模式: '[[[1, 1], "line replacement"], ["text", "replace"]]'
        """
        # 使用新的在线编辑模式
        return self.cmd_edit_online(filename, replacement_spec, preview, backup)
