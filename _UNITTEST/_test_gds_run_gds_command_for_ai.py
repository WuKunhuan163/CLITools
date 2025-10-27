from test_gds import GDSTest

# Create an instance
test_instance = GDSTest()
GDSTest.setUpClass()  # 初始化类属性
test_instance.setUp()

print("=== 专门研究JSON引号问题 ===")

# 测试1: 基本JSON引号问题
print("\n测试1: 基本JSON引号问题")
json_content = "{'name': 'test', 'value': 123}"
json_echo_file = test_instance._get_test_file_path("json_quote_test.txt")

print(f"期望的JSON内容: {json_content}")
print(f"目标文件: {json_echo_file}")

# 测试echo到文件
command = f'echo "{json_content}" > "{json_echo_file}"'
print(f"执行命令: {command}")

try:
    result = test_instance._run_gds_command(command)
    print(f"返回码: {result.returncode}")
    print(f"stdout: {repr(result.stdout)}")
    print(f"stderr: {repr(result.stderr)}")
    
    if result.returncode == 0:
        print("验证文件内容:")
        # 读取文件内容
        cat_result = test_instance._run_gds_command(f'cat "{json_echo_file}"')
        if cat_result.returncode == 0:
            actual_content = cat_result.stdout.strip()
            print(f"实际文件内容: {repr(actual_content)}")
            print(f"期望内容: {repr(json_content)}")
            print(f"内容匹配: {actual_content == json_content}")
            
            # 检查引号是否丢失
            if "name" in actual_content and "test" in actual_content:
                if "'" in actual_content:
                    print("✅ 引号保留正常")
                else:
                    print("❌ 引号丢失！")
                    print(f"丢失引号的内容: {actual_content}")
        else:
            print("❌ 无法读取文件内容")
    else:
        print("❌ 命令执行失败")
        
except Exception as e:
    print(f"命令执行异常: {e}")

# 测试2: 直接echo到stdout
print("\n测试2: 直接echo到stdout（不重定向）")
direct_command = f'echo "{json_content}"'
print(f"执行命令: {direct_command}")

try:
    result = test_instance._run_gds_command(direct_command)
    print(f"返回码: {result.returncode}")
    print(f"stdout: {repr(result.stdout)}")
    
    if result.returncode == 0:
        actual_stdout = result.stdout.strip()
        print(f"实际stdout内容: {repr(actual_stdout)}")
        print(f"期望内容: {repr(json_content)}")
        print(f"内容匹配: {actual_stdout == json_content}")
        
        # 检查引号是否丢失
        if "name" in actual_stdout and "test" in actual_stdout:
            if "'" in actual_stdout:
                print("✅ stdout中引号保留正常")
            else:
                print("❌ stdout中引号丢失！")
                print(f"丢失引号的stdout: {actual_stdout}")
        
except Exception as e:
    print(f"命令执行异常: {e}")

# 测试3: 不同的引号组合
print("\n测试3: 不同的引号组合")
test_cases = [
    ('{"name": "test", "value": 123}', "双引号JSON"),
    ("{'name': 'test', 'value': 123}", "单引号JSON"),
    ('{"name": "test", "nested": {"key": "value"}}', "嵌套双引号JSON"),
    ("{'name': 'test', 'nested': {'key': 'value'}}", "嵌套单引号JSON")
]

for test_content, description in test_cases:
    print(f"\n{description}: {test_content}")
    test_file = test_instance._get_test_file_path(f"quote_test_{len(test_content)}.txt")
    
    try:
        # 使用单引号包围整个命令避免shell解释
        safe_command = f"echo '{test_content}' > '{test_file}'"
        result = test_instance._run_gds_command(safe_command)
        
        if result.returncode == 0:
            cat_result = test_instance._run_gds_command(f"cat '{test_file}'")
            if cat_result.returncode == 0:
                actual = cat_result.stdout.strip()
                print(f"  期望: {repr(test_content)}")
                print(f"  实际: {repr(actual)}")
                print(f"  匹配: {actual == test_content}")
                
                if actual != test_content:
                    print(f"  ❌ 引号处理有问题！")
                else:
                    print(f"  ✅ 引号处理正常")
    except Exception as e:
        print(f"  异常: {e}")

print("\n=== JSON引号问题研究完成 ===")