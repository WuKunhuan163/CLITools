"""
Venv command handler for GDS.
"""
from typing import List
from .base_command import BaseCommand
import json

class VenvCommand(BaseCommand):
    """Handler for venv commands."""
    
    @property
    def command_name(self) -> str:
        return "venv"
    
    def execute(self, cmd: str, args: List[str], **kwargs) -> int:
        """Execute venv command."""
        # 检查是否请求帮助
        if '--help' in args or '-h' in args:
            self.show_help()
            return 0
            
        if not args:
            self.print_error("venv command needs arguments")
            return 1

        result = self.cmd_venv(*args)
        if result.get("success", False): 
            self.shell.sync_venv_state_to_local_shell(args)
            return 0
        else:
            error_message = result.get("error", "Virtual environment operation failed")
            self.print_error(error_message)
            return 1

    def show_help(self):
        """显示venv命令帮助信息"""
        print("GDS Virtual Environment Command Help")
        print("=" * 50)
        print()
        print("USAGE:")
        print("  GDS venv --create <env_name>        # Create virtual environment")
        print("  GDS venv --delete <env_name>        # Delete virtual environment")
        print("  GDS venv --activate <env_name>      # Activate virtual environment")
        print("  GDS venv --deactivate               # Deactivate current environment")
        print("  GDS venv --list                     # List all virtual environments")
        print("  GDS venv --current                  # Show current active environment")
        print("  GDS venv --protect <env_name>       # Protect environment from deletion")
        print("  GDS venv --unprotect <env_name>     # Remove protection")
        print("  GDS venv --help                     # Show this help")
        print()
        print("DESCRIPTION:")
        print("  Manage Python virtual environments in the remote environment.")
        print("  Provides isolation for different projects and their dependencies.")
        print()
        print("EXAMPLES:")
        print("  GDS venv --create myproject         # Create 'myproject' environment")
        print("  GDS venv --activate myproject       # Activate 'myproject'")
        print("  GDS venv --list                     # List all environments")
        print("  GDS venv --current                  # Check current environment")
        print("  GDS venv --deactivate               # Deactivate current environment")
        print("  GDS venv --delete myproject         # Delete 'myproject' environment")
        print()
        print("RELATED COMMANDS:")
        print("  GDS python --help                   # Python execution")
        print("  GDS pip --help                      # Package management")
        print("  GDS pyenv --help                    # Python version management")

    def cmd_venv(self, *args):
        """
        虚拟环境管理命令
        
        支持的子命令：
        - --create <env_name>: 创建虚拟环境
        - --delete <env_name>: 删除虚拟环境
        - --activate <env_name>: 激活虚拟环境（设置PYTHONPATH）
        - --deactivate: 取消激活虚拟环境（清除PYTHONPATH）
        - --list: 列出所有虚拟环境
        - --current: 显示当前激活的虚拟环境
        - --protect <env_name>: 保护虚拟环境（防止误删）
        - --unprotect <env_name>: 取消保护虚拟环境
        
        Args:
            *args: 命令参数
            
        Returns:
            dict: 操作结果
        """
        try:
            if not args:
                return {
                    "success": False,
                    "error": "Usage: venv --create|--delete|--activate|--deactivate|--list|--current|--protect|--unprotect [env_name...]"
                }
            
            action = args[0]
            env_names = args[1:] if len(args) > 1 else []
            
            if action == "--create":
                if not env_names:
                    return {"success": False, "error": "Please specify at least one environment name"}
                return self.venv_create_batch(env_names)
            elif action == "--delete":
                if not env_names:
                    return {"success": False, "error": "Please specify at least one environment name"}
                return self.venv_delete_batch(env_names)
            elif action == "--activate":
                if len(env_names) != 1:
                    return {"success": False, "error": "Please specify exactly one environment name for activation"}
                return self.venv_activate(env_names[0])
            elif action == "--deactivate":
                return self.venv_deactivate()
            elif action == "--list":
                return self.venv_list()
            elif action == "--current":
                return self.venv_current()
            elif action == "--protect":
                if not env_names:
                    return {"success": False, "error": "Please specify at least one environment name"}
                return self.venv_protect_batch(env_names)
            elif action == "--unprotect":
                if not env_names:
                    return {"success": False, "error": "Please specify at least one environment name"}
                return self.venv_protect_batch(env_names, protected=False)
            else:
                return {
                    "success": False,
                    "error": f"Unknown venv command: {action}. Supported commands: --create, --delete, --activate, --deactivate, --list, --current, --protect, --unprotect"
                }
                
        except Exception as e:
            return {"success": False, "error": f"venv命令执行失败: {str(e)}"}
    
    def venv_create_batch(self, env_names):
        """批量创建虚拟环境"""
        results = []
        for env_name in env_names:
            result = self.venv_create(env_name)
            results.append(result)
        
        # 返回综合结果
        all_success = all(r.get("success", False) for r in results)
        if all_success:
            return {"success": True, "message": f"Created {len(env_names)} virtual environment(s)"}
        else:
            failed = [r.get("error", "Unknown error") for r in results if not r.get("success", False)]
            return {"success": False, "error": failed}
    
    def get_venv_base_path(self):
        """获取虚拟环境基础路径"""
        return f"{self.shell.REMOTE_ENV}/venv"
    
    def get_venv_api_manager(self):
        """获取虚拟环境API管理器"""
        if not hasattr(self, '_venv_api_manager'):
            from ..venv_manager import VenvApiManager
            self._venv_api_manager = VenvApiManager(self.shell.drive_service , self.shell)
        return self._venv_api_manager
    
    def get_venv_state_file_path(self):
        """获取虚拟环境状态文件路径（统一的JSON格式）"""
        return f"{self.get_venv_base_path()}/venv_states.json"
    
    def venv_create(self, env_name):
        """创建虚拟环境"""
        if not env_name:
            return {"success": False, "error": "Environment name required"}
        
        if env_name.startswith('.'):
            return {"success": False, "error": "Environment name cannot start with '.'"}
        
        try:
            # 使用正确的路径：REMOTE_ENV/venv
            env_path = f"{self.get_venv_base_path()}/{env_name}"
            

            
            # 使用API管理器检查环境是否已存在
            api_manager = self.get_venv_api_manager()
            existing_envs = api_manager.list_venv_environments()
            
            if env_name in existing_envs:
                return {
                    "success": False,
                    "error": f"Virtual environment '{env_name}' already exists"
                }
            commands = [f"mkdir -p '{env_path}'"]
            command_script = " && ".join(commands)
            result = self.shell.execute_command_interface("bash", ["-c", command_script])
            
            if result.get("success", False):
                data = result.get("data", {})
                exit_code = data.get("exit_code") if "exit_code" in data else result.get("exit_code", -1)
                stdout = data.get("stdout") if "stdout" in data else result.get("stdout", "")
                if exit_code == 0:
                    print(f"Virtual environment '{env_name}' created successfully")
                    print(f"Environment path: {env_path}")
                    return {"success": True, "message": f"Virtual environment '{env_name}' created successfully"}
                else:
                    stderr = data.get("stderr") if "stderr" in data else result.get("stderr", "")
                    error_details = []
                    error_details.append(f"remote command failed with exit code {exit_code}")
                    
                    if stdout.strip():
                        error_details.append(f"stdout: {stdout.strip()}")
                    
                    if stderr.strip():
                        error_details.append(f"stderr: {stderr.strip()}")
                    
                    error_message = f"Failed to create virtual environment: {'; '.join(error_details)}"
                    return {"success": False, "error": error_message}
            else:
                error_msg = f"Failed to create virtual environment: {result.get('error', 'Unknown error')}"
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            return {"success": False, "error": f"Error creating environment '{env_name}': {str(e)}"}
    
    def venv_delete_batch(self, env_names):
        """批量删除虚拟环境（优化版：一个远程命令完成检查和删除）"""
        # 获取被保护的环境列表
        protected_envs = self.get_protected_environments()
        candidate_envs = []
        skipped_protected = []
        
        for env_name in env_names:
            if env_name in protected_envs:
                skipped_protected.append(env_name)
            else:
                candidate_envs.append(env_name)
        
        if skipped_protected:
            print(f"Warning:  Skipped {len(skipped_protected)} protected environment(s): {', '.join(skipped_protected)}")
        
        if not candidate_envs:
            return {
                "success": True,
                "message": "All specified environments are protected, no deletions performed",
                "skipped": {"protected": skipped_protected}
            }
        
        print(f"Deleting {len(candidate_envs)} virtual environment(s): {', '.join(candidate_envs)}")
        
        # 生成智能删除命令：在远程端进行所有检查
        current_shell = self.shell.get_current_shell()
        shell_id = current_shell.get("id", "default") if current_shell else "default"
        current_venv_file = f"{self.shell.REMOTE_ENV}/current_venv_{shell_id}.txt"
        
        # 构建智能删除脚本
        delete_script_parts = [
            f'CURRENT_ENV=$(cat "{current_venv_file}" 2>/dev/null || echo "none")'
        ]
        
        # 为每个候选环境添加检查和删除逻辑
        for env_name in candidate_envs:
            env_path = f"{self.get_venv_base_path()}/{env_name}"
            env_script = f'''
if [ "$CURRENT_ENV" != "{env_name}" ] && [ -d "{env_path}" ]; then
  rm -rf "{env_path}"
fi
'''
            delete_script_parts.append(env_script.strip())
        
        full_command = "; ".join(delete_script_parts)
        result = self.shell.execute_command_interface("bash", ["-c", full_command])
        if result.get("success"):
            return {"success": True, "message": "Batch delete completed successfully"}
        else:
            return {
                "success": False,
                "error": f"Failed to execute delete operation: {result.get('error', 'Unknown error')}"
            }
    
    def update_venv_json_field(self, env_name, field_path, value, success_message="Field updated"):
        """
        统一的JSON状态文件字段更新方法
        
        Args:
            env_name (str): 环境名称
            field_path (str): 字段路径，例如 "environments.{env}.protected" 或 "shells.{shell}.current_venv"
            value: 要设置的值
            success_message (str): 成功时显示的消息
            
        Returns:
            dict: 操作结果
        """
        if not env_name or env_name.startswith('.'):
            return {"success": False, "error": "Invalid environment name"}
        
        try:
            env_path = f"{self.get_venv_base_path()}/{env_name}"
            venv_states_file = self.get_venv_state_file_path()
            
            # 将value转换为JSON字符串（如果是字符串则添加引号，如果是bool/None则用Python表示）
            if isinstance(value, str):
                value_json = f'"{value}"'
            elif isinstance(value, bool):
                value_json = 'True' if value else 'False'
            elif value is None:
                value_json = 'None'
            else:
                value_json = str(value)
            
            # 生成远程命令
            remote_command = f'''
# 检查环境是否存在
if [ -d "{env_path}" ]; then
    : # Environment exists, continue
else
    echo "ERROR: Environment '{env_name}' does not exist"
    exit 1
fi

# 确保状态文件存在
mkdir -p "{self.get_venv_base_path()}"
if [ -f "{venv_states_file}" ]; then
    : # State file exists
else
    echo '{{}}' > "{venv_states_file}"
fi

# 使用Python更新状态文件
python3 -c "
import json

state_file = '{venv_states_file}'
env_name = '{env_name}'
field_path = '{field_path}'
value = {value_json}

# 读取现有状态
try:
    with open(state_file, 'r') as f:
        states = json.load(f)
except:
    states = {{}}

# 解析字段路径并设置值
# 例如: 'environments.{{env}}.protected' -> states['environments'][env_name]['protected'] = value
parts = field_path.replace('{{env}}', env_name).replace('{{shell}}', '${{GDS_SHELL_ID:-default_shell}}').split('.')

# 确保中间路径存在
current = states
for part in parts[:-1]:
    if part not in current:
        current[part] = {{}}
    current = current[part]

# 设置最终值
current[parts[-1]] = value

# 写入更新后的状态
with open(state_file, 'w') as f:
    json.dump(states, f, indent=2, ensure_ascii=False)

print('{success_message}')
"
'''
            
            result = self.shell.execute_command_interface("bash", ["-c", remote_command])
            
            if result.get("success"):
                data = result.get("data", {})
                exit_code = data.get("exit_code", result.get("exit_code", -1))
                
                if exit_code == 0:
                    return {"success": True, "message": success_message}
                else:
                    stderr = data.get("stderr", result.get("stderr", ""))
                    if "does not exist" in stderr:
                        return {"success": False, "error": f"Environment '{env_name}' does not exist"}
                    return {"success": False, "error": f"Failed to update field: {stderr}"}
            else:
                return {"success": False, "error": f"Command execution failed: {result.get('error', 'Unknown error')}"}
                
        except Exception as e:
            return {"success": False, "error": f"Error updating field: {str(e)}"}
    
    def venv_activate(self, env_name):
        """激活虚拟环境（设置PYTHONPATH）"""
        if not env_name:
            return {"success": False, "error": "Please specify the environment name"}
        
        if env_name.startswith('.'):
            return {"success": False, "error": "Environment name cannot start with '.'"}
        
        try:
            venv_states_file = f"{self.get_venv_base_path()}/venv_states.json"
            env_path = f"{self.get_venv_base_path()}/{env_name}"
            
            remote_env_path = self.shell.REMOTE_ENV
            remote_command = f'''
# 获取当前shell ID
SHELL_ID="${{GDS_SHELL_ID:-default_shell}}"

# 检查环境是否存在
ENV_PATH="{env_path}"
if [ -d "$ENV_PATH" ]; then
    : # Virtual environment exists, continue
else
    exit 1  # Virtual environment does not exist
fi

# 检查是否已经激活
VENV_STATES_FILE="{venv_states_file}"
if [ -f "$VENV_STATES_FILE" ]; then
    CURRENT_VENV=$(cat "$VENV_STATES_FILE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    shell_id = '$SHELL_ID'
    if shell_id in data and data[shell_id].get('current_venv') == '{env_name}':
        print('already_active')
    else:
        print('not_active')
except:
    print('not_active')
")
else
    CURRENT_VENV="not_active"
fi

if [ "$CURRENT_VENV" = "already_active" ]; then
    echo "Virtual environment '{env_name}' is already active"
    exit 0
fi

# 保存新的状态到JSON文件
mkdir -p "{self.get_venv_base_path()}"
python3 -c "
import json
import os
from datetime import datetime

# 读取现有状态
states = {{}}
if os.path.exists('$VENV_STATES_FILE'):
    try:
        with open('$VENV_STATES_FILE', 'r') as f:
            states = json.load(f)
    except:
        states = {{}}

# 更新当前shell的状态
states['$SHELL_ID'] = {{
    'current_venv': '{env_name}',
    'env_path': '$ENV_PATH',
    'activated_at': datetime.now().isoformat(),
    'shell_id': '$SHELL_ID'
}}

# 保存状态
with open('$VENV_STATES_FILE', 'w') as f:
    json.dump(states, f, indent=2, ensure_ascii=False)

print('Virtual environment \\'{env_name}\\' activated successfully')
"

# 创建虚拟环境的shell文件
mkdir -p "{remote_env_path}/venv"
cat > "{remote_env_path}/venv/venv_pythonpath.sh" << 'EOF'
# Virtual environment activation script for {env_name}
export PYTHONPATH="{env_path}:$PYTHONPATH"
EOF

# 验证保存是否成功
sleep 1
VERIFICATION_RESULT=$(cat "$VENV_STATES_FILE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    shell_id = '$SHELL_ID'
    if shell_id in data and data[shell_id].get('current_venv') == '{env_name}':
        print('VERIFICATION_SUCCESS')
    else:
        print('VERIFICATION_FAILED')
except:
    print('VERIFICATION_FAILED')
")

if [ "$VERIFICATION_RESULT" != "VERIFICATION_SUCCESS" ]; then
    exit 1  # Activation verification failed
fi
'''
            result = self.shell.execute_command_interface("bash", ["-c", remote_command])
            if result.get("success"):
                data = result.get("data", {})
                exit_code = data.get("exit_code") if "exit_code" in data else result.get("exit_code", -1)
                output = (data.get("stdout") if "stdout" in data else result.get("stdout", "")).strip()
                if exit_code == 0:  
                    if "already active" in output:
                        print(f"Virtual environment already activated!")
                        return {
                            "success": True,
                            "message": f"Virtual environment '{env_name}' is already active",
                            "environment": env_name,
                            "skipped": True
                        }
                    
                    # 检查是否成功激活
                    if "activated successfully" in output:
                        print(f"Virtual environment activated successfully")
                        return {
                            "success": True,
                            "message": f"Virtual environment '{env_name}' activated successfully",
                            "env_path": env_path,
                            "pythonpath": env_path,
                            "action": "activate"
                        }
                    else:
                        print(f"Virtual environment activated successfully (based on exit code)")
                        return {
                            "success": True,
                            "message": f"Virtual environment '{env_name}' activated successfully",
                            "env_path": env_path,
                            "pythonpath": env_path,
                            "action": "activate"
                        }
                else:
                    error_msg = f"Virtual environment activation failed"
                    if output.strip():
                        error_msg += f": {output}"
                    else:
                        error_msg += f". Environment '{env_name}' may not exist. Please check available environments with 'GDS venv --list'"
                    
                    return {
                        "success": False,
                        "error": error_msg
                    }
            else:
                error_msg = f"Failed to activate virtual environment: {result.get('error', 'Unknown error')}"
                return {
                    "success": False,
                    "error": error_msg
                }
                
        except Exception as e:
            return {"success": False, "error": f"Error activating virtual environment: {str(e)}"}
    
    def venv_deactivate(self):
        """取消激活虚拟环境（清除PYTHONPATH）"""
        try:
            venv_states_file = self.get_venv_state_file_path()
            
            remote_command = f'''
# 获取当前shell ID
SHELL_ID="${{GDS_SHELL_ID:-default_shell}}"

# 从JSON文件中移除当前shell的状态
VENV_STATES_FILE="{venv_states_file}"
if [ -f "$VENV_STATES_FILE" ]; then
    python3 -c "
import json
import os

# 读取现有状态
states = {{}}
if os.path.exists('$VENV_STATES_FILE'):
    try:
        with open('$VENV_STATES_FILE', 'r') as f:
            states = json.load(f)
    except:
        states = {{}}

# 移除当前shell的状态
if '$SHELL_ID' in states:
    del states['$SHELL_ID']

# 保存状态
with open('$VENV_STATES_FILE', 'w') as f:
    json.dump(states, f, indent=2, ensure_ascii=False)

print('Virtual environment deactivated successfully')
"
fi

# 删除或重置虚拟环境的shell文件
rm -f "{self.shell.REMOTE_ENV}/venv/venv_pythonpath.sh"

# 验证移除是否成功
sleep 1
if [ -f "$VENV_STATES_FILE" ]; then
    VERIFICATION_RESULT=$(cat "$VENV_STATES_FILE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    shell_id = '$SHELL_ID'
    if shell_id in data:
        print('VERIFICATION_FAILED')
    else:
        print('VERIFICATION_SUCCESS')
except:
    print('VERIFICATION_SUCCESS')
")
else
    VERIFICATION_RESULT="VERIFICATION_SUCCESS"
fi

if [ "$VERIFICATION_RESULT" != "VERIFICATION_SUCCESS" ]; then
    exit 1  # Deactivation verification failed
fi
'''
            
            result = self.shell.execute_command_interface("bash", ["-c", remote_command])
            if result.get("success", False):
                data = result.get("data", {})
                # 明确处理exit_code，优先使用data中的值
                exit_code = data.get("exit_code") if "exit_code" in data else result.get("exit_code", -1)                
                if exit_code == 0:
                    print(f"Virtual environment deactivated successfully")
                    return {
                        "success": True,
                        "message": "Virtual environment deactivated successfully"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to deactivate virtual environment: remote command failed with exit code {exit_code}"
                    }
            else:
                return {
                    "success": False,
                    "error": f"Failed to deactivate virtual environment: {result.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            return {"success": False, "error": f"Error deactivating virtual environment: {str(e)}"}
    
    def venv_list(self):
        """列出所有虚拟环境（显示当前激活环境的*标记）"""
        try:
            # 使用API管理器列出虚拟环境
            api_manager = self.get_venv_api_manager()
            env_names = api_manager.list_venv_environments()
            
            # 获取当前激活的环境
            current_env = None
            states = api_manager.read_venv_states()
            if states.get("success"):
                current_shell = self.shell.get_current_shell()
                shell_id = current_shell.get("id", "default_shell") if current_shell else "default_shell"
                shell_states = states.get("data", {})
                if shell_id in shell_states:
                    current_env = shell_states[shell_id].get("current_venv")
            
            if not env_names:
                print(f"No virtual environments found")
                return {
                    "success": True,
                    "message": "No virtual environments found",
                    "environments": [],
                    "count": 0
                }
            
            # 格式化输出
            env_list = []
            print(f"Virtual environments ({len(env_names)} total):")
            for env_name in sorted(env_names):
                if env_name == current_env:
                    env_list.append(f"* {env_name}")
                    print(f"* {env_name}")
                else:
                    env_list.append(f"  {env_name}")
                    print(f"  {env_name}")
                
            return {
                "success": True,
                "message": f"Virtual environments ({len(env_names)} total):",
                "environments": env_list,
                "count": len(env_names),
                "current": current_env
            }
                
        except Exception as e:
            return {"success": False, "error": f"Error listing environments: {str(e)}"}
    
    def venv_current(self):
        """显示当前激活的虚拟环境"""
        try:
            # 使用API管理器获取当前状态
            api_manager = self.get_venv_api_manager()
            states = api_manager.read_venv_states()
            
            if states.get("success"):
                # 获取当前shell ID
                current_shell = self.shell.get_current_shell()
                shell_id = current_shell.get("id", "default_shell") if current_shell else "default_shell"
                
                # 检查当前shell的状态
                shell_states = states.get("data", {})
                if shell_id in shell_states:
                    current_venv = shell_states[shell_id].get("current_venv")
                    if current_venv:
                        env_path = shell_states[shell_id].get("env_path")
                        activated_at = shell_states[shell_id].get("activated_at")
                        
                        print(f"Current virtual environment: {current_venv}")
                        if env_path:
                            print(f"Environment path: {env_path}")
                        if activated_at:
                            print(f"Activated at: {activated_at}")
                        
                        return {
                            "success": True, 
                            "current": current_venv,
                            "env_path": env_path,
                            "activated_at": activated_at
                        }
                
                # 没有激活的环境
                print(f"No virtual environment currently activated")
                return {"success": True, "current": None}
            else:
                print(f"No virtual environment currently activated")
                return {"success": True, "current": None}
                
        except Exception as e:
            print(f"No virtual environment currently activated")
            return {"success": True, "current": None, "error": str(e)}
    
    def venv_protect_batch(self, env_names, protected=True):
        """
        批量保护或取消保护虚拟环境（优化：单次远程命令，只弹出一个窗口）
        
        Args:
            env_names (list): 环境名称列表
            protected (bool): True=保护, False=取消保护
        """
        if not env_names:
            return {"success": False, "error": "No environments specified"}
        
        # 过滤无效的环境名
        valid_env_names = [name for name in env_names if name and not name.startswith('.')]
        if not valid_env_names:
            return {"success": False, "error": "No valid environment names provided"}
        
        try:
            venv_base_path = self.get_venv_base_path()
            venv_states_file = self.get_venv_state_file_path()
            
            # 生成JSON数组用于Python脚本
            env_names_json = json.dumps(valid_env_names)
            
            # 生成单个远程命令处理所有环境
            remote_command = f'''
#!/bin/bash
# 批量保护虚拟环境

# 确保状态文件存在
mkdir -p "{venv_base_path}"
if [ ! -f "{venv_states_file}" ]; then
    echo '{{}}' > "{venv_states_file}"
fi

# 使用Python批量处理所有环境
python3 << 'PYEOF'
import json
import os
import sys

env_names = {env_names_json}
venv_base_path = "{venv_base_path}"
state_file = "{venv_states_file}"

success_list = []
failed_list = []

# 检查每个环境是否存在
for env_name in env_names:
    env_path = os.path.join(venv_base_path, env_name)
    if not os.path.isdir(env_path):
        failed_list.append(f"{{env_name}}: Environment does not exist")
    else:
        success_list.append(env_name)

# 如果有成功的环境，更新状态文件
if success_list:
    try:
        # 读取现有状态
        try:
            with open(state_file, 'r') as f:
                states = json.load(f)
        except:
            states = {{}}
        
        # 确保environments字段存在
        if 'environments' not in states:
            states['environments'] = {{}}
        
        # 批量添加/移除protected标记
        for env_name in success_list:
            if env_name not in states['environments']:
                states['environments'][env_name] = {{}}
            states['environments'][env_name]['protected'] = {protected}
        
        # 写入更新后的状态
        with open(state_file, 'w') as f:
            json.dump(states, f, indent=2, ensure_ascii=False)
    except Exception as e:
        # 如果状态文件更新失败，将所有环境标记为失败
        failed_list.extend([f"{{env}}: State file update failed" for env in success_list])
        success_list = []

# 输出JSON结果
action_key = "protected" if {protected} else "unprotected"
result = {{
    "success": len(success_list) > 0,
    action_key: success_list,
    "failed": failed_list,
    "success_count": len(success_list),
    "failed_count": len(failed_list)
}}
print(json.dumps(result))
PYEOF
'''
            
            result = self.shell.execute_command_interface("bash", ["-c", remote_command])
            
            if result.get("success"):
                data = result.get("data", {})
                stdout = data.get("stdout", "") if "stdout" in data else result.get("stdout", "")
                
                # 解析JSON结果
                try:
                    batch_result = json.loads(stdout.strip())
                    
                    if batch_result.get("success"):
                        action_key = "protected" if protected else "unprotected"
                        action_list = batch_result.get(action_key, [])
                        failed = batch_result.get("failed", [])
                        action_verb = "Protected" if protected else "Unprotected"
                        
                        if action_list:
                            print(f"{action_verb} {len(action_list)} environment(s): {', '.join(action_list)}")
                        if failed:
                            print(f"Failed {len(failed)} environment(s): {', '.join(failed)}")
                        
                        return {
                            "success": True,
                            "message": f"Successfully {action_verb.lower()} {len(action_list)} environment(s)",
                            action_key: action_list,
                            "failed": failed
                        }
                    else:
                        action_verb = "protect" if protected else "unprotect"
                        return {
                            "success": False,
                            "error": f"Failed to {action_verb} environments: {', '.join(batch_result.get('failed', []))}",
                            "failed": batch_result.get("failed", [])
                        }
                except json.JSONDecodeError:
                    return {"success": False, "error": f"Failed to parse result: {stdout}"}
            else:
                return {"success": False, "error": f"Command execution failed: {result.get('error', 'Unknown error')}"}
                
        except Exception as e:
            return {"success": False, "error": f"Error protecting environments: {str(e)}"}
    
    
    def venv_protect(self, env_name, protected=True):
        """
        保护或取消保护虚拟环境
        
        Args:
            env_name (str): 环境名称
            protected (bool): True=保护, False=取消保护
            
        Returns:
            dict: 操作结果
        """
        if not env_name:
            return {"success": False, "error": "Environment name required"}
        
        action_msg = "protected" if protected else "unprotected"
        result = self.update_venv_json_field(
            env_name, 
            "environments.{env}.protected", 
            protected, 
            f"Environment {env_name} has been {action_msg}"
        )
        
        if result.get("success"):
            status = "protected" if protected else "unprotected"
            print(f"Virtual environment '{env_name}' is now {status}")
        
        return result
    
    
    def get_protected_environments(self):
        """获取被保护的虚拟环境列表"""
        try:
            venv_states_file = self.get_venv_state_file_path()
            
            # 读取状态文件
            read_command = f'''
if [ -f "{venv_states_file}" ]; then
    cat "{venv_states_file}"
else
    echo "{{}}"
fi
'''
            
            result = self.shell.execute_command_interface("bash", ["-c", read_command])
            
            if result.get("success"):
                data = result.get("data", {})
                stdout = data.get("stdout") if "stdout" in data else result.get("stdout", "")
                
                if stdout:
                    import json
                    try:
                        states = json.loads(stdout)
                        protected = []
                        
                        # 检查environments字段
                        if "environments" in states:
                            for env_name, env_data in states["environments"].items():
                                if isinstance(env_data, dict) and env_data.get("protected"):
                                    protected.append(env_name)
                        
                        return protected
                    except json.JSONDecodeError as e:
                        print(f"Warning: Failed to parse venv states: {e}")
                        return []
                else:
                    return []
            else:
                print(f"Warning: Failed to read venv states: {result.get('error', 'Unknown error')}")
                return []
                
        except Exception as e:
            print(f"Warning: Error getting protected environments: {e}")
            return []

