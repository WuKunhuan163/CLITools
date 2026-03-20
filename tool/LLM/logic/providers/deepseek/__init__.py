"""DeepSeek vendor configuration.

API docs: https://api-docs.deepseek.com
Auth: Bearer token in Authorization header
Key format: sk-...
Pricing: Very affordable. $0.28/M input (cache miss), $0.42/M output.

Models: deepseek-chat (V3.2 non-thinking), deepseek-reasoner (V3.2 thinking)
Both models share the same endpoint and key.
"""

DISPLAY_NAME = "DeepSeek"
CONFIG_VENDOR = "deepseek"
CONFIG_KEY_ENV = "DEEPSEEK_API_KEY"
API_URL = "https://api.deepseek.com/chat/completions"
DOCS_URL = "https://api-docs.deepseek.com"
KEY_PORTAL_URL = "https://platform.deepseek.com/api_keys"
