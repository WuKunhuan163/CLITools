"""Zhipu GLM-4.7-Flash context pipeline.

GLM-4.7-Flash is a reasoning model: it produces reasoning_content (thinking)
separately from content (answer). Reasoning tokens consume the max_tokens
budget, so this pipeline:

1. Inherits tool history flattening from GLM-4-Flash pipeline (safety net)
2. Validates responses: if reasoning was produced but content is empty AND
   finish_reason is 'length', it means max_tokens was too low for both
   reasoning + content — signals retry with note to increase budget
3. Handles the case where the model produces only reasoning (all tokens
   consumed by thinking) — returns the reasoning as a fallback
"""
from typing import Any, Dict, List, Optional

from tool.LLM.logic.providers.zhipu_glm4.pipeline.context import ZhipuContextPipeline


class ZhipuGLM47FlashPipeline(ZhipuContextPipeline):
    """Pipeline for Zhipu GLM-4.7-Flash reasoning model.

    Extends GLM-4-Flash pipeline with reasoning-specific validation.
    """

    def validate_response(
        self,
        text: str,
        tool_calls: List[Dict[str, Any]],
        finish_reason: str = "",
        usage: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        reasoning_tokens = (usage or {}).get("reasoning_tokens", 0)

        if not text and not tool_calls and finish_reason == "length" and reasoning_tokens > 0:
            return {
                "valid": False,
                "retry": True,
                "reason": (
                    f"Reasoning model used {reasoning_tokens} tokens for thinking "
                    f"but ran out of budget for content (finish_reason=length). "
                    f"Retrying with higher max_tokens."),
                "text": text,
                "tool_calls": tool_calls,
                "increase_max_tokens": True,
            }

        return super().validate_response(text, tool_calls, finish_reason, usage)

    def get_max_retries(self) -> int:
        return 3

    def get_recommended_max_tokens(self, current: int) -> int:
        """Suggest a higher max_tokens when reasoning exhausts the budget."""
        return min(current * 2, 16384)
