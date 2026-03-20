"""Tencent Hunyuan vendor configuration.

API docs: https://cloud.tencent.com/document/product/1729/111007
Free tier: 5 QPS (concurrent sessions)
Key portal: https://console.cloud.tencent.com/hunyuan/start
OpenAI-compatible endpoint using Bearer token auth.
"""

DISPLAY_NAME = "Tencent"
CONFIG_VENDOR = "tencent"
CONFIG_KEY_ENV = "TENCENT_API_KEY"
API_URL = "https://api.hunyuan.cloud.tencent.com/v1/chat/completions"
DOCS_URL = "https://cloud.tencent.com/document/product/1729/111007"
KEY_PORTAL_URL = "https://console.cloud.tencent.com/hunyuan/start"
