"""Baidu Qianfan vendor configuration.

V2 API Key authentication (OpenAI-compatible).
API key format: bce-v3/ALTAK-xxx/secret

API docs: https://cloud.baidu.com/doc/qianfan-docs/s/Jm8r1826a
Key portal: https://console.bce.baidu.com/iam/#/iam/apikey/list
"""

DISPLAY_NAME = "Baidu"
CONFIG_VENDOR = "baidu"
CONFIG_KEY_ENV = "BAIDU_API_KEY"
API_URL = "https://qianfan.baidubce.com/v2/chat/completions"
DOCS_URL = "https://cloud.baidu.com/doc/qianfan-docs/s/Jm8r1826a"
KEY_PORTAL_URL = "https://console.bce.baidu.com/iam/#/iam/apikey/list"
