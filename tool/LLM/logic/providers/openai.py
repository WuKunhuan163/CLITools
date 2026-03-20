"""OpenAI vendor configuration.

API docs: https://platform.openai.com/docs
Auth: Bearer token in Authorization header
Key format: sk-...
Pricing: Pay-per-token, no free tier.

Models: GPT-4o, GPT-4o-mini, GPT-5.4 (latest), GPT-5-mini
"""

DISPLAY_NAME = "OpenAI"
CONFIG_VENDOR = "openai"
CONFIG_KEY_ENV = "OPENAI_API_KEY"
API_URL = "https://api.openai.com/v1/chat/completions"
DOCS_URL = "https://platform.openai.com/docs"
KEY_PORTAL_URL = "https://platform.openai.com/api-keys"
