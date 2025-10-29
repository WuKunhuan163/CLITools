"""
Venv command handler for GDS.
"""

from typing import List
from .base_command import BaseCommand


class VenvCommand(BaseCommand):
    """Handler for venv commands."""
    
    @property
    def command_name(self) -> str:
        return "venv"
    
    def execute(self, cmd: str, args: List[str], **kwargs) -> int:
        """Execute venv command."""
        if not args:
            self.print_error("venv command needs arguments")
            return 1
        
        # 直接调用cmd_venv方法
        result = self.cmd_venv(*args)
        
        if result.get("success", False):
            # venv命令成功后，同步更新本地shell状态
            self.shell._sync_venv_state_to_local_shell(args)
            return 0
        else:
            error_message = result.get("error", "Virtual environment operation failed")
            self.print_error(error_message)
            return 1

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
                return self._venv_create_batch(env_names)
            elif action == "--delete":
                if not env_names:
                    return {"success": False, "error": "Please specify at least one environment name"}
                return self._venv_delete_batch(env_names)
            elif action == "--activate":
                if len(env_names) != 1:
                    return {"success": False, "error": "Please specify exactly one environment name for activation"}
                return self._venv_activate(env_names[0])
            elif action == "--deactivate":
                return self._venv_deactivate()
            elif action == "--list":
                return self._venv_list()
            elif action == "--current":
                return self._venv_current()
            elif action == "--protect":
                if not env_names:
                    return {"success": False, "error": "Please specify at least one environment name"}
                return self._venv_protect_batch(env_names)
            elif action == "--unprotect":
                if not env_names:
                    return {"success": False, "error": "Please specify at least one environment name"}
                return self._venv_unprotect_batch(env_names)
            else:
                return {
                    "success": False,
                    "error": f"Unknown venv command: {action}. Supported commands: --create, --delete, --activate, --deactivate, --list, --current, --protect, --unprotect"
                }
                
        except Exception as e:
            return {"success": False, "error": f"venv命令执行失败: {str(e)}"}
    
    def _venv_create_batch(self, env_names):
        """批量创建虚拟环境"""
        results = []
        for env_name in env_names:
            result = self._venv_create(env_name)
            results.append(result)
        
        # 返回综合结果
        all_success = all(r.get("success", False) for r in results)
        if all_success:
            return {"success": True, "message": f"Created {len(env_names)} virtual environment(s)"}
        else:
            failed = [r.get("error", "Unknown error") for r in results if not r.get("success", False)]
            return {"success": False, "error": failed}
    
    def _get_venv_base_path(self):
        """获取虚拟环境基础路径"""
        return f"{self.shell.REMOTE_ENV}/venv"
    
    def _get_venv_api_manager(self):
        """获取虚拟环境API管理器"""
        if not hasattr(self, '_venv_api_manager'):
            from ..venv_manager import VenvApiManager
            self._venv_api_manager = VenvApiManager(self.shell.drive_service , self.shell)
        return self._venv_api_manager
    
    def _get_venv_state_file_path(self):
        """获取虚拟环境状态文件路径（统一的JSON格式）"""
        return f"{self._get_venv_base_path()}/venv_states.json"
    
    def _venv_create(self, env_name):
        """创建虚拟环境"""
        if not env_name:
            return {"success": False, "error": "Environment name required"}
        
        if env_name.startswith('.'):
            return {"success": False, "error": "Environment name cannot start with '.'"}
        
        try:
            # 使用正确的路径：REMOTE_ENV/venv
            env_path = f"{self._get_venv_base_path()}/{env_name}"
            

            
            # 使用API管理器检查环境是否已存在
            api_manager = self._get_venv_api_manager()
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
    
    def _venv_delete_batch(self, env_names):
        """批量删除虚拟环境（优化版：一个远程命令完成检查和删除）"""
        # 获取被保护的环境列表
        protected_envs = self._get_protected_environments()
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
            env_path = f"{self._get_venv_base_path()}/{env_name}"
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
    
    def _venv_activate(self, env_name):
        """激活虚拟环境（设置PYTHONPATH）"""
        if not env_name:
            return {"success": False, "error": "Please specify the environment name"}
        
        if env_name.startswith('.'):
            return {"success": False, "error": "Environment name cannot start with '.'"}
        
        try:
            venv_states_file = f"{self._get_venv_base_path()}/venv_states.json"
            env_path = f"{self._get_venv_base_path()}/{env_name}"
            
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
mkdir -p "{self._get_venv_base_path()}"
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
    
    def _venv_deactivate(self):
        """取消激活虚拟环境（清除PYTHONPATH）"""
        try:
            venv_states_file = self._get_venv_state_file_path()
            
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
    
    def _venv_list(self):
        """列出所有虚拟环境（显示当前激活环境的*标记）"""
        try:
            # 使用API管理器列出虚拟环境
            api_manager = self._get_venv_api_manager()
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
    
    def _venv_current(self):
        """显示当前激活的虚拟环境"""
        try:
            # 使用API管理器获取当前状态
            api_manager = self._get_venv_api_manager()
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
    
    def _venv_protect_batch(self, env_names):
        """批量保护虚拟环境（防止误删）"""
        success_list = []
        failed_list = []
        
        for env_name in env_names:
            result = self._venv_protect(env_name)
            if result.get("success"):
                success_list.append(env_name)
            else:
                failed_list.append(f"{env_name}: {result.get('error', 'Unknown error')}")
        
        if failed_list:
            return {
                "success": False,
                "error": f"Failed to protect some environments: {', '.join(failed_list)}",
                "success_count": len(success_list),
                "failed_count": len(failed_list)
            }
        else:
            return {
                "success": True,
                "message": f"Successfully protected {len(success_list)} environment(s)",
                "protected": success_list
            }
    
    def _venv_unprotect_batch(self, env_names):
        """批量取消保护虚拟环境"""
        success_list = []
        failed_list = []
        
        for env_name in env_names:
            result = self._venv_unprotect(env_name)
            if result.get("success"):
                success_list.append(env_name)
            else:
                failed_list.append(f"{env_name}: {result.get('error', 'Unknown error')}")
        
        if failed_list:
            return {
                "success": False,
                "error": f"Failed to unprotect some environments: {', '.join(failed_list)}",
                "success_count": len(success_list),
                "failed_count": len(failed_list)
            }
        else:
            return {
                "success": True,
                "message": f"Successfully unprotected {len(success_list)} environment(s)",
                "unprotected": success_list
            }
    
    def _venv_protect(self, env_name):
        """保护虚拟环境（在状态文件中标记为protected）"""
        if not env_name:
            return {"success": False, "error": "Environment name required"}
        
        if env_name.startswith('.'):
            return {"success": False, "error": "Environment name cannot start with '.'"}
        
        try:
            env_path = f"{self._get_venv_base_path()}/{env_name}"
            venv_states_file = self._get_venv_state_file_path()
            
            # 使用远程命令更新状态文件
            remote_command = f'''
# 检查环境是否存在
if [ -d "{env_path}" ]; then
    : # Environment exists, continue
else
    echo "ERROR: Environment '{env_name}' does not exist"
    exit 1
fi

# 确保状态文件存在
mkdir -p "{self._get_venv_base_path()}"
if [ -f "{venv_states_file}" ]; then
    : # State file exists
else
    echo '{{}}' > "{venv_states_file}"
fi

# 使用Python更新状态文件，添加protected标记
python3 -c "
import json
import os

state_file = '{venv_states_file}'
env_name = '{env_name}'

# 读取现有状态
try:
    with open(state_file, 'r') as f:
        states = json.load(f)
except:
    states = {{}}

# 确保environments字段存在
if 'environments' not in states:
    states['environments'] = {{}}

# 添加或更新环境的protected标记
if env_name not in states['environments']:
    states['environments'][env_name] = {{}}

states['environments'][env_name]['protected'] = True

# 写入更新后的状态
with open(state_file, 'w') as f:
    json.dump(states, f, indent=2, ensure_ascii=False)

print(f'Environment {{env_name}} has been protected')
"
'''
            
            result = self.shell.execute_command_interface("bash", ["-c", remote_command])
            
            if result.get("success"):
                data = result.get("data", {})
                exit_code = data.get("exit_code") if "exit_code" in data else result.get("exit_code", -1)
                
                if exit_code == 0:
                    print(f"Virtual environment '{env_name}' is now protected")
                    return {"success": True, "message": f"Environment '{env_name}' protected"}
                else:
                    stderr = data.get("stderr") if "stderr" in data else result.get("stderr", "")
                    if "does not exist" in stderr:
                        return {"success": False, "error": f"Environment '{env_name}' does not exist"}
                    return {"success": False, "error": f"Failed to protect environment: {stderr}"}
            else:
                return {"success": False, "error": f"Command execution failed: {result.get('error', 'Unknown error')}"}
                
        except Exception as e:
            return {"success": False, "error": f"Error protecting environment: {str(e)}"}
    
    def _venv_unprotect(self, env_name):
        """取消保护虚拟环境（移除protected标记）"""
        if not env_name:
            return {"success": False, "error": "Environment name required"}
        
        if env_name.startswith('.'):
            return {"success": False, "error": "Environment name cannot start with '.'"}
        
        try:
            env_path = f"{self._get_venv_base_path()}/{env_name}"
            venv_states_file = self._get_venv_state_file_path()
            
            # 使用远程命令更新状态文件
            remote_command = f'''
# 检查环境是否存在
if [ -d "{env_path}" ]; then
    : # Environment exists, continue
else
    echo "ERROR: Environment '{env_name}' does not exist"
    exit 1
fi

# 确保状态文件存在
if [ -f "{venv_states_file}" ]; then
    : # State file exists, continue
else
    echo "WARNING: State file does not exist, nothing to unprotect"
    exit 0
fi

# 使用Python更新状态文件，移除protected标记
python3 -c "
import json
import os

state_file = '{venv_states_file}'
env_name = '{env_name}'

# 读取现有状态
try:
    with open(state_file, 'r') as f:
        states = json.load(f)
except:
    print(f'Environment {{env_name}} was not protected')
    exit(0)

# 移除protected标记
if 'environments' in states and env_name in states['environments']:
    if 'protected' in states['environments'][env_name]:
        del states['environments'][env_name]['protected']
        
        # 如果环境记录变为空字典，也保留它（可能有其他元数据）
        
        # 写入更新后的状态
        with open(state_file, 'w') as f:
            json.dump(states, f, indent=2, ensure_ascii=False)
        
        print(f'Environment {{env_name}} protection removed')
    else:
        print(f'Environment {{env_name}} was not protected')
else:
    print(f'Environment {{env_name}} was not protected')
"
'''
            
            result = self.shell.execute_command_interface("bash", ["-c", remote_command])
            
            if result.get("success"):
                data = result.get("data", {})
                exit_code = data.get("exit_code") if "exit_code" in data else result.get("exit_code", -1)
                
                if exit_code == 0:
                    print(f"Virtual environment '{env_name}' protection removed")
                    return {"success": True, "message": f"Environment '{env_name}' unprotected"}
                else:
                    stderr = data.get("stderr") if "stderr" in data else result.get("stderr", "")
                    if "does not exist" in stderr:
                        return {"success": False, "error": f"Environment '{env_name}' does not exist"}
                    return {"success": False, "error": f"Failed to unprotect environment: {stderr}"}
            else:
                return {"success": False, "error": f"Command execution failed: {result.get('error', 'Unknown error')}"}
                
        except Exception as e:
            return {"success": False, "error": f"Error unprotecting environment: {str(e)}"}
    
    def _get_protected_environments(self):
        """获取被保护的虚拟环境列表"""
        try:
            venv_states_file = self._get_venv_state_file_path()
            
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

