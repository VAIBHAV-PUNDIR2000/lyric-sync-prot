"""Streaming audio sink for memory-constrained IoT clients (e.g. ESP32).

Saves incoming chunked streams directly to disk without loading full clips into RAM.
Supports raw PCM (auto-wrapping with WAV header) and standard WAV.
"""

from __future__ import annotations

import os
import struct
import tempfile
import wave
from typing import AsyncIterator

# 10 seconds of 16 kHz 16-bit mono = 320 KB.
MAX_STREAM_BYTES = 16000 * 2 * 10

WAV_HEADER_SIZE = 44


def build_wav_header(data_size: int, sample_rate: int = 16000, channels: int = 1,
                     bits_per_sample: int = 16) -> bytes:
    byte_rate = sample_rate * channels * (bits_per_sample // 8)
    block_align = channels * (bits_per_sample // 8)
    total_chunk_size = 36 + data_size
    return struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        total_chunk_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )


async def save_audio_stream(
    stream: AsyncIterator[bytes],
    content_type: str,
    sample_rate: int = 16000,
    channels: int = 1,
    bits_per_sample: int = 16,
) -> tuple[str, float]:
    """Streams audio chunks directly to a temporary file on disk.

    Returns (temp_file_path, duration_seconds).
    Raises HTTPException(413) if the stream exceeds MAX_STREAM_BYTES.
    """
    import anyio

    is_pcm = "pcm" in content_type.lower() or "raw" in content_type.lower()
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    bytes_written = 0
    too_large = False

    try:
        async with await anyio.open_file(path, "wb") as f:
            if is_pcm:
                await f.seek(WAV_HEADER_SIZE)

            async for chunk in stream:
                if chunk:
                    await f.write(chunk)
                    bytes_written += len(chunk)
                    if bytes_written > MAX_STREAM_BYTES:
                        too_large = True
                        break

            if is_pcm and not too_large:
                await f.seek(0)
                header = build_wav_header(
                    data_size=bytes_written,
                    sample_rate=sample_rate,
                    channels=channels,
                    bits_per_sample=bits_per_sample,
                )
                await f.write(header)

        if too_large:
            if os.path.exists(path):
                os.unlink(path)
            from fastapi import HTTPException
            raise HTTPException(status_code=413, detail="Payload Too Large")

        # M6: for WAV uploads, bytes_written includes the WAV header which is
        # not audio data.  Subtract it so the duration is accurate.
        audio_bytes = bytes_written
        if not is_pcm and bytes_written > WAV_HEADER_SIZE:
            audio_bytes = bytes_written - WAV_HEADER_SIZE

        bytes_per_second = sample_rate * channels * (bits_per_sample // 8)
        duration_s = audio_bytes / float(bytes_per_second) if bytes_per_second else 0.0

        return path, duration_s

    except BaseException:
        if os.path.exists(path):
            os.unlink(path)
        raise
