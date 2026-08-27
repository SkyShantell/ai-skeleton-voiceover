from __future__ import annotations

import re
from pathlib import Path

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
