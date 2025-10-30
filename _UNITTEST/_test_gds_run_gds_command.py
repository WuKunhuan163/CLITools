from test_gds import GDSTest

# Create an instance
test_instance = GDSTest()
GDSTest.setUpClass()  # 初始化类属性
test_instance.setUp()

print("=" * 60)
print("测试echo重定向命令")
print("=" * 60)

# Test echo redirection
echo_file = test_instance.get_test_file_path("test_echo.txt")
print(f"目标文件路径: {echo_file}")

# 构造命令 - 按照test_02中的格式
command = f'\'echo "Test content" > "{echo_file}"\''
print(f"执行命令: {command}")

# 执行命令
result = test_instance._run_gds_command(command)
print(f"返回码: {result.returncode}")
print(f"Stdout长度: {len(result.stdout)}")
print(f"Stdout前500字符: {result.stdout[:500]}")
print(f"Stderr: {result.stderr if result.stderr else '(empty)'}")

# 验证文件内容
print(f"\n开始验证文件内容...")
verify_result = test_instance._verify_file_content_contains(echo_file, "Test content")
print(f"验证结果: {verify_result}")

# 如果验证失败，读取实际的文件内容
if not verify_result:
    print(f"\n读取实际文件内容...")
    cat_result = test_instance._run_gds_command(f"cat {echo_file}")
    print(f"cat返回码: {cat_result.returncode}")
    print(f"cat输出: {cat_result.stdout}")
else:
    print(f"✅ 测试通过！")
