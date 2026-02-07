import requests
from typing import List, Dict, Optional

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def openrouter_chat(
    api_key: str,
    messages: List[Dict[str, str]],
    model: str = "openai/gpt-4o-mini",
    temperature: float = 0.2,
    max_tokens: int = 400,
    site_url: Optional[str] = "http://localhost:8501",
    app_name: Optional[str] = "Streamlit Chatbot",
) -> str:
    """
    Send a chat completion request to OpenRouter and return assistant text.
    messages example: [{"role": "user", "content": "Hello"}]
    """
    if not api_key or not api_key.strip():
        raise ValueError("Missing OPENROUTER_API_KEY")

    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    }

    # Optional but recommended by OpenRouter
    if site_url:
        headers["HTTP-Referer"] = site_url
    if app_name:
        headers["X-Title"] = app_name

    payload = {
        "model": model,
        "messages": messages,
        "temperature": float(temperature),
        "max_tokens": int(max_tokens),
    }

    r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)

    if r.status_code != 200:
        raise RuntimeError(f"OpenRouter error {r.status_code}: {r.text}")

    data = r.json()
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        raise RuntimeError(f"Unexpected OpenRouter response format: {data}")


def simple_prompt(api_key: str, prompt: str, model: str = "openai/gpt-4o-mini") -> str:
    return openrouter_chat(
        api_key=api_key,
        messages=[{"role": "user", "content": prompt}],
        model=model,
    )

