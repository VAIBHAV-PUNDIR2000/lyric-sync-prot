import pytest
from httpx import ASGITransport, AsyncClient
from main import app
from lyrics import TrackInfo, LyricLine

@pytest.mark.anyio
async def test_device_status_compact_payload():
    from synchronizer import Synchronizer
    app.state.sync = Synchronizer()
    app.state.sync.load(
        TrackInfo(id=1, title="Test Song", artist="Test Artist", album=None, duration_s=100.0, has_synced=True),
        [LyricLine(1000, "Line 1"), LyricLine(5000, "Line 2")],
        position_ms=2000,
        source="test",
        playing=True,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/device/status")
        assert r.status_code == 200
        data = r.json()
        # Verify compact keys and that all lines are returned for offline rendering
        assert data["m"] is True
        assert data["p"] is True
        assert "srv" in data
        assert len(data["lines"]) == 2
        assert data["lines"][0]["s"] == "Line 1"
        # Payload size should be small but sufficient for zero-polling
        assert len(r.content) < 300
