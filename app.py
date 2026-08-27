from __future__ import annotations

import hashlib
import hmac
import os
import re
from pathlib import Path
from typing import Any

import streamlit as st

from services.compliance import apply_selected_rewrites, audit_script, parse_final_summary, parse_rewrite_suggestions
from services.elevenlabs import synthesize
from services.llm import LLMError, analyze_product_images
from services.script_engine import extract_product_facts, generate_script
from services.script_library import (
    ScriptLibraryError,
    delete_script,
    load_scripts,
    upsert_script,
)
from services.silence import clean_audio
from services.sociavault import SociaVaultError, fetch_tiktok_shop_product

APP_DIR = Path(__file__).resolve().parent
LOCAL_LIBRARY_PATH = APP_DIR / "data" / "saved_scripts.json"

VOICE_PRESETS = {
    "Julie US": {
        "id": "5WTtMD3P8AHUXTVqCYcJ",
        "description": "Confident & Conversational",
        "speed": 1.13,
        "stability": 0.66,
        "similarity": 1.00,
        "style": 0.26,
        "speaker_boost": True,
    },
    "Mark US": {
        "id": "1SM7GgM6IMuvQlz2BwM3",
        "description": "ConvoAI",
        "speed": 1.14,
        "stability": 0.50,
        "similarity": 0.75,
        "style": 0.00,
        "speaker_boost": True,
    },
    "Lucy UK": {
        "id": "lcMyyd2HUfFzxdCaC4Ta",
        "description": "Fresh & Casual",
        "speed": 1.15,
        "stability": 0.50,
        "similarity": 0.75,
        "style": 0.00,
        "speaker_boost": True,
    },
    "Toby UK": {
        "id": "pYDLV125o4CgqP8i49Lg",
        "description": "Raspy, Youthful & Articulate",
        "speed": 1.16,
        "stability": 1.00,
        "similarity": 1.00,
        "style": 0.56,
        "speaker_boost": True,
    },
}

ARCHITECTURE_OPTIONS = [
    "Auto Detect",
    "Symptom Stack (Arch A)",
    "Day-by-Day Journey (Arch C)",
]

REGENERATION_ANGLES = [
    "Fresh take",
    "More relatable / emotional",
    "More aggressive hook",
    "More educational",
    "Different pain points",
    "Different villain / objection",
]

