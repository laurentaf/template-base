"""
LLM Client — NIM Bridge (primary) + OpenRouter (fallback).

Provides chat completion, structured output, and embedding access
for all agents in the system.
"""

import asyncio
import json
import time
from dataclasses import dataclass

import httpx
from opentelemetry import trace

from src.core.config import settings

tracer = trace.get_tracer(__name__)

_MAX_RETRIES = 3
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


@dataclass
class LLMResponse:
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    provider: str = ""


class LLMClient:
    def __init__(self):
        self.nim_url = settings.NIM_BRIDGE_URL
        self.nim_key = settings.NVIDIA_API_KEY
        self.openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
        self.openrouter_key = settings.OPENROUTER_API_KEY
        self.default_model = "deepseek-ai/deepseek-v4-flash"
        self.http = httpx.Client(timeout=60.0)
        self.async_http = httpx.AsyncClient(timeout=60.0)

    def _build_providers(self):
        providers = []
        if self.nim_key:
            providers.append(("nim", self.nim_url, {"Authorization": f"Bearer {self.nim_key}"}))
        if self.openrouter_key:
            providers.append(
                (
                    "openrouter",
                    self.openrouter_url,
                    {
                        "Authorization": f"Bearer {self.openrouter_key}",
                        "HTTP-Referer": "https://github.com/laurentaf/template-base",
                    },
                )
            )
        return providers

    def _parse_response(
        self, data: dict, model: str, provider_name: str, elapsed: float
    ) -> LLMResponse:
        choice = data["choices"][0]
        usage = data.get("usage", {})
        return LLMResponse(
            content=choice["message"]["content"],
            model=data.get("model", model),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            latency_ms=round(elapsed, 1),
            provider=provider_name,
        )

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        response_format: dict | None = None,
    ) -> LLMResponse:
        model = model or self.default_model
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            body["response_format"] = response_format

        start = time.time()
        last_error: str | None = None
        providers = self._build_providers()

        for provider_name, url, headers in providers:
            for attempt in range(_MAX_RETRIES):
                try:
                    resp = self.http.post(
                        url,
                        headers={"Content-Type": "application/json", **headers},
                        json=body,
                        timeout=min(self.http.timeout, 120.0),
                    )
                    if resp.status_code == 200:
                        elapsed = (time.time() - start) * 1000
                        return self._parse_response(resp.json(), model, provider_name, elapsed)
                    if resp.status_code in _RETRYABLE_STATUS:
                        wait = 2**attempt
                        time.sleep(wait)
                        continue
                    last_error = f"{provider_name} {resp.status_code}: {resp.text[:200]}"
                    break
                except Exception as e:
                    last_error = f"{provider_name} error: {e}"
                    break

        raise RuntimeError(f"LLM call failed: {last_error}")

    async def chat_async(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        response_format: dict | None = None,
    ) -> LLMResponse:
        model = model or self.default_model
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            body["response_format"] = response_format

        start = time.time()
        last_error: str | None = None
        providers = self._build_providers()

        for provider_name, url, headers in providers:
            for attempt in range(_MAX_RETRIES):
                try:
                    resp = await self.async_http.post(
                        url,
                        headers={"Content-Type": "application/json", **headers},
                        json=body,
                        timeout=min(self.async_http.timeout, 120.0),
                    )
                    if resp.status_code == 200:
                        elapsed = (time.time() - start) * 1000
                        return self._parse_response(resp.json(), model, provider_name, elapsed)
                    if resp.status_code in _RETRYABLE_STATUS:
                        wait = 2**attempt
                        await asyncio.sleep(wait)
                        continue
                    last_error = f"{provider_name} {resp.status_code}: {resp.text[:200]}"
                    break
                except Exception as e:
                    last_error = f"{provider_name} error: {e}"
                    break

        raise RuntimeError(f"LLM async call failed: {last_error}")

    def extract_structured(self, messages, schema: dict, model=None) -> dict:
        resp = self.chat(
            messages,
            model=model,
            response_format={"type": "json_object"},
        )
        return json.loads(resp.content)

    async def extract_structured_async(self, messages, schema: dict, model=None) -> dict:
        resp = await self.chat_async(
            messages,
            model=model,
            response_format={"type": "json_object"},
        )
        return json.loads(resp.content)

    def embed(self, text: str, model: str | None = None) -> list[float] | None:
        body = {
            "model": model or "nvidia/nv-embed-qa-4",
            "input": text,
        }
        if self.nim_key:
            try:
                url = self.nim_url.replace("/chat/completions", "/embeddings")
                resp = self.http.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.nim_key}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
                if resp.status_code == 200:
                    return resp.json()["data"][0]["embedding"]
            except Exception:
                pass
        if self.openrouter_key:
            try:
                url = "https://openrouter.ai/api/v1/embeddings"
                resp = self.http.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.openrouter_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/laurentaf/template-base",
                    },
                    json=body,
                )
                if resp.status_code == 200:
                    return resp.json()["data"][0]["embedding"]
            except Exception:
                pass
        return None

    def close(self):
        self.http.close()

    async def aclose(self):
        await self.async_http.aclose()


llm = LLMClient()
