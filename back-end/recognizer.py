"""Song recognition. Deliberately swappable.

A recognizer takes a short audio clip (WAV bytes) and returns a Match: which
song it is and *where in the song the clip started*. The rest of the app only
depends on the `Recognizer` interface, so you can replace Shazam with
AcoustID, your own fingerprinting, etc. without touching anything else.

Why Shazam (via `shazamio`) rather than AcoustID: AcoustID is built to look up
whole-track fingerprints and does not tell you the playback offset, which we
need to sync lyrics mid-song. `shazamio` is an unofficial client, fine for a
proof of concept but not something to ship in a product.
"""

from __future__ import annotations

import io
import os
import tempfile
import wave
from dataclasses import dataclass
from typing import Protocol


@dataclass
class Match:
    title: str
    artist: str
    offset_s: float  # position in the song at the START of the clip
    raw: dict | None = None


class RecognitionUnavailable(RuntimeError):
    """The recognizer's dependency is missing or the service can't be reached."""


class Recognizer(Protocol):
    async def identify(self, wav_bytes: bytes) -> Match | None: ...
    async def identify_file(self, file_path: str) -> Match | None: ...


def wav_duration_s(wav_bytes: bytes) -> float:
    with wave.open(io.BytesIO(wav_bytes), "rb") as w:
        return w.getnframes() / float(w.getframerate())


class ShazamRecognizer:
    def __init__(self) -> None:
        try:
            from shazamio import Shazam  # imported lazily so the app runs without it
        except ImportError as e:
            raise RecognitionUnavailable(
                "shazamio is not installed. Run: pip install shazamio"
            ) from e
        self._shazam = Shazam()

    async def identify(self, wav_bytes: bytes) -> Match | None:
        # shazamio reads from a file path
        fd, path = tempfile.mkstemp(suffix=".wav")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(wav_bytes)
            try:
                result = await self._shazam.recognize(path)
            except Exception as e:  # network / API errors
                raise RecognitionUnavailable(f"Shazam request failed: {e}") from e
        finally:
            os.unlink(path)

        matches = result.get("matches") or []
        track = result.get("track")
        if not matches or not track:
            return None
        return Match(
            title=track.get("title", "Unknown"),
            artist=track.get("subtitle", "Unknown"),
            offset_s=float(matches[0].get("offset", 0.0)),
            raw={"key": track.get("key"), "match": matches[0]},
        )

    async def identify_file(self, file_path: str) -> Match | None:
        try:
            result = await self._shazam.recognize(file_path)
        except Exception as e:
            raise RecognitionUnavailable(f"Shazam request failed: {e}") from e

        matches = result.get("matches") or []
        track = result.get("track")
        if not matches or not track:
            return None
        return Match(
            title=track.get("title", "Unknown"),
            artist=track.get("subtitle", "Unknown"),
            offset_s=float(matches[0].get("offset", 0.0)),
            raw={"key": track.get("key"), "match": matches[0]},
        )


def build_recognizer() -> Recognizer | None:
    """Return the configured recognizer, or None if it can't be created."""
    try:
        return ShazamRecognizer()
    except RecognitionUnavailable:
        return None
