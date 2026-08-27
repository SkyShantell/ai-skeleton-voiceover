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
        min_words, max_words = 240, 270
    else:
        min_words, max_words = 195, 210

    word_count_ok = min_words <= wc <= max_words

    style_issues: list[str] = []
    meta_filler_patterns = [
        r"\bI also like that\b",
        r"\bOne thing I noticed\b",
        r"\bWhat I like about\b",
        r"\bwhat I love about\b",
        r"\bthe listing shows\b",
        r"\bthe product page says\b",
        r"\bstrong trust signals\b",
        r"\btrust signals from shoppers\b",
        r"\bshoppers seem to\b",
    ]

    if resolved == "ARCH A":
        first_sentence = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0]
        if not re.match(r"^If\b|^If your\b|^If you're\b", first_sentence, flags=re.I):
            style_issues.append("Arch A should open immediately with an If/If your/If you're symptom stack.")
        if first_sentence.count(",") < 4:
            style_issues.append("Opening symptom stack is too short; chain four concrete problems into one opening sentence.")
        if not re.search(r"(?:^|[.!?]\s+)Because\b", text, flags=re.I):
            style_issues.append("Missing direct Because... cause/reframe beat.")
        if not re.search(r"\bAnd no,", text, flags=re.I):
            style_issues.append("Missing sharp And no,... objection-preempt beat.")
        if not re.search(r"\bBut don['’]t\b", text, flags=re.I):
            style_issues.append("Missing compressed But don't... villain/alternative beat.")

        benefit_markers = re.findall(
            r"\b(?:to help(?: support| improve| maintain| deliver)?|can help(?: support)?|may help(?: support)?|helps? support)\b",
            text,
            flags=re.I,
        )
        if len(benefit_markers) < 3:
            style_issues.append("Benefit stack is too blended; write three distinct feature/ingredient-first benefit beats.")

        callback_positions = [pos for pos in (lower.rfind("i recommend"), lower.rfind("i'd try"), lower.rfind("i would try")) if pos != -1]
        callback_pos = max(callback_positions) if callback_positions else -1
        pre_callback = text[:callback_pos] if callback_pos != -1 else text
        if re.search(r"\b(?:I|me|my)\b", pre_callback, flags=re.I):
            style_issues.append("First-person language appears before the final recommendation; keep early/middle beats in second person.")

    elif resolved == "ARCH C":
        if not re.match(r"^What would actually happen\b", text, flags=re.I):
            style_issues.append("Arch C should open with the canonical 'What would actually happen...' curiosity question.")
        if not re.search(r"\bDay one,", text, flags=re.I):
            style_issues.append("Missing explicit Day one first-use beat.")
        if not re.search(r"\bWeek (?:one|two),", text, flags=re.I):
            style_issues.append("Missing Week one or Week two subtle first-milestone beat.")

        day_markers = re.findall(r"\bDay (?:fourteen|thirty|sixty|\d{1,3}),", text, flags=re.I)
        if not day_markers:
            style_issues.append("Missing a later day milestone such as Day fourteen, Day thirty, or Day sixty.")
        if re.search(r"\bDay sixty,", text, flags=re.I) and not re.search(
            r"Day sixty,.*?this is (?:usually )?where people (?:start|realize)", text, flags=re.I
        ):
            style_issues.append("Day sixty should use the canonical strongest-payoff framing ('this is usually where people start/realize...').")
        if re.search(r"\bDay thirty,", text, flags=re.I) and not re.search(
            r"Day thirty,.*?this is where things may start to (?:shift|click)", text, flags=re.I
        ):
            style_issues.append("Day thirty should use the canonical shift/click beat.")

        if not re.search(r"\bBut here['’]s (?:where most people go wrong|what most people (?:get|go) wrong)\b", text, flags=re.I):
            style_issues.append("Missing sharp Arch C villain pivot: use 'But here\'s where most people go wrong' or 'But here\'s what most people get wrong.'")

        hedge_markers = re.findall(r"\b(?:may|might)\b", text, flags=re.I)
        if len(hedge_markers) < 4:
            style_issues.append("Arch C milestones are not hedged enough; use may/might throughout progressive result beats.")

        day_one_match = re.search(r"\bDay one,(.*?)(?=\bWeek (?:one|two),)", text, flags=re.I)
        if day_one_match:
            day_one = day_one_match.group(1)
            if not re.search(r"\bnothing\b|\bfeel absolutely nothing\b|\bnothing looks different\b|\bnothing feels different\b", day_one, flags=re.I):
                style_issues.append("Day one should explicitly establish little/no immediate visible result or change.")
            if not re.search(r"\bBut\b", day_one, flags=re.I):
                style_issues.append("Day one should pivot with 'But...' into the documented formula/ingredient setup.")

        villain_match = re.search(r"\bBut here['’]s (?:where most people go wrong|what most people (?:get|go) wrong)\b", text, flags=re.I)
        if villain_match:
            tail = text[villain_match.end():]
            if not re.search(r"\b(?:uses|combines|combined|built|packed|put|made|designed)\b", tail, flags=re.I):
                style_issues.append("Product reveal after the villain needs a decisive construction verb such as uses/combines/combined/built/packed/designed.")

        callback_positions = [pos for pos in (lower.rfind("i'd try"), lower.rfind("i would try"), lower.rfind("i recommend")) if pos != -1]
        callback_pos = max(callback_positions) if callback_positions else -1
        pre_callback = text[:callback_pos] if callback_pos != -1 else text
        if re.search(r"\b(?:I|me|my)\b", pre_callback, flags=re.I):
            style_issues.append("First-person language appears before the final Arch C recommendation; keep the timeline in second person.")

    for pattern in meta_filler_patterns:
        if re.search(pattern, text, flags=re.I):
            style_issues.append(f"Generic/meta filler detected: {pattern}")

    style_ok = not style_issues
    return {
        "word_count": wc,
        "architecture": resolved,
        "target": f"{min_words}-{max_words}",
        "word_count_ok": word_count_ok,
        "banned_patterns": banned,
        "cta_ok": cta_ok,
        "style_ok": style_ok,
        "style_issues": style_issues,
        "pass": word_count_ok and not banned and cta_ok and style_ok,
    }


def _repair_script(
    api_key: str,
    model: str,
    skill: str,
    grounding: str,
    style_lock: str,
    script: str,
    verification: dict[str, Any],
    product_name: str,
    product_details: str,
    product_facts: dict[str, Any],
    architecture: str,
) -> str:
    system = skill + "\n\n" + style_lock + "\n\n" + grounding
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
    style_lock = read_prompt("script_style_lock.md")
    grounding = read_prompt("script_grounding.md")
    architecture = architecture_from_choice(architecture_choice)
    system = skill + "\n\n" + style_lock + "\n\n" + grounding

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
    for _ in range(3):
        if verification["pass"]:
            break
        script = _repair_script(
            api_key,
            model,
            skill,
            grounding,
            style_lock,
            script,
            verification,
            product_name,
            product_details,
            product_facts,
            architecture,
        )
        verification = verify_script(script, architecture)

    return re.sub(r"\s+", " ", script).strip(), verification
