from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI


class LLMError(RuntimeError):
    pass


def _output_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return text.strip()

    parts: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            value = getattr(content, "text", None)
            if value:
                parts.append(value)
    if parts:
        return "\n".join(parts).strip()
    raise LLMError("The AI response did not contain text output.")


def generate_text(
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float | None = None,
) -> str:
    if not api_key:
        raise LLMError("OPENAI_API_KEY is missing.")

    client = OpenAI(api_key=api_key)
    kwargs: dict[str, Any] = {
        "model": model,
        "instructions": system_prompt,
        "input": user_prompt,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature

    try:
        response = client.responses.create(**kwargs)
    except Exception as exc:
        # Some reasoning/model configurations do not expose temperature.
        if temperature is not None and "temperature" in str(exc).lower():
            kwargs.pop("temperature", None)
            try:
                response = client.responses.create(**kwargs)
            except Exception as retry_exc:
                raise LLMError(str(retry_exc)) from retry_exc
        else:
            raise LLMError(str(exc)) from exc
    return _output_text(response)


def generate_multimodal_text(
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    image_urls: list[str],
    temperature: float | None = None,
) -> str:
    """Generate text from a prompt plus remote images using the Responses API."""
    if not api_key:
        raise LLMError("OPENAI_API_KEY is missing.")

    client = OpenAI(api_key=api_key)
    content: list[dict[str, Any]] = [{"type": "input_text", "text": user_prompt}]
    for url in image_urls:
        if isinstance(url, str) and url.startswith("http"):
            content.append({"type": "input_image", "image_url": url})

    kwargs: dict[str, Any] = {
        "model": model,
        "instructions": system_prompt,
        "input": [{"role": "user", "content": content}],
    }
    if temperature is not None:
        kwargs["temperature"] = temperature

    try:
        response = client.responses.create(**kwargs)
    except Exception as exc:
        if temperature is not None and "temperature" in str(exc).lower():
            kwargs.pop("temperature", None)
            try:
                response = client.responses.create(**kwargs)
            except Exception as retry_exc:
                raise LLMError(str(retry_exc)) from retry_exc
        else:
            raise LLMError(str(exc)) from exc
    return _output_text(response)


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            obj = json.loads(cleaned[start : end + 1])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError as exc:
            raise LLMError(f"Could not parse product-fact JSON: {exc}") from exc
    raise LLMError("The product fact extractor did not return a JSON object.")
