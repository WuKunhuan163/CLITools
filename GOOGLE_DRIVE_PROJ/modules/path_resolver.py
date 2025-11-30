#!/usr/bin/env python3
"""
Google Drive Shell - Path Resolver Module

This module provides comprehensive path resolution and management functionality for the Google Drive Shell system.
It handles the complex mapping between local paths, remote logical paths, and Google Drive folder IDs.

Key Features:
- Logical path resolution (~/path, @/path formats)
- Remote absolute path calculation
- Google Drive folder ID resolution
- Path normalization and validation
- Support for both user space (~) and environment space (@) paths
- Integration with Google Drive API for folder ID lookup

Path Formats:
- Logical paths: ~/documents/file.txt (user space), @/python/script.py (environment space)
- Remote absolute paths: /content/drive/MyDrive/documents/file.txt
- Google Drive IDs: Folder and file IDs for API operations

Classes:
    PathResolver: Main path resolution class handling all path operations

Dependencies:
    - Google Drive API service for folder ID resolution
    - Path constants for base directory definitions
    - Shell state management for current directory tracking
"""

import os
import sys
current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

class PathResolver:
    """Google Drive Shell Path Resolver"""

    def __init__(self, drive_service=None, main_instance=None):
        """初始化管理器"""
        self.drive_service = drive_service
        self.main_instance = main_instance

    @staticmethod
    def protect_special_chars(text):
        r"""
        将字符串中的特殊符号和重定向符号替换为placeholder
        
        保护的符号包括：
        - 引号字符串：完整的双引号或单引号字符串（包括引号本身和内容）
        - 转义序列：\n, \t, \r, \\, \", \', 等所有 \x 形式的转义
        - 真实控制字符：换行符(ASCII 10), 回车符(ASCII 13), 制表符(ASCII 9)
        - 重定向操作符：>, <, >>, <<, |, &>, 2>, 2>&1, &>>
        - 引号：", '
        - shell特殊字符：$, `, {, }, [, ], #, &, ;, *, ?, (, )
        - bash/echo命令本身（避免被误解析）
        - 多个连续空格
        
        Args:
            text (str): 输入字符串
        
        Returns:
            tuple: (转换后的字符串, placeholder字典)
                placeholder字典的格式为 {placeholder: original_symbol}
        """
        import uuid
        import re
        
        placeholders = {}
        result = text
        
        # 步骤0: 首先保护完整的引号字符串（包括引号和内容）
        # 这样引号内的特殊字符（如@、~等）就不会被后续的路径展开逻辑处理
        # 双引号字符串：匹配 "..." ，支持转义的引号 \"
        double_quoted_pattern = r'"(?:[^"\\]|\\.)*"'
        double_quoted_matches = list(re.finditer(double_quoted_pattern, result))
        for match in reversed(double_quoted_matches):
            quoted_str = match.group(0)
            quoted_placeholder = f"QUOTED_STR_{uuid.uuid4().hex[:8].upper()}"
            placeholders[quoted_placeholder] = quoted_str
            result = result[:match.start()] + quoted_placeholder + result[match.end():]
        
        # 单引号字符串：匹配 '...' ，单引号内不支持转义
        single_quoted_pattern = r"'[^']*'"
        single_quoted_matches = list(re.finditer(single_quoted_pattern, result))
        for match in reversed(single_quoted_matches):
            quoted_str = match.group(0)
            quoted_placeholder = f"QUOTED_STR_{uuid.uuid4().hex[:8].upper()}"
            placeholders[quoted_placeholder] = quoted_str
            result = result[:match.start()] + quoted_placeholder + result[match.end():]
        
        # 步骤1: 保护所有的转义序列 \x（将 \x 替换为 PHx）
        escape_pattern = r'\\(.)'
        escape_matches = list(re.finditer(escape_pattern, result))
        # 从后往前替换，避免索引变化
        for match in reversed(escape_matches):
            escaped_char = match.group(1)
            # 生成唯一的placeholder，使用字符的ASCII码避免特殊字符
            char_code = ord(escaped_char)
            escape_placeholder = f"ESCAPE{char_code}PH{uuid.uuid4().hex[:8].upper()}"
            placeholders[escape_placeholder] = f'\\{escaped_char}'
            result = result[:match.start()] + escape_placeholder + result[match.end():]
        
        # 步骤1.2: 保护真实的控制字符（换行符、回车符、制表符等）
        # 这些字符是实际的ASCII控制字符，不是转义序列
        # 必须在步骤1之后处理，因为转义序列\n和真实换行符\n是不同的
        control_chars_to_protect = [
            ('\n', 'REAL_NEWLINE'),        # 真实换行符 (ASCII 10)
            ('\r', 'REAL_CARRIAGE_RET'),  # 真实回车符 (ASCII 13)
            ('\t', 'REAL_TAB'),            # 真实制表符 (ASCII 9)
        ]
        
        for char, base_name in control_chars_to_protect:
            if char in result:
                # 为每个控制字符生成唯一的placeholder
                # 注意：由于换行符可能出现多次，需要逐个替换
                while char in result:
                    control_char_placeholder = f"{base_name}_{uuid.uuid4().hex[:8].upper()}"
                    placeholders[control_char_placeholder] = char
                    # 只替换第一个出现的控制字符
                    result = result.replace(char, control_char_placeholder, 1)
        
        # 步骤1.5: 保护多个连续空格（每两个空格为一组）
        # 循环替换，直到不再有两个连续空格
        while '  ' in result:  # 两个空格
            double_space_placeholder = f"DOUBLE_SPACE_{uuid.uuid4().hex[:8].upper()}"
            placeholders[double_space_placeholder] = '  '
            # 只替换第一个出现的两个连续空格
            result = result.replace('  ', double_space_placeholder, 1)
        
        # 步骤1.6: 保护bash和echo命令（避免bash -c 'echo/bash ...'时被误解析）
        # 注意：这里保护的是"bash"和"echo"（不带空格），避免影响后面的 ~ 展开
        if 'bash' in result:
            bash_cmd_placeholder = f"BASH_CMD_{uuid.uuid4().hex[:8].upper()}"
            placeholders[bash_cmd_placeholder] = 'bash'
            result = result.replace('bash', bash_cmd_placeholder)
        if 'echo' in result:
            echo_cmd_placeholder = f"ECHO_CMD_{uuid.uuid4().hex[:8].upper()}"
            placeholders[echo_cmd_placeholder] = 'echo'
            result = result.replace('echo', echo_cmd_placeholder)
        
        # 步骤3: 定义需要保护的符号（按长度从长到短排序，避免替换冲突）
        symbols_to_protect = [
            ('2>&1', 'REDIR_2GT_AMP_1'),
            ('>>', 'REDIR_GTGT'),
            ('<<', 'REDIR_LTLT'),
            ('&>>', 'REDIR_AMP_GTGT'),
            ('&>', 'REDIR_AMP_GT'),
            ('2>', 'REDIR_2GT'),
            ('>', 'REDIR_GT'),
            ('<', 'REDIR_LT'),
            ('|', 'REDIR_PIPE'),
            ('"', 'QUOTE_DOUBLE'),
            ("'", 'QUOTE_SINGLE'),
            ('{', 'LEFT_BRACE'),
            ('}', 'RIGHT_BRACE'),
            ('[', 'LEFT_BRACKET'),
            (']', 'RIGHT_BRACKET'),
            ('$', 'DOLLAR'),
            ('`', 'BACKTICK'),
            ('#', 'HASH'),
            ('&', 'AMP'),
            (';', 'SEMICOLON'),
            ('*', 'ASTERISK'),
            ('?', 'QUESTION'),
            ('(', 'LEFT_PAREN'),
            (')', 'RIGHT_PAREN'),
        ]
        
        for symbol, base_name in symbols_to_protect:
            if symbol in result:
                # 为每个符号生成唯一的placeholder
                placeholder = f"{base_name}_{uuid.uuid4().hex[:8].upper()}"
                placeholders[placeholder] = symbol
                result = result.replace(symbol, placeholder)
        
        return result, placeholders
    
    @staticmethod
    def restore_special_chars(text, placeholders):
        """
        将placeholder恢复为原始特殊符号（递归恢复，直到没有placeholder为止）
        
        Args:
            text (str): 包含placeholder的字符串
            placeholders (dict): placeholder字典 {placeholder: original_symbol}
        
        Returns:
            str: 恢复后的字符串
        """
        result = text
        # 递归恢复：持续替换直到没有更多的placeholder可以被恢复
        max_iterations = 100  # 防止无限循环
        for iteration in range(max_iterations):
            changed = False
            for placeholder, symbol in placeholders.items():
                if placeholder in result:
                    result = result.replace(placeholder, symbol)
                    changed = True
            if not changed:
                # 没有任何替换发生，说明已经完全恢复
                break
        return result

    def expand_path(self, path):
        """展开路径，处理~等特殊字符"""
        try:
            import os
            return os.path.expanduser(os.path.expandvars(path))
        except Exception as e:
            print(f"Path expansion failed: {e}")
            return path

    def resolve_drive_id(self, path, current_shell=None):
        """
        解析路径，返回对应的Google Drive文件夹ID和逻辑路径
        重构后的版本：使用resolve_remote_absolute_path获取逻辑路径，然后从逻辑路径获取Drive ID
        """
        if not self.drive_service:
            return None, None
            
        if not current_shell:
            current_shell = self.main_instance.get_current_shell()
            
        if not current_shell:
            return None, None
        
        try:
            # 步骤1：使用resolve_remote_absolute_path获取规范化的逻辑路径（~/xxx格式）
            logical_path = self.resolve_remote_absolute_path(path, current_shell, return_logical=True)
            
            # 步骤2：从逻辑路径获取Drive ID
            # 处理特殊路径：DRIVE_EQUIVALENT
            def _resolve_id_by_parts(path_parts, base_folder_id, base_logical_path):
                """
                从路径parts逐级获取Drive ID（简化版本）
                
                Args:
                    path_parts (list): 路径组件列表，如["tmp", "subfolder"]
                    base_folder_id (str): 基础文件夹ID
                    base_logical_path (str): 基础逻辑路径（如"~"或"@drive_equivalent"）
                    
                Returns:
                    tuple: (folder_id, logical_path) or (None, None) if path doesn't exist
                """
                current_id = base_folder_id
                current_logical_path = base_logical_path
                
                try:
                    for part in path_parts:
                        # 跳过空组件
                        if not part:
                            continue
                        
                        # 查找该部分对应的文件夹 - 移除max_results限制，使用完整的分页逻辑
                        files_result = self.drive_service.list_files(folder_id=current_id)
                        if not files_result['success']:
                            return None, None
                        
                        found_folder = None
                        for file in files_result['files']:
                            if file['name'] == part and file['mimeType'] == 'application/vnd.google-apps.folder':
                                found_folder = file
                                break
                        
                        if not found_folder:
                            # 路径不存在
                            return None, None
                        
                        # 更新当前ID和逻辑路径
                        current_id = found_folder['id']
                        if current_logical_path == "~":
                            current_logical_path = f"~/{part}"
                        elif current_logical_path == "@":
                            current_logical_path = f"@/{part}"
                        elif current_logical_path == "@drive_equivalent":
                            current_logical_path = f"@drive_equivalent/{part}"
                        else:
                            current_logical_path = f"{current_logical_path}/{part}"
                    
                    return current_id, current_logical_path
                    
                except Exception as e:
                    print(f"Error: Resolve ID by parts failed: {e}")
                    return None, None

            # 处理@路径（代表REMOTE_ENV）
            if logical_path == "@":
                return self.main_instance.REMOTE_ENV_FOLDER_ID, "@"
            elif logical_path.startswith("@/"):
                relative_parts = logical_path[2:].split("/")
                return _resolve_id_by_parts(
                    relative_parts, 
                    self.main_instance.REMOTE_ENV_FOLDER_ID, 
                    "@"
                )
            
            # 处理@drive_equivalent路径（向后兼容）
            if logical_path == "@drive_equivalent":
                return self.main_instance.DRIVE_EQUIVALENT_FOLDER_ID, "@drive_equivalent"
            elif logical_path.startswith("@drive_equivalent/"):
                relative_parts = logical_path[len("@drive_equivalent/"):].split("/")
                return _resolve_id_by_parts(
                    relative_parts, 
                    self.main_instance.DRIVE_EQUIVALENT_FOLDER_ID, 
                    "@drive_equivalent"
                )
            # 处理REMOTE_ROOT路径（~/xxx格式）
            elif logical_path == "~":
                return self.main_instance.REMOTE_ROOT_FOLDER_ID, "~"
            elif logical_path.startswith("~/"):
                # 从REMOTE_ROOT开始逐层访问
                relative_parts = logical_path[2:].split("/") if logical_path[2:] else []
                return _resolve_id_by_parts(
                    relative_parts, 
                    self.main_instance.REMOTE_ROOT_FOLDER_ID, 
                    "~"
                )
            else:
                # 不应该到达这里（所有路径都应该被规范化为~/xxx格式）
                print(f"Warning: Unexpected logical_path format: {logical_path}")
                return None, None
                
        except Exception as e:
            print(f"Error: Resolve drive ID failed: {e}")
            return None, None
    
    def undo_local_path_user_expansion(self, command_or_path):
        """
        将bash shell扩展的本地路径转换回远程路径格式
        
        当用户输入 'GDS cd ~/tmp/test' 时，bash会将 ~/tmp/test 扩展为 /Users/username/tmp/test
        这个函数将其转换回 ~/tmp/test 格式，以便正确解析为远程路径
        
        Args:
            command_or_path: 可以是完整的命令字符串或单个路径
        
        Returns:
            转换后的命令字符串或路径
        """
        import os
        import uuid
        import subprocess
        
        # 特殊处理：如果输入包含实际的换行符，直接返回
        # 因为这些不是路径，而是多行字符串参数（如echo -e的内容）
        # 使用bash -c -x测试会导致换行符被误解释为多个命令
        if '\n' in command_or_path:
            # 仍然需要替换可能已展开的home目录
            home_dir = os.path.expanduser("~")
            result = command_or_path.replace(home_dir, '~')
            return result
        
        # 获取用户的home目录
        home_dir = os.path.expanduser("~")
        
        # 步骤1: 先保护所有特殊符号（包括引号字符串、重定向等）
        # 这样引号内的~就不会被后续步骤替换
        protected_command, special_placeholders = self.protect_special_chars(command_or_path)
        
        # 步骤2: 保护原始的~（此时引号内的~已经被保护在引号字符串placeholder中）
        import uuid
        tilde_placeholder = f"__TILDE_PLACEHOLDER_{uuid.uuid4().hex[:8].upper()}__"
        protected_command = protected_command.replace('~', tilde_placeholder)
        
        # 步骤3: 将已展开的home_dir替换回~
        suspicious_command = protected_command.replace(home_dir, '~')
        
        # 步骤4: 直接使用suspicious_command，不进行bash测试
        # 原因：对于bash -c命令，placeholder已经破坏了bash语法，bash测试会产生错误的输出
        # 而且bash -c命令本身就是要在远端执行的，不需要在本地测试
        final_command = suspicious_command
        
        # 步骤5: 统一恢复所有placeholder
        result = final_command.replace(tilde_placeholder, '~')
        result = self.restore_special_chars(result, special_placeholders)
        return result
    
    def get_parent_path(self, path):
        """获取路径的父目录，支持~和@前缀"""
        if path == "~":
            return None  # 根目录没有父目录，返回None表示无效
        
        if path == "@":
            return None  # REMOTE_ENV根目录没有父目录，返回None表示无效
        
        if path.startswith("~/"):
            parts = path.split("/")
            if len(parts) <= 2:  # ~/something -> ~
                return "~"
            else:  # ~/a/b/c -> ~/a/b
                return "/".join(parts[:-1])
        
        if path.startswith("@/"):
            parts = path.split("/")
            if len(parts) <= 2:  # @/something -> @
                return "@"
            else:  # @/a/b/c -> @/a/b
                return "/".join(parts[:-1])
        
        return path
    
    def join_paths(self, base_path, relative_path):
        """连接基础路径和相对路径，支持~和@前缀"""
        if not relative_path:
            return base_path
        
        if base_path == "~":
            return f"~/{relative_path}"
        elif base_path == "@":
            return f"@/{relative_path}"
        else:
            return f"{base_path}/{relative_path}"
    
    def normalize_path_components(self, base_path, relative_path):
        """规范化路径组件，处理路径中的 .. 和 .
        
        支持~（REMOTE_ROOT）和@（REMOTE_ENV）前缀
        """
        try:
            # 先连接路径
            combined_path = self.join_paths(base_path, relative_path)
            
            # 处理@路径（REMOTE_ENV）
            if combined_path == "@":
                return "@"
            
            if combined_path.startswith("@/"):
                # 移除 @/ 前缀
                path_without_root = combined_path[2:]
                if not path_without_root:
                    return "@"
                
                # 分割路径组件
                components = path_without_root.split("/")
                normalized_components = []
                
                for component in components:
                    if component == "." or component == "":
                        # 跳过当前目录和空组件
                        continue
                    elif component == "..":
                        # 父目录 - 移除上一个组件
                        if normalized_components:
                            normalized_components.pop()
                        # 如果没有组件可移除，说明已经到根目录，忽略
                    else:
                        # 普通目录名
                        normalized_components.append(component)
                
                # 重建路径
                if not normalized_components:
                    return "@"
                else:
                    return "@/" + "/".join(normalized_components)
            
            # 处理~路径（REMOTE_ROOT）
            if combined_path == "~":
                return "~"
            
            if not combined_path.startswith("~/"):
                return combined_path
            
            # 移除 ~/ 前缀
            path_without_root = combined_path[2:]
            if not path_without_root:
                return "~"
            
            # 分割路径组件
            components = path_without_root.split("/")
            normalized_components = []
            
            for component in components:
                if component == "." or component == "":
                    # 跳过当前目录和空组件
                    continue
                elif component == "..":
                    # 父目录 - 移除上一个组件
                    if normalized_components:
                        normalized_components.pop()
                    # 如果没有组件可移除，说明已经到根目录，忽略
                else:
                    # 普通目录名
                    normalized_components.append(component)
            
            # 重建路径
            if not normalized_components:
                result = "~"
            else:
                result = "~/" + "/".join(normalized_components)
            
            
            return result
                
        except Exception as e:
            # 如果规范化失败，返回原始连接的路径
            return self.join_paths(base_path, relative_path)

    def normalize_logical_path(self, logical_path):
        """简化的逻辑路径规范化：使用堆栈方法处理../和.
        
        Args:
            logical_path (str): 逻辑路径，如 ~/test/level1/../level2
            
        Returns:
            str: 规范化后的逻辑路径，如果路径无效返回None
        """
        if not logical_path:
            return logical_path
            
        # 处理~路径
        if logical_path == "~":
            return "~"
        elif logical_path.startswith("~/"):
            path_part = logical_path[2:]  # 去掉~/
            if not path_part:
                return "~"
            
            # 分割并规范化
            components = path_part.split("/")
            stack = []
            
            for component in components:
                if component == "" or component == ".":
                    continue
                elif component == "..":
                    if stack:
                        stack.pop()
                    else:
                        # 尝试在根目录上级，这是无效的
                        return None  # 返回None表示路径无效
                else:
                    stack.append(component)
            
            if not stack:
                return "~"
            else:
                return "~/" + "/".join(stack)
        
        # 处理@路径
        elif logical_path == "@":
            return "@"
        elif logical_path.startswith("@/"):
            path_part = logical_path[2:]  # 去掉@/
            if not path_part:
                return "@"
            
            # 分割并规范化
            components = path_part.split("/")
            stack = []
            
            for component in components:
                if component == "" or component == ".":
                    continue
                elif component == "..":
                    if stack:
                        stack.pop()
                    else:
                        # 尝试在根目录上级，这是无效的
                        return None  # 返回None表示路径无效
                else:
                    stack.append(component)
            
            if not stack:
                return "@"
            else:
                return "@/" + "/".join(stack)
        
        # 其他情况直接返回
        return logical_path

    def resolve_remote_absolute_path(self, path, current_shell=None, return_logical=False):
        """
        通用路径解析接口：将相对路径解析为远端绝对路径
        
        Args:
            path (str): 要解析的路径
            current_shell (dict): 当前shell状态，如果为None则自动获取
            return_logical (bool): 如果为True，返回逻辑路径（~/xxx），否则返回完整远端路径
            
        Returns:
            str: 解析后的路径（根据return_logical参数决定格式）
        """
        try:
            if not current_shell:
                current_shell = self.main_instance.get_current_shell()
                if not current_shell:
                    raise ValueError("Current shell or default shell both not available for path resolution. ")
            
            # 获取当前路径
            current_path = current_shell.get("current_path", "~")
            remote_root_path = self.main_instance.REMOTE_ROOT if self.main_instance else "/content/drive/MyDrive/REMOTE_ROOT"
            remote_env_path = self.main_instance.REMOTE_ENV if self.main_instance else "/content/drive/MyDrive/REMOTE_ENV"
            
            #### Special Processing for REMOTE_ROOT and REMOTE_ENV ####
            #### 正常来讲，用户不会输入绝对路径，而是输入~以及@开头的逻辑路径 ####
            # 首先检查是否是完整的远程路径，需要转换回逻辑路径
            if path.startswith(remote_root_path):
                if path == remote_root_path:
                    logical_path = "~"
                elif path.startswith(f"{remote_root_path}/"):
                    relative_part = path[len(remote_root_path) + 1:]
                    logical_path = f"~/{relative_part}"
                else:
                    logical_path = path  # 不应该到这里，但保持原样
                
                if return_logical:
                    return logical_path
                else:
                    return path  # 已经是绝对路径
            elif path.startswith(remote_env_path):
                if path == remote_env_path:
                    logical_path = "@"
                elif path.startswith(f"{remote_env_path}/"):
                    relative_part = path[len(remote_env_path) + 1:]
                    logical_path = f"@/{relative_part}"
                else:
                    logical_path = path  # 不应该到这里，但保持原样
                
                if return_logical:
                    return logical_path
                else:
                    return path  # 已经是绝对路径
            
            # 如果仍然是绝对路径（以/开头），转换为~/xxx格式
            elif path.startswith("/"):
                # 真正的绝对路径，映射为逻辑路径
                # 例如 /tmp/file.txt -> ~/tmp/file.txt
                relative_part = path[1:]  # 去掉前导的 /
                if relative_part:
                    logical_path = f"~/{relative_part}"
                else:
                    logical_path = "~"
                # 根据return_logical决定返回格式
                if return_logical:
                    return logical_path
                else:
                    return f"{remote_root_path}/{relative_part}" if relative_part else remote_root_path
            
            # 处理@开头的路径（代表REMOTE_ENV）
            if path.startswith("@"):
                logical_path = path
                if '../' in path or '/./' in path or path.endswith('/..') or path.endswith('/.'):
                    logical_path = self.normalize_path_components("@", path[2:] if path.startswith("@/") else path[1:])
                
                # 根据return_logical决定返回格式
                if return_logical:
                    return logical_path
                else:
                    if logical_path == "@":
                        return remote_env_path
                    elif logical_path.startswith("@/"):
                        relative_part = logical_path[2:]
                        return f"{remote_env_path}/{relative_part}"
                    else:
                        return f"{remote_env_path}/{logical_path[1:]}"
            
            # 计算逻辑路径（~/xxx格式）
            if path.startswith("~"):
                # 使用简化的规范化方法
                logical_path = self.normalize_logical_path(path)
                if logical_path is None:
                    # 路径无效（如在根目录尝试..）
                    return None
            elif path == "." or path == "":
                # 当前目录
                logical_path = current_path
            else:
                # 相对路径，需要基于当前目录计算
                if path.startswith("./"):
                    path = path[2:]  # 移除./
                
                # 处理父目录路径
                if path == "..":
                    logical_path = self.get_parent_path(current_path)
                    if logical_path is None:
                        # 在根目录尝试..，无效路径
                        return None
                elif path.startswith("../"):
                    # 递归处理父目录路径
                    parent_path = self.get_parent_path(current_path)
                    if parent_path is None:
                        # 在根目录尝试../，无效路径
                        return None
                    remaining_path = path[3:]  # 移除../
                    # 递归调用，传入parent_path作为current_path，同时传递return_logical参数
                    return self.resolve_remote_absolute_path(remaining_path, {"current_path": parent_path}, return_logical=return_logical)
                else:
                    # 普通相对路径，使用normalize处理
                    logical_path = self.normalize_path_components(current_path, path)
            
            # 根据return_logical参数决定返回格式
            if return_logical:
                return logical_path
            else:
                if logical_path == "~":
                    return remote_root_path
                elif logical_path.startswith("~/"):
                    relative_part = logical_path[2:]
                    return f"{remote_root_path}/{relative_part}"
                else:
                    # 不应该到达这里，但作为fallback
                    return f"{remote_root_path}/{logical_path}"
            
        except Exception as e:
            # 如果解析失败，返回原路径
            return path
