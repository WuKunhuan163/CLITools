"""Re-export shared NVIDIA GLM-4.7 provider."""
from logic.llm.nvidia_glm47 import (  # noqa: F401
    NvidiaGLM47Provider,
    get_api_key,
    save_api_key,
    NVIDIA_API_URL,
    MODEL_ID,
    DEFAULT_RPM,
    DEFAULT_MAX_CONTEXT,
)
