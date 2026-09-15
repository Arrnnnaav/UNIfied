"""Provider-neutral synthesis client for local OpenAI-compatible runtimes and cloud gateways."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from app.core.config import get_settings
from app.core.providers import choose_model


def grounded_completion(question: str, evidence: list[dict[str, Any]]) -> tuple[str | None, dict[str, Any]]:
    settings = get_settings()
    decision = choose_model("tutor")
    base_url = settings.local_llm_base_url
    api_key = None
    if base_url:
        model = settings.local_llm_model
        api_key = "local"
    elif settings.openai_api_key:
        base_url, model, api_key = "https://api.openai.com/v1", settings.tutor_model or "gpt-4o-mini", settings.openai_api_key
    elif settings.anthropic_api_key:
        model = settings.tutor_model or "claude-3-5-sonnet-latest"
        try:
            import httpx
            prompt = "\n\n".join(f"SOURCE {i+1} (page {item.get('page')}, chunk {item.get('chunk')}): {item.get('quote')}" for i, item in enumerate(evidence))
            with httpx.Client(trust_env=False, timeout=settings.llm_timeout_seconds) as client:
                response = client.post("https://api.anthropic.com/v1/messages", headers={
                    "x-api-key": settings.anthropic_api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}, json={
                    "model": model, "max_tokens": 900, "temperature": 0.1,
                    "system": "You are a careful study tutor. Answer only from the supplied sources. If they are insufficient, say so. Do not invent citations.",
                    "messages": [{"role": "user", "content": f"Question: {question}\n\n{prompt}"}]})
            response.raise_for_status()
            data = response.json()
            answer = "".join(item.get("text", "") for item in data.get("content", []) if item.get("type") == "text")
            return answer, {"provider": "anthropic", "model": model, "status": "generated"}
        except Exception as exc:
            return None, {"provider": "anthropic", "model": model, "status": "fallback", "error": str(exc)[:160]}
    else:
        return None, {"provider": decision.provider, "model": decision.model, "status": "fallback"}
    try:
        import httpx
        prompt = "\n\n".join(f"SOURCE {i+1} (page {item.get('page')}, chunk {item.get('chunk')}): {item.get('quote')}" for i, item in enumerate(evidence))
        if settings.local_llm_base_url:
            parsed = urlparse(settings.local_llm_base_url)
            native_base = settings.local_llm_base_url.rstrip("/")[:-3] if parsed.path.rstrip("/").endswith("/v1") else settings.local_llm_base_url.rstrip("/")
            with httpx.Client(trust_env=False, timeout=settings.llm_timeout_seconds) as client:
                response = client.post(f"{native_base}/api/chat", json={
                    "model": model,
                    "stream": False,
                    "think": False,
                    "options": {"temperature": 0.1, "num_predict": 300},
                    "messages": [{"role": "system", "content": "You are a careful study tutor. Answer only from the supplied sources. If they are insufficient, say so. Do not invent citations."}, {"role": "user", "content": f"Question: {question}\n\n{prompt}"}],
                })
            response.raise_for_status()
            return response.json()["message"]["content"], {"provider": "local", "model": model, "status": "generated", "transport": "ollama-native"}
        with httpx.Client(trust_env=False, timeout=settings.llm_timeout_seconds) as client:
            response = client.post(f"{base_url.rstrip('/')}/chat/completions", headers={"Authorization": f"Bearer {api_key}"}, json={
            "model": model, "temperature": 0.1, "messages": [{"role": "system", "content": "You are a careful study tutor. Answer only from the supplied sources. If they are insufficient, say so. Do not invent citations."}, {"role": "user", "content": f"Question: {question}\n\n{prompt}"}],
            })
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"], {"provider": "local" if settings.local_llm_base_url else "openai", "model": model, "status": "generated"}
    except Exception as exc:
        local_error = str(exc)[:160]
        if settings.local_llm_base_url and settings.openai_api_key:
            try:
                with httpx.Client(trust_env=False, timeout=settings.llm_timeout_seconds) as client:
                    response = client.post("https://api.openai.com/v1/chat/completions", headers={"Authorization": f"Bearer {settings.openai_api_key}"}, json={
                        "model": settings.tutor_model or "gpt-4o-mini", "temperature": 0.1,
                        "messages": [{"role": "system", "content": "You are a careful study tutor. Answer only from the supplied sources. If they are insufficient, say so. Do not invent citations."}, {"role": "user", "content": f"Question: {question}\n\n{prompt}"}],
                    })
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"], {"provider": "openai", "model": settings.tutor_model or "gpt-4o-mini", "status": "generated", "fallback_from": "local"}
            except Exception as cloud_exc:
                return None, {"provider": "local", "model": model, "status": "fallback", "error": local_error, "cloud_fallback_error": str(cloud_exc)[:160]}
        return None, {"provider": "local" if settings.local_llm_base_url else "openai", "model": model, "status": "fallback", "error": local_error}
