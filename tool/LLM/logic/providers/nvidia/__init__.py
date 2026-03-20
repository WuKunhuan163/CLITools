"""NVIDIA Build vendor configuration.

API docs: https://build.nvidia.com/
Free tier: ~40 RPM
Key format: nvapi-... (NGC keys do NOT work)
"""

DISPLAY_NAME = "NVIDIA"
CONFIG_VENDOR = "nvidia"
CONFIG_KEY_ENV = "NVIDIA_API_KEY"
API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
DOCS_URL = "https://build.nvidia.com/"
KEY_PORTAL_URL = "https://build.nvidia.com/"
