from test_gds import GDSTest

# Create an instance
test_instance = GDSTest()
GDSTest.setUpClass()  # 初始化类属性
test_instance.setUp()

print("=== 研究test_02的问题 ===")

# 复现test_02中失败的具体命令
print("\n测试1: 复现test_02中失败的JSON命令")
json_content = '{"name": "test", "value": 123}'
json_echo_file = test_instance._get_test_file_path("json_echo.txt")

print(f"JSON内容: {json_content}")
print(f"目标文件: {json_echo_file}")

# 使用与test_02相同的语法
command = f'\'echo "{json_content}" > "{json_echo_file}"\''
print(f"执行命令: {command}")

try:
    result = test_instance._run_gds_command(command)
    print(f"返回码: {result.returncode}")
    print(f"stdout: {repr(result.stdout)}")
    print(f"stderr: {repr(result.stderr)}")
    
    if result.returncode == 0:
        print("验证文件是否存在:")
        exists = test_instance._verify_file_exists(json_echo_file)
        print(f"文件存在: {exists}")
        
        if exists:
            print("验证文件内容:")
            contains_json = test_instance._verify_file_content_contains(json_echo_file, json_content)
            print(f"包含JSON内容: {contains_json}")
except Exception as e:
    print(f"命令执行异常: {e}")

print("\n测试2: 复现test_02中失败的中文特殊字符命令")
chinese_content = "测试中文：你好世界 Special chars: @#$%^&*()_+-=[]{}|;:,.<>?"
chinese_echo_file = test_instance._get_test_file_path("chinese_echo.txt")

print(f"中文内容: {chinese_content}")
print(f"目标文件: {chinese_echo_file}")

# 使用原始的有问题的方法
original_command = '\'echo "' + chinese_content + '" > "' + chinese_echo_file + '"\''
print(f"原始有问题的命令: {original_command}")

try:
    result = test_instance._run_gds_command(original_command)
    print(f"原始命令返回码: {result.returncode}")
    print(f"原始命令stdout: {repr(result.stdout)}")
    print(f"原始命令stderr: {repr(result.stderr)}")
except Exception as e:
    print(f"原始命令异常: {e}")

# 使用修复后的方法（shlex.quote）
print("\n使用修复后的方法:")
import shlex
safe_content = shlex.quote(chinese_content)
safe_file = shlex.quote(chinese_echo_file)
fixed_command = f'echo {safe_content} > {safe_file}'
print(f"修复后的命令: {fixed_command}")

try:
    result = test_instance._run_gds_command(fixed_command)
    print(f"修复命令返回码: {result.returncode}")
    print(f"修复命令stdout: {repr(result.stdout)}")
    print(f"修复命令stderr: {repr(result.stderr)}")
    
    if result.returncode == 0:
        print("验证修复后的文件:")
        exists = test_instance._verify_file_exists(chinese_echo_file)
        print(f"文件存在: {exists}")
        
        if exists:
            contains_chinese = test_instance._verify_file_content_contains(chinese_echo_file, "你好世界")
            print(f"包含中文内容: {contains_chinese}")
except Exception as e:
    print(f"修复命令异常: {e}")

print("\n=== test_02问题研究完成 ===")