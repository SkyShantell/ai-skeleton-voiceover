---
name: tiktok-script-dna
description: >
  Generates TikTok Shop affiliate voiceover scripts using the "Script DNA" framework.
  Two architectures: Arch A (Symptom Stack, ~66s, 195-210 words) for standard product
  scripts, and Arch C (Day-by-Day Journey, ~84s, 240-270 words) for timeline-based
  transformation scripts. Outputs plain prose script text only — no timestamps, no beat
  labels, no formatting. Fully compliant with TikTok Shop content policies. Trigger on:
  "write a script for [product]", "TikTok script", "affiliate script", "skeleton script",
  "Script DNA", "day-by-day script", "60 day script", "30 day script", or any time the
  user provides a TikTok Shop product and wants a spoken voiceover script. Also trigger
  when the user provides product images, descriptions, or links and asks for a script.
  Always use this skill — don't write TikTok Shop scripts without it.
---

# TikTok Script DNA — Voiceover Script Generator

## What This Skill Does

Takes a product (name, key ingredients/features, benefits) and outputs a single block of
plain voiceover script text. No timestamps. No beat labels. No markdown formatting. Just
the script as one continuous paragraph the user can copy directly into TTS or hand to a
voice actor.

If the user also provides a **viral transcript**, absorb its strongest structural elements
(hook energy, unique beats, emotional angles) into the standard architecture.

---

## Architecture Selection

### ARCH A — Symptom Stack (default)
**Use when:** The user sends a product and asks for a script without specifying a format.
**Target:** 195–210 words | ~66 seconds at 3.0 w/s

### ARCH C — Day-by-Day Journey
**Use when:** The user says "day-by-day", "60 day", "30 day", "what would happen if",
"journey script", or references the timeline format.
**Target:** 240–260 words preferred; up to 270 is acceptable when the timeline needs it | ~80–90 seconds at 3.0 w/s

---

## ARCH A — Symptom Stack (15 Beats)

All beats flow as natural prose. No labels visible in output.

```
1. HOOK — "If your [visual symptom]..." (2-3 seconds)
2-4. SYMPTOM STACK — 3 more escalating problems, "and" chained. NEVER TRIM.
5. PIVOT — Under 10 words. Reframes blame.
6. REFRAME — Names the real cause. Redirects from viewer's assumed blame.
7. OBJECTION PRE-EMPT — "And no, [thing they tried] is not going to fix that."
8. THESIS — "You need [simple solution framing]."
9-11. INGREDIENT-BENEFIT ×3 — Always ingredient FIRST, benefit second. Always hedged.
12. VILLAIN — Attack the alternative, never the viewer. First-person "I" enters here.
13. SOLUTION REVEAL — Social proof + brand. "Combined all of that into [format]."
14. DIFFERENTIATOR — One surprise fact or friction reducer.
15. CREDENTIALS — Discount / free shipping / trust signals.
16. CALLBACK — Mirror the hook, flip pain → resolution.
17. SOFT CTA — "I recommend trying this/these. Tap the orange cart down below."
```

### Arch A Pacing Rules
- Total: 195–210 words
- ~66 seconds at 3.0 w/s
- Differentiator deliberately slowed in delivery
- Pivot under 10 words

---

## ARCH C — Day-by-Day Journey

```
1. CURIOSITY HOOK — "What would actually happen to your [area] if you [used/took]
   the viral [product type] for [timeframe] straight?"
2. DAY ONE — Nothing happens / skepticism / first sensory detail
3. WEEK ONE OR WEEK TWO — Subtle early shifts, heavily hedged with "may"
4. DAY THIRTY — Noticeable improvements, still hedged
5. DAY SIXTY (or endpoint) — Strongest payoff, still hedged, "this is usually where people start..."
6. VILLAIN PIVOT — "But here's where most people go wrong..."
7. SOLUTION REVEAL — Brand + what makes it different
8. CREDENTIALS — Clean formula callouts / discount / free shipping
9. CALLBACK CTA — "So if you're tired of [hook pain], I'd try it before it sells out.
   Tap the orange cart down below."
```

