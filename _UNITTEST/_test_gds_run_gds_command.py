from test_gds import GDSTest

# Create an instance
test_instance = GDSTest()
GDSTest.setUpClass()
test_instance.setUp()

# Define necessary variables here
complex_json = '{"users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}], "total": 2}'
complex_json_escaped = complex_json.replace('"', '\\"')
json_file = "~/correct_json.txt"

# Run the test
result = test_instance.gds(f'''
echo "{complex_json_escaped}" > "{json_file}"; 
''')
print(result)

test_instance.assertTrue(test_instance.verify_file_content_contains(json_file, complex_json, terminal_erase = True))
