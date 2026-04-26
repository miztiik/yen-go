"""Model-agnostic LLM client using OpenAI-compatible API.

Supports any provider with an OpenAI-compatible endpoint:
- OpenAI (api.openai.com)
- Anthropic Claude (via OpenAI-compat endpoint)
- GitHub Copilot subagents
- Local models (Ollama, LM Studio, vLLM)
- Azure OpenAI, Together AI, Groq, etc.

Swapping models = changing base_url + model + api_key_env. Zero code changes.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

from openai import OpenAI

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for the LLM provider."""

    base_url: str = "https://api.openai.com/v1"
    api_key_env: str = "OPENAI_API_KEY"
    model: str = "gpt-4o"
    temperature: float = 0.3
    max_tokens: int = 2048

    @classmethod
    def from_dict(cls, data: dict) -> LLMConfig:
        provider = data.get("provider", {})
        return cls(
            base_url=provider.get("base_url", cls.base_url),
            api_key_env=provider.get("api_key_env", cls.api_key_env),
            model=provider.get("model", cls.model),
            temperature=provider.get("temperature", cls.temperature),
            max_tokens=provider.get("max_tokens", cls.max_tokens),
        )


class TeachingLLMClient:
    """OpenAI-compatible LLM client for teaching comment generation."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        api_key = os.environ.get(config.api_key_env, "")
        if not api_key:
            raise ValueError(
                f"API key not found. Set the {config.api_key_env} environment variable."
            )
        self.client = OpenAI(
            base_url=config.base_url,
            api_key=api_key,
        )

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict:
        """Send a prompt to the LLM and parse the JSON response.

        Args:
            system_prompt: System instruction (persona + constraints).
            user_prompt: The enrichment data + request.

        Returns:
            Parsed JSON dict from the LLM response.

        Raises:
            ValueError: If the LLM response cannot be parsed as JSON.
        """
        logger.info(
            "LLM request: model=%s, base_url=%s",
            self.config.model,
            self.config.base_url,
        )

        response = self.client.chat.completions.create(
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from LLM")

        logger.info(
            "LLM response: %d chars, model=%s",
            len(content),
            response.model,
        )

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}") from e
