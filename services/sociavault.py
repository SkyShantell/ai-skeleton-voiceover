from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import requests


API_URL = "https://api.sociavault.com/v1/scrape/tiktok-shop/product-details"


class SociaVaultError(RuntimeError):
    pass


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _unwrap(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise SociaVaultError("SociaVault returned an unexpected response.")

    data: Any = payload
    # The documented response is commonly {success:true,data:{success:true,...}}.
    for _ in range(3):
        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            data = data["data"]
        else:
            break
    if not isinstance(data, dict):
        raise SociaVaultError("SociaVault returned an unexpected product payload.")
    return data


def _best_image_url(image: Any) -> str:
    if not isinstance(image, dict):
        return ""
    urls = image.get("url_list") or image.get("thumb_url_list") or []
    if isinstance(urls, dict):
        urls = list(urls.values())
    if isinstance(urls, list):
        for value in urls:
            text = _clean(value)
            if text.startswith("http"):
                return text
    return ""


def _description_text(desc_detail: Any) -> str:
    """Extract readable seller-provided text from TikTok's rich description tree."""
    chunks: list[str] = []

    def walk(node: Any, parent_key: str = "") -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                # These keys hold actual human-readable description strings.
                if key in {"text", "plain_text", "tag_text"} and isinstance(value, str):
                    text = _clean(value)
                    if text and not text.startswith(("http://", "https://", "aweme://", "sslocal://")):
                        chunks.append(text)
                else:
                    walk(value, key)
        elif isinstance(node, list):
            for value in node:
                walk(value, parent_key)

    walk(desc_detail)

    unique: list[str] = []
    seen: set[str] = set()
    for text in chunks:
        marker = text.lower()
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(text)
    # Keep the prompt bounded even on extremely long PDPs.
    combined = "\n".join(unique)
    return combined[:10000].strip()


def _specifications(specs: Any) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    if not isinstance(specs, list):
        return result
    for item in specs:
        if not isinstance(item, dict):
            continue
        name = _clean(item.get("name"))
        value = _clean(item.get("value"))
        if name and value:
            result.append({"name": name, "value": value})
    return result


def _review_summary(review_block: Any) -> dict[str, Any]:
    if not isinstance(review_block, dict):
        return {"rating": None, "count": None}
    return {
        "rating": review_block.get("product_rating"),
        "count": review_block.get("review_count"),
    }


def _official_shop(seller: dict[str, Any]) -> bool:
    label = seller.get("store_label") if isinstance(seller, dict) else None
    if not isinstance(label, dict):
        return False
    identity = label.get("store_identity_label")
    if not isinstance(identity, dict):
        return False
    data = identity.get("identity_label_data")
    if not isinstance(data, dict):
        return False
    return _clean(data.get("shop_identity_key")).lower() == "official"


def _format_script_details(product: dict[str, Any]) -> str:
    """Build the stable listing context sent into Product DNA / Script DNA.

    Dynamic price, coupon and individual customer-review text are intentionally omitted.
    """
    lines: list[str] = []
    title = _clean(product.get("title"))
    if title:
        lines.append(f"LISTING TITLE: {title}")
    if product.get("category"):
        lines.append(f"CATEGORY: {_clean(product['category'])}")
    specs = product.get("specifications") or []
    if specs:
        lines.append("\nLISTING SPECIFICATIONS:")
        for spec in specs:
            lines.append(f"- {spec['name']}: {spec['value']}")

    description = _clean(product.get("description"))
    if description:
        lines.append("\nSELLER-PROVIDED PRODUCT DESCRIPTION:")
        lines.append(description)

    lines.append(
        "\nSOURCE NOTE: These text/specification details were pulled from the current TikTok Shop listing via SociaVault. "
        "Selected product photos are analyzed separately before Script DNA runs. Seller/shop status, ratings, review counts, sold counts, individual customer-review claims, price, stock, coupon values, and shipping offers are excluded from Script DNA grounding."
    )
    return "\n".join(lines).strip()


def parse_product_response(payload: Any, source_url: str = "") -> dict[str, Any]:
    data = _unwrap(payload)
    base = data.get("product_base") if isinstance(data.get("product_base"), dict) else {}
    seller = data.get("seller") if isinstance(data.get("seller"), dict) else {}
    reviews = _review_summary(data.get("product_detail_review"))
    logistic = data.get("logistic") if isinstance(data.get("logistic"), dict) else {}

    images: list[str] = []
    raw_images = base.get("images") or []
    if isinstance(raw_images, dict):
        raw_images = list(raw_images.values())
    if isinstance(raw_images, list):
        for item in raw_images:
            url = _best_image_url(item)
            if url and url not in images:
                images.append(url)

    product: dict[str, Any] = {
        "source_url": source_url,
        "product_id": _clean(data.get("product_id")),
        "title": _clean(base.get("title")),
        "category": _clean(base.get("category_name")),
        "seller_name": _clean(seller.get("name")),
        "seller_rating": seller.get("rating"),
        "official_shop": _official_shop(seller),
        "specifications": _specifications(base.get("specifications")),
        "description": _description_text(base.get("desc_detailv3")),
        "images": images[:12],
        "sold_count": base.get("sold_count"),
        "rating": reviews.get("rating"),
        "review_count": reviews.get("count"),
        "shipping": {
            "free_shipping": logistic.get("free_shipping"),
            "delivery_name": _clean(logistic.get("delivery_name")),
        },
    }
    product["script_details"] = _format_script_details(product)
    return product


def fetch_tiktok_shop_product(
    api_key: str,
    product_url: str,
    region: str = "US",
    get_related_videos: bool = False,
) -> dict[str, Any]:
    api_key = api_key.strip()
    product_url = product_url.strip()
    if not api_key:
        raise SociaVaultError("SociaVault is not configured. Ask the administrator to add SOCIAVAULT_API_KEY.")
    if not product_url:
        raise SociaVaultError("Paste a TikTok Shop product URL first.")

    parsed = urlparse(product_url)
    if "tiktok.com" not in parsed.netloc.lower():
        raise SociaVaultError("That does not look like a TikTok product URL.")

    try:
        response = requests.get(
            API_URL,
            headers={"X-API-Key": api_key, "Accept": "application/json"},
            params={
                "url": product_url,
                "get_related_videos": "true" if get_related_videos else "false",
                "region": (region or "US").upper(),
            },
            timeout=60,
        )
    except requests.RequestException as exc:
        raise SociaVaultError("Could not reach SociaVault. Try again in a moment.") from exc

    if response.status_code in {401, 403}:
        raise SociaVaultError("SociaVault authentication failed. Check the SOCIAVAULT_API_KEY server secret.")
    if response.status_code == 429:
        raise SociaVaultError("SociaVault rate limit or credit limit reached. Check the SociaVault dashboard.")
    if response.status_code != 200:
        raise SociaVaultError(f"SociaVault product lookup failed ({response.status_code}).")

    try:
        payload = response.json()
    except ValueError as exc:
        raise SociaVaultError("SociaVault returned an unreadable response.") from exc

    if isinstance(payload, dict) and payload.get("success") is False:
        message = _clean(payload.get("message") or payload.get("error"))
        raise SociaVaultError(message or "SociaVault could not fetch that TikTok Shop product.")

    product = parse_product_response(payload, source_url=product_url)
    if not product.get("title"):
        raise SociaVaultError("The TikTok Shop product loaded, but no product title was returned.")
    return product
