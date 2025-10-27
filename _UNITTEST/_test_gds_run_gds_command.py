from test_gds import GDSTest

# Create an instance
test_instance = GDSTest()
GDSTest.setUpClass()  # 初始化类属性
test_instance.setUp()

# Define necessary variables here
json_content = "{'name': 'test', 'value': 123}".replace("'", "\'")
json_file = "~/correct_json.txt"

# Run the test
result = test_instance._run_gds_command(f'echo "{json_content}" > "{json_file}"; ')
print(result)

test_instance.assertTrue(test_instance._verify_file_content_contains(json_file, json_content, terminal_erase = True))
