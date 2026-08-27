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


def analyze_product_images(
    api_key: str,
    model: str,
    image_urls: list[str],
) -> str:
    """Read selected official TikTok Shop listing images conservatively.

    Returns only visibly supported packaging/listing-image facts. It intentionally
    ignores prices, stock, testimonials, and inferred before/after effects.
    """
    urls = [str(u).strip() for u in image_urls if str(u).strip().startswith("http")][:12]
    if not urls:
        return ""
    if not api_key:
        raise LLMError("OPENAI_API_KEY is missing.")

    client = OpenAI(api_key=api_key.strip())
    instructions = """You are a conservative product-image fact reader for a TikTok Shop script workflow.
Read only text and clearly labeled facts that are visibly present on the supplied OFFICIAL PRODUCT LISTING IMAGES.

Extract useful script grounding such as:
- product/brand name and format
- ingredients, components, materials, quantities, or included items
- benefit/support statements literally printed on the image
- usage directions
- differentiators, certifications, formula attributes, warnings, and limitations
- sensory details explicitly stated on the image

HARD RULES:
- Do NOT use or report price, discounts, coupons, stock, scarcity, shipping, or countdowns.
- Do NOT treat customer testimonials/reviews as verified product facts.
- Do NOT infer a benefit from a visual before/after, body change, diagram, icon, pose, or implied result unless corresponding text explicitly states it.
- Do NOT upgrade wording. Preserve hedges such as 'helps support' and 'may'.
- If text is unreadable or ambiguous, omit it rather than guessing.
- Do not use outside knowledge.

Return concise plain text grouped under: VISIBLE PRODUCT IMAGE FACTS, WARNINGS/LIMITATIONS, and IGNORED/UNVERIFIED IMAGE CLAIMS."""

    content: list[dict[str, Any]] = [
        {
            "type": "input_text",
            "text": "Read the selected TikTok Shop product images and extract only visibly supported product facts for downstream Script DNA grounding.",
        }
    ]
    content.extend({"type": "input_image", "image_url": url} for url in urls)

    try:
        response = client.responses.create(
            model=model,
            instructions=instructions,
            input=[{"role": "user", "content": content}],
        )
    except Exception as exc:
        raise LLMError(f"Product photo analysis failed: {exc}") from exc
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
