"""
LLM Client — NIM Bridge (primary) + OpenRouter (fallback).

Provides chat completion, structured output, and embedding access
for all agents in the system.
"""

import json
import time
from dataclasses import dataclass

import httpx
from opentelemetry import trace

from src.core.config import settings

tracer = trace.get_tracer(__name__)


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

        for provider_name, url, headers in providers:
            try:
                resp = self.http.post(
                    url,
                    headers={"Content-Type": "application/json", **headers},
                    json=body,
                    timeout=min(self.http.timeout, 120.0),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    elapsed = (time.time() - start) * 1000
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
                last_error = f"{provider_name} {resp.status_code}: {resp.text[:200]}"
            except Exception as e:
                last_error = f"{provider_name} error: {e}"

        raise RuntimeError(f"LLM call failed: {last_error}")

    def chat_async(self, messages, model=None, temperature=0.3, max_tokens=2048):
        """Non-blocking variant for use inside async agents."""
        return self.chat(messages, model, temperature, max_tokens)

    def extract_structured(self, messages, schema: dict, model=None) -> dict:
        resp = self.chat(
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


llm = LLMClient()
