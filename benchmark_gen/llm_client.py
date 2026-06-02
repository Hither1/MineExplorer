from __future__ import annotations

import copy
import os
import time
from typing import Dict, List, Optional

import openai

DEFAULT_BASE_URL = ""  # Set AGENT_API_BASE in ~/.zshrc


def _is_claude_model(model: str) -> bool:
    return "claude" in model.lower()


def _apply_prefix_cache(messages: List[Dict]) -> List[Dict]:
    """Inject Anthropic prompt-cache control into the last cacheable message."""
    messages_copy = copy.deepcopy(messages)
    for msg in reversed(messages_copy):
        if msg.get("role") in ("user", "system", "tool"):
            content = msg.get("content", "")
            if isinstance(content, list):
                if content:
                    last_block = content[-1]
                    if isinstance(last_block, dict) and "cache_control" not in last_block:
                        last_block["cache_control"] = {"type": "ephemeral", "ttl": "5m"}
            else:
                msg["content"] = [{
                    "type": "text",
                    "text": content,
                    "cache_control": {"type": "ephemeral", "ttl": "5m"},
                }]
            break
    return messages_copy


class LLMClient:
    """OpenAI-SDK-based LLM client with parallel batch dispatch."""

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        batch_size: int = 20,
        timeout: int = 600,
        max_retries: int = 5,
    ):
        self.api_key = (
            api_key
            or os.environ.get("AGENT_API_KEY")
            or os.environ.get("AIGC_APP_KEY")
            or os.environ.get("OPENAI_API_KEY", "")
        )
        self.base_url = (
            base_url
            or os.environ.get("AGENT_API_BASE")
            or os.environ.get("AIGC_BASE_URL")
            or DEFAULT_BASE_URL
            or None
        )
        self.model = model
        self.batch_size = max(1, batch_size)
        self.timeout = timeout
        self.max_retries = max(0, max_retries)

        self._client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=0,
        )

    def chat(
        self,
        conversations: List[List[Dict]],
        temperature: float = 0.7,
        max_new_tokens: int = 4096,
    ) -> List[str]:
        """Send multiple conversations in parallel and return responses."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        total = len(conversations)
        results: List[str] = [""] * total
        if total == 0:
            return results

        def process_one(idx: int) -> None:
            messages = [
                {"role": m.get("role", "user"), "content": m.get("content", "")}
                for m in conversations[idx]
            ]
            results[idx] = self._call_one(messages, temperature, max_new_tokens)

        num_chunks = (total + self.batch_size - 1) // self.batch_size
        for chunk_idx in range(num_chunks):
            start = chunk_idx * self.batch_size
            end = min(start + self.batch_size, total)
            with ThreadPoolExecutor(max_workers=end - start) as executor:
                futures = [executor.submit(process_one, i) for i in range(start, end)]
                for future in as_completed(futures):
                    future.result()

        return results

    def _call_one(
        self,
        messages: List[Dict],
        temperature: float,
        max_new_tokens: int,
    ) -> str:
        use_cache = _is_claude_model(self.model)

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                send_messages = _apply_prefix_cache(messages) if use_cache else messages
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=send_messages,
                    temperature=temperature,
                    max_tokens=max_new_tokens,
                )
                if not response.choices:
                    raise ValueError(
                        f"Empty choices in response (model={self.model}, "
                        f"usage={response.usage})"
                    )
                choice = response.choices[0]

                if choice.finish_reason == "length" or choice.message is None:
                    usage = getattr(response, "usage", None)
                    reasoning = (
                        getattr(getattr(usage, "completion_tokens_details", None),
                                "reasoning_tokens", None)
                        if usage else None
                    )
                    hint = (
                        f" (reasoning_tokens={reasoning} consumed hidden budget)"
                        if reasoning else ""
                    )
                    print(
                        f"[LLMClient] WARNING: output truncated/empty because "
                        f"max_tokens={max_new_tokens} is too small{hint}. "
                        f"Increase --max-new-tokens and retry.",
                        flush=True,
                    )
                    return ""
                return choice.message.content or ""
            except Exception as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                sleep_s = min(60, 5 * (attempt + 1))
                print(
                    f"[LLMClient] request failed ({exc}), retry {attempt+1}/{self.max_retries} "
                    f"after {sleep_s}s",
                    flush=True,
                )
                time.sleep(sleep_s)

        if last_error is not None:
            print(f"[LLMClient] request failed after all retries: {last_error}", flush=True)
        return ""
