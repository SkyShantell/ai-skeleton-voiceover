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

Model configuration:

All OpenAI stages are fixed to **GPT-5.6 Sol** in this build: product fact extraction, selected-photo reading, Script DNA writing/repair, and compliance auditing. The old `OPENAI_MODEL_SCRIPT`, `OPENAI_MODEL_COMPLIANCE`, and `OPENAI_MODEL_IMAGE` secrets are ignored, so an older Streamlit secret cannot accidentally keep one stage on a mini model.

```toml
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


## TikTok Shop product photo selection
After **Fetch Product**, the app shows up to **12** TikTok Shop listing photos directly on the page. **None are selected by default.** The VA checks only the photos they want GPT-5.6 Sol to read. On **Generate Script + Run Compliance**, those selected photos are analyzed for visible benefits, ingredients, usage directions, differentiators, warnings, and other labeled product facts. Price, stock, coupons, testimonials, and inferred before/after effects are excluded.

## Script style lock

ARCH A generation includes a canonical sample-style lock based on the supplied Skeleton sample scripts. It enforces the long four-problem opening stack, direct `Because...` reframe, `And no,...` objection, three distinct benefit beats, `But don't...` villain, decisive brand/product reveal, concrete differentiators, and a short callback CTA. Vague meta phrases such as `the listing shows strong trust signals`, `I also like that`, and `One thing I noticed` are rejected and automatically rewritten before compliance runs.

TikTok rating/review-count/sold-count metadata is kept out of Script DNA grounding so the model does not turn marketplace metadata into vague selling copy. Product images and seller-provided product text remain available as grounded sources.

## Arch C sample-style lock

Arch C generation now follows the supplied canonical day-by-day samples: `What would actually happen...` hook, a real Day 1 use/sensory + skepticism beat, Week 1/2 subtle milestone, Day 30 shift/click, Day 60/endpoint payoff, `But here's where/what most people go/get wrong` villain pivot, decisive product reveal, then a short callback + orange-cart CTA. The preferred length remains 240-260 words, with up to 270 accepted when the timeline needs the extra room. Unsupported price, stock, discount, free-shipping, scarcity, and marketplace-meta claims are not added just to mimic the samples.

## Canonical sample scripts + regeneration

The writer now receives the user's real **Arch A** and **Arch C** scripts directly as few-shot style references via `prompts/canonical_arch_a_examples.md` and `prompts/canonical_arch_c_examples.md`. They are used for cadence, compression, transitions, and beat shape only; product facts/offers from the examples are never treated as facts for the current product.

After a script is generated, **Regenerate Script** writes a materially fresh take from the same loaded product and currently selected photos without spending another SociaVault credit. The prior draft is sent as an explicit “do not copy” reference so the rerun changes the angle/wording rather than merely paraphrasing sentence-by-sentence. The new script is automatically sent through compliance again.

## Selective compliance rewrites

When the compliance auditor returns one or more `Original -> Compliant Rewrite` fixes, the app now displays each fix separately with its own checkbox under **Choose which compliance fixes to apply**. Nothing is applied automatically.

The VA can select only the fixes they agree with and click **Apply Selected Fixes + Recheck**. The app applies only those selected changes, automatically runs compliance again on the exact revised script, clears any old manual override/audio approval, and keeps ElevenLabs locked until the revised script passes or is manually approved.

The auditor prompt also requires atomic rewrite pairs so unrelated changes are not bundled into one checkbox.

## Stronger creator-style writing + regeneration angles

The Script DNA writer still uses GPT-5.6 Sol and the user's canonical Arch A / Arch C sample scripts, but the prompt now explicitly prioritizes creator sales cadence over checklist-like label recitation. The verified product-fact JSON is treated as the sole **Verified Claim Bank**. Marketplace metadata such as official-shop status, ratings, sold/review counts, seller metrics, prices, stock, coupons, and shipping offers is excluded from Script DNA grounding.

For products dominated by one hero ingredient/form, the writer is specifically told not to repeat the same ingredient at the start of three consecutive benefit lines. It instead varies the middle around the documented hero differentiator, strongest supported benefit, second supported benefit, and/or practical formulation advantage.

The **Regenerate Script** control now includes an angle selector:

- Fresh take
- More relatable / emotional
- More aggressive hook
- More educational
- Different pain points
- Different villain / objection

Regeneration still reuses the already fetched product and selected photos, so it does not spend another SociaVault credit.

## Compact tabbed workbench

The post-generation workspace is now split into four tabs: **Script**, **Compliance**, **Save**, and **Voiceover**. This keeps the page short and prevents the compliance audit from creating a long wall of text.

The Compliance tab shows only the current rating, the auditor's short final verdict, and a compact selectable rewrite table. The full compliance report is collapsed under **Full auditor report** and only needs to be opened when deeper review is necessary. Manual override is also collapsed by default.

TikTok Shop product photos are now kept inside a collapsed **Choose product photos** section so the main setup screen stays compact while still allowing manual photo selection.

## Balanced compliance mode
The compliance auditor is intentionally a guardrail rather than a second scriptwriter. It now receives the same verified product claim bank used by the writer. Normal grounded structure/function language (for example, "helps support focus" or "may support sleep quality") should not be stripped merely for being health-adjacent. Only clear policy blockers create required rewrite pairs; lower-confidence concerns remain advisory and do not block a PASS.
