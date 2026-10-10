import pytest
from httpx import ASGITransport, AsyncClient
from main import app
from recognizer import Match

class DummyRecognizer:
    async def identify_file(self, file_path: str):
        return Match(title="Streaming Track", artist="IoT Artist", offset_s=15.0)
    async def identify(self, wav_bytes: bytes):
        return await self.identify_file("")

@pytest.mark.anyio
async def test_streaming_identify_endpoint(monkeypatch):
    from synchronizer import Synchronizer
    from lyrics import LyricsService
    app.state.sync = Synchronizer()
    app.state.lyrics = LyricsService()
    # Mock recognizer and lyrics lookup
    app.state.recognizer = DummyRecognizer()

    async def mock_find_best(title, artist):
        from lyrics import TrackInfo
        track = TrackInfo(id=999, title=title, artist=artist, album=None, duration_s=180.0, has_synced=True)
        record = {"syncedLyrics": "[00:15.00]First streamed line\n[00:20.00]Second streamed line"}
        return track, record

    app.state.lyrics.find_best = mock_find_best

    async def chunk_generator():
        # Stream 32,000 bytes of raw PCM in 1024-byte chunks
        for _ in range(32):
            yield b"\x00" * 1024

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/identify/stream?compact=true",
            content=chunk_generator(),
            headers={"Content-Type": "audio/pcm; rate=16000"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["m"] is True
        assert "lines" in data
        assert len(data["lines"]) == 2
