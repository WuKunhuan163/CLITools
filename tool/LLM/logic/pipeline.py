"""Base context pipeline for LLM providers.

Each provider can have a custom pipeline that transforms messages,
tools, and responses to handle model-specific quirks. The default
pipeline is a pass-through.

Pipeline stages:
  1. prepare_messages(): Transform messages before sending to API
  2. prepare_tools(): Filter/transform tool schemas for the model
  3. validate_response(): Check response and decide if retry needed

Architecture:
    ConversationManager
        → pipeline.prepare_messages(messages)
        → pipeline.prepare_tools(tools, capabilities)
        → provider.stream(prepared_messages, tools=prepared_tools)
        → pipeline.validate_response(response)
"""
from typing import Any, Dict, List, Optional


class ContextPipeline:
    """Base context pipeline — pass-through implementation.

    Override in provider-specific pipelines to handle model quirks.
    """

    def prepare_messages(
        self,
        messages: List[Dict[str, Any]],
        turn_number: int = 1,
    ) -> List[Dict[str, Any]]:
        """Transform messages before sending to the API.

        Parameters
        ----------
        messages : list
            OpenAI-format message list.
        turn_number : int
            Which user turn this is (1 = first message, 2+ = follow-up).

        Returns
        -------
        list
            Transformed messages.
        """
        return messages

    def prepare_tools(
        self,
        tools: Optional[List[Dict[str, Any]]],
        capabilities: Optional[Any] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """Filter or transform tool schemas based on model capabilities.

        For example, remove image-related tools for non-vision models,
        or simplify complex tool schemas for weaker models.
        """
        return tools

    def validate_response(
        self,
        text: str,
        tool_calls: List[Dict[str, Any]],
        finish_reason: str = "",
        usage: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Validate the model's response and decide if retry is needed.

        Returns
        -------
        dict
            {
                "valid": bool,
                "retry": bool,
                "reason": str (if invalid),
                "text": str (possibly cleaned text),
                "tool_calls": list (possibly cleaned tool_calls),
            }
        """
        return {
            "valid": True,
            "retry": False,
            "text": text,
            "tool_calls": tool_calls,
        }

    def get_max_retries(self) -> int:
        """Maximum number of retries this pipeline allows for empty responses."""
        return 2
