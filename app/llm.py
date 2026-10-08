"""Thin wrapper around any OpenAI-compatible endpoint (Featherless by default)."""
import json
import re

from . import config

_client = None


class LLMError(Exception):
    pass


def available() -> bool:
    return not config.MOCK_LLM


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI

        _client = OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY, timeout=60)
    return _client


def chat(messages: list[dict], temperature: float = 0.8, max_tokens: int = 400) -> str:
    if not available():
        raise LLMError("LLM disabled (no API key)")
    resp = _get_client().chat.completions.create(
        model=config.LLM_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    text = (resp.choices[0].message.content or "").strip()
    # Reasoning models sometimes leak their scratchpad.
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    if not text:
        raise LLMError("empty response")
    return text


def chat_json(messages: list[dict], max_tokens: int = 500) -> dict:
    text = chat(messages, temperature=0.1, max_tokens=max_tokens)
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise LLMError(f"no JSON in response: {text[:200]}")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as e:
        raise LLMError(f"bad JSON: {e}") from e
