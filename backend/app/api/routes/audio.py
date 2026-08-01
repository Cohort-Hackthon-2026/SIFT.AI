from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

SUPPORTED_AUDIO_CONTENT_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/webm",
    "audio/ogg",
}


class TranscriptionSegment(BaseModel):
    start: float
    end: float
    text: str


class TranscriptionResponse(BaseModel):
    text: str
    language: str | None = None
    segments: list[TranscriptionSegment] = []


@lru_cache(maxsize=1)
def _load_model():
    """Lazily load (and cache) the Faster-Whisper model on first use.

    This intentionally happens on first request rather than at startup so
    the API can still boot (and health-check) in environments where the
    Whisper model weights haven't been downloaded/cached yet.
    """
    from faster_whisper import WhisperModel

    model_size = os.getenv("WHISPER_MODEL_SIZE", "base")
    device = os.getenv("WHISPER_DEVICE", "cpu")
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    return WhisperModel(model_size, device=device, compute_type=compute_type)


def _transcribe_sync(file_path: str, language: str | None) -> TranscriptionResponse:
    model = _load_model()
    segments_iter, info = model.transcribe(file_path, language=language, vad_filter=True)

    segments = [
        TranscriptionSegment(start=segment.start, end=segment.end, text=segment.text.strip())
        for segment in segments_iter
    ]
    full_text = " ".join(segment.text for segment in segments).strip()

    return TranscriptionResponse(
        text=full_text,
        language=getattr(info, "language", language),
        segments=segments,
    )


@router.post("/audio/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str | None = None,
) -> TranscriptionResponse:
    """Transcribe an uploaded audio clip with Faster-Whisper.

    Used as the fallback path for browsers without Web Speech API support
    (the frontend's MediaRecorder .wav payload lands here).
    """
    if file.content_type and file.content_type not in SUPPORTED_AUDIO_CONTENT_TYPES:
        logger.info(f"Unrecognized audio content-type '{file.content_type}', attempting transcription anyway")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty")

    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
        tmp_file.write(audio_bytes)
        tmp_path = tmp_file.name

    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _transcribe_sync, tmp_path, language)
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Audio transcription is unavailable: the `faster-whisper` package is not installed. "
                f"({exc})"
            ),
        ) from exc
    except Exception as exc:  # pragma: no cover - depends on model/runtime availability
        logger.error(f"Transcription failed: {exc}")
        raise HTTPException(status_code=502, detail=f"Transcription failed: {exc}") from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)
