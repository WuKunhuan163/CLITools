#!/usr/bin/env python3
"""
Google Drive Shell - Virtual environment management
"""

class VenvApiManager:
    """虚拟环境API管理器 - 统一处理所有虚拟环境相关的API操作"""
    
    def __init__(self, drive_service, main_instance):
        self.drive_service = drive_service
        self.main_instance = main_instance
    
    def read_venv_states(self):
        """读取虚拟环境状态文件"""
        try:
            import json
            
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API服务未初始化"}
            
            # 构建文件路径：REMOTE_ENV/venv/venv_states.json
            venv_states_filename = "venv_states.json"
            
            # 首先需要找到REMOTE_ENV/venv文件夹
            try:
                # 列出REMOTE_ENV文件夹的内容，寻找venv子文件夹
                env_files_result = self.drive_service.list_files(
                    folder_id=self.main_instance.REMOTE_ENV_FOLDER_ID, 
                    max_results=100
                )
                
                if not env_files_result['success']:
                    return {"success": False, "error": "无法列出REMOTE_ENV目录内容"}
                
                # 寻找venv文件夹
                venv_folder_id = None
                for file in env_files_result['files']:
                    if file['name'] == 'venv' and file['mimeType'] == 'application/vnd.google-apps.folder':
                        venv_folder_id = file['id']
                        break
                
                if not venv_folder_id:
                    # venv文件夹不存在，返回空状态
                    return {"success": True, "data": {}, "note": "venv文件夹不存在"}
                
                # 在venv文件夹中寻找venv_states.json文件
                venv_files_result = self.drive_service.list_files(
                    folder_id=venv_folder_id, 
                    max_results=100
                )
                
                if not venv_files_result['success']:
                    return {"success": False, "error": "无法列出venv目录内容"}
                
                # 寻找venv_states.json文件
                states_file_id = None
                for file in venv_files_result['files']:
                    if file['name'] == venv_states_filename:
                        states_file_id = file['id']
                        break
                
                if not states_file_id:
                    # 文件不存在，返回空状态
                    return {"success": True, "data": {}, "note": "venv_states.json文件不存在"}
                
                # 读取文件内容
                try:
                    import io
                    from googleapiclient.http import MediaIoBaseDownload
                    
                    request = self.drive_service.service.files().get_media(fileId=states_file_id)
                    fh = io.BytesIO()
                    downloader = MediaIoBaseDownload(fh, request)
                    
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()
                    
                    content = fh.getvalue().decode('utf-8', errors='replace')
                    
                    # 解析JSON内容
                    try:
                        states_data = json.loads(content)
                        return {"success": True, "data": states_data if isinstance(states_data, dict) else {}}
                    except json.JSONDecodeError as e:
                        return {"success": False, "error": f"JSON解析失败: {e}"}
                        
                except Exception as e:
                    return {"success": False, "error": f"读取文件内容失败: {e}"}
                    
            except Exception as e:
                return {"success": False, "error": f"查找文件失败: {e}"}
                
        except Exception as e:
            return {"success": False, "error": f"API读取venv状态失败: {e}"}
    
    def list_venv_environments(self):
        """列出所有虚拟环境"""
        try:
            if not self.drive_service:
                return []
            
            # 首先需要找到REMOTE_ENV/venv文件夹
            try:
                # 列出REMOTE_ENV文件夹的内容，寻找venv子文件夹
                env_files_result = self.drive_service.list_files(
                    folder_id=self.main_instance.REMOTE_ENV_FOLDER_ID, 
                    max_results=100
                )
                
                if not env_files_result['success']:
                    return []
                
                # 寻找venv文件夹
                venv_folder_id = None
                for file in env_files_result['files']:
                    if file['name'] == 'venv' and file['mimeType'] == 'application/vnd.google-apps.folder':
                        venv_folder_id = file['id']
                        break
                
                if not venv_folder_id:
                    # venv文件夹不存在
                    return []
                
                # 在venv文件夹中列出所有文件夹（虚拟环境）
                venv_files_result = self.drive_service.list_files(
                    folder_id=venv_folder_id, 
                    max_results=100
                )
                
                if not venv_files_result['success']:
                    return []
                
                # 过滤出文件夹（虚拟环境），排除venv_states.json等文件
                env_names = []
                for file in venv_files_result['files']:
                    if (file['mimeType'] == 'application/vnd.google-apps.folder' and 
                        not file['name'].startswith('.') and 
                        file['name'] != 'venv_states.json'):
                        env_names.append(file['name'])
                
                return env_names
                    
            except Exception as e:
                return []
                
        except Exception as e:
            return []
    
    def read_venv_states_via_api(self):
        """通过API读取venv状态文件（如果可用）"""
        # 这是一个回退方法，暂未实现API读取
        return {"success": False, "error": "API read not implemented"}
    
    def load_all_venv_states(self):
        """从统一的JSON文件加载所有虚拟环境状态（优先使用API，回退到远程命令）"""
        try:
            import json
            
            # 首先尝试通过API读取
            try:
                api_result = self.read_venv_states_via_api()
                if api_result.get("success"):
                    return api_result.get("data", {{}})
            except Exception as api_error:
                print(f"API call failed: {{api_error}}")
            
            # 回退到远程命令
            check_command = f'cat "{{state_file}}" 2>/dev/null || echo "{{}}"'
            result = self.main_instance.execute_command_interface("bash", ["-c", check_command])
            if result.get("success") and result.get("stdout"):
                stdout_content = result["stdout"].strip()
                try:
                    state_data = json.loads(stdout_content)
                    return state_data if isinstance(state_data, dict) else {{}}
                except json.JSONDecodeError as e:
                    return {{}}
            else:
                self.create_initial_venv_states_file()
                return {{}}
            
        except Exception: 
            import traceback
            traceback.print_exc()
            return {{}}
    
    def create_initial_venv_states_file(self):
        """创建初始的虚拟环境状态文件"""
        try:
            import json
            state_file = self.get_venv_state_file_path()
            
            # 创建基本的JSON结构
            import datetime
            initial_structure = {
                "environments": {},
                "created_at": datetime.datetime.now().isoformat(),
                "version": "1.0"
            }
            
            # 确保目录存在
            venv_dir = f"{self.get_venv_base_path()}"
            mkdir_command = f'mkdir -p "{venv_dir}"'
            mkdir_result = self.main_instance.execute_command_interface("bash", ["-c", mkdir_command])
            print(f"创建目录结果: {mkdir_result}")
            
            # 写入初始JSON文件
            json_content = json.dumps(initial_structure, indent=2, ensure_ascii=False)
            create_command = f'cat > "{state_file}" << \'EOF\'\n{json_content}\nEOF'
            create_result = self.main_instance.execute_command_interface("bash", ["-c", create_command])
            print(f"Create JSON file result: {create_result}")
            
            if create_result.get("success"):
                print(f"Successfully created initial state file: {state_file}")
                return True
            else:
                print(f"Error: Create state file failed: {create_result.get('error')}")
                return False
            
        except Exception as e:
            print(f"Error: Create initial state file failed: {e}")
            return False
