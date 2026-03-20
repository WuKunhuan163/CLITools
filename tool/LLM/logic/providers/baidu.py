"""Baidu Qianfan vendor configuration.

API docs: https://cloud.baidu.com/doc/qianfan/s/rmh4stp0j
Free models: ernie-speed-pro-128k, ernie-lite-pro-128k (10000 RPM, 800K TPM)
Key format: bce-v3/ALTAK-... (Bearer token authentication)
"""

DISPLAY_NAME = "Baidu"
CONFIG_VENDOR = "baidu"
CONFIG_KEY_ENV = "BAIDU_API_KEY"
API_URL = "https://qianfan.baidubce.com/v2/chat/completions"
DOCS_URL = "https://cloud.baidu.com/doc/qianfan/s/rmh4stp0j"
KEY_PORTAL_URL = "https://console.bce.baidu.com/iam/#/iam/apikey/list"
