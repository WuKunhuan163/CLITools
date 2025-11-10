from test_gds import GDSTest

# Create an instance
test_instance = GDSTest()
GDSTest.setUpClass()
test_instance.setUp()

# Test complex_echo from test_02
complex_echo_file = test_instance.get_test_remote_path("complex_echo.txt")
content = "Line 1\\nLine 2\\tTabbed\\Backslash"  # bash默认echo输出字面值
# 注意：heredoc（单引号）不解释反斜杠，echo输出的是字面值 Line 1\nLine 2\tTabbed\Backslash
expected_content = "Line 1\\nLine 2\\tTabbed\\Backslash"  # 双反斜杠表示字面的单反斜杠

print(f"测试文件: {complex_echo_file}")
print(f"输入内容 (Python repr): {repr(content)}")
print(f"期望内容 (Python repr): {repr(expected_content)}")
print(f"期望内容 (实际字符): {expected_content}")

result = test_instance.gds(f'echo "{content}" > {complex_echo_file}')
print(f"\nEcho命令执行结果: returncode={result.returncode}")

# 读取实际内容
import time
time.sleep(2)
cat_result = test_instance.gds(f'cat {complex_echo_file}')
print(f"Cat命令返回码: {cat_result.returncode}")
print(f"实际内容 (stdout repr): {repr(cat_result.stdout)}")
print(f"实际内容 (显示): {cat_result.stdout}")

# 验证
verify_result = test_instance.verify_file_content_contains(complex_echo_file, expected_content, terminal_erase=True)
print(f"\n验证结果: {verify_result}")

# 清理
test_instance.tearDown()
GDSTest.tearDownClass()
