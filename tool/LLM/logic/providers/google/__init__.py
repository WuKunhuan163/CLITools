"""Google (Gemini) provider — delegates to model-specific implementations.

Actual provider implementations live at the model level:
  - gemini-2.0-flash: tool/LLM/logic/models/gemini_2_0_flash/providers/google/

Register via the registry:
  from tool.LLM.logic.registry import get_provider
  provider = get_provider("google-gemini-2.0-flash")
"""
from tool.LLM.logic.models.gemini_2_0_flash.providers.google.interface import (
    GoogleGeminiFlashProvider,
)

__all__ = ["GoogleGeminiFlashProvider"]
