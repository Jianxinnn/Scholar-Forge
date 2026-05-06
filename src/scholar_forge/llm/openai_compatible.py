from __future__ import annotations

from typing import Any

import httpx

from scholar_forge.config import ScholarForgeConfig


class OpenAICompatibleLLM:
    def __init__(self, config: ScholarForgeConfig):
        self.base_url = (config.llm_base_url or "https://api.openai.com/v1").rstrip("/")
        self.api_key = config.llm_api_key
        self.model = config.llm_model

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def complete_text(self, prompt: str, *, temperature: float = 0.1, max_tokens: int = 1200) -> str:
        if not self.available:
            raise RuntimeError("LLM API key is not configured")
        base_payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        payloads = [
            {**base_payload, "max_tokens": max_tokens},
            {**base_payload, "max_completion_tokens": max_tokens},
            {"model": self.model, "messages": base_payload["messages"], "max_tokens": max_tokens},
        ]
        if self.base_url.endswith("/v1"):
            urls = [f"{self.base_url}/chat/completions"]
        else:
            urls = [f"{self.base_url}/v1/chat/completions", f"{self.base_url}/chat/completions"]
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        last_error: Exception | None = None
        with httpx.Client(timeout=180, trust_env=False) as client:
            for url in urls:
                for payload in payloads:
                    try:
                        resp = client.post(url, json=payload, headers=headers)
                        if resp.status_code in {400, 404, 405, 422}:
                            last_error = httpx.HTTPStatusError(
                                f"Client error {resp.status_code} for {url}: {resp.text[:500]}",
                                request=resp.request,
                                response=resp,
                            )
                            continue
                        resp.raise_for_status()
                        data = resp.json()
                        return data["choices"][0]["message"]["content"]
                    except httpx.TimeoutException as exc:
                        raise exc
                    except Exception as exc:
                        last_error = exc
                        continue
        if last_error:
            raise last_error
        raise RuntimeError("LLM request failed")
