# AI Skeleton Voiceover Generator

A private Streamlit app for a VA to turn pasted TikTok Shop product information into a Script DNA voiceover, run the exact compliance audit, generate ElevenLabs TTS, remove silence with NeuralFalcon's Hugging Face Space, and download a clean MP3.

## Workflow

1. VA pastes **Product Name** + **Product Details**.
2. App extracts only the facts supported by the pasted listing.
3. The supplied **TikTok Script DNA** skill generates the voiceover.
4. Script DNA's mechanical checks run (architecture word count, banned terms, orange-cart CTA).
5. The supplied **TikTok Shop Compliance Auditor** mega prompt audits the finished script plus optional on-screen text / visual cues.
6. If the rating is yellow or red, production stops. The VA edits the script using the report and clicks **Recheck Compliance**.
7. Only a green PASS unlocks **Generate Clean Voiceover**.
8. ElevenLabs creates the raw MP3.
9. The app calls `NeuralFalcon/Remove-Silence-From-Audio`. If the public Space fails, the app automatically runs the same pydub-style silence logic locally.
10. The VA can play and download the cleaned MP3 (and optionally the raw MP3).

## Files

- `app.py` — Streamlit UI and workflow state
- `prompts/script_dna.md` — exact uploaded Script DNA skill
- `prompts/compliance_auditor.md` — exact compliance system prompt from the handoff
- `prompts/product_fact_extractor.md` — strict fact-only input normalization
- `services/script_engine.py` — Script DNA generation + its mandatory mechanical verification
- `services/compliance.py` — mega-prompt audit + PASS/YELLOW/RED parser
- `services/elevenlabs.py` — voice list + text-to-speech
- `services/silence.py` — Hugging Face silence remover + local fallback
- `packages.txt` — installs ffmpeg for audio processing

## Local setup (owner/testing)

```bash
cd ai-skeleton-voiceover
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install ffmpeg on macOS if needed:

```bash
brew install ffmpeg
```

Create `.streamlit/secrets.toml` by copying the example:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Put in your API keys, then run:

```bash
streamlit run app.py
```

## Deploy for your VA with Streamlit Community Cloud

1. Create a private GitHub repository and upload the contents of this folder.
2. Go to Streamlit Community Cloud and create a new app from that repo.
3. Set the main file to `app.py`.
4. In **App settings → Secrets**, paste the values from `.streamlit/secrets.toml.example` with your real keys.
5. Deploy.
6. Give the deployed URL and `APP_PASSWORD` to your VA.

`packages.txt` tells Streamlit Cloud to install ffmpeg automatically.

## Secrets

Required:

```toml
OPENAI_API_KEY = "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"
ELEVENLABS_API_KEY = "sk_422dc08ee2db7ded3d2ca8a7577246c3bce913143db602fe"
```

Recommended:

```toml
APP_PASSWORD = "1H@ppyVa"
HF_TOKEN = "hf_..."
```

Optional model overrides:

```toml
OPENAI_MODEL_SCRIPT = "gpt-5.4-mini"
OPENAI_MODEL_COMPLIANCE = "gpt-5.4-mini"
ELEVENLABS_MODEL = "eleven_multilingual_v2"
```

## Compliance behavior

The app intentionally does **not** auto-send yellow/red scripts to ElevenLabs. A flagged script must be edited and re-audited. This matches the supplied compliance handoff's halt-and-review routing.

The app also invalidates previously generated audio if the script changes, preventing an edited but unchecked script from being mistaken for the approved version.

## Hugging Face behavior

The primary silence-cleaning path uses the public Gradio Space:

`NeuralFalcon/Remove-Silence-From-Audio`

The app requests the Space's `process_audio` API with the generated MP3 and the configured keep-silence duration. It then converts the returned audio back to MP3. If the Space is unavailable or its endpoint changes, the local fallback uses the same core parameters: 100 ms minimum silence, -45 dB threshold, configured silence padding, and a dynamic threshold fallback for quiet recordings.
