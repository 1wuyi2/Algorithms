"""External large-language-model client for scheduling assistant features.

The client is intentionally small and optional. If no API key is configured,
the assistant falls back to rule-based explanations so the project can still be
run and tested without network access.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class LLMProvider(str, Enum):
    """Supported LLM provider identifiers."""

    OPENAI = "openai"
    DOUBAO = "doubao"
    QIANWEN = "qianwen"
    ZHIPU = "zhipu"


@dataclass(frozen=True)
class LLMConfig:
    """Configuration for external LLM calls."""

    provider: LLMProvider
    api_key: str
    base_url: Optional[str] = None
    model: str = "gpt-3.5-turbo"
    timeout: int = 30


@dataclass(frozen=True)
class LLMResponse:
    """Normalized response returned by LLMClient."""

    content: str
    tokens_used: int
    success: bool
    error_message: Optional[str] = None


class LLMClient:
    """Minimal HTTP client for large-language-model APIs."""

    def __init__(self, config: LLMConfig):
        self.config = config

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """Generate text from the configured provider."""

        try:
            if self.config.provider == LLMProvider.OPENAI:
                return self._call_openai_compatible(
                    self.config.base_url or "https://api.openai.com/v1/chat/completions",
                    prompt,
                    system_prompt,
                )
            if self.config.provider == LLMProvider.DOUBAO:
                return self._call_openai_compatible(
                    self.config.base_url or "https://api.doubao.com/v1/chat/completions",
                    prompt,
                    system_prompt,
                )
            if self.config.provider == LLMProvider.ZHIPU:
                return self._call_openai_compatible(
                    self.config.base_url or "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                    prompt,
                    system_prompt,
                )
            if self.config.provider == LLMProvider.QIANWEN:
                return self._call_qianwen(
                    self.config.base_url or "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                    prompt,
                    system_prompt,
                )
            return LLMResponse("", 0, False, "Unsupported LLM provider")
        except Exception as exc:  # pragma: no cover - network failures depend on environment.
            return LLMResponse("", 0, False, str(exc))

    def _call_openai_compatible(self, url: str, prompt: str, system_prompt: Optional[str]) -> LLMResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": 0.3,
        }
        data = self._post_json(url, payload)
        content = data["choices"][0]["message"]["content"]
        tokens = int(data.get("usage", {}).get("total_tokens", 0))
        return LLMResponse(content=content, tokens_used=tokens, success=True)

    def _call_qianwen(self, url: str, prompt: str, system_prompt: Optional[str]) -> LLMResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.config.model,
            "input": {"messages": messages},
            "parameters": {"temperature": 0.3},
        }
        data = self._post_json(url, payload)
        output = data.get("output", {})
        choices = output.get("choices") or []
        content = choices[0]["message"]["content"] if choices else output.get("text", "")
        tokens = int(data.get("usage", {}).get("total_tokens", 0))
        return LLMResponse(content=content, tokens_used=tokens, success=True)

    def _post_json(self, url: str, payload: dict[str, object]) -> dict[str, object]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM API error {exc.code}: {detail}") from exc


def create_default_client() -> Optional[LLMClient]:
    """Create an LLM client from environment variables.

    Required:
    - LLM_API_KEY

    Optional:
    - LLM_PROVIDER: openai, doubao, qianwen, or zhipu
    - LLM_BASE_URL
    - LLM_MODEL
    """

    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        return None

    provider_value = os.getenv("LLM_PROVIDER", LLMProvider.OPENAI.value).lower()
    try:
        provider = LLMProvider(provider_value)
    except ValueError:
        return None

    return LLMClient(
        LLMConfig(
            provider=provider,
            api_key=api_key,
            base_url=os.getenv("LLM_BASE_URL"),
            model=os.getenv("LLM_MODEL", "gpt-3.5-turbo"),
        )
    )
