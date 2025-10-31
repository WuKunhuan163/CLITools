from .base_command import BaseCommand
import re

class EditCommand(BaseCommand):
    @property
    def command_name(self):
        return "edit"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行edit命令"""
        preview = False
        backup = False
        remaining_args = []
        
        for arg in args:
            if arg == '--preview':
                preview = True
            elif arg == '--backup':
                backup = True
            else:
                remaining_args.append(arg)
        if len(remaining_args) < 2:
            print("Error: edit command needs a file name and edit specification")
            return 1
        
        filename = remaining_args[0]
        shell_cmd_clean = f"{cmd} {' '.join(args)}"
        
        # 构建选项字符串用于匹配
        options_pattern = ""
        if preview:
            options_pattern += r"(?:--preview\s+)?"
        if backup:
            options_pattern += r"(?:--backup\s+)?"
        
        # 匹配命令：edit [options] filename JSON_spec
        pattern = rf'^edit\s+{options_pattern}(\S+)\s+(.+)$'
        match = re.search(pattern, shell_cmd_clean)
        if match:
            edit_spec = match.group(2)  # 直接提取JSON部分，不做空格连接
        else:
            # 回退方案：如果只有一个JSON参数，直接使用
            if len(remaining_args) == 2:
                edit_spec = remaining_args[1]
            else:
                # 多个参数时，可能是引号被分割了，尝试重新组合
                edit_spec = ' '.join(remaining_args[1:])
        
        try:
            result = self.shell.cmd_edit(filename, edit_spec, preview=preview, backup=backup)
        except KeyboardInterrupt:
            result = {"success": False, "error": "Operation interrupted by user"}
        
        if result.get("success", False):
            # 显示diff比较（预览模式和正常模式都显示）
            diff_output = result.get("diff_output", "")
            
            if diff_output and diff_output != "No changes detected":
                print(f"\nEdit comparison: {filename}")
                print(f"=" * 50)
                
                # 过滤diff输出，只移除文件头，保留行号信息和上下文
                diff_lines = diff_output.splitlines()
                filtered_lines = []
                for line in diff_lines:
                    # 跳过文件头行（--- 和 +++）
                    if line.startswith('---') or line.startswith('+++'):
                        continue
                    # 保留行号信息行（@@）和所有其他内容
                    filtered_lines.append(line)
                
                # 显示过滤后的diff内容
                if filtered_lines:
                    print('\n'.join(filtered_lines))
                print(f"=" * 50)
            elif diff_output == "No changes detected":
                print(f"No changes detected")
            
            # 显示成功信息
            if result.get("mode") == "preview":
                print("\nEdit preview completed")
            else:
                print(result.get("message", "\nFile edited successfully"))
            
            # 显示linter结果（如果有）
            if result.get("has_linter_issues"):
                print(f"=" * 50)
                linter_output = result.get("linter_output", "")
                total_issues = linter_output.count("ERROR:") + linter_output.count("WARNING:")
                print(f"{total_issues} linter warnings or errors found:")
                print(linter_output)
                print(f"=" * 50)
            elif result.get("linter_error"):
                print(f"=" * 50)
                print(f"Linter check failed: {result.get('linter_error')}")
                print(f"=" * 50)
            elif result.get("has_linter_issues") == False:
                # Only show "no issues" message if linter actually ran
                pass  # No need to show anything for clean files
            
            return 0
        else:
            error_msg = result.get("error", "Failed to edit file")
            if "Download failed: file not found" in error_msg:
                error_msg = f"File not found: {filename}"
            elif "file not found" in error_msg.lower():
                error_msg = f"File not found: {filename}"
            print(error_msg)
            return 1

    def cmd_edit(self, filename, replacement_spec, preview=False, backup=False):
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
            
            # 2. 解析远程绝对路径
            remote_absolute_path = self.main_instance.resolve_remote_absolute_path(filename, current_shell)
            
            # 4. 直接在远程执行编辑操作（不需要上传脚本）
            result = self.execute_online_edit(remote_absolute_path, replacements, preview, backup)
            return result
            
        except Exception as e:
            return {"success": False, "error": f"Edit operation failed: {str(e)}"}

    def generate_online_edit_script(self, filename, replacements, preview, backup):
        """生成在线编辑的Python脚本"""
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

    def execute_online_edit(self, filename, replacements, preview, backup):
        """直接在远程执行编辑操作，不需要上传脚本"""
        try:
            import base64
            import json
            
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
            
            # 生成并执行远程Python代码
            command = f"python3 -c \"import base64; exec(base64.b64decode('{script_b64}').decode('utf-8'))\""
            
            # 先生成远程命令
            current_shell = self.main_instance.get_current_shell()
            remote_command, result_filename, cmd_hash = self.main_instance.command_generator.generate_command(
                command, None, current_shell
            )
            
            # 执行远程命令
            execute_result = self.main_instance.command_executor.execute_command(
                remote_command=remote_command,
                result_filename=result_filename,
                cmd_hash=cmd_hash,
                raw_command=command
            )
            
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
