"""
LLM abstraction layer using LiteLLM.

Supports any model LiteLLM supports — switch with a single string:
  - OpenAI:     "gpt-4o", "gpt-5.4", "o3-pro"
  - Anthropic:  "claude-opus-4-6", "claude-sonnet-4-6"
  - Local:      "ollama/llama3", "ollama/mistral"
  - And 100+ more providers

API keys are read from environment variables (loaded from root .env):
  OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.

Usage:
    from agent.llm import LLMClient

    llm = LLMClient(model="gpt-4o")
    response = llm.chat(
        messages=[{"role": "user", "content": "Hello"}],
        tools=[...],  # OpenAI function-calling format
    )
"""

import json
import logging
from typing import Any, Dict, List, Optional

import litellm

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Thin wrapper around LiteLLM for consistent tool-calling across providers.

    The same code works whether you're hitting GPT-4o, Claude, or a local
    Ollama model — LiteLLM handles the translation.
    """

    def __init__(
        self,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Any:
        """
        Send messages to the LLM and get a response.

        Args:
            messages: Conversation history in OpenAI format
                      [{"role": "system", "content": "..."}, ...]
            tools: Optional list of tools in OpenAI function-calling format
                   [{"type": "function", "function": {"name": ..., "parameters": ...}}]

        Returns:
            LiteLLM ModelResponse (same shape as OpenAI ChatCompletion).
        """
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        logger.debug(f"LLM request: model={self.model}, messages={len(messages)}, tools={len(tools or [])}")
        response = litellm.completion(**kwargs)
        logger.debug(f"LLM response: finish_reason={response.choices[0].finish_reason}")

        return response

    @staticmethod
    def extract_tool_calls(response) -> List[Dict[str, Any]]:
        """
        Extract tool calls from an LLM response.

        Returns a list of dicts:
            [{"id": "call_xyz", "name": "tool_name", "arguments": {...}}]
        Returns empty list if the LLM didn't request any tool calls.
        """
        choice = response.choices[0]
        if not choice.message.tool_calls:
            return []

        calls = []
        for tc in choice.message.tool_calls:
            args = tc.function.arguments
            if isinstance(args, str):
                args = json.loads(args)
            calls.append({
                "id": tc.id,
                "name": tc.function.name,
                "arguments": args,
            })
        return calls

    @staticmethod
    def get_text_response(response) -> Optional[str]:
        """Extract plain text content from an LLM response (if any)."""
        choice = response.choices[0]
        return choice.message.content
