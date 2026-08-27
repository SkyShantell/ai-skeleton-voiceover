from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path
from typing import Any

from pydub import AudioSegment
from pydub.silence import split_on_silence


class SilenceRemovalError(RuntimeError):
    pass


def _duration_seconds(audio_bytes: bytes, fmt: str = "mp3") -> float:
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=fmt)
    return len(audio) / 1000.0


def _to_mp3_bytes(path: str | Path) -> bytes:
    audio = AudioSegment.from_file(str(path))
    buf = io.BytesIO()
    audio.export(buf, format="mp3", bitrate="128k")
    return buf.getvalue()


def remove_silence_local(raw_mp3: bytes, keep_seconds: float = 0.05) -> bytes:
    source = AudioSegment.from_file(io.BytesIO(raw_mp3), format="mp3")
    keep_ms = max(0, int(float(keep_seconds) * 1000))
    chunks = split_on_silence(
        source,
        min_silence_len=100,
        silence_thresh=-45,
        keep_silence=keep_ms,
    )
    if not chunks:
        dynamic_thresh = source.dBFS - 16
        chunks = split_on_silence(
            source,
            min_silence_len=100,
            silence_thresh=dynamic_thresh,
            keep_silence=keep_ms,
        )
    combined = AudioSegment.empty()
    for chunk in chunks:
        combined += chunk
    if len(combined) == 0:
        combined = source

    out = io.BytesIO()
    combined.export(out, format="mp3", bitrate="128k")
    return out.getvalue()


def remove_silence_huggingface(
    raw_mp3: bytes,
    keep_seconds: float = 0.05,
    hf_token: str | None = None,
    space_id: str = "NeuralFalcon/Remove-Silence-From-Audio",
) -> bytes:
    from gradio_client import Client, handle_file

    with tempfile.TemporaryDirectory(prefix="skeleton_audio_") as tmp:
        in_path = Path(tmp) / "voiceover.mp3"
        in_path.write_bytes(raw_mp3)
        client = Client(space_id, token=hf_token or None, verbose=False)
        try:
            result: Any = client.predict(
                handle_file(str(in_path)),
                float(keep_seconds),
                api_name="/process_audio",
            )
        except Exception:
            # If the Space changes endpoint naming, try the first compatible endpoint.
            result = client.predict(handle_file(str(in_path)), float(keep_seconds))

        candidates: list[str] = []
        if isinstance(result, (tuple, list)):
            for item in result:
                if isinstance(item, str) and os.path.exists(item):
                    candidates.append(item)
                elif hasattr(item, "path") and os.path.exists(str(item.path)):
                    candidates.append(str(item.path))
        elif isinstance(result, str) and os.path.exists(result):
            candidates.append(result)
        elif hasattr(result, "path") and os.path.exists(str(result.path)):
            candidates.append(str(result.path))

        if not candidates:
            raise SilenceRemovalError("Hugging Face returned no downloadable audio file.")
        return _to_mp3_bytes(candidates[-1])


def clean_audio(
    raw_mp3: bytes,
    keep_seconds: float = 0.05,
    hf_token: str | None = None,
    use_huggingface: bool = True,
) -> tuple[bytes, dict[str, Any]]:
    before = _duration_seconds(raw_mp3, "mp3")
    source = "local"
    warning = ""

    if use_huggingface:
        try:
            cleaned = remove_silence_huggingface(raw_mp3, keep_seconds, hf_token)
            source = "Hugging Face / NeuralFalcon"
        except Exception as exc:
            cleaned = remove_silence_local(raw_mp3, keep_seconds)
            source = "local fallback"
            warning = f"Hugging Face failed, so local silence removal was used: {exc}"
    else:
        cleaned = remove_silence_local(raw_mp3, keep_seconds)
        source = "local"

    after = _duration_seconds(cleaned, "mp3")
    return cleaned, {
        "before_seconds": before,
        "after_seconds": after,
        "seconds_removed": max(0.0, before - after),
        "source": source,
        "warning": warning,
    }
