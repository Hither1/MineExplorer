from __future__ import annotations
from typing import Any

from loguru import logger
from openai import OpenAI
from .base import BaseLLMProvider
from playground.utils.timeout import deco_retry_exponential, deco_retry_on_ratelimit

class OpenAIProvider(BaseLLMProvider):
    def __init__(
        self, 
        api_key: str | None = None, 
        api_base: str | None = None,
        default_model: str = "gpt-5.2-chat"
    ) -> None:
        super().__init__(api_key, api_base)
        self.default_model = default_model

        if api_base and not api_base.endswith('/'):
            api_base += '/'
        self.api_base = api_base

        self.client = OpenAI(api_key=self.api_key, base_url=self.api_base)


    @deco_retry_on_ratelimit(max_retries=10, wait_seconds=60)
    def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        timeout : int = 60,
        response_format: dict | None = None
    ) -> str:
        logger.info("Querying LLM directly via OpenAI client...")
        # Strip provider prefix if it exists, as OpenAI client doesn't need it
        model = model if model else self.default_model
        # kimi models only accept temperature=1
        if model.startswith("kimi"):
            temperature = 1
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            timeout=timeout,
            temperature=temperature,
            response_format=response_format
        )
        response_content = response.choices[0].message.content

        return response_content