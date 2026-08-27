from __future__ import annotations

import json
from typing import Any

import requests

from .llm import extract_json_object, generate_multimodal_text


API_URL = "https://api.sociavault.com/v1/scrape/tiktok-shop/product-details"


class SociaVaultError(RuntimeError):
    pass


def fetch_product(api_key: str, product_url: str, region: str = "US") -> dict[str, Any]:
    """Fetch one TikTok Shop product from SociaVault.

    We intentionally do not request related affiliate videos because the VA workflow only
    needs listing information and listing images for Script DNA grounding.
    """
    if not api_key:
        raise SociaVaultError("SOCIAVAULT_API_KEY is missing.")
    if not product_url.strip():
        raise SociaVaultError("Paste a TikTok Shop product URL first.")

    try:
        response = requests.get(
            API_URL,
            headers={"X-API-Key": api_key.strip()},
            params={
                "url": product_url.strip(),
                "get_related_videos": "false",
                "region": region,
            },
            timeout=90,
        )
    except requests.RequestException as exc:
        raise SociaVaultError(f"Could not reach SociaVault: {exc}") from exc

    if response.status_code in {401, 403}:
        raise SociaVaultError("SociaVault authentication failed. Check SOCIAVAULT_API_KEY in Streamlit Secrets.")
    if response.status_code == 402:
        raise SociaVaultError("SociaVault says the account does not have enough credits for this request.")
    if response.status_code != 200:
        body = response.text[:500]
        raise SociaVaultError(f"SociaVault request failed ({response.status_code}): {body}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise SociaVaultError("SociaVault returned a non-JSON response.") from exc

    # Current docs show an outer success/data wrapper, and the inner data may itself
    # contain a success flag. Keep this defensive in case the API flattens the shape.
    if isinstance(payload, dict) and payload.get("success") is False:
        raise SociaVaultError(str(payload.get("message") or payload.get("error") or "SociaVault returned success=false."))

    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    if isinstance(data, dict) and data.get("success") is False:
        raise SociaVaultError(str(data.get("message") or data.get("error") or "SociaVault product lookup failed."))
    if not isinstance(data, dict):
        raise SociaVaultError("SociaVault returned an unexpected product response.")
    return data


def _first_url(image: Any) -> str:
    if not isinstance(image, dict):
        return ""
    for key in ("url_list", "thumb_url_list"):
        values = image.get(key)
        if isinstance(values, dict):
            values = list(values.values())
        if isinstance(values, list):
            for value in values:
                if isinstance(value, str) and value.startswith("http"):
                    return value
    return ""


def _walk_rich_blocks(value: Any, text_parts: list[str], image_urls: list[str]) -> None:
    """Recursively pull visible rich-description text and images without price/stock data."""
    if isinstance(value, dict):
        # Text nodes in TikTok's rich description generally use text or plain_text.
        for key in ("text", "plain_text"):
            text = value.get(key)
            if isinstance(text, str) and text.strip():
                text_parts.append(text.strip())

        # Rich description image nodes expose url_list.
        if "url_list" in value or "thumb_url_list" in value:
            url = _first_url(value)
            if url:
                image_urls.append(url)

        for child in value.values():
            _walk_rich_blocks(child, text_parts, image_urls)
    elif isinstance(value, list):
        for child in value:
            _walk_rich_blocks(child, text_parts, image_urls)


def normalize_product(data: dict[str, Any], source_url: str) -> dict[str, Any]:
    product = data.get("product_base") or {}
    seller = data.get("seller") or {}

    title = str(product.get("title") or "").strip()
    category = str(product.get("category_name") or "").strip()
    seller_name = str(seller.get("name") or "").strip()

    specs: dict[str, str] = {}
    for item in product.get("specifications") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        value = str(item.get("value") or "").strip()
        if name and value:
            specs[name] = value

    image_urls: list[str] = []
    for image in product.get("images") or []:
        url = _first_url(image)
        if url:
            image_urls.append(url)

    description_parts: list[str] = []
    description_images: list[str] = []
    _walk_rich_blocks(product.get("desc_detailv3") or {}, description_parts, description_images)

    # Preserve order while deduplicating. Product-gallery images come first, then
    # description graphics because either can contain benefit/ingredient text.
    all_images: list[str] = []
    for url in image_urls + description_images:
        if url and url not in all_images:
            all_images.append(url)

    deduped_description: list[str] = []
    for text in description_parts:
        clean = " ".join(text.split())
        if clean and clean not in deduped_description:
            deduped_description.append(clean)

    return {
        "source_url": source_url,
        "product_id": str(data.get("product_id") or ""),
        "title": title,
        "category": category,
        "seller": seller_name,
        "specifications": specs,
        "description_text": deduped_description,
        "image_urls": all_images,
    }


def analyze_product_images(
    openai_api_key: str,
    model: str,
    product_name: str,
    image_urls: list[str],
    max_images: int = 12,
) -> dict[str, Any]:
    """Read listing photos for visible benefits/ingredients/directions.

    This is intentionally extraction-only: the model is told not to infer outcomes from
    imagery and not to turn customer-style imagery into product claims.
    """
    selected = [u for u in image_urls if isinstance(u, str) and u.startswith("http")][:max_images]
    if not selected:
        return {
            "visible_benefits": [],
            "ingredients": [],
            "directions": [],
            "differentiators": [],
            "warnings": [],
            "other_visible_text": [],
            "images_analyzed": 0,
        }

    system = """You extract factual text from official TikTok Shop product-listing images for a script-writing workflow.
Only report information that is visibly written or unmistakably shown on the supplied product images.
Do NOT infer medical effects, transformations, before/after results, or benefits that are not explicitly written.
Do NOT use prices, discounts, coupons, stock counts, shipping offers, or scarcity language even if visible.
Do NOT treat customer testimonial language as a verified product claim.
Return JSON only with these keys: visible_benefits, ingredients, directions, differentiators, warnings, other_visible_text, images_analyzed.
Each of the first six fields must be an array of concise strings. Deduplicate repeated wording across images."""

    user = f"Product: {product_name}\nRead the supplied TikTok Shop listing photos and extract only script-useful, visibly supported product information."
    raw = generate_multimodal_text(
        openai_api_key,
        model,
        system,
        user,
        selected,
        temperature=0.1,
    )
    parsed = extract_json_object(raw)
    parsed["images_analyzed"] = len(selected)
    return parsed


def build_product_details(product: dict[str, Any], image_analysis: dict[str, Any]) -> str:
    """Create the editable product-details block used by the existing fact extractor.

    No price or stock fields are included by design.
    """
    lines: list[str] = []
    if product.get("category"):
        lines.append(f"Category: {product['category']}")
    if product.get("seller"):
        lines.append(f"Seller/Shop: {product['seller']}")

    specs = product.get("specifications") or {}
    if specs:
        lines.append("\nLISTING SPECIFICATIONS:")
        for name, value in specs.items():
            lines.append(f"- {name}: {value}")

    desc = product.get("description_text") or []
    if desc:
        lines.append("\nLISTING DESCRIPTION / SELLER-PROVIDED TEXT:")
        for text in desc:
            lines.append(f"- {text}")

    image_sections = [
        ("visible_benefits", "BENEFITS WRITTEN ON PRODUCT PHOTOS"),
        ("ingredients", "INGREDIENTS / COMPONENTS WRITTEN ON PRODUCT PHOTOS"),
        ("directions", "USAGE / DIRECTIONS WRITTEN ON PRODUCT PHOTOS"),
        ("differentiators", "DIFFERENTIATORS WRITTEN ON PRODUCT PHOTOS"),
        ("warnings", "WARNINGS / LIMITATIONS WRITTEN ON PRODUCT PHOTOS"),
        ("other_visible_text", "OTHER USEFUL TEXT FOUND ON PRODUCT PHOTOS"),
    ]
    for key, heading in image_sections:
        values = image_analysis.get(key) or []
        if values:
            lines.append(f"\n{heading}:")
            for value in values:
                if str(value).strip():
                    lines.append(f"- {str(value).strip()}")

    lines.append("\nSOURCE NOTE: The information above was pulled from the TikTok Shop listing and its product images. Price and stock were intentionally excluded.")
    return "\n".join(lines).strip()
