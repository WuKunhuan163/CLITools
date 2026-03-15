"""Zhipu AI vendor configuration.

API docs: https://open.bigmodel.cn/dev/api/thirdparty-frame/openai-sdk
Free tier: varies by model (GLM-4.7-Flash: free with rate limits)
Key portal: https://open.bigmodel.cn/usercenter/apikeys

Supports both zhipuai SDK and OpenAI-compatible urllib fallback.
"""

DISPLAY_NAME = "Zhipu"
CONFIG_VENDOR = "zhipu"
CONFIG_KEY_ENV = "ZHIPU_API_KEY"
API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
DOCS_URL = "https://open.bigmodel.cn/dev/api/thirdparty-frame/openai-sdk"
KEY_PORTAL_URL = "https://open.bigmodel.cn/usercenter/apikeys"
