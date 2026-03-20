"""SiliconFlow vendor configuration.

API docs: https://docs.siliconflow.cn/quickstart
Free tier: 3 RPS, 100 RPM (select open-source models)
Key format: sk-...

Note: Keys from cloud.siliconflow.com use api.siliconflow.com endpoint.
      Keys from cloud.siliconflow.cn use api.siliconflow.cn endpoint.
"""

DISPLAY_NAME = "SiliconFlow"
CONFIG_VENDOR = "siliconflow"
CONFIG_KEY_ENV = "SILICONFLOW_API_KEY"
API_URL = "https://api.siliconflow.com/v1/chat/completions"
API_URL_CN = "https://api.siliconflow.cn/v1/chat/completions"
DOCS_URL = "https://docs.siliconflow.cn/quickstart"
KEY_PORTAL_URL = "https://cloud.siliconflow.com/me/account/ak"