### Arch C Pacing Rules
- Preferred: 240–260 words; acceptable ceiling: 270
- ~80–90 seconds at 3.0 w/s
- Each day section gets progressively more confident
- All improvements hedged: "may start," "might not," "may look"

### Arch C Timeline Selection
- **14 days** — lymphatic, drainage, bloating products
- **30 days** — products named "30 Days" / single month supply / skincare systems
- **60 days** — supplements with 60-count supply / products needing longer timelines
- Match the timeline to the product's actual supply duration or brand positioning

---

## Voice & Tone Rules (Both Architectures)

- **Register:** Concerned friend explaining something over lunch
- **POV:** Second-person ("your," "you") throughout. First-person ("I") ONLY at
  villain beat and CTA
- **Energy:** Moderate — not hype, not ASMR
- **"I recommend"** — never "you need to buy" or "go buy this"
- **CTA:** Always "Tap the orange cart down below" — NEVER "links down below,"
  NEVER "link in bio"

---

## Compliance Rules (Hard)

### NEVER use:
- Coupon codes / promo codes / discount codes — NEVER
- "Link in bio" or "links down below" — always "tap the orange cart down below"
- Disease names: "diabetes," "cancer," "arthritis," "gingivitis," "eczema," "PCOS"
- Treatment claims: "cures," "treats," "heals," "prevents"
- Weight loss language: "lose weight," "burn fat," "slimming," "appetite suppression,"
  "diet pill," "reducing body fat," "feel full for longer," "appetite control"
- Body-shaming before/after framing
- Hype adjectives: "insane," "obsessed," "game-changer," "literally shaking," "miracle"
- Unverifiable superlatives: "#1 selling," "best product," "most effective"
  (UNLESS the product listing itself makes this claim with documentation)
- Profanity (TikTok Shop suppresses it)
- "Anti-inflammatory" in a disease context
- "Anxiety" / "depression" as medical conditions
- "Clinically proven" without documentation
- "Detox" in a weight-loss context
- "GLP-1" or any variation
- "Blood sugar" (use "energy levels" instead)

### ALWAYS use:
- Hedged benefit language: "to help," "can help," "may help," "to help support"
- Structure/function claims only
- Symptom descriptions instead of disease names
- "Tap the orange cart down below" for CTA

### Allowed (not flagged):
- Hormones, estrogen, progesterone, cortisol (structure/function)
- PMS, cycle, period (wellness language)
- "Bloating," "puffiness," "water retention" (unless tied to weight loss)
- DHT, follicles, scalp health (hair care context)
- Ingredient names and their functions
- Cellulite descriptions ("cottage cheese texture," "dimpled skin")
- "Metabolic function" / "metabolism" (structure/function, not weight loss)

---

## How to Build a Script

### STEP 1 — Extract Product DNA
From the product name, description, images, and/or ingredients, identify:
1. **Category** — supplement, skincare, haircare, oral care, body care, etc.
2. **Top 3 ingredients** — strongest benefit stories
3. **Key differentiator** — what makes THIS product different
4. **Format** — gummies, capsules, powder, serum, spray, stick, drops, cream, etc.
5. **Trust signals** — units sold, trending status, brand heritage, awards, clinical data
6. **Sensory detail** — flavor, texture, scent, application feel

### STEP 2 — Build the Symptom Stack (Arch A) or Timeline (Arch C)

**For Arch A:** Write 3-4 symptoms that are visual, physical, escalating, and
second-person. The stack IS the hook. NEVER trim it.

**For Arch C:** Map realistic improvements across the timeline. Day 1 must include the actual first-use action, a supplied sensory/use detail when available, no visible/immediate change, skepticism, then the formula setup. Use Week 1 or Week 2 for the first subtle shift. Day 30 is the “shift/click” beat. Day 60/endpoint is the strongest payoff but remains hedged. Each milestone must progress instead of repeating the same benefit. All efficacy claims remain grounded and hedged with “may,” “might,” or equivalent.

### STEP 3 — Map Ingredients to Benefits
Pick exactly 3 ingredient-benefit pairs:
- Ingredient FIRST, benefit second
- Each benefit ties back to a symptom or concern
- All benefits hedged: "to help," "to help support," "can help"

