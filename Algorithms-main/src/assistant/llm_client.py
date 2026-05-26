"""Large language model API integration.

This module provides interfaces to external AI models for natural language
processing tasks including:
- Schedule explanation generation
- Optimization suggestion generation
- Q&A about scheduling problems
- Natural language interaction for scheduling
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import requests


class LLMProvider(str, Enum):
    """Supported large language model providers."""
    OPENAI = "openai"
    DOUBAO = "doubao"
    QIANWEN = "qianwen"
    ZHIPU = "zhipu"


@dataclass(frozen=True)
class LLMConfig:
    """Configuration for LLM API access."""
    provider: LLMProvider
    api_key: str
    base_url: Optional[str] = None
    model: str = "gpt-3.5-turbo"
    timeout: int = 30


@dataclass(frozen=True)
class LLMResponse:
    """Response from LLM API."""
    content: str
    tokens_used: int
    success: bool
    error_message: Optional[str] = None


class LLMClient:
    """Client for interacting with large language models."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.session = requests.Session()
        self.session.timeout = config.timeout
        if config.api_key:
            self.session.headers.update({"Authorization": f"Bearer {config.api_key}"})

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """Generate text using the configured LLM."""
        try:
            if self.config.provider == LLMProvider.OPENAI:
                return self._call_openai(prompt, system_prompt)
            elif self.config.provider == LLMProvider.DOUBAO:
                return self._call_doubao(prompt, system_prompt)
            elif self.config.provider == LLMProvider.QIANWEN:
                return self._call_qianwen(prompt, system_prompt)
            elif self.config.provider == LLMProvider.ZHIPU:
                return self._call_zhipu(prompt, system_prompt)
            else:
                return LLMResponse(content="", tokens_used=0, success=False, 
                                   error_message="Unsupported provider")
        except Exception as e:
            return LLMResponse(content="", tokens_used=0, success=False, 
                               error_message=str(e))

    def _call_openai(self, prompt: str, system_prompt: Optional[str]) -> LLMResponse:
        """Call OpenAI API."""
        url = self.config.base_url or "https://api.openai.com/v1/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.session.post(
            url,
            json={
                "model": self.config.model,
                "messages": messages,
                "temperature": 0.7,
            }
        )
        data = response.json()
        
        if response.status_code == 200:
            content = data["choices"][0]["message"]["content"]
            tokens = data["usage"]["total_tokens"]
            return LLMResponse(content=content, tokens_used=tokens, success=True)
        else:
            return LLMResponse(content="", tokens_used=0, success=False,
                               error_message=data.get("error", {}).get("message", "API error"))

    def _call_doubao(self, prompt: str, system_prompt: Optional[str]) -> LLMResponse:
        """Call Doubao API."""
        url = self.config.base_url or "https://api.doubao.com/v1/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.session.post(
            url,
            json={
                "model": self.config.model,
                "messages": messages,
                "temperature": 0.7,
            }
        )
        data = response.json()
        
        if response.status_code == 200:
            content = data["choices"][0]["message"]["content"]
            tokens = data["usage"].get("total_tokens", 0)
            return LLMResponse(content=content, tokens_used=tokens, success=True)
        else:
            return LLMResponse(content="", tokens_used=0, success=False,
                               error_message=data.get("error", {}).get("message", "API error"))

    def _call_qianwen(self, prompt: str, system_prompt: Optional[str]) -> LLMResponse:
        """Call Qianwen API."""
        url = self.config.base_url or "https://dashscope.aliyuncs.com/api/text/v1/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.session.post(
            url,
            json={
                "model": self.config.model,
                "input": {"messages": messages},
                "parameters": {"temperature": 0.7},
            }
        )
        data = response.json()
        
        if response.status_code == 200 and data.get("status") == "success":
            content = data["output"]["choices"][0]["message"]["content"]
            tokens = data["usage"].get("total_tokens", 0)
            return LLMResponse(content=content, tokens_used=tokens, success=True)
        else:
            return LLMResponse(content="", tokens_used=0, success=False,
                               error_message=data.get("message", "API error"))

    def _call_zhipu(self, prompt: str, system_prompt: Optional[str]) -> LLMResponse:
        """Call Zhipu API."""
        url = self.config.base_url or "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.session.post(
            url,
            json={
                "model": self.config.model,
                "messages": messages,
                "temperature": 0.7,
            }
        )
        data = response.json()
        
        if response.status_code == 200:
            content = data["choices"][0]["message"]["content"]
            tokens = data["usage"]["total_tokens"]
            return LLMResponse(content=content, tokens_used=tokens, success=True)
        else:
            return LLMResponse(content="", tokens_used=tokens, success=False,
                               error_message=data.get("error", {}).get("message", "API error"))


# Default client with environment configuration
def create_default_client() -> Optional[LLMClient]:
    """Create LLM client from environment variables."""
    provider_str = os.getenv("LLM_PROVIDER", "openai").lower()
    api_key = os.getenv("LLM_API_KEY")
    
    if not api_key:
        return None
    
    try:
        provider = LLMProvider(provider_str)
    except ValueError:
        return None
    
    config = LLMConfig(
        provider=provider,
        api_key=api_key,
        base_url=os.getenv("LLM_BASE_URL"),
        model=os.getenv("LLM_MODEL", "gpt-3.5-turbo"),
    )
    return LLMClient(config)
