import os
import wave
import pytest
from stream_sink import save_audio_stream

async def mock_pcm_stream(chunk_size: int = 1024, total_bytes: int = 32000):
    """Yields simulated 16-bit mono 16kHz PCM audio (1 second = 32000 bytes)."""
    produced = 0
    while produced < total_bytes:
        count = min(chunk_size, total_bytes - produced)
        yield b"\x00" * count
        produced += count

@pytest.mark.anyio
async def test_save_audio_stream_from_pcm():
    path, duration = await save_audio_stream(
        mock_pcm_stream(chunk_size=1024, total_bytes=64000),
        content_type="audio/pcm",
        sample_rate=16000,
    )
    try:
        assert os.path.exists(path)
        assert abs(duration - 2.0) < 0.01
        with wave.open(path, "rb") as w:
            assert w.getnchannels() == 1
            assert w.getsampwidth() == 2
            assert w.getframerate() == 16000
            assert w.getnframes() == 32000
    finally:
        if os.path.exists(path):
            os.unlink(path)

@pytest.mark.anyio
async def test_save_audio_stream_from_wav():
    # Generate a genuine small WAV in memory
    import io
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00" * 32000)
    wav_bytes = buf.getvalue()

    async def wav_stream():
        yield wav_bytes[:100]
        yield wav_bytes[100:]

    path, duration = await save_audio_stream(
        wav_stream(),
        content_type="audio/wav",
        sample_rate=16000,
    )
    try:
        assert os.path.exists(path)
        assert abs(duration - 1.0) < 0.01
    finally:
        if os.path.exists(path):
            os.unlink(path)
