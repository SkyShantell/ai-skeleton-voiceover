# AI Skeleton Voiceover Generator

A private Streamlit app for a VA to turn TikTok Shop product information into a Script DNA voiceover, run a TikTok Shop compliance audit, save/recall scripts, generate ElevenLabs TTS, remove silence, and download a clean MP3.

## Daily VA workflow

1. Paste **Product Name** + **Product Details**.
2. Generate the Script DNA voiceover.
3. Review the compliance result.
4. If green, continue. If a known false positive appears, edit/recheck or use **Manual compliance override** after reviewing it.
5. Save the script to the **Saved Script Library** if you want to recall it later.
6. Generate ElevenLabs audio.
7. Silence removal runs automatically with a default keep-silence value of **0.03 seconds**.
8. Play/download the cleaned MP3.

## Important compliance behavior

The compliance auditor now explicitly treats native TikTok Shop orange-cart CTAs as compliant. Phrases such as:

- `Tap the orange cart down below`
- `Tap the orange cart`
- `Check the orange cart`

must **not** be flagged as off-platform directing. External destinations such as `link in bio`, websites, phone numbers, email, DMs, or external checkout remain flagged.

### Manual compliance override

If the auditor still produces a false positive, open **Manual compliance override**, choose the reason, confirm that you reviewed the report, and click **Approve This Script for Voiceover**.

The override is intentionally tied to the exact script text. If even one word changes, the override stops working until the new script is rechecked or manually approved again.

## Saved Script Library

The app now has a searchable Saved Script Library. A saved item keeps:

- saved script name
- product name/details
- final script text
- Script DNA verification data
- compliance rating/report when current
- voice choice and voice settings
- silence-removal setting
- optional viral transcript / on-screen text / visual cues

You can **Load**, **Update**, **Save as New Copy**, and **Delete** saved scripts.

### Permanent storage on Streamlit Cloud — recommended

Streamlit's local filesystem can be reset during app reboot/redeploy, so local saves are not guaranteed to be permanent.

For permanent storage, I recommend a **separate private GitHub repository** such as `ai-skeleton-script-library`. Keeping the library separate prevents every script save from creating a commit in the Streamlit app repository and potentially triggering an unnecessary app redeploy:

1. Create a fine-grained GitHub token.
2. Give it access **only** to the private script-library repository.
3. Permission: **Contents → Read and write**.
4. Put the following in **Streamlit → App settings → Secrets**:

```toml
SCRIPT_LIBRARY_GITHUB_TOKEN = "github_pat_YOUR_TOKEN"
SCRIPT_LIBRARY_GITHUB_REPO = "YOUR_GITHUB_USERNAME/ai-skeleton-script-library"
SCRIPT_LIBRARY_GITHUB_PATH = "data/saved_scripts.json"
```

Do **not** put the real token in README, app.py, or any GitHub file.

When these secrets are present, the app saves the library into `data/saved_scripts.json` through the GitHub API. Without them, the library still works using local app storage, but the site clearly warns that those saves may disappear after a redeploy.

## Files

- `app.py` — Streamlit UI, saved-script library controls, compliance override, workflow state
- `prompts/script_dna.md` — uploaded Script DNA skill
- `prompts/compliance_auditor.md` — TikTok compliance mega prompt + native orange-cart exception
- `prompts/product_fact_extractor.md` — strict fact-only input normalization
- `services/script_engine.py` — Script DNA generation + mechanical verification
- `services/compliance.py` — compliance audit + PASS/YELLOW/RED parser
- `services/elevenlabs.py` — text-to-speech
- `services/silence.py` — Hugging Face silence remover + local fallback
- `services/script_library.py` — local/GitHub persistent saved-script storage
- `data/saved_scripts.json` — empty starter library / GitHub-backed library file
- `packages.txt` — installs ffmpeg for audio processing

## Deploy with Streamlit Community Cloud

1. Upload the app files to your private GitHub repository.
2. Create/redeploy the Streamlit app with `app.py` as the main file.
3. In **App settings → Secrets**, add your real API keys.
4. Optional: add the GitHub library secrets above for permanent script saves.
5. Reboot/redeploy.

## Required secrets

```toml
OPENAI_API_KEY = "sk-..."
ELEVENLABS_API_KEY = "..."
```

Recommended:

```toml
APP_PASSWORD = "team-password"
HF_TOKEN = "hf_..."
```

Optional model overrides:

```toml
OPENAI_MODEL_SCRIPT = "gpt-5.4-mini"
OPENAI_MODEL_COMPLIANCE = "gpt-5.4-mini"
ELEVENLABS_MODEL = "eleven_multilingual_v2"
```

## ElevenLabs voice presets

- **Julie US — Confident & Conversational** — `5WTtMD3P8AHUXTVqCYcJ`  
  Speed `1.13` · Stability `66%` · Similarity `100%` · Style `26%` · Speaker boost `On`
- **Mark US — ConvoAI** — `1SM7GgM6IMuvQlz2BwM3`  
  Speed `1.14` · Stability `50%` · Similarity `75%` · Style `0%` · Speaker boost `On`
- **Lucy UK — Fresh & Casual** — `lcMyyd2HUfFzxdCaC4Ta`  
  Speed `1.15` · Stability `50%` · Similarity `75%` · Style `0%` · Speaker boost `On`
- **Toby UK — Raspy, Youthful & Articulate** — `pYDLV125o4CgqP8i49Lg`  
  Speed `1.16` · Stability `100%` · Similarity `100%` · Style `56%` · Speaker boost `On`

## Button/UI fix

All primary, secondary, download, hover, and disabled button states now use explicit high-contrast backgrounds and text colors. This prevents the white-button/white-text problem caused by Streamlit theme overrides.

## Python 3.13 / 3.14 compatibility

`audioop-lts` remains included for Python 3.13+ because the standard-library `audioop` module was removed. The pydub local silence-removal fallback therefore remains compatible with current Streamlit Cloud runtimes.
