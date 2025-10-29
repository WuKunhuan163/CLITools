from .base_command import BaseCommand

class LsCommand(BaseCommand):
    @property
    def command_name(self):
        return "ls"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行ls命令"""
        # 解析参数
        detailed = False
        recursive = False
        path = None
        
        for arg in args:
            if arg == '--detailed':
                detailed = True
            elif arg == '-R':
                recursive = True
            elif not arg.startswith('-'):
                path = arg
        
        # 检查是否包含通配符
        if path and ('*' in path or '?' in path or '[' in path):
            return self.shell._handle_wildcard_ls(path)
        
        # 调用shell的ls方法
        result = self.shell.cmd_ls(path, detailed=detailed, recursive=recursive)
        
        if result.get("success", False):
            files = result.get("files", [])
            folders = result.get("folders", [])
            all_items = folders + files
            
            if all_items:
                # 按名称排序，文件夹优先
                sorted_folders = sorted(folders, key=lambda x: x.get('name', '').lower())
                sorted_files = sorted(files, key=lambda x: x.get('name', '').lower())
                
                # 合并列表，文件夹在前
                all_sorted_items = sorted_folders + sorted_files
                
                # 简单的列表格式，类似bash ls
                for item in all_sorted_items:
                    name = item.get('name', 'Unknown')
                    if item.get('mimeType') == 'application/vnd.google-apps.folder':
                        print(f"{name}/")
                    else:
                        print(name)
            
            return 0
        else:
            print(result.get("error", "Failed to list directory"))
            return 1


    def cmd_ls(self, path=None, detailed=False, recursive=False, show_hidden=False):
        """列出目录内容，支持递归、详细模式和扩展信息模式，支持文件路径"""
        try:
            
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API服务未初始化"}
                
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell，请先创建或切换到一个shell"}
            
            
            if path is None or path == ".":
                # 当前目录
                target_folder_id = current_shell.get("current_folder_id", self.main_instance.REMOTE_ROOT_FOLDER_ID)
                display_path = current_shell.get("current_path", "~")
            elif path == "~":
                # 根目录
                target_folder_id = self.main_instance.REMOTE_ROOT_FOLDER_ID
                display_path = "~"
            else:
                # 首先将本地路径转换为远程路径格式以便在错误消息中正确显示
                converted_path = self.main_instance.path_resolver._convert_local_path_to_remote(path)
                
                # 首先尝试作为目录解析
                target_folder_id, display_path = self.main_instance.resolve_path(path, current_shell)
                
                if not target_folder_id:
                    file_result = self._resolve_file_path(path, current_shell)
                    if file_result:
                        return {
                            "success": True,
                            "path": converted_path,
                            "files": [file_result],
                            "folders": [],
                            "count": 1,
                            "mode": "single_file"
                        }
                    else:
                        return {"success": False, "error": f"Path not found: {converted_path}"}
            
            if recursive:
                return self.ls_recursive(target_folder_id, display_path, detailed, show_hidden)
            else:
                # 内联_ls_single的逻辑
                result = self.drive_service.list_files(folder_id=target_folder_id, max_results=None)
                
                if result['success']:
                    files = result['files']
                    
                    # 添加网页链接到每个文件
                    for file in files:
                        file['url'] = self.generate_web_url(file)
                    
                    # 按名称排序，文件夹优先
                    folders = sorted([f for f in files if f['mimeType'] == 'application/vnd.google-apps.folder'], 
                                   key=lambda x: x['name'].lower())
                    other_files = sorted([f for f in files if f['mimeType'] != 'application/vnd.google-apps.folder'], 
                                       key=lambda x: x['name'].lower())
                    
                    # 去重处理
                    seen_names = set()
                    clean_folders = []
                    clean_files = []
                    
                    # 处理文件夹
                    for folder in folders:
                        if folder["name"] not in seen_names:
                            clean_folders.append(folder)
                            seen_names.add(folder["name"])
                    
                    # 处理文件
                    for file in other_files:
                        if file["name"] not in seen_names:
                            clean_files.append(file)
                            seen_names.add(file["name"])
                    
                    if detailed:
                        # 详细模式：返回完整JSON
                        return {
                            "success": True,
                            "path": display_path,
                            "folder_id": target_folder_id,
                            "folder_url": self._generate_folder_url(target_folder_id),
                            "files": clean_files,  # 只有非文件夹文件
                            "folders": clean_folders,  # 只有文件夹
                            "count": len(clean_folders) + len(clean_files),
                            "mode": "detailed"
                        }
                    else:
                        # bash风格：只返回文件名列表
                        return {
                            "success": True,
                            "path": display_path,
                            "folder_id": target_folder_id,
                            "files": clean_files,  # 只有非文件夹文件
                            "folders": clean_folders,  # 只有文件夹
                            "count": len(clean_folders) + len(clean_files),
                            "mode": "bash"
                        }
                else:
                    return {"success": False, "error": f"列出文件失败: {result['error']}"}
                
        except Exception as e:

            return {"success": False, "error": f"执行ls命令时出错: {e}"}

    def ls_recursive(self, root_folder_id, root_path, detailed, show_hidden=False, max_depth=5):
        """递归列出目录内容"""
        try:
            all_items = []
            visited_folders = set()  # 防止循环引用
            
            def scan_folder(folder_id, folder_path, depth=0):
                # 深度限制
                if depth > max_depth:
                    return
                
                # 循环检测
                if folder_id in visited_folders:
                    return
                visited_folders.add(folder_id)
                
                result = self.drive_service.list_files(folder_id=folder_id, max_results=100)
                if not result['success']:
                    visited_folders.discard(folder_id)  # 失败时移除，允许重试
                    return
                
                files = result['files']
                
                # 添加网页链接
                for file in files:
                    file['url'] = self.generate_web_url(file)
                    file['path'] = folder_path
                    file['depth'] = depth
                    all_items.append(file)
                    
                    # 如果是文件夹，递归扫描
                    if file['mimeType'] == 'application/vnd.google-apps.folder':
                        sub_path = f"{folder_path}/{file['name']}" if folder_path != "~" else f"~/{file['name']}"
                        scan_folder(file['id'], sub_path, depth + 1)
                
                visited_folders.discard(folder_id)  # 扫描完成后移除，允许在其他路径中再次访问
            
            # 开始递归扫描
            scan_folder(root_folder_id, root_path)
            
            # 按路径和名称排序
            all_items.sort(key=lambda x: (x['path'], x['name'].lower()))
            
            # 分离文件夹和文件
            folders = [f for f in all_items if f['mimeType'] == 'application/vnd.google-apps.folder']
            other_files = [f for f in all_items if f['mimeType'] != 'application/vnd.google-apps.folder']
            
            if detailed:
                # 详细模式：返回嵌套的树形结构
                nested_structure = self.build_nested_structure(all_items, root_path)
                
                return {
                    "success": True,
                    "path": root_path,
                    "folder_id": root_folder_id,
                    "folder_url": self._generate_folder_url(root_folder_id),
                    "files": nested_structure["files"],
                    "folders": nested_structure["folders"],  # 每个文件夹包含自己的files和folders
                    "count": len(all_items),
                    "mode": "recursive_detailed"
                }
            else:
                # 简单模式：只返回基本信息
                return {
                    "success": True,
                    "path": root_path,
                    "folder_id": root_folder_id,
                    "files": other_files,
                    "folders": folders,
                    "all_items": all_items,
                    "count": len(all_items),
                    "mode": "recursive_bash"
                }
                
        except Exception as e:
            return {"success": False, "error": f"递归列出目录时出错: {e}"}

    def build_nested_structure(self, all_items, root_path):
        """构建嵌套的文件夹结构，每个文件夹包含自己的files和folders"""
        try:
            # 按路径分组所有项目
            path_groups = {}
            
            for item in all_items:
                path = item['path']
                if path not in path_groups:
                    path_groups[path] = {'files': [], 'folders': []}
                
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    path_groups[path]['folders'].append(item)
                else:
                    path_groups[path]['files'].append(item)
            
            # 构建嵌套结构
            def build_folder_content(folder_path):
                content = path_groups.get(folder_path, {'files': [], 'folders': []})
                
                # 为每个子文件夹递归构建内容
                enriched_folders = []
                for folder in content['folders']:
                    folder_copy = folder.copy()
                    sub_path = f"{folder_path}/{folder['name']}" if folder_path != "~" else f"~/{folder['name']}"
                    sub_content = build_folder_content(sub_path)
                    
                    # 将子内容添加到文件夹中
                    folder_copy['files'] = sub_content['files']
                    folder_copy['folders'] = sub_content['folders']
                    enriched_folders.append(folder_copy)
                
                return {
                    'files': content['files'],
                    'folders': enriched_folders
                }
            
            # 从根路径开始构建
            return build_folder_content(root_path)
            
        except Exception as e:
            return {'files': [], 'folders': [], 'error': str(e)}


    def cmd_pwd(self):
        """显示当前路径"""
        try:
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell，请先创建或切换到一个shell"}
            
            return {
                "success": True,
                "current_path": current_shell.get("current_path", "~"),
                "home_url": self.main_instance.HOME_URL,
                "shell_id": current_shell["id"],
                "shell_name": current_shell["name"]
            }
            
        except Exception as e:
            return {"success": False, "error": f"获取当前路径时出错: {e}"}


    def cmd_cd(self, path):
        """切换目录"""
        try:
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell，请先创建或切换到一个shell"}
            
            if not path:
                path = "~"
            
            # 转换bash扩展的本地路径为远程路径格式
            path = self.main_instance.path_resolver._convert_local_path_to_remote(path)
            
            # 使用新的路径解析器计算绝对路径
            current_shell_path = current_shell.get("current_path", "~")
            absolute_path = self.main_instance.path_resolver.compute_absolute_path(current_shell_path, path)
            
            # 使用统一的cmd_ls接口检测目录是否存在
            ls_result = self.main_instance.cmd_ls(absolute_path)
            
            if not ls_result.get('success'): 
                return {"success": False, "error": f"Directory does not exist: {path} (resolved to: {absolute_path})"}
            
            # 如果ls成功，说明目录存在，使用resolve_path获取目标ID和路径
            target_id, target_path = self.main_instance.resolve_path(absolute_path, current_shell)
            
            if not target_id:
                return {"success": False, "error": f"Directory does not exist: {path} (resolved path failed)"}
            
            # 更新shell状态
            shells_data = self.main_instance.load_shells()
            shell_id = current_shell['id']
            
            shells_data["shells"][shell_id]["current_path"] = target_path
            shells_data["shells"][shell_id]["current_folder_id"] = target_id
            shells_data["shells"][shell_id]["last_accessed"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            if self.main_instance.save_shells(shells_data):
                return {
                    "success": True,
                    "new_path": target_path,
                    "folder_id": target_id,
                    "message": f"Switched to directory: {target_path}"
                }
            else:
                return {"success": False, "error": "Save shell state failed"}
                
        except Exception as e:
            return {"success": False, "error": f"Execute cd command failed: {e}"}

