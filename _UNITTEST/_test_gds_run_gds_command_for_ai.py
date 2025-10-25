from test_gds import GDSTest

# Create an instance
test_instance = GDSTest()
GDSTest.setUpClass()  # 初始化类属性
test_instance.setUp()

print("=== 测试GDS echo JSON结构的bug ===")

# 测试1: 简单的JSON结构
print("\n测试1: 简单JSON结构")
json_content = '{"name": "test", "value": 123}'
print(f"JSON内容: {json_content}")

# 直接echo测试（不重定向）
try:
    result = test_instance._run_gds_command(f"echo '{json_content}'")
    print(f"直接echo返回码: {result.returncode}")
    print(f"直接echo输出: {repr(result.stdout)}")
    print(f"直接echo错误: {repr(result.stderr)}")
except Exception as e:
    print(f"直接echo失败: {e}")

# 测试2: 带重定向的JSON
print("\n测试2: JSON重定向")
try:
    result = test_instance._run_gds_command(f"echo '{json_content}' > test_json.txt")
    print(f"重定向返回码: {result.returncode}")
    print(f"重定向输出: {repr(result.stdout)}")
    print(f"重定向错误: {repr(result.stderr)}")
except Exception as e:
    print(f"重定向失败: {e}")

# 测试3: 使用双引号的JSON
print("\n测试3: 双引号JSON")
try:
    result = test_instance._run_gds_command(f'echo "{json_content}"')
    print(f"双引号返回码: {result.returncode}")
    print(f"双引号输出: {repr(result.stdout)}")
    print(f"双引号错误: {repr(result.stderr)}")
except Exception as e:
    print(f"双引号失败: {e}")

# 测试4: 转义的JSON
print("\n测试4: 转义JSON")
escaped_json = json_content.replace('"', '\\"')
print(f"转义后的JSON: {escaped_json}")
try:
    result = test_instance._run_gds_command(f'echo "{escaped_json}"')
    print(f"转义返回码: {result.returncode}")
    print(f"转义输出: {repr(result.stdout)}")
    print(f"转义错误: {repr(result.stderr)}")
except Exception as e:
    print(f"转义失败: {e}")

print("\n=== 测试完成 ===")