"""Anthropic vendor configuration.

API docs: https://docs.anthropic.com/en/api/messages
Auth: x-api-key header (NOT Bearer token)
Key format: sk-ant-...
Pricing: Pay-per-token, no free tier.

Models: Claude Opus 4.6, Claude Sonnet 4.6, Claude Haiku 4.5
"""

DISPLAY_NAME = "Anthropic"
CONFIG_VENDOR = "anthropic"
CONFIG_KEY_ENV = "ANTHROPIC_API_KEY"
API_URL = "https://api.anthropic.com/v1/messages"
DOCS_URL = "https://docs.anthropic.com/en/api"
KEY_PORTAL_URL = "https://console.anthropic.com/settings/keys"
API_VERSION = "2023-06-01"
