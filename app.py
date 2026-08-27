from __future__ import annotations

import hashlib
import hmac
import os
import re
from pathlib import Path

import streamlit as st

from services.compliance import audit_script
from services.elevenlabs import ElevenLabsError, list_voices, synthesize
from services.llm import LLMError
from services.script_engine import extract_product_facts, generate_script
from services.silence import clean_audio

APP_DIR = Path(__file__).resolve().parent

st.set_page_config(
    page_title="AI Skeleton Voiceover",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
:root { --card: rgba(255,255,255,.055); --line: rgba(255,255,255,.09); }
.block-container { max-width: 1180px; padding-top: 2rem; padding-bottom: 4rem; }
[data-testid="stAppViewContainer"] { background: radial-gradient(circle at 15% 0%, #18202b 0, #0a0c10 38%, #06070a 100%); }
[data-testid="stHeader"] { background: transparent; }
.hero { padding: 1.2rem 0 1.5rem 0; }
.hero h1 { font-size: 2.35rem; letter-spacing: -0.04em; margin: 0; }
.hero p { color: #9fa6b2; font-size: 1.02rem; margin-top: .5rem; }
.glass { background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 18px 20px; backdrop-filter: blur(18px); }
.status-pass { border-left: 4px solid #42d392; }
.status-warn { border-left: 4px solid #f5c451; }
.status-risk { border-left: 4px solid #ff5c70; }
.small-muted { color:#8d94a0; font-size:.9rem; }
.stButton > button { border-radius: 12px; min-height: 44px; font-weight: 650; }
.stDownloadButton > button { border-radius: 12px; min-height: 44px; font-weight: 650; }
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

    st.markdown('<div class="hero"><h1>AI Skeleton Voiceover</h1><p>Private creator tool</p></div>', unsafe_allow_html=True)
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


require_login()

OPENAI_API_KEY = secret("OPENAI_API_KEY")
ELEVENLABS_API_KEY = secret("ELEVENLABS_API_KEY")
HF_TOKEN = secret("HF_TOKEN")
SCRIPT_MODEL = secret("OPENAI_MODEL_SCRIPT", "gpt-5.4-mini")
COMPLIANCE_MODEL = secret("OPENAI_MODEL_COMPLIANCE", "gpt-5.4-mini")
ELEVEN_MODEL = secret("ELEVENLABS_MODEL", "eleven_multilingual_v2")

st.markdown(
    '<div class="hero"><h1>AI Skeleton Voiceover Generator</h1>'
    '<p>Product details → Script DNA → TikTok compliance → ElevenLabs → cleaned voiceover.</p></div>',
    unsafe_allow_html=True,
)

if not OPENAI_API_KEY or not ELEVENLABS_API_KEY:
    missing = []
    if not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    if not ELEVENLABS_API_KEY:
        missing.append("ELEVENLABS_API_KEY")
    st.error("Missing server secrets: " + ", ".join(missing) + ". Add them before using the app.")

left, right = st.columns([1.15, 0.85], gap="large")

with left:
    st.subheader("Product")
    product_name = st.text_input("Product name", placeholder="e.g. Goli SuperFruits Beauty Gummies")
    product_details = st.text_area(
        "Product details",
        height=260,
        placeholder="Paste the listing details, ingredients/features, benefits, directions, disclaimers, offer details, etc.",
    )
    architecture_choice = st.selectbox(
        "Script style",
        ["Auto Detect", "Symptom Stack (Arch A)", "Day-by-Day Journey (Arch C)"],
        help="Auto uses Arch A by default and switches to Arch C when the request clearly calls for a timeline format.",
    )
    with st.expander("Optional viral transcript"):
        viral_transcript = st.text_area(
            "Viral transcript",
            height=180,
            placeholder="Paste a reference transcript if you want Script DNA to absorb its hook energy or structure.",
            label_visibility="collapsed",
        )

    with st.expander("Optional compliance context"):
        on_screen_text = st.text_area("On-screen text", height=100, placeholder="Any captions or text overlays")
        visual_cues = st.text_area("Visual cues", height=100, placeholder="Avatar actions, product demo, before/after visuals, etc.")

    generate_clicked = st.button(
        "Generate + Check Compliance",
        type="primary",
        use_container_width=True,
        disabled=not (OPENAI_API_KEY and product_name.strip() and product_details.strip()),
    )

with right:
    st.subheader("Voice")
    if ELEVENLABS_API_KEY and "voices" not in st.session_state:
        try:
            with st.spinner("Loading ElevenLabs voices…"):
                st.session_state.voices = list_voices(ELEVENLABS_API_KEY)
        except ElevenLabsError as exc:
            st.session_state.voices = []
            st.warning(str(exc))

    voices = st.session_state.get("voices", [])
    voice_labels = [f'{v["name"]}  ·  {v["id"][-6:]}' for v in voices]
    selected_label = st.selectbox(
        "ElevenLabs voice",
        voice_labels if voice_labels else ["No voices loaded"],
        disabled=not bool(voice_labels),
    )
    selected_voice_id = ""
    if voice_labels and selected_label in voice_labels:
        selected_voice_id = voices[voice_labels.index(selected_label)]["id"]

    with st.expander("Voice & silence settings"):
        voice_speed = st.slider("Voice speed", 0.70, 1.20, 1.00, 0.05)
        stability = st.slider("Stability", 0.0, 1.0, 0.50, 0.05)
        similarity = st.slider("Similarity", 0.0, 1.0, 0.75, 0.05)
        keep_silence = st.slider("Keep silence around cuts (seconds)", 0.00, 0.30, 0.05, 0.01)
        use_hf = st.checkbox("Use NeuralFalcon Hugging Face silence remover", value=True)

    st.caption("Only scripts with a 🟢 PASS can be sent to ElevenLabs.")

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
    st.subheader("Final script")
    verification = st.session_state.get("script_verification", {})
    if verification:
        c1, c2, c3 = st.columns(3)
        c1.metric("Words", verification.get("word_count", "—"))
        c2.metric("Architecture", verification.get("architecture", "—"))
        c3.metric("DNA check", "PASS" if verification.get("pass") else "Needs attention")

    st.text_area(
        "Edit script before voiceover",
        key="script_editor",
        height=300,
        help="If you change anything, re-run compliance. Audio generation is locked until the current text has passed.",
    )

    recheck = st.button("Recheck Compliance", use_container_width=True)
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

    rating = st.session_state.get("compliance_rating", "UNKNOWN")
    report = st.session_state.get("compliance_report", "")
    if rating == "PASS":
        st.success("🟢 PASS — ready for voiceover")
    elif rating == "NEEDS REVISION":
        st.warning("🟡 NEEDS REVISION — edit the script using the suggested fixes, then recheck")
    elif rating == "HIGH RISK":
        st.error("🔴 HIGH RISK — voiceover generation is blocked until the script passes")
    else:
        st.warning("Compliance rating could not be parsed. Review the report and recheck before generating audio.")

    with st.expander("Compliance report", expanded=rating != "PASS"):
        st.markdown(report or "No compliance report available.")
        if report:
            st.download_button(
                "Download compliance report",
                data=report.encode("utf-8"),
                file_name=f"{safe_filename(product_name)}_compliance.txt",
                mime="text/plain",
            )

    with st.expander("Extracted product facts"):
        st.json(st.session_state.get("product_facts", {}))

    current_hash = script_hash(st.session_state.script_editor)
    compliance_hash = st.session_state.get("compliance_script_hash")
    audio_hash = st.session_state.get("audio_script_hash")
    current_pass = rating == "PASS" and compliance_hash == current_hash

    if rating == "PASS" and compliance_hash != current_hash:
        st.warning("The script has been edited since its green compliance check. Click Recheck Compliance before generating audio.")

    st.subheader("Voiceover")
    if audio_hash and audio_hash != current_hash:
        st.info("The script changed after the audio was created. Recheck compliance and regenerate the voiceover for the new script.")

    generate_voice = st.button(
        "Generate Clean Voiceover",
        type="primary",
        use_container_width=True,
        disabled=not (current_pass and selected_voice_id and ELEVENLABS_API_KEY),
    )

    if generate_voice:
        try:
            status = st.status("Generating voiceover…", expanded=True)
            status.write("Sending the compliance-approved script to ElevenLabs…")
            raw = synthesize(
                ELEVENLABS_API_KEY,
                selected_voice_id,
                st.session_state.script_editor,
                model_id=ELEVEN_MODEL,
                stability=stability,
                similarity_boost=similarity,
                speed=voice_speed,
            )
            status.write("Removing silence…")
            cleaned, meta = clean_audio(
                raw,
                keep_seconds=keep_silence,
                hf_token=HF_TOKEN or None,
                use_huggingface=use_hf,
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
    st.subheader("Finished audio")
    meta = st.session_state.get("audio_meta", {})
    if meta.get("warning"):
        st.warning(meta["warning"])
    m1, m2, m3 = st.columns(3)
    m1.metric("Before", f'{meta.get("before_seconds", 0):.1f}s')
    m2.metric("After", f'{meta.get("after_seconds", 0):.1f}s')
    m3.metric("Removed", f'{meta.get("seconds_removed", 0):.1f}s')
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
