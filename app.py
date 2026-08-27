from __future__ import annotations

import hashlib
import hmac
import os
import re
from pathlib import Path

import streamlit as st

from services.compliance import audit_script
from services.elevenlabs import synthesize
from services.llm import LLMError
from services.script_engine import extract_product_facts, generate_script
from services.silence import clean_audio

APP_DIR = Path(__file__).resolve().parent

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
    --bg: #090b10;
    --panel: #121722;
    --panel-2: #171d29;
    --line: #2a3242;
    --text: #f7f8fb;
    --muted: #b5bdca;
    --accent: #8aa4ff;
    --good: #49d69d;
    --warn: #ffd166;
    --bad: #ff6b7f;
}
html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg);
    color: var(--text);
}
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 8% -10%, rgba(88,115,255,.20), transparent 32%),
        radial-gradient(circle at 95% 5%, rgba(122,74,255,.12), transparent 28%),
        var(--bg);
}
[data-testid="stHeader"] { background: transparent; }
.block-container {
    max-width: 1320px;
    padding-top: 1.55rem;
    padding-bottom: 5rem;
}
.hero {
    border: 1px solid var(--line);
    border-radius: 22px;
    padding: 1.45rem 1.55rem;
    margin-bottom: 1.15rem;
    background: linear-gradient(135deg, rgba(138,164,255,.13), rgba(255,255,255,.035));
}
.hero h1 {
    font-size: clamp(2.15rem, 4vw, 3.35rem);
    line-height: 1.03;
    letter-spacing: -0.045em;
    margin: 0;
    color: #ffffff;
}
.hero p {
    color: #c4cad5;
    font-size: 1.13rem;
    line-height: 1.55;
    margin: .7rem 0 0 0;
    max-width: 900px;
}
.quick-flow {
    display: flex;
    gap: .65rem;
    flex-wrap: wrap;
    margin-top: 1rem;
}
.quick-flow span {
    display: inline-block;
    padding: .52rem .78rem;
    border: 1px solid #39445a;
    background: #161d2b;
    border-radius: 999px;
    color: #e8ebf2;
    font-weight: 700;
    font-size: .93rem;
}
.step-heading {
    display:flex;
    align-items:center;
    gap:.7rem;
    margin: .2rem 0 .8rem 0;
}
.step-number {
    width: 2rem;
    height: 2rem;
    border-radius: 999px;
    display:inline-flex;
    align-items:center;
    justify-content:center;
    background: #718cff;
    color:#fff;
    font-weight:800;
    font-size:1rem;
}
.step-heading strong {
    color:#fff;
    font-size:1.32rem;
    letter-spacing:-.015em;
}
.voice-card {
    border: 1px solid var(--line);
    border-radius: 18px;
    background: linear-gradient(180deg, #171d2a, #111620);
    padding: 1rem 1.05rem;
    margin: .55rem 0 .75rem 0;
}
.voice-name { font-size:1.25rem; font-weight:800; color:#fff; }
.voice-desc { color:#b8c0ce; margin-top:.15rem; font-size:1rem; }
.voice-settings {
    display:grid;
    grid-template-columns: repeat(2, minmax(0,1fr));
    gap:.55rem .8rem;
    margin-top:.85rem;
}
.voice-setting {
    border:1px solid #303a4d;
    border-radius:12px;
    padding:.62rem .72rem;
    background:#0f141e;
}
.voice-setting b { display:block; color:#fff; font-size:1.05rem; }
.voice-setting span { color:#96a1b2; font-size:.82rem; }
.status-box {
    border-radius: 16px;
    padding: 1rem 1.05rem;
    border: 1px solid var(--line);
    margin: .7rem 0;
    font-size:1.05rem;
    font-weight:700;
}
.status-pass { border-left: 5px solid var(--good); background: rgba(73,214,157,.08); }
.status-warn { border-left: 5px solid var(--warn); background: rgba(255,209,102,.07); }
.status-risk { border-left: 5px solid var(--bad); background: rgba(255,107,127,.08); }
.small-muted { color:#aeb7c5; font-size:.95rem; }

/* Make the actual Streamlit controls easier to read. */
[data-testid="stWidgetLabel"] p {
    font-size: 1.03rem !important;
    font-weight: 750 !important;
    color: #f5f7fb !important;
}
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-baseweb="select"] > div {
    font-size: 1.05rem !important;
}
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: #111620 !important;
    border-color: #343e52 !important;
    color: #f8f9fb !important;
}
[data-testid="stTextArea"] textarea { line-height: 1.55 !important; }
[data-testid="stSelectbox"] > div > div {
    min-height: 48px;
}
.stButton > button,
.stDownloadButton > button {
    border-radius: 13px;
    min-height: 52px;
    font-size: 1.04rem;
    font-weight: 800;
    border-width: 1px;
}
.stButton > button[kind="primary"] {
    min-height: 58px;
    font-size: 1.12rem;
}
[data-testid="stMetric"] {
    background:#111620;
    border:1px solid #2a3344;
    border-radius:14px;
    padding:.72rem .82rem;
}
[data-testid="stMetricLabel"] p { color:#aeb7c5 !important; font-size:.92rem !important; }
[data-testid="stMetricValue"] { color:#fff !important; }
[data-testid="stExpander"] {
    border-color:#2d3648 !important;
    border-radius:14px !important;
    background:rgba(18,23,34,.55);
}
hr { border-color:#252d3c !important; }
@media (max-width: 760px) {
    .block-container { padding-left: 1rem; padding-right: 1rem; }
    .voice-settings { grid-template-columns: 1fr 1fr; }
}
</style>
""",
    unsafe_allow_html=True,
)


def secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets[name]
        return str(value)
    except Exception:
        return os.getenv(name, default)


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


def reset_output() -> None:
    for key in [
        "product_facts",
        "script_verification",
        "script_editor",
        "compliance_rating",
        "compliance_report",
        "compliance_script_hash",
        "raw_audio",
        "clean_audio",
        "audio_meta",
        "audio_script_hash",
    ]:
        st.session_state.pop(key, None)


def script_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def safe_filename(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return clean[:80] or "voiceover"


def apply_voice_preset(voice_name: str | None = None) -> None:
    name = voice_name or st.session_state.get("voice_selector", "Julie US")
    preset = VOICE_PRESETS[name]
    st.session_state.voice_speed = float(preset["speed"])
    st.session_state.voice_stability = float(preset["stability"])
    st.session_state.voice_similarity = float(preset["similarity"])
    st.session_state.voice_style = float(preset["style"])
    st.session_state.voice_speaker_boost = bool(preset["speaker_boost"])


def on_voice_change() -> None:
    apply_voice_preset()
    # A different voice/settings means prior audio is no longer the desired output.
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
  <div class="voice-name">{name}</div>
  <div class="voice-desc">{preset['description']}</div>
  <div class="voice-settings">
    <div class="voice-setting"><span>Speed</span><b>{speed:.2f}</b></div>
    <div class="voice-setting"><span>Stability</span><b>{stability:.0%}</b></div>
    <div class="voice-setting"><span>Similarity</span><b>{similarity:.0%}</b></div>
    <div class="voice-setting"><span>Style</span><b>{style:.0%}</b></div>
    <div class="voice-setting"><span>Speaker boost</span><b>{'On' if speaker else 'Off'}</b></div>
    <div class="voice-setting"><span>Silence kept</span><b>{st.session_state.get('keep_silence', 0.03):.2f}s</b></div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


require_login()

OPENAI_API_KEY = secret("OPENAI_API_KEY")
ELEVENLABS_API_KEY = secret("ELEVENLABS_API_KEY")
HF_TOKEN = secret("HF_TOKEN")
SCRIPT_MODEL = secret("OPENAI_MODEL_SCRIPT", "gpt-5.4-mini")
COMPLIANCE_MODEL = secret("OPENAI_MODEL_COMPLIANCE", "gpt-5.4-mini")
ELEVEN_MODEL = secret("ELEVENLABS_MODEL", "eleven_multilingual_v2")

# Initialize the approved default voice and exact ElevenLabs preset settings.
if "voice_selector" not in st.session_state:
    st.session_state.voice_selector = "Julie US"
if "voice_speed" not in st.session_state:
    apply_voice_preset(st.session_state.voice_selector)
if "keep_silence" not in st.session_state:
    st.session_state.keep_silence = 0.03
if "use_hf" not in st.session_state:
    st.session_state.use_hf = True

st.markdown(
    """
<div class="hero">
  <h1>AI Skeleton Voiceover Generator</h1>
  <p>Paste the product once. The app writes the Script DNA voiceover, audits it for TikTok Shop compliance, then creates and cleans the ElevenLabs audio.</p>
  <div class="quick-flow">
    <span>1 · Paste product</span>
    <span>2 · Get a green compliance check</span>
    <span>3 · Generate clean MP3</span>
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

render_step(1, "Product + voice setup")
left, right = st.columns([1.45, 0.75], gap="large")

with left:
    product_name = st.text_input(
        "Product name",
        placeholder="e.g. Goli SuperFruits Beauty Gummies",
    )
    product_details = st.text_area(
        "Product details",
        height=300,
        placeholder="Paste the listing details, ingredients/features, benefits, directions, disclaimers, offer details, etc.",
    )
    architecture_choice = st.selectbox(
        "Script style",
        ["Auto Detect", "Symptom Stack (Arch A)", "Day-by-Day Journey (Arch C)"],
        help="Auto uses Arch A by default and switches to Arch C when the request clearly calls for a timeline format.",
    )
    with st.expander("Optional: viral transcript"):
        viral_transcript = st.text_area(
            "Viral transcript",
            height=190,
            placeholder="Paste a reference transcript if you want Script DNA to absorb its hook energy or structure.",
            label_visibility="collapsed",
        )

    with st.expander("Optional: on-screen text / visual compliance context"):
        on_screen_text = st.text_area("On-screen text", height=110, placeholder="Any captions or text overlays")
        visual_cues = st.text_area(
            "Visual cues",
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

    st.info("🔒 ElevenLabs stays locked until the current script has a 🟢 PASS.")

st.markdown("<div style='height:.45rem'></div>", unsafe_allow_html=True)
generate_clicked = st.button(
    "Generate Script + Run Compliance",
    type="primary",
    use_container_width=True,
    disabled=not (OPENAI_API_KEY and product_name.strip() and product_details.strip()),
)

if generate_clicked:
    reset_output()
    try:
        progress = st.status("Building Script DNA voiceover…", expanded=True)
        progress.write("Extracting only the product facts supplied in the listing…")
        facts = extract_product_facts(OPENAI_API_KEY, SCRIPT_MODEL, product_name, product_details)
        st.session_state.product_facts = facts

        progress.write("Writing the Skeleton / Script DNA script…")
        script, verification = generate_script(
            OPENAI_API_KEY,
            SCRIPT_MODEL,
            product_name,
            product_details,
            facts,
            architecture_choice,
            viral_transcript,
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
    except (LLMError, Exception) as exc:
        st.error(f"Generation failed: {exc}")

if "script_editor" in st.session_state:
    st.divider()
    render_step(2, "Review script + compliance")

    verification = st.session_state.get("script_verification", {})
    if verification:
        c1, c2, c3 = st.columns(3)
        c1.metric("Words", verification.get("word_count", "—"))
        c2.metric("Architecture", verification.get("architecture", "—"))
        c3.metric("Script DNA", "PASS" if verification.get("pass") else "Needs attention")

    rating = st.session_state.get("compliance_rating", "UNKNOWN")
    report = st.session_state.get("compliance_report", "")
    if rating == "PASS":
        st.markdown('<div class="status-box status-pass">🟢 PASS — this exact script is cleared for voiceover.</div>', unsafe_allow_html=True)
    elif rating == "NEEDS REVISION":
        st.markdown('<div class="status-box status-warn">🟡 NEEDS REVISION — use the suggested fixes below, then recheck.</div>', unsafe_allow_html=True)
    elif rating == "HIGH RISK":
        st.markdown('<div class="status-box status-risk">🔴 HIGH RISK — voiceover is blocked until the script passes.</div>', unsafe_allow_html=True)
    else:
        st.warning("Compliance rating could not be parsed. Review the report and recheck before generating audio.")

    script_col, audit_col = st.columns([1.2, 0.8], gap="large")
    with script_col:
        st.text_area(
            "Final script — editable",
            key="script_editor",
            height=420,
            help="If you change anything, re-run compliance. Audio generation is locked until the current text has passed.",
        )
        recheck = st.button("Recheck Edited Script", use_container_width=True)
        if recheck:
            try:
                with st.spinner("Rechecking the edited script…"):
                    rating, report = audit_script(
                        OPENAI_API_KEY,
                        COMPLIANCE_MODEL,
                        st.session_state.script_editor,
                        on_screen_text,
                        visual_cues,
                    )
                st.session_state.compliance_rating = rating
                st.session_state.compliance_report = report
                st.session_state.compliance_script_hash = script_hash(st.session_state.script_editor)
                st.session_state.pop("raw_audio", None)
                st.session_state.pop("clean_audio", None)
                st.session_state.pop("audio_meta", None)
                st.session_state.pop("audio_script_hash", None)
                st.rerun()
            except Exception as exc:
                st.error(f"Compliance check failed: {exc}")

    with audit_col:
        with st.expander("Compliance report", expanded=rating != "PASS"):
            st.markdown(report or "No compliance report available.")
            if report:
                st.download_button(
                    "Download compliance report",
                    data=report.encode("utf-8"),
                    file_name=f"{safe_filename(product_name)}_compliance.txt",
                    mime="text/plain",
                    use_container_width=True,
                )
        with st.expander("Extracted product facts"):
            st.json(st.session_state.get("product_facts", {}))

    current_hash = script_hash(st.session_state.script_editor)
    compliance_hash = st.session_state.get("compliance_script_hash")
    audio_hash = st.session_state.get("audio_script_hash")
    current_pass = rating == "PASS" and compliance_hash == current_hash

    if rating == "PASS" and compliance_hash != current_hash:
        st.warning("⚠️ The script was edited after the green check. Click **Recheck Edited Script** before generating audio.")

    st.divider()
    render_step(3, "Generate clean ElevenLabs audio")
    voice_left, voice_right = st.columns([0.78, 1.22], gap="large")
    with voice_left:
        render_voice_card(selected_voice_name)
    with voice_right:
        if audio_hash and audio_hash != current_hash:
            st.info("The script changed after the audio was created. Recheck compliance and regenerate the voiceover for the new script.")
        st.caption("The button only activates when the exact current script has a green compliance result.")
        generate_voice = st.button(
            "Generate Clean Voiceover",
            type="primary",
            use_container_width=True,
            disabled=not (current_pass and selected_voice_id and ELEVENLABS_API_KEY),
        )

    if generate_voice:
        try:
            status = st.status("Generating voiceover…", expanded=True)
            status.write(f"Generating {selected_voice_name} in ElevenLabs with its saved preset…")
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
    st.divider()
    render_step(4, "Finished audio")
    meta = st.session_state.get("audio_meta", {})
    if meta.get("warning"):
        st.warning(meta["warning"])
    m1, m2, m3 = st.columns(3)
    m1.metric("Before cleanup", f'{meta.get("before_seconds", 0):.1f}s')
    m2.metric("Final length", f'{meta.get("after_seconds", 0):.1f}s')
    m3.metric("Silence removed", f'{meta.get("seconds_removed", 0):.1f}s')
    st.caption(f'Silence processing: {meta.get("source", "—")}')

    st.audio(st.session_state.clean_audio, format="audio/mp3")
    name = safe_filename(product_name)
    d1, d2 = st.columns(2)
    d1.download_button(
        "Download Clean MP3",
        data=st.session_state.clean_audio,
        file_name=f"{name}_clean.mp3",
        mime="audio/mpeg",
        use_container_width=True,
    )
    d2.download_button(
        "Download Raw ElevenLabs MP3",
        data=st.session_state.raw_audio,
        file_name=f"{name}_raw.mp3",
        mime="audio/mpeg",
        use_container_width=True,
    )