### STEP 4 — Write the Full Script
Write all beats as one continuous flowing paragraph. No labels, no timestamps.
The beats are invisible — it reads like natural speech.

### STEP 5 — Verify (mandatory, run silently)

```python
script = """[full script text]"""
wc = len(script.split())

# Arch A: 195-210 | Arch C: 240-270 (240-260 preferred)
target_min, target_max = (195, 210)  # or (240, 270) for Arch C
assert target_min <= wc <= target_max, f"ADJUST: {wc} words (need {target_min}-{target_max})"

banned = ["code","cure","treat","heal","prevent","lose weight","fat burn",
          "link in bio","insane","obsessed","game-changer","miracle",
          "killer","treatment","breakout","slimming","diet pill",
          "links down below","appetite suppress","appetite control"]
lower = script.lower()
for b in banned:
    assert b not in lower, f"BANNED: '{b}'"

assert "tap the orange cart" in lower, "Missing CTA"
print(f"✅ PASS — {wc} words, {wc/66.0:.2f} w/s")
```

**If over target:** trim reframe, villain, or credentials (in that order). NEVER trim
the symptom stack or ingredient-benefit pairs.
**If under target:** expand reframe or add sensory detail to differentiator.
**If banned word found:** replace with compliant alternative.

Note: "healthier" will substring-match "heal" — this is a false positive and is fine.

---

## Hook Variation

When the user asks for "different hooks," "embarrassment hooks," "new pain points,"
or "insecurity hooks," swap ONLY beats 1-4 (hook + symptom stack) while keeping
beats 5-17 identical.

| Angle | Example Symptoms |
|---|---|
| Embarrassment | "you angle your head in photos," "you avoid bright lighting" |
| Daily frustration | "you can't get through a task," "you read the same page three times" |
| Social comparison | "everyone around you is running circles while you're stuck" |
| Self-consciousness | "people keep asking if you're tired," "makeup won't sit right" |
| Physical discomfort | "you're tossing and turning," "muscles cramp for no reason" |
| Avoidance behavior | "you pick outfits based on what hides your skin," "you dread pool days" |

---

## Absorbing Viral Transcripts

When the user provides a viral transcript alongside the product:
1. Identify the transcript's hook formula and unique beats
2. Extract absorbable elements (specific lines, structural innovations)
3. Flag any policy violations in the original
4. Rebuild as a full Arch A or Arch C script with viral elements woven into
   the appropriate beats
5. NEVER simply adapt the viral transcript's short format — always rebuild as
   a full skeleton script

---

## Bundle / Multi-Step System Scripts

When the product is a bundle or multi-step system:
- The ingredient-benefit stack becomes a STEP stack ("step one... step two...")
- The villain becomes "buying random products from different brands"
- The differentiator is "designed as one system"
- Word count may run 5-10 words over standard Arch A target — acceptable for systems

---

## Output Format

**Always output ONLY the plain script text as one continuous block.** No headers, no
beat labels, no timestamps, no word count, no compliance notes, no markdown.

Run verification silently. Only surface details if the script fails and needs adjustment.

---

## Product Category Quick Reference

| Category | Symptom Stack Focus | Watch Out For |
|---|---|---|
| Supplements (gummies/capsules) | Energy, mood, sleep, recovery | No disease claims, no weight loss |
| Skincare (serums/creams) | Dullness, fine lines, firmness, pores | No "treats acne," no "anti-aging cure" |
| Haircare (shampoo/spray) | Thinning, shedding, scalp, volume | DHT is fine, no "hair loss cure" |
| Oral care (mouthwash/toothpaste) | Bad breath, sensitivity, staining | No disease names like "gingivitis" |
| Body care (wash/oil/cream) | Bumps, texture, dark spots, irritation | No "treats acne," use "supports clearer-looking skin" |
| Wellness drinks (powder/mix) | Energy crashes, dehydration, sluggishness | No weight loss, no "appetite suppression" |
| Tools/devices (nasal stick/mask) | Breathing, congestion, pores, lifting | No medical device claims |
| Hair removal (oil/cream) | Stubble, razor bumps, ingrowns, strawberry skin | No permanent removal claims |
