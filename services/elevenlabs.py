from __future__ import annotations

from typing import Any

import requests

BASE_URL = "https://api.elevenlabs.io"


class ElevenLabsError(RuntimeError):
    pass


def list_voices(api_key: str) -> list[dict[str, str]]:
    if not api_key:
        raise ElevenLabsError("ELEVENLABS_API_KEY is missing.")
    headers = {"xi-api-key": api_key}
    params: dict[str, Any] = {"page_size": 100, "sort": "name", "sort_direction": "asc"}
    voices: list[dict[str, str]] = []

    while True:
        response = requests.get(f"{BASE_URL}/v2/voices", headers=headers, params=params, timeout=30)
        if response.status_code != 200:
            raise ElevenLabsError(f"Voice list failed ({response.status_code}): {response.text[:300]}")
        data = response.json()
        for voice in data.get("voices", []):
            vid = voice.get("voice_id")
            name = voice.get("name") or "Unnamed voice"
            if vid:
                voices.append({"id": vid, "name": name})
        if not data.get("has_more") or not data.get("next_page_token"):
            break
        params["next_page_token"] = data["next_page_token"]

    # Deduplicate by ID while preserving the API order.
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for voice in voices:
        if voice["id"] not in seen:
            seen.add(voice["id"])
            unique.append(voice)
    return unique


def synthesize(
    api_key: str,
    voice_id: str,
    text: str,
    model_id: str = "eleven_multilingual_v2",
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0.0,
    speed: float = 1.0,
    use_speaker_boost: bool = True,
) -> bytes:
    if not api_key:
        raise ElevenLabsError("ELEVENLABS_API_KEY is missing.")
    if not voice_id:
        raise ElevenLabsError("Select an ElevenLabs voice first.")
    if not text.strip():
        raise ElevenLabsError("The script is empty.")

    url = f"{BASE_URL}/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    params = {"output_format": "mp3_44100_128"}
    body = {
        "text": text.strip(),
        "model_id": model_id,
        "voice_settings": {
            "stability": float(stability),
            "similarity_boost": float(similarity_boost),
            "style": float(style),
            "speed": float(speed),
            "use_speaker_boost": bool(use_speaker_boost),
        },
    }
    response = requests.post(url, headers=headers, params=params, json=body, timeout=180)
    if response.status_code != 200:
        raise ElevenLabsError(f"TTS failed ({response.status_code}): {response.text[:500]}")
    return response.content
