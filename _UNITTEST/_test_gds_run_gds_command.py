from test_gds import GDSTest

# Create an instance
test_instance = GDSTest()
GDSTest.setUpClass()  # 初始化类属性
test_instance.setUp()

# Define necessary variables here
json_content = "{'name': 'test', 'value': 123}"
correct_json_file = "/Users/wukunhuan/.local/bin/_UNITTEST/_TEMP/correct_json.txt"

# Run the test
result = test_instance._run_gds_command(f"""

echo "{json_content}" > "{correct_json_file}"

""")
print(result)
