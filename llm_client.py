import requests
from config import LLM_PROVIDERS

def call_llm(prompt: str) -> str:
    for provider in LLM_PROVIDERS:
        if not provider["key"]:
            continue
        try:
            result = _call_provider(provider, prompt)
            if result:
                print(f"[LLM] Used: {provider['name']}")
                return result
        except Exception as e:
            print(f"[LLM] {provider['name']} failed: {e}, trying next...")
    raise Exception("All LLM providers failed!")

def _call_provider(provider: dict, prompt: str) -> str:
    name  = provider["name"]
    key   = provider["key"]
    model = provider["model"]

    if name == "gemini":
        return _call_gemini(key=key, model=model, prompt=prompt)
    else:
        urls = {
            "groq":       "https://api.groq.com/openai/v1/chat/completions",
            "openai":     "https://api.openai.com/v1/chat/completions",
            "deepseek":   "https://api.deepseek.com/v1/chat/completions",
            "mistral":    "https://api.mistral.ai/v1/chat/completions",
            "openrouter": "https://openrouter.ai/api/v1/chat/completions",
        }
        return _call_openai_compatible(
            url=urls[name], key=key, model=model, prompt=prompt
        )

def _call_openai_compatible(url, key, model, prompt) -> str:
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    res = requests.post(url, headers=headers, json=body, timeout=30)
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]

def _call_gemini(key, model, prompt) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    res = requests.post(url, json=body, timeout=30)
    res.raise_for_status()
    return res.json()["candidates"][0]["content"]["parts"][0]["text"]
