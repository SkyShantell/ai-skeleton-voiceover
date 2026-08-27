from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .llm import generate_text

PROMPTS = Path(__file__).resolve().parents[1] / "prompts"


def audit_script(
    api_key: str,
    model: str,
    script_text: str,
    on_screen_text: str = "",
    visual_cues: str = "",
) -> tuple[str, str]:
    system = (PROMPTS / "compliance_auditor.md").read_text(encoding="utf-8")
    user = (
        "Please audit the following content for TikTok Shop compliance:\n"
        f"Spoken Script: `{script_text.strip()}`\n"
        f"On-Screen Text: `{on_screen_text.strip()}`\n"
        f"Visual Cues: `{visual_cues.strip()}`"
    )
    report = generate_text(api_key, model, system, user, temperature=0.1).strip()
    return parse_rating(report), report


def parse_rating(report: str) -> str:
    rating_block = report
    match = re.search(
        r"##\s*1\.\s*COMPLIANCE RATING\s*(.*?)(?=##\s*2\.|\Z)",
        report,
        flags=re.I | re.S,
    )
    if match:
        rating_block = match.group(1)

    if "🟢" in rating_block and "PASS" in rating_block.upper():
        return "PASS"
    if "🟡" in rating_block and "NEEDS REVISION" in rating_block.upper():
        return "NEEDS REVISION"
    if "🔴" in rating_block and "HIGH RISK" in rating_block.upper():
        return "HIGH RISK"

    upper = rating_block.upper()
    if "NEEDS REVISION" in upper:
        return "NEEDS REVISION"
    if "HIGH RISK" in upper:
        return "HIGH RISK"
    if re.search(r"\bPASS\b", upper):
        return "PASS"
    return "UNKNOWN"




def parse_final_summary(report: str) -> str:
    """Return only the auditor's short final verdict for compact UI display."""
    if not report.strip():
        return ""
    match = re.search(
        r"##\s*4\.\s*FINAL SUMMARY\s*(.*?)(?=##\s*\d+\.|\Z)",
        report,
        flags=re.I | re.S,
    )
    text = match.group(1) if match else ""
    text = re.sub(r"^[\s\-•]+", "", text.strip())
    text = re.sub(r"\s+", " ", text).strip()
    return text

def _clean_rewrite_value(value: str) -> str:
    text = value.strip()
    text = re.sub(r"^[\-•]\s*", "", text)
    text = text.strip(" \t\r\n`\"")
    # Preserve apostrophes and punctuation; only remove one pair of wrapping smart quotes.
    if len(text) >= 2 and text[0] in {"“", "‘"} and text[-1] in {"”", "’"}:
        text = text[1:-1].strip()
    return text


def parse_rewrite_suggestions(report: str) -> list[dict[str, str]]:
    """Parse the auditor's section 3 into selectable Original -> Rewrite pairs."""
    if not report.strip():
        return []

    section_match = re.search(
        r"##\s*3\.\s*REQUIRED FIXES\s*&\s*SUGGESTED REVIEWS\s*(.*?)(?=##\s*4\.|\Z)",
        report,
        flags=re.I | re.S,
    )
    section = section_match.group(1) if section_match else report

    # Primary format required by the compliance prompt.
    pattern = re.compile(
        r"(?:^|\n)\s*(?:[-*•]|\d+[.)])?\s*\*\*Original:\*\*\s*(.*?)\s*\n\s*(?:[-*•]|\d+[.)])?\s*\*\*Compliant Rewrite:\*\*\s*(.*?)(?=(?:\n\s*(?:[-*•]|\d+[.)])?\s*\*\*Original:\*\*)|\Z)",
        flags=re.I | re.S,
    )

    suggestions: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for original, rewrite in pattern.findall(section):
        original_clean = _clean_rewrite_value(original)
        rewrite_clean = _clean_rewrite_value(rewrite)
        # Trim stray markdown/list material that may follow the rewrite.
        rewrite_clean = re.split(r"\n\s*(?:[-*]\s*)?\*\*(?:Why|Note|Original):", rewrite_clean, maxsplit=1, flags=re.I)[0].strip()
        if not original_clean or not rewrite_clean:
            continue
        key = (original_clean, rewrite_clean)
        if key in seen:
            continue
        seen.add(key)
        suggestions.append({"original": original_clean, "rewrite": rewrite_clean})
    return suggestions


def _replace_once_case_insensitive(text: str, old: str, new: str) -> tuple[str, bool]:
    if not old:
        return text, False
    match = re.search(re.escape(old), text, flags=re.I)
    if not match:
        return text, False
    return text[: match.start()] + new + text[match.end() :], True


def apply_selected_rewrites(
    api_key: str,
    model: str,
    script_text: str,
    selected: list[dict[str, str]],
) -> str:
    """Apply only user-selected compliance rewrites.

    Exact phrase replacements are deterministic. If the auditor's Original text is not
    literally present in the script, GPT is used only as a narrow fallback for those
    unmatched selections and is instructed not to touch anything else.
    """
    updated = script_text
    unmatched: list[dict[str, str]] = []

    for item in selected:
        original = str(item.get("original") or "").strip()
        rewrite = str(item.get("rewrite") or "").strip()
        if not original or not rewrite:
            continue
        updated, replaced = _replace_once_case_insensitive(updated, original, rewrite)
        if not replaced:
            # Try common wrapping punctuation variants before invoking the model.
            variants = [
                original.strip('"“”‘’` '),
                re.sub(r"\s+", " ", original).strip(),
            ]
            for variant in variants:
                if not variant:
                    continue
                updated, replaced = _replace_once_case_insensitive(updated, variant, rewrite)
                if replaced:
                    break
        if not replaced:
            unmatched.append({"original": original, "rewrite": rewrite})

    if not unmatched:
        return updated.strip()

    system = """You are a precision text editor. Apply ONLY the user-selected compliance substitutions to the supplied script.
Do not improve, paraphrase, shorten, expand, reorganize, or rewrite any other wording. Preserve all unselected wording as closely to verbatim as possible.
If an 'Original' phrase is not literally present because the auditor quoted it approximately, locate only the closest matching phrase and replace only that phrase with its paired 'Compliant Rewrite'.
Return ONLY the updated full script, with no notes or formatting."""
    user = (
        "CURRENT SCRIPT:\n"
        f"{updated}\n\n"
        "SELECTED REWRITES THAT STILL NEED TO BE APPLIED:\n"
        f"{unmatched}"
    )
    return generate_text(api_key, model, system, user, temperature=0.0).strip()