st.set_page_config(
    page_title="AI Skeleton Voiceover",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
:root {
    --bg: #080b11;
    --panel: #111722;
    --panel-2: #171e2b;
    --line: #344054;
    --text: #f8fafc;
    --muted: #b9c2d0;
    --accent: #718cff;
    --accent-hover: #8299ff;
    --secondary: #202b3c;
    --secondary-hover: #2a374b;
    --good: #4adea5;
    --warn: #ffd166;
    --bad: #ff6b7f;
    --override: #c084fc;
}
html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg);
    color: var(--text);
}
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 8% -10%, rgba(88,115,255,.22), transparent 32%),
        radial-gradient(circle at 95% 5%, rgba(122,74,255,.13), transparent 28%),
        var(--bg);
}
[data-testid="stHeader"] { background: transparent; }
.block-container {
    max-width: 1320px;
    padding-top: 1.45rem;
    padding-bottom: 5rem;
}
.hero {
    border: 1px solid var(--line);
    border-radius: 22px;
    padding: 1.05rem 1.2rem;
    margin-bottom: .8rem;
    background: linear-gradient(135deg, rgba(113,140,255,.16), rgba(255,255,255,.035));
}
.hero h1 {
    font-size: clamp(1.85rem, 3.4vw, 2.75rem);
    line-height: 1.03;
    letter-spacing: -0.045em;
    margin: 0;
    color: #ffffff;
}
.hero p {
    color: #d0d6df;
    font-size: 1.01rem;
    line-height: 1.48;
    margin: .45rem 0 0 0;
    max-width: 980px;
}
.quick-flow {
    display: flex;
    gap: .65rem;
    flex-wrap: wrap;
    margin-top: .65rem;
}
.quick-flow span {
    display: inline-block;
    padding: .4rem .65rem;
    border: 1px solid #45516a;
    background: #182132;
    border-radius: 999px;
    color: #f2f5fa;
    font-weight: 750;
    font-size: .86rem;
}
.step-heading {
    display:flex;
    align-items:center;
    gap:.7rem;
    margin: .25rem 0 .85rem 0;
}
.step-number {
    width: 2.05rem;
    height: 2.05rem;
    border-radius: 999px;
    display:inline-flex;
    align-items:center;
    justify-content:center;
    background: var(--accent);
    color:#fff;
    font-weight:850;
    font-size:1rem;
}
.step-heading strong {
    color:#fff;
    font-size:1.34rem;
    letter-spacing:-.015em;
}
.voice-card {
    border: 1px solid #374357;
    border-radius: 18px;
    background: linear-gradient(180deg, #192131, #111722);
    padding: .75rem .9rem;
    margin: .4rem 0 .55rem 0;
}
.voice-name { font-size:1.27rem; font-weight:850; color:#fff; }
.voice-desc { color:#c3cbd7; margin-top:.15rem; font-size:1rem; }
.voice-settings {
    display:grid;
    grid-template-columns: repeat(2, minmax(0,1fr));
    gap:.55rem .8rem;
    margin-top:.85rem;
}
.voice-setting {
    border:1px solid #364157;
    border-radius:12px;
    padding:.62rem .72rem;
    background:#0d131d;
}
.voice-setting b { display:block; color:#fff; font-size:1.05rem; }
.voice-setting span { color:#aab5c5; font-size:.83rem; }
.status-box {
    border-radius: 16px;
    padding: 1rem 1.08rem;
    border: 1px solid var(--line);
    margin: .7rem 0;
    font-size:1.07rem;
    font-weight:750;
    color:#f9fbff;
}
.status-pass { border-left: 5px solid var(--good); background: rgba(73,214,157,.09); }
.status-warn { border-left: 5px solid var(--warn); background: rgba(255,209,102,.08); }
.status-risk { border-left: 5px solid var(--bad); background: rgba(255,107,127,.09); }
.status-override { border-left: 5px solid var(--override); background: rgba(192,132,252,.09); }
.small-muted { color:#b2bccb; font-size:.96rem; }

/* Labels and fields */
[data-testid="stWidgetLabel"] p {
    font-size: 1.04rem !important;
    font-weight: 760 !important;
    color: #f7f9fc !important;
}
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-baseweb="select"] > div {
    font-size: 1.06rem !important;
}
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: #101722 !important;
    border-color: #3b465b !important;
    color: #f9fbff !important;
}
[data-testid="stTextArea"] textarea { line-height: 1.58 !important; }
[data-testid="stSelectbox"] > div > div { min-height: 50px; }
[data-baseweb="select"] * { color: #f8fafc !important; }
[data-baseweb="popover"] { color: #111827 !important; }

/* High-contrast buttons. Explicit colors stop Streamlit themes from producing white-on-white. */
button[data-testid="stBaseButton-secondary"],
button[data-testid="stBaseButton-tertiary"],
.stDownloadButton > button {
    background: var(--secondary) !important;
    color: #ffffff !important;
    border: 1px solid #52617a !important;
    border-radius: 13px !important;
    min-height: 52px !important;
    font-size: 1.04rem !important;
    font-weight: 800 !important;
    box-shadow: none !important;
}
button[data-testid="stBaseButton-secondary"]:hover,
button[data-testid="stBaseButton-tertiary"]:hover,
.stDownloadButton > button:hover {
    background: var(--secondary-hover) !important;
    border-color: #71809c !important;
    color: #ffffff !important;
}
button[data-testid="stBaseButton-primary"] {
    background: var(--accent) !important;
    color: #ffffff !important;
    border: 1px solid #91a4ff !important;
    border-radius: 13px !important;
    min-height: 58px !important;
    font-size: 1.12rem !important;
    font-weight: 850 !important;
    box-shadow: none !important;
}
button[data-testid="stBaseButton-primary"]:hover {
    background: var(--accent-hover) !important;
    color: #ffffff !important;
}
button[data-testid^="stBaseButton"] p,
button[data-testid^="stBaseButton"] span,
button[data-testid^="stBaseButton"] div,
.stDownloadButton button p,
.stDownloadButton button span,
.stDownloadButton button div {
    color: #ffffff !important;
}
button[data-testid^="stBaseButton"] svg,
.stDownloadButton button svg {
    fill: currentColor !important;
    color: #ffffff !important;
}
button[data-testid^="stBaseButton"]:disabled,
.stDownloadButton > button:disabled {
    background: #151b25 !important;
    color: #7f8998 !important;
    border-color: #303949 !important;
    opacity: 1 !important;
}
button[data-testid^="stBaseButton"]:disabled p,
button[data-testid^="stBaseButton"]:disabled span,
button[data-testid^="stBaseButton"]:disabled div {
    color: #7f8998 !important;
}

[data-testid="stMetric"] {
    background:#101722;
    border:1px solid #303a4d;
    border-radius:14px;
    padding:.72rem .82rem;
}
[data-testid="stMetricLabel"] p { color:#b5bfce !important; font-size:.93rem !important; }
[data-testid="stMetricValue"] { color:#fff !important; }
[data-testid="stExpander"] {
    border-color:#354055 !important;
    border-radius:14px !important;
    background:rgba(18,24,36,.62);
}
[data-testid="stAlert"] { font-size: 1.01rem; }
hr { border-color:#2b3444 !important; }
@media (max-width: 760px) {
    .block-container { padding-left: 1rem; padding-right: 1rem; }
    .voice-settings { grid-template-columns: 1fr 1fr; }
}

/* Compact workbench */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: .35rem;
    background: #0d131d;
    border: 1px solid #2e394b;
    border-radius: 14px;
    padding: .28rem;
}
[data-testid="stTabs"] button[role="tab"] {
    min-height: 44px;
    border-radius: 10px;
    font-weight: 800;
    padding: .45rem .8rem;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    background: #202b3c;
}
[data-testid="stDataEditor"] {
    border: 1px solid #354055;
    border-radius: 12px;
    overflow: hidden;
}
.compact-note {
    color:#b9c2d0;
    font-size:.94rem;
    margin:-.25rem 0 .65rem 0;
}

</style>
""",
    unsafe_allow_html=True,
)


def secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets[name]
        return str(value).strip()
    except Exception:
        return os.getenv(name, default).strip()


def require_login() -> None:
    password = secret("APP_PASSWORD")
    if not password:
        return
    if st.session_state.get("authenticated"):
        return

    st.markdown(
        '<div class="hero"><h1>AI Skeleton Voiceover</h1><p>Private creator tool for your team.</p></div>',
        unsafe_allow_html=True,
    )
    st.subheader("Sign in")
    entered = st.text_input("Password", type="password", placeholder="Enter team password")
    if st.button("Enter", type="primary", use_container_width=True):
        if hmac.compare_digest(entered, password):
            st.session_state.authenticated = True
            st.rerun()
        st.error("Incorrect password.")
    st.stop()


def reset_output(clear_loaded_id: bool = False) -> None:
    for key in [
        "product_facts",
        "script_verification",
        "script_editor",
        "compliance_rating",
        "compliance_report",
        "compliance_script_hash",
        "compliance_bypass_hash",
        "compliance_bypass_reason",
        "raw_audio",
        "clean_audio",
        "audio_meta",
        "audio_script_hash",
    ]:
        st.session_state.pop(key, None)
    if clear_loaded_id:
        st.session_state.pop("loaded_script_id", None)
        st.session_state.pop("save_script_title", None)


def clear_workspace() -> None:
    reset_output(clear_loaded_id=True)
    defaults = {
        "product_name_input": "",
        "product_details_input": "",
        "architecture_choice_input": "Auto Detect",
        "viral_transcript_input": "",
        "on_screen_text_input": "",
        "visual_cues_input": "",
        "save_script_title": "",
        "tiktok_product_url_input": "",
        "scraped_product": {},
        "selected_product_image_urls": [],
        "product_image_facts": "",
        "regeneration_angle_select": "Fresh take",
    }
    for key, value in defaults.items():
        st.session_state[key] = value


def script_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def safe_filename(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return clean[:80] or "voiceover"


def apply_voice_preset(voice_name: str | None = None) -> None:
    name = voice_name or st.session_state.get("voice_selector", "Julie US")
    if name not in VOICE_PRESETS:
        name = "Julie US"
        st.session_state.voice_selector = name
    preset = VOICE_PRESETS[name]
    st.session_state.voice_speed = float(preset["speed"])
    st.session_state.voice_stability = float(preset["stability"])
    st.session_state.voice_similarity = float(preset["similarity"])
    st.session_state.voice_style = float(preset["style"])
    st.session_state.voice_speaker_boost = bool(preset["speaker_boost"])


def on_voice_change() -> None:
    apply_voice_preset()
    for key in ["raw_audio", "clean_audio", "audio_meta", "audio_script_hash"]:
        st.session_state.pop(key, None)


def render_step(number: int, title: str) -> None:
    st.markdown(
        f'<div class="step-heading"><span class="step-number">{number}</span><strong>{title}</strong></div>',
        unsafe_allow_html=True,
    )


def render_voice_card(name: str) -> None:
    preset = VOICE_PRESETS[name]
    speed = st.session_state.get("voice_speed", preset["speed"])
    stability = st.session_state.get("voice_stability", preset["stability"])
    similarity = st.session_state.get("voice_similarity", preset["similarity"])
    style = st.session_state.get("voice_style", preset["style"])
    speaker = st.session_state.get("voice_speaker_boost", preset["speaker_boost"])
    st.markdown(
        f"""
<div class="voice-card">
  <div class="voice-name">{name} <span style="font-size:.88rem;color:#aeb8c8;font-weight:650">· {preset['description']}</span></div>
  <div class="voice-desc" style="margin-top:.55rem">Speed <b>{speed:.2f}</b> &nbsp;·&nbsp; Stability <b>{stability:.0%}</b> &nbsp;·&nbsp; Similarity <b>{similarity:.0%}</b> &nbsp;·&nbsp; Style <b>{style:.0%}</b> &nbsp;·&nbsp; Boost <b>{'On' if speaker else 'Off'}</b></div>
</div>
""",
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=20, show_spinner=False)
def cached_load_library(
    local_path: str,
    github_token: str,
    github_repo: str,
    github_path: str,
) -> tuple[list[dict[str, Any]], str]:
    return load_scripts(local_path, github_token, github_repo, github_path)


def load_saved_into_workspace(entry: dict[str, Any]) -> None:
    script = str(entry.get("script_text") or "")
    st.session_state.product_name_input = str(entry.get("product_name") or "")
    st.session_state.tiktok_product_url_input = str(entry.get("tiktok_product_url") or "")
    st.session_state.scraped_product = entry.get("scraped_product") or {}
    st.session_state.selected_product_image_urls = list(entry.get("selected_product_image_urls") or [])
    st.session_state.product_image_facts = str(entry.get("product_image_facts") or "")
    st.session_state.product_details_input = str(entry.get("product_details") or "")
    architecture = str(entry.get("architecture_choice") or "Auto Detect")
    st.session_state.architecture_choice_input = architecture if architecture in ARCHITECTURE_OPTIONS else "Auto Detect"
    st.session_state.viral_transcript_input = str(entry.get("viral_transcript") or "")
    st.session_state.on_screen_text_input = str(entry.get("on_screen_text") or "")
    st.session_state.visual_cues_input = str(entry.get("visual_cues") or "")
    st.session_state.script_editor = script
    st.session_state.product_facts = entry.get("product_facts") or {}
    st.session_state.script_verification = entry.get("script_verification") or {}
    st.session_state.compliance_rating = str(entry.get("compliance_rating") or "UNKNOWN")
    st.session_state.compliance_report = str(entry.get("compliance_report") or "")
    if script and entry.get("compliance_is_current"):
        st.session_state.compliance_script_hash = script_hash(script)
    else:
        st.session_state.pop("compliance_script_hash", None)
    st.session_state.pop("compliance_bypass_hash", None)
    st.session_state.pop("compliance_bypass_reason", None)
    st.session_state.loaded_script_id = str(entry.get("id") or "")
    st.session_state.save_script_title = str(entry.get("title") or entry.get("product_name") or "Saved Script")

    voice_name = str(entry.get("voice_name") or "Julie US")
    if voice_name not in VOICE_PRESETS:
        voice_name = "Julie US"
    st.session_state.voice_selector = voice_name
    settings = entry.get("voice_settings") or {}
    preset = VOICE_PRESETS[voice_name]
    st.session_state.voice_speed = float(settings.get("speed", preset["speed"]))
    st.session_state.voice_stability = float(settings.get("stability", preset["stability"]))
    st.session_state.voice_similarity = float(settings.get("similarity", preset["similarity"]))
    st.session_state.voice_style = float(settings.get("style", preset["style"]))
    st.session_state.voice_speaker_boost = bool(settings.get("speaker_boost", preset["speaker_boost"]))
    st.session_state.keep_silence = float(entry.get("keep_silence", 0.03))

    for key in ["raw_audio", "clean_audio", "audio_meta", "audio_script_hash"]:
        st.session_state.pop(key, None)


def build_saved_entry() -> dict[str, Any]:
    script = str(st.session_state.get("script_editor") or "")
    current_hash = script_hash(script) if script.strip() else ""
    compliance_is_current = bool(
        current_hash
        and st.session_state.get("compliance_script_hash") == current_hash
        and st.session_state.get("compliance_rating") in {"PASS", "NEEDS REVISION", "HIGH RISK", "UNKNOWN"}
    )
    rating = st.session_state.get("compliance_rating", "UNKNOWN") if compliance_is_current else "STALE"
    report = st.session_state.get("compliance_report", "") if compliance_is_current else ""
    return {
        "id": st.session_state.get("loaded_script_id", ""),
        "title": (st.session_state.get("save_script_title") or st.session_state.get("product_name_input") or "Saved Script").strip(),
        "product_name": st.session_state.get("product_name_input", ""),
        "tiktok_product_url": st.session_state.get("tiktok_product_url_input", ""),
        "scraped_product": st.session_state.get("scraped_product", {}),
        "selected_product_image_urls": st.session_state.get("selected_product_image_urls", []),
        "product_image_facts": st.session_state.get("product_image_facts", ""),
        "product_details": st.session_state.get("product_details_input", ""),
        "architecture_choice": st.session_state.get("architecture_choice_input", "Auto Detect"),
        "viral_transcript": st.session_state.get("viral_transcript_input", ""),
        "on_screen_text": st.session_state.get("on_screen_text_input", ""),
        "visual_cues": st.session_state.get("visual_cues_input", ""),
        "script_text": script,
        "product_facts": st.session_state.get("product_facts", {}),
        "script_verification": st.session_state.get("script_verification", {}),
        "compliance_rating": rating,
        "compliance_report": report,
        "compliance_is_current": compliance_is_current,
        "manual_override_used": st.session_state.get("compliance_bypass_hash") == current_hash,
        "manual_override_reason": st.session_state.get("compliance_bypass_reason", ""),
        "voice_name": st.session_state.get("voice_selector", "Julie US"),
        "voice_settings": {
            "speed": float(st.session_state.get("voice_speed", 1.0)),
            "stability": float(st.session_state.get("voice_stability", 0.5)),
            "similarity": float(st.session_state.get("voice_similarity", 0.75)),
            "style": float(st.session_state.get("voice_style", 0.0)),
            "speaker_boost": bool(st.session_state.get("voice_speaker_boost", True)),
        },
        "keep_silence": float(st.session_state.get("keep_silence", 0.03)),
    }


require_login()

OPENAI_API_KEY = secret("OPENAI_API_KEY")
ELEVENLABS_API_KEY = secret("ELEVENLABS_API_KEY")
HF_TOKEN = secret("HF_TOKEN")
SOCIAVAULT_API_KEY = secret("SOCIAVAULT_API_KEY")
# All OpenAI stages intentionally use the same high-quality model.
# Legacy OPENAI_MODEL_SCRIPT / COMPLIANCE / IMAGE secrets are ignored.
OPENAI_MODEL = "gpt-5.6-sol"
SCRIPT_MODEL = OPENAI_MODEL
COMPLIANCE_MODEL = OPENAI_MODEL
IMAGE_MODEL = OPENAI_MODEL
ELEVEN_MODEL = secret("ELEVENLABS_MODEL", "eleven_multilingual_v2")
LIBRARY_GITHUB_TOKEN = secret("SCRIPT_LIBRARY_GITHUB_TOKEN")
LIBRARY_GITHUB_REPO = secret("SCRIPT_LIBRARY_GITHUB_REPO")
LIBRARY_GITHUB_PATH = secret("SCRIPT_LIBRARY_GITHUB_PATH", "data/saved_scripts.json")

# Stable widget/session defaults.
defaults: dict[str, Any] = {
    "voice_selector": "Julie US",
    "keep_silence": 0.03,
    "use_hf": True,
    "product_name_input": "",
    "product_details_input": "",
    "architecture_choice_input": "Auto Detect",
    "viral_transcript_input": "",
    "on_screen_text_input": "",
    "visual_cues_input": "",
    "save_script_title": "",
    "tiktok_product_url_input": "",
    "scraped_product": {},
    "selected_product_image_urls": [],
    "product_image_facts": "",
    "regeneration_angle_select": "Fresh take",
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value
if "voice_speed" not in st.session_state:
    apply_voice_preset(st.session_state.voice_selector)

st.markdown(
    """
<div class="hero">
  <h1>AI Skeleton Voiceover Generator</h1>
  <p>Fetch the product, write the script, approve compliance, and create the voiceover.</p>
  <div class="quick-flow">
    <span>Product</span><span>Script</span><span>Compliance</span><span>Voiceover</span><span>GPT-5.6 Sol</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

if not OPENAI_API_KEY or not ELEVENLABS_API_KEY:
    missing = []
    if not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    if not ELEVENLABS_API_KEY:
        missing.append("ELEVENLABS_API_KEY")
    st.error("Missing server secrets: " + ", ".join(missing) + ". Add them before using the app.")

# Saved script library appears before the form so a loaded entry can populate widget state safely.
with st.expander("📚 Saved Script Library — load, search, or delete scripts", expanded=False):
    library_error = ""
    try:
        saved_scripts, library_mode = cached_load_library(
            str(LOCAL_LIBRARY_PATH),
            LIBRARY_GITHUB_TOKEN,
            LIBRARY_GITHUB_REPO,
            LIBRARY_GITHUB_PATH,
        )
    except ScriptLibraryError as exc:
        saved_scripts, library_mode = [], "error"
        library_error = str(exc)

    if library_error:
        st.error(library_error)
    elif library_mode == "github":
        st.success("Saved-script storage: GitHub persistent library")
    else:
        st.warning(
            "Saved-script storage: local app storage. It works now, but Streamlit may erase it during a reboot/redeploy. "
            "Add the optional GitHub library secrets for permanent storage."
        )

    top_left, top_right = st.columns([1.25, 0.75])
    with top_left:
        search_saved = st.text_input(
            "Search saved scripts",
            key="library_search",
            placeholder="Search product name or saved title…",
        )
    with top_right:
        if st.button("Start New / Clear Workspace", use_container_width=True):
            clear_workspace()
            st.rerun()

    filtered = saved_scripts
    if search_saved.strip():
        query = search_saved.lower().strip()
        filtered = [
            item
            for item in saved_scripts
            if query in str(item.get("title") or "").lower()
            or query in str(item.get("product_name") or "").lower()
            or query in str(item.get("script_text") or "").lower()
        ]

    if filtered:
        label_to_id: dict[str, str] = {}
        for item in filtered:
            title = str(item.get("title") or item.get("product_name") or "Saved Script")
            updated = str(item.get("updated_at") or item.get("created_at") or "")[:10]
            suffix = f" · {updated}" if updated else ""
            label = f"{title}{suffix}"
            # Avoid selectbox collisions for duplicate titles.
            if label in label_to_id:
                label = f"{label} · {str(item.get('id'))[:6]}"
            label_to_id[label] = str(item.get("id"))
        selected_label = st.selectbox("Saved scripts", list(label_to_id.keys()), key="saved_script_selector")
        selected_saved_id = label_to_id[selected_label]
        selected_entry = next(item for item in filtered if str(item.get("id")) == selected_saved_id)
        meta_cols = st.columns(3)
        meta_cols[0].metric("Product", str(selected_entry.get("product_name") or "—")[:42])
        meta_cols[1].metric("Compliance", str(selected_entry.get("compliance_rating") or "—"))
        meta_cols[2].metric("Voice", str(selected_entry.get("voice_name") or "—"))
        load_col, delete_col = st.columns([1, 1])
        with load_col:
            if st.button("Load Selected Script", type="primary", use_container_width=True):
                load_saved_into_workspace(selected_entry)
                st.rerun()
        with delete_col:
            confirm_delete = st.checkbox("Confirm delete", key=f"confirm_delete_{selected_saved_id}")
            if st.button("Delete Selected", use_container_width=True, disabled=not confirm_delete):
                try:
                    delete_script(
                        selected_saved_id,
                        LOCAL_LIBRARY_PATH,
                        LIBRARY_GITHUB_TOKEN,
                        LIBRARY_GITHUB_REPO,
                        LIBRARY_GITHUB_PATH,
                    )
                    if st.session_state.get("loaded_script_id") == selected_saved_id:
                        st.session_state.pop("loaded_script_id", None)
                    cached_load_library.clear()
                    st.success("Saved script deleted.")
                    st.rerun()
                except ScriptLibraryError as exc:
                    st.error(str(exc))
    else:
        st.info("No saved scripts found yet.")

render_step(1, "Product + voice setup")
left, right = st.columns([1.45, 0.75], gap="large")

with left:
    st.markdown("#### TikTok Shop URL — optional")
    url_col, fetch_col = st.columns([1.45, 0.55], gap="small")
    with url_col:
        tiktok_product_url = st.text_input(
            "TikTok Shop product URL",
            key="tiktok_product_url_input",
            placeholder="https://www.tiktok.com/shop/pdp/... or https://www.tiktok.com/view/product/...",
            label_visibility="collapsed",
        )
    with fetch_col:
        fetch_product = st.button(
            "Fetch Product",
            type="primary",
            use_container_width=True,
            disabled=not (SOCIAVAULT_API_KEY and tiktok_product_url.strip()),
        )
    if not SOCIAVAULT_API_KEY:
        st.caption("SociaVault is not configured yet. Manual product entry still works.")
    else:
        st.caption("Fetches the current TikTok Shop listing with SociaVault. One product lookup uses one SociaVault credit.")

    if fetch_product:
        try:
            with st.spinner("Fetching TikTok Shop product details…"):
                scraped = fetch_tiktok_shop_product(
                    SOCIAVAULT_API_KEY,
                    tiktok_product_url,
                    region="US",
                    get_related_videos=False,
                )
            reset_output(clear_loaded_id=True)
            for key in list(st.session_state.keys()):
                if str(key).startswith("use_product_photo_"):
                    st.session_state.pop(key, None)
            st.session_state.scraped_product = scraped
            # Product photos are intentionally NOT auto-selected. The VA chooses exactly which ones to read.
            st.session_state.selected_product_image_urls = []
            st.session_state.product_image_facts = ""
            st.session_state.product_name_input = scraped.get("title", "")
            st.session_state.product_details_input = scraped.get("script_details", "")
            st.session_state.save_script_title = scraped.get("title", "")
            st.rerun()
        except SociaVaultError as exc:
            st.error(str(exc))
        except Exception:
            st.error("TikTok Shop lookup failed. Try again in a moment.")

    scraped = st.session_state.get("scraped_product") or {}
    if scraped:
        image_urls = (scraped.get("images") or [])[:12]
        seller_label = str(scraped.get("seller_name") or "TikTok Shop")
        st.success(f"Product loaded from {seller_label}. {len(image_urls)} listing photo(s) available.")

        if image_urls:
            with st.expander(f"🖼️ Choose product photos ({len(image_urls)} available)", expanded=False):
                st.caption("Nothing is selected automatically. Check only the photos you want GPT-5.6 Sol to read. Price and stock are ignored.")
                selected_before = set(st.session_state.get("selected_product_image_urls") or [])
                selected_now: list[str] = []
                safe_pid = re.sub(r"[^A-Za-z0-9]+", "_", str(scraped.get("product_id") or "product"))
                image_cols = st.columns(min(4, len(image_urls)))
                for idx, image_url in enumerate(image_urls):
                    with image_cols[idx % len(image_cols)]:
                        st.image(image_url, use_container_width=True)
                        photo_key = f"use_product_photo_{safe_pid}_{idx}"
                        if photo_key not in st.session_state:
                            st.session_state[photo_key] = image_url in selected_before
                        use_photo = st.checkbox(f"Use photo {idx + 1}", key=photo_key)
                        if use_photo:
                            selected_now.append(image_url)
                st.session_state.selected_product_image_urls = selected_now
                st.caption(f"Selected: {len(selected_now)} of {len(image_urls)}")

                image_facts_preview = str(st.session_state.get("product_image_facts") or "").strip()
                if image_facts_preview:
                    with st.expander("AI text extracted from selected photos", expanded=False):
                        st.text(image_facts_preview)

    product_name = st.text_input(
        "Product name",
        key="product_name_input",
        placeholder="e.g. Goli SuperFruits Beauty Gummies",
    )
    product_details = st.text_area(
        "Product details",
        key="product_details_input",
        height=220,
        placeholder="Paste the listing details, ingredients/features, benefits, directions, disclaimers, offer details, etc.",
    )
    architecture_choice = st.selectbox(
        "Script style",
        ARCHITECTURE_OPTIONS,
        key="architecture_choice_input",
        help="Auto uses Arch A by default and switches to Arch C when the request clearly calls for a timeline format.",
    )
    with st.expander("Optional: viral transcript"):
        viral_transcript = st.text_area(
            "Viral transcript",
            key="viral_transcript_input",
            height=190,
            placeholder="Paste a reference transcript if you want Script DNA to absorb its hook energy or structure.",
            label_visibility="collapsed",
        )

    with st.expander("Optional: on-screen text / visual compliance context"):
        on_screen_text = st.text_area(
            "On-screen text",
            key="on_screen_text_input",
            height=110,
            placeholder="Any captions or text overlays",
        )
        visual_cues = st.text_area(
            "Visual cues",
            key="visual_cues_input",
            height=110,
            placeholder="Avatar actions, product demo, before/after visuals, etc.",
        )

with right:
    selected_voice_name = st.selectbox(
        "ElevenLabs voice",
        list(VOICE_PRESETS.keys()),
        key="voice_selector",
        on_change=on_voice_change,
        help="Each voice automatically loads the exact approved ElevenLabs preset shown below.",
    )
    selected_voice_id = str(VOICE_PRESETS[selected_voice_name]["id"])
    render_voice_card(selected_voice_name)

    with st.expander("Advanced: manually adjust this voice"):
        st.caption("Changing voices resets these controls back to that voice's approved preset.")
        st.slider("Voice speed", 0.70, 1.20, step=0.01, key="voice_speed")
        st.slider("Stability", 0.0, 1.0, step=0.01, key="voice_stability")
        st.slider("Similarity boost", 0.0, 1.0, step=0.01, key="voice_similarity")
        st.slider("Style", 0.0, 1.0, step=0.01, key="voice_style")
        st.checkbox("Speaker boost", key="voice_speaker_boost")

    with st.expander("Silence removal"):
        st.slider(
            "Keep silence around cuts (seconds)",
            0.00,
            0.30,
            step=0.01,
            key="keep_silence",
            help="Default is 0.03 seconds.",
        )
        st.checkbox(
            "Use NeuralFalcon Hugging Face silence remover",
            key="use_hf",
            help="If the public Space fails, the app automatically falls back to the local silence remover.",
        )

    st.info("🔒 ElevenLabs unlocks after a green PASS or a manual override for the exact current script.")

st.markdown("<div style='height:.45rem'></div>", unsafe_allow_html=True)
generate_clicked = st.button(
    "Generate Script + Run Compliance",
    type="primary",
    use_container_width=True,
    disabled=not (OPENAI_API_KEY and product_name.strip() and product_details.strip()),
)

regenerate_requested = bool(st.session_state.pop("regenerate_script_requested", False))
should_generate = generate_clicked or regenerate_requested
previous_script_for_regen = str(st.session_state.get("script_editor") or "") if regenerate_requested else ""

if should_generate:
    reset_output(clear_loaded_id=False)
    st.session_state.save_script_title = product_name.strip()
    try:
        progress = st.status(
            "Regenerating Script DNA voiceover…" if regenerate_requested else "Building Script DNA voiceover…",
            expanded=True,
        )
        selected_images = list(st.session_state.get("selected_product_image_urls") or [])
        image_facts = ""
        if selected_images:
            progress.write(f"Reading {len(selected_images)} selected product photo(s) for visible benefits, ingredients, directions, and differentiators…")
            image_facts = analyze_product_images(OPENAI_API_KEY, IMAGE_MODEL, selected_images)
            st.session_state.product_image_facts = image_facts
        else:
            st.session_state.product_image_facts = ""

        grounded_details = product_details.strip()
        if image_facts.strip():
            grounded_details += "\n\nOFFICIAL TIKTOK SHOP PRODUCT IMAGE FACTS (read only from selected listing photos; price/stock/testimonial claims excluded):\n" + image_facts.strip()

        progress.write("Extracting only the product facts supplied in the listing and selected product photos…")
        facts = extract_product_facts(OPENAI_API_KEY, SCRIPT_MODEL, product_name, grounded_details)
        st.session_state.product_facts = facts

        progress.write("Writing the Skeleton / Script DNA script with GPT-5.6 Sol using the canonical sample scripts…")
        script, verification = generate_script(
            OPENAI_API_KEY,
            SCRIPT_MODEL,
            product_name,
            grounded_details,
            facts,
            architecture_choice,
            viral_transcript,
            previous_script=previous_script_for_regen,
            regeneration_angle=st.session_state.get("regeneration_angle_select", "Fresh take"),
        )
        st.session_state.script_editor = script
        st.session_state.script_verification = verification

        progress.write("Running the TikTok Shop compliance mega prompt…")
        rating, report = audit_script(
            OPENAI_API_KEY,
            COMPLIANCE_MODEL,
            script,
            on_screen_text,
            visual_cues,
        )
        st.session_state.compliance_rating = rating
        st.session_state.compliance_report = report
        st.session_state.compliance_script_hash = script_hash(script)
        progress.update(label="Script and compliance review complete", state="complete", expanded=False)
        st.rerun()
    except Exception as exc:
        st.error(f"Generation failed: {exc}")

if "script_editor" in st.session_state:
    st.divider()
    render_step(2, "Script workbench")

    verification = st.session_state.get("script_verification", {})
    rating = st.session_state.get("compliance_rating", "UNKNOWN")
    report = st.session_state.get("compliance_report", "")
    current_hash = script_hash(st.session_state.script_editor)
    compliance_hash = st.session_state.get("compliance_script_hash")
    bypass_hash = st.session_state.get("compliance_bypass_hash")
    current_pass = rating == "PASS" and compliance_hash == current_hash
    current_bypass = bypass_hash == current_hash
    current_approved = current_pass or current_bypass
    short_verdict = parse_final_summary(report)

    if current_bypass:
        st.markdown(
            '<div class="status-box status-override">🟣 MANUAL OVERRIDE — voiceover enabled for this exact script.</div>',
            unsafe_allow_html=True,
        )
    elif current_pass:
        st.markdown(
            '<div class="status-box status-pass">🟢 PASS — ready for voiceover.</div>',
            unsafe_allow_html=True,
        )
    elif rating == "NEEDS REVISION":
        st.markdown(
            '<div class="status-box status-warn">🟡 NEEDS REVISION — open the Compliance tab to choose fixes.</div>',
            unsafe_allow_html=True,
        )
    elif rating == "HIGH RISK":
        st.markdown(
            '<div class="status-box status-risk">🔴 HIGH RISK — review the Compliance tab before continuing.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.warning("Compliance result needs review. Open the Compliance tab.")

    script_tab, compliance_tab, save_tab, voice_tab = st.tabs(
        ["✍️ Script", "🛡️ Compliance", "💾 Save", "🎙️ Voiceover"]
    )

    with script_tab:
        if verification:
            m1, m2, m3 = st.columns(3)
            m1.metric("Words", verification.get("word_count", "—"))
            m2.metric("Architecture", verification.get("architecture", "—"))
            m3.metric("Script DNA", "PASS" if verification.get("pass") else "Needs attention")

        st.text_area(
            "Final script",
            key="script_editor",
            height=390,
            help="Any edit invalidates the prior compliance approval until the exact edited script is rechecked or manually approved.",
        )

        control_left, control_mid, control_right = st.columns([1.15, 1, 1])
        with control_left:
            st.selectbox(
                "Regenerate angle",
                REGENERATION_ANGLES,
                key="regeneration_angle_select",
                help="Uses the current product data and selected photos. SociaVault is not called again.",
            )
        with control_mid:
            st.markdown("<div style='height:1.8rem'></div>", unsafe_allow_html=True)
            regenerate = st.button("Regenerate Script", type="primary", use_container_width=True)
        with control_right:
            st.markdown("<div style='height:1.8rem'></div>", unsafe_allow_html=True)
            recheck = st.button("Recheck Edited Script", use_container_width=True)

        if regenerate:
            st.session_state.regenerate_script_requested = True
            st.rerun()

        if recheck:
            try:
                with st.spinner("Rechecking the edited script…"):
                    rating, report = audit_script(
                        OPENAI_API_KEY,
                        COMPLIANCE_MODEL,
                        st.session_state.script_editor,
                        st.session_state.get("on_screen_text_input", ""),
                        st.session_state.get("visual_cues_input", ""),
                    )
                st.session_state.compliance_rating = rating
                st.session_state.compliance_report = report
                st.session_state.compliance_script_hash = script_hash(st.session_state.script_editor)
                st.session_state.pop("compliance_bypass_hash", None)
                st.session_state.pop("compliance_bypass_reason", None)
                for key in ["raw_audio", "clean_audio", "audio_meta", "audio_script_hash"]:
                    st.session_state.pop(key, None)
                st.rerun()
            except Exception as exc:
                st.error(f"Compliance check failed: {exc}")

        if verification.get("style_issues"):
            with st.expander("Script DNA notes", expanded=False):
                for issue in verification.get("style_issues") or []:
                    st.write(f"• {issue}")
        with st.expander("Extracted product facts", expanded=False):
            st.json(st.session_state.get("product_facts", {}))

    with compliance_tab:
        # Recompute after the editable script widget above.
        current_hash = script_hash(st.session_state.script_editor)
        compliance_hash = st.session_state.get("compliance_script_hash")
        bypass_hash = st.session_state.get("compliance_bypass_hash")
        rating = st.session_state.get("compliance_rating", "UNKNOWN")
        report = st.session_state.get("compliance_report", "")
        current_pass = rating == "PASS" and compliance_hash == current_hash
        current_bypass = bypass_hash == current_hash
        rewrite_suggestions = parse_rewrite_suggestions(report) if (report and compliance_hash == current_hash) else []
        short_verdict = parse_final_summary(report)

        if short_verdict:
            st.markdown(f"**Auditor verdict:** {short_verdict}")

        if current_pass:
            st.success("No action needed. This exact script passed compliance.")
        elif current_bypass:
            reason = st.session_state.get("compliance_bypass_reason", "Manually reviewed")
            st.info(f"Manual approval is active for this exact script. Reason: {reason}")
        else:
            if compliance_hash != current_hash:
                st.warning("The script changed after the last audit. Recheck it from the Script tab before relying on these results.")
            elif rewrite_suggestions:
                st.markdown(f"### {len(rewrite_suggestions)} suggested fix{'es' if len(rewrite_suggestions) != 1 else ''}")
                st.caption("Check only the rewrites you want. The full compliance report is hidden below unless you need it.")
                report_token = hashlib.sha1(report.encode("utf-8")).hexdigest()[:10]
                editor_data = {
                    "Apply": [False] * len(rewrite_suggestions),
                    "Flagged phrase": [item["original"] for item in rewrite_suggestions],
                    "Suggested rewrite": [item["rewrite"] for item in rewrite_suggestions],
                }
                edited = st.data_editor(
                    editor_data,
                    key=f"compliance_fix_table_{report_token}",
                    hide_index=True,
                    use_container_width=True,
                    height=min(330, 72 + 58 * len(rewrite_suggestions)),
                    column_config={
                        "Apply": st.column_config.CheckboxColumn("Apply", width="small", default=False),
                        "Flagged phrase": st.column_config.TextColumn("Flagged phrase", width="medium"),
                        "Suggested rewrite": st.column_config.TextColumn("Suggested rewrite", width="large"),
                    },
                    disabled=["Flagged phrase", "Suggested rewrite"],
                )
                apply_values = edited.get("Apply", []) if isinstance(edited, dict) else []
                selected_rewrites = [
                    item for item, should_apply in zip(rewrite_suggestions, apply_values) if should_apply
                ]

                if st.button(
                    f"Apply {len(selected_rewrites)} Selected Fix{'es' if len(selected_rewrites) != 1 else ''} + Recheck",
                    type="primary",
                    use_container_width=True,
                    disabled=not selected_rewrites,
                ):
                    try:
                        with st.spinner("Applying the selected fixes and rechecking…"):
                            revised_script = apply_selected_rewrites(
                                OPENAI_API_KEY,
                                COMPLIANCE_MODEL,
                                st.session_state.script_editor,
                                selected_rewrites,
                            )
                            st.session_state.script_editor = revised_script
                            st.session_state.pop("compliance_bypass_hash", None)
                            st.session_state.pop("compliance_bypass_reason", None)
                            for key in ["raw_audio", "clean_audio", "audio_meta", "audio_script_hash"]:
                                st.session_state.pop(key, None)
                            revised_rating, revised_report = audit_script(
                                OPENAI_API_KEY,
                                COMPLIANCE_MODEL,
                                revised_script,
                                st.session_state.get("on_screen_text_input", ""),
                                st.session_state.get("visual_cues_input", ""),
                            )
                            st.session_state.compliance_rating = revised_rating
                            st.session_state.compliance_report = revised_report
                            st.session_state.compliance_script_hash = script_hash(revised_script)
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not apply/recheck the selected fixes: {exc}")
            else:
                st.info("No selectable rewrite suggestions were returned. Use the full report below only if you need more detail.")

        override_left, report_right = st.columns(2)
        with override_left:
            if not current_pass:
                with st.expander("Manual override", expanded=False):
                    st.warning("Use only after personally reviewing the flag. Approval applies only to the exact current script.")
                    override_reason = st.selectbox(
                        "Reason",
                        [
                            "Known-safe TikTok orange-cart CTA false positive",
                            "Reviewed manually — flag does not apply",
                            "Other reviewed false positive",
                        ],
                        key="override_reason_select",
                    )
                    override_ack = st.checkbox(
                        "I reviewed this script and approve it for voiceover.",
                        key="override_ack",
                    )
                    if st.button(
                        "Approve Exact Script",
                        use_container_width=True,
                        disabled=not override_ack,
                    ):
                        st.session_state.compliance_bypass_hash = script_hash(st.session_state.script_editor)
                        st.session_state.compliance_bypass_reason = override_reason
                        for key in ["raw_audio", "clean_audio", "audio_meta", "audio_script_hash"]:
                            st.session_state.pop(key, None)
                        st.rerun()
                    if current_bypass and st.button("Remove Override", use_container_width=True):
                        st.session_state.pop("compliance_bypass_hash", None)
                        st.session_state.pop("compliance_bypass_reason", None)
                        st.rerun()
        with report_right:
            with st.expander("Full auditor report", expanded=False):
                st.markdown(report or "No compliance report available.")
                if report:
                    st.download_button(
                        "Download Full Report",
                        data=report.encode("utf-8"),
                        file_name=f"{safe_filename(st.session_state.get('product_name_input', 'product'))}_compliance.txt",
                        mime="text/plain",
                        use_container_width=True,
                    )

    with save_tab:
        st.markdown("### Save for later")
        st.caption("Save the current script, product setup, selected photos, voice, and current compliance result.")
        st.text_input(
            "Saved script name",
            key="save_script_title",
            placeholder="Name this script so it is easy to find later",
        )
        save_update_col, save_new_col = st.columns(2)
        with save_update_col:
            save_label = "Update Saved Script" if st.session_state.get("loaded_script_id") else "Save Script"
            if st.button(save_label, type="primary", use_container_width=True):
                try:
                    saved, mode = upsert_script(
                        build_saved_entry(),
                        LOCAL_LIBRARY_PATH,
                        LIBRARY_GITHUB_TOKEN,
                        LIBRARY_GITHUB_REPO,
                        LIBRARY_GITHUB_PATH,
                        force_new=False,
                    )
                    st.session_state.loaded_script_id = saved["id"]
                    cached_load_library.clear()
                    st.success("Script saved permanently to GitHub." if mode == "github" else "Script saved to the app library.")
                    st.rerun()
                except ScriptLibraryError as exc:
                    st.error(str(exc))
        with save_new_col:
            if st.button("Save as New Copy", use_container_width=True):
                try:
                    entry = build_saved_entry()
                    entry["id"] = ""
                    saved, _mode = upsert_script(
                        entry,
                        LOCAL_LIBRARY_PATH,
                        LIBRARY_GITHUB_TOKEN,
                        LIBRARY_GITHUB_REPO,
                        LIBRARY_GITHUB_PATH,
                        force_new=True,
                    )
                    st.session_state.loaded_script_id = saved["id"]
                    cached_load_library.clear()
                    st.success("New saved copy created.")
                    st.rerun()
                except ScriptLibraryError as exc:
                    st.error(str(exc))

    with voice_tab:
        # Recompute because the script may have been edited.
        current_hash = script_hash(st.session_state.script_editor)
        compliance_hash = st.session_state.get("compliance_script_hash")
        bypass_hash = st.session_state.get("compliance_bypass_hash")
        audio_hash = st.session_state.get("audio_script_hash")
        current_pass = st.session_state.get("compliance_rating") == "PASS" and compliance_hash == current_hash
        current_bypass = bypass_hash == current_hash
        current_approved = current_pass or current_bypass

        if st.session_state.get("compliance_rating") == "PASS" and compliance_hash != current_hash and not current_bypass:
            st.warning("The script was edited after its green check. Recheck it in the Script tab first.")
        elif bypass_hash and bypass_hash != current_hash:
            st.warning("The script changed after manual approval. Recheck it or approve the exact edited version again.")
        elif current_bypass:
            st.info("Manual approval active for this exact script.")
        elif current_pass:
            st.success("Compliance passed. Voiceover is unlocked.")
        else:
            st.info("Voiceover unlocks after a PASS or manual approval for the exact current script.")

        render_voice_card(selected_voice_name)
        if audio_hash and audio_hash != current_hash:
            st.info("The script changed after this audio was created. Generate a new voiceover for the current script.")

        generate_voice = st.button(
            "Generate Clean Voiceover",
            type="primary",
            use_container_width=True,
            disabled=not (current_approved and selected_voice_id and ELEVENLABS_API_KEY),
        )

        if generate_voice:
            try:
                status = st.status("Generating voiceover…", expanded=True)
                status.write(f"Generating {selected_voice_name} in ElevenLabs…")
                raw = synthesize(
                    ELEVENLABS_API_KEY,
                    selected_voice_id,
                    st.session_state.script_editor,
                    model_id=ELEVEN_MODEL,
                    stability=float(st.session_state.voice_stability),
                    similarity_boost=float(st.session_state.voice_similarity),
                    style=float(st.session_state.voice_style),
                    speed=float(st.session_state.voice_speed),
                    use_speaker_boost=bool(st.session_state.voice_speaker_boost),
                )
                status.write(f"Removing silence and keeping {float(st.session_state.keep_silence):.2f}s around cuts…")
                cleaned, meta = clean_audio(
                    raw,
                    keep_seconds=float(st.session_state.keep_silence),
                    hf_token=HF_TOKEN or None,
                    use_huggingface=bool(st.session_state.use_hf),
                )
                st.session_state.raw_audio = raw
                st.session_state.clean_audio = cleaned
                st.session_state.audio_meta = meta
                st.session_state.audio_script_hash = current_hash
                status.update(label="Clean voiceover ready", state="complete", expanded=False)
                st.rerun()
            except Exception as exc:
                st.error(f"Voiceover generation failed: {exc}")

        if st.session_state.get("clean_audio"):
            st.markdown("### Finished audio")
            meta = st.session_state.get("audio_meta", {})
            if meta.get("warning"):
                st.warning(meta["warning"])
            m1, m2, m3 = st.columns(3)
            m1.metric("Before", f'{meta.get("before_seconds", 0):.1f}s')
            m2.metric("Final", f'{meta.get("after_seconds", 0):.1f}s')
            m3.metric("Removed", f'{meta.get("seconds_removed", 0):.1f}s')
            st.audio(st.session_state.clean_audio, format="audio/mp3")
            name = safe_filename(st.session_state.get("product_name_input", "voiceover"))
            d1, d2 = st.columns(2)
            d1.download_button(
                "Download Clean MP3",
                data=st.session_state.clean_audio,
                file_name=f"{name}_clean.mp3",
                mime="audio/mpeg",
                use_container_width=True,
            )
            d2.download_button(
                "Download Raw MP3",
                data=st.session_state.raw_audio,
                file_name=f"{name}_raw.mp3",
                mime="audio/mpeg",
                use_container_width=True,
            )
