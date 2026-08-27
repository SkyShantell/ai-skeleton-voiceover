from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .llm import extract_json_object, generate_text

PROMPTS = Path(__file__).resolve().parents[1] / "prompts"


BANNED_PATTERNS = [
    r"\bcoupon\s+code\b",
    r"\bpromo\s+code\b",
    r"\bdiscount\s+code\b",
    r"\blink\s+in\s+bio\b",
    r"\blinks\s+down\s+below\b",
    r"\bdiabetes\b",
    r"\bcancer\b",
    r"\barthritis\b",
    r"\bgingivitis\b",
    r"\beczema\b",
    r"\bpcos\b",
    r"\bcures?\b",
    r"\btreats?\b",
    r"\bheals?\b",
    r"\bprevents?\b",
    r"\blose\s+weight\b",
    r"\bburn\s+fat\b",
    r"\bfat\s+burn\b",
    r"\bslimming\b",
    r"\bappetite\s+suppress(?:ion|ant|ants)?\b",
    r"\bappetite\s+control\b",
    r"\bdiet\s+pill\b",
    r"\bglp[-\s]?1\b",
    r"\bblood\s+sugar\b",
    r"\binsane\b",
    r"\bobsessed\b",
    r"\bgame[-\s]?changer\b",
    r"\bliterally\s+shaking\b",
    r"\bmiracle\b",
]


def read_prompt(name: str) -> str:
    return (PROMPTS / name).read_text(encoding="utf-8")


def architecture_from_choice(choice: str) -> str:
    if choice == "Symptom Stack (Arch A)":
        return "ARCH A"
    if choice == "Day-by-Day Journey (Arch C)":
        return "ARCH C"
    return "AUTO"


def extract_product_facts(api_key: str, model: str, product_name: str, details: str) -> dict[str, Any]:
    system = read_prompt("product_fact_extractor.md")
    user = f"PRODUCT NAME:\n{product_name.strip()}\n\nPRODUCT DETAILS:\n{details.strip()}"
    raw = generate_text(api_key, model, system, user, temperature=0.1)
    return extract_json_object(raw)


def verify_script(script: str, architecture: str) -> dict[str, Any]:
    text = re.sub(r"\s+", " ", script).strip()
    wc = len(text.split())
    lower = text.lower()
    banned = [p for p in BANNED_PATTERNS if re.search(p, lower, flags=re.I)]
    cta_ok = "tap the orange cart" in lower

    # Auto can be resolved from generated length if the user did not force one.
    resolved = architecture
    if architecture == "AUTO":
        resolved = "ARCH C" if 230 <= wc <= 270 else "ARCH A"

    if resolved == "ARCH C":
        min_words, max_words = 240, 260
    else:
        min_words, max_words = 195, 210

    word_count_ok = min_words <= wc <= max_words
    return {
        "word_count": wc,
        "architecture": resolved,
        "target": f"{min_words}-{max_words}",
        "word_count_ok": word_count_ok,
        "banned_patterns": banned,
        "cta_ok": cta_ok,
        "pass": word_count_ok and not banned and cta_ok,
    }


def _repair_script(
    api_key: str,
    model: str,
    skill: str,
    grounding: str,
    script: str,
    verification: dict[str, Any],
    product_name: str,
    product_details: str,
    product_facts: dict[str, Any],
    architecture: str,
) -> str:
    system = skill + "\n\n" + grounding
    user = f"""Repair the draft below so it passes the Script DNA skill's own mandatory verification.
Do not change factual grounding and do not introduce new product claims.

REQUESTED ARCHITECTURE: {architecture}
PRODUCT NAME: {product_name}
PRODUCT DETAILS: {product_details}
EXTRACTED PRODUCT FACTS: {json.dumps(product_facts, ensure_ascii=False)}

CURRENT VERIFICATION:
{json.dumps(verification, ensure_ascii=False)}

DRAFT SCRIPT:
{script}

Return ONLY the repaired final script as one continuous paragraph."""
    return generate_text(api_key, model, system, user, temperature=0.2).strip()


def generate_script(
    api_key: str,
    model: str,
    product_name: str,
    product_details: str,
    product_facts: dict[str, Any],
    architecture_choice: str,
    viral_transcript: str = "",
) -> tuple[str, dict[str, Any]]:
    skill = read_prompt("script_dna.md")
    grounding = read_prompt("script_grounding.md")
    architecture = architecture_from_choice(architecture_choice)
    system = skill + "\n\n" + grounding

    viral = viral_transcript.strip() or "None supplied."
    user = f"""Create one TikTok Shop affiliate voiceover script using the supplied Script DNA skill.

ARCHITECTURE SELECTION: {architecture}
PRODUCT NAME: {product_name.strip()}
PRODUCT DETAILS (source material):
{product_details.strip()}

STRICTLY EXTRACTED PRODUCT FACTS:
{json.dumps(product_facts, indent=2, ensure_ascii=False)}

OPTIONAL VIRAL TRANSCRIPT:
{viral}

If architecture is AUTO, follow the skill's architecture-selection rules. Return only the final plain voiceover script."""

    script = generate_text(api_key, model, system, user, temperature=0.2).strip()
    verification = verify_script(script, architecture)

    # The skill itself requires silent adjustment until its mechanical checks pass.
    for _ in range(2):
        if verification["pass"]:
            break
        script = _repair_script(
            api_key,
            model,
            skill,
            grounding,
            script,
            verification,
            product_name,
            product_details,
            product_facts,
            architecture,
        )
        verification = verify_script(script, architecture)

    return re.sub(r"\s+", " ", script).strip(), verification
