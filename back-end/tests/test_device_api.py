import pytest
from httpx import ASGITransport, AsyncClient
from main import app
from lyrics import TrackInfo, LyricLine

@pytest.mark.anyio
async def test_device_status_compact_payload_no_lines():
    """GET /device/status should NOT include lines (lightweight poll)."""
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
        assert data["m"] is True
        assert data["p"] is True
        assert "srv" in data
        assert "tid" in data
        # H1: /device/status should NOT have lines
        assert "lines" not in data


@pytest.mark.anyio
async def test_compact_status_with_lines():
    """format_compact_status with include_lines=True should include lines."""
    from synchronizer import Synchronizer
    from device_api import format_compact_status
    sync = Synchronizer()
    sync.load(
        TrackInfo(id=1, title="Test Song", artist="Test Artist", album=None, duration_s=100.0, has_synced=True),
        [LyricLine(1000, "Line 1"), LyricLine(5000, "Line 2")],
        position_ms=2000,
        source="test",
        playing=True,
    )
    data = format_compact_status(sync, include_lines=True)
    assert data["m"] is True
    assert len(data["lines"]) == 2
    assert data["lines"][0]["s"] == "Line 1"
