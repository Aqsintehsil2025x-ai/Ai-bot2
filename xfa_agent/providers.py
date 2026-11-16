"""Per-user AI provider catalogue and safe API adapters for XFA."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

PROVIDERS = {
    "gemini": {
        "name": "Google Gemini", "kind": "gemini",
        "models": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
        "default_model": "gemini-2.5-flash",
        "note": "Google AI Studio API key",
    },
    "nvidia": {
        "name": "NVIDIA NIM", "kind": "openai",
        "base_url": "https://integrate.api.nvidia.com/v1/chat/completions",
        "models": ["meta/llama-3.3-70b-instruct", "deepseek-ai/deepseek-v4-flash", "qwen/qwen3-next-80b-a3b-instruct", "openai/gpt-oss-120b"],
        "default_model": "meta/llama-3.3-70b-instruct",
        "note": "NVIDIA NIM API key",
    },
    "groq": {
        "name": "Groq", "kind": "openai",
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "models": ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"],
        "default_model": "openai/gpt-oss-120b",
        "note": "GroqCloud API key; current models and pricing may change",
    },
    "openrouter": {
        "name": "OpenRouter", "kind": "openai",
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "models": ["openrouter/free", "nvidia/nemotron-3-ultra:free", "nvidia/nemotron-3.5-super-vl:free"],
        "default_model": "openrouter/free",
        "note": "One key for multiple models; free routes are rate-limited",
    },
    "cerebras": {
        "name": "Cerebras", "kind": "openai",
        "base_url": "https://api.cerebras.ai/v1/chat/completions",
        "models": ["gpt-oss-120b", "qwen3.8-27b"],
        "default_model": "gpt-oss-120b",
        "note": "Cerebras API key; check current usage pricing and access limits",
    },
    "deepseek": {
        "name": "DeepSeek", "kind": "openai",
        "base_url": "https://api.deepseek.com/chat/completions",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "default_model": "deepseek-chat",
        "note": "DeepSeek API key",
    },
    "mistral": {
        "name": "Mistral AI", "kind": "openai",
        "base_url": "https://api.mistral.ai/v1/chat/completions",
        "models": ["mistral-small-latest", "mistral-large-latest", "codestral-latest"],
        "default_model": "mistral-small-latest",
        "note": "Mistral API key",
    },
    "together": {
        "name": "Together AI", "kind": "openai",
        "base_url": "https://api.together.xyz/v1/chat/completions",
        "models": ["meta-llama/Llama-3.3-70B-Instruct-Turbo", "Qwen/Qwen3-Next-80B-A3B-Instruct"],
        "default_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "note": "Together AI API key",
    },
    "openai": {
        "name": "OpenAI", "kind": "openai",
        "base_url": "https://api.openai.com/v1/chat/completions",
        "models": ["gpt-4.1-mini", "gpt-4.1"],
        "default_model": "gpt-4.1-mini",
        "note": "OpenAI API key; paid usage may apply",
    },
}


def public_catalog():
    return {
        key: {
            "id": key, "name": value["name"], "models": value["models"],
            "default_model": value["default_model"], "note": value["note"],
        }
        for key, value in PROVIDERS.items()
    }


def _openai_compatible(provider: str, api_key: str, model: str, messages: list[dict], *, test=False) -> str:
    config = PROVIDERS[provider]
    payload = {
        "model": model,
        "messages": (
            [{"role": "user", "content": "Reply with OK."}]
            if test else [
                {"role": "system", "content": "You are XFA, a careful and helpful AI assistant. Reply in the user's language. Never claim actions were completed when they were not. Never ask for passwords or API keys."},
                *[{"role": "assistant" if item["role"] == "model" else "user", "content": item["content"]}
                  for item in messages],
            ]
        ),
        "max_tokens": 8 if test else 1200,
        "temperature": 0.2 if test else 0.55,
    }
    request = urllib.request.Request(
        config["base_url"],
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "XFA/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            raw = response.read(2 * 1024 * 1024)
    except urllib.error.HTTPError as exc:
        # Never return the provider response body: it may contain sensitive metadata.
        if exc.code in (401, 403):
            raise ValueError("API anahtarı geçersiz veya bu modele erişim izni yok.") from exc
        if exc.code == 429:
            raise ValueError("API kullanım limiti dolmuş. Daha sonra tekrar dene.") from exc
        raise RuntimeError("AI sağlayıcısı isteği reddetti. Model adını ve sağlayıcı durumunu kontrol et.") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("AI sağlayıcısına bağlanılamadı.") from exc
    try:
        data = json.loads(raw.decode("utf-8"))
        answer = data["choices"][0]["message"]["content"]
        if isinstance(answer, list):
            answer = "".join(str(part.get("text", "")) for part in answer if isinstance(part, dict))
        return str(answer or "").strip()
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("AI sağlayıcısından beklenmeyen yanıt alındı.") from exc


def generate(provider: str, api_key: str, model: str, messages: list[dict], *, test=False) -> str:
    if provider not in PROVIDERS:
        raise ValueError("Desteklenmeyen AI sağlayıcısı.")
    config = PROVIDERS[provider]
    if model not in config["models"]:
        raise ValueError("Bu sağlayıcı için desteklenmeyen model seçildi.")
    if not isinstance(api_key, str) or not api_key.strip() or len(api_key) > 20000 or chr(13) in api_key or chr(10) in api_key:
        raise ValueError("Geçerli bir API anahtarı gir.")
    if config["kind"] == "gemini":
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        contents = "Reply with OK." if test else "\n\n".join(
            ("Kullanıcı" if item["role"] == "user" else "XFA") + ": " + item["content"]
            for item in messages
        )
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction="Sen XFA'sın. Kullanıcının dilinde açık, dikkatli ve uygulanabilir yanıtlar ver. Gerçekleştirmediğin işlemleri yapılmış gibi gösterme. API anahtarı veya parola isteme.",
                max_output_tokens=8 if test else 1200,
                temperature=0.2 if test else 0.55,
            ),
        )
        return (response.text or "").strip()
    return _openai_compatible(provider, api_key, model, messages, test=test)
