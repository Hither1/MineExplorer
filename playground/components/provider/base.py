from __future__ import annotations
import abc
from abc import abstractmethod
from typing import Any


class BaseLLMProvider(abc.ABC):
    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None
    ) -> None:
        self.api_key = api_key
        self.api_base = api_base
    
    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        max_tokens: int = 10240,
        temperature: float = 0.7,
        response_format: dict | None = None
    ) -> str:
        raise NotImplementedError("BaseLLMProvider is an abstract class, you need to  implement subclass")