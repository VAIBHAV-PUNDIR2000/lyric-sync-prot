# ESP32 Chunked Audio Streaming & RAM Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the ~250 KB RAM barrier on microcontrollers by enabling HTTP chunked audio streaming directly from I2S DMA buffers, raw PCM ingestion, and lightweight IoT client synchronization.

**Architecture:** The client streams audio in small 1–2 KB chunks (`Transfer-Encoding: chunked`) directly from I2S DMA to the FastAPI backend without buffering in device RAM. The server streams incoming chunks directly to disk via `request.stream()`, performs latency-compensated identification, and returns structured timestamp anchors allowing the ESP32 to maintain local driftless clock synchronization without 1 Hz HTTP polling.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, httpx, shazamio, pytest, FreeRTOS / ESP-IDF / Arduino C++ (ESP32 reference).

**Spec:** System Design Description & Requirements Traceability Matrix embedded below (governed by [`.agents/skills/engineering-planning-standards/SKILL.md`](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/.agents/skills/engineering-planning-standards/SKILL.md)).

## Global Constraints
- Target hardware: ESP32-WROOM (320 KB SRAM total, ~120–160 KB usable heap) and ESP32-S3.
- Maximum RAM allocation on ESP32 during audio capture: $\le 8\text{ KB}$.
- Audio standard: 16,000 Hz, 16-bit mono linear PCM.
- Backward compatibility: The existing browser UI ([`front-end/index.html`](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/front-end/index.html)) and existing `POST /identify` WAV uploads must remain 100% functional without breaking changes.
- Git policy: Adhere to user constraints — do not push any code to remotes, and never commit to git without explicit user instruction.

---

## 1. Requirements Traceability Matrix (RTM)

| Req ID | Requirement Description | Design Element / Task | Verification Method | Status |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-RAM-01** | Support HTTP chunked transfer streaming (`Transfer-Encoding: chunked`) to avoid buffering audio clips in device RAM. | Task 1 & Task 2 (`AudioStreamSink`, `POST /identify/stream`) | Automated pytest with chunked generator stream | Planned |
| **REQ-RAM-02** | Accept raw headerless PCM bytes (`audio/pcm` or `audio/raw`) so microcontrollers do not need to construct RIFF/WAVE headers. | Task 1 (`pcm_to_wav_stream`) | Unit test verifying valid WAV conversion from raw PCM stream | Planned |
| **REQ-LAT-01** | Account for network transmission duration and server ingestion time in clock synchronization offset. | Task 2 (`position_ms` computation) | Test asserting offset matches reception latency | Planned |
| **REQ-NET-01** | Provide a compact IoT response payload (`/device/identify`, `/device/status`) minimizing JSON parsing overhead. | Task 3 (`CompactStatusFormatter`) | Test validating minified schema and byte size < 35% of full payload | Planned |
| **REQ-CLK-01** | Enable offline driftless rendering on microcontroller by returning anchor timestamp + lyric line array. | Task 3 & Task 5 (Local `millis()` synchronization) | Simulated time progression verification test | Planned |
| **REQ-EMU-01** | Provide a mock ESP32 I2S streaming test suite verifying memory bounds and stream robustness under simulated packet jitter. | Task 4 (`test_esp32_streaming_client.py`) | Integration test verifying 1024-byte chunked stream succeeds | Planned |

---

## 2. System Design Description (SDD)

### 2.1 Audio Ingestion Architecture

```
[ ESP32 Microphone (INMP441) ]
             │ (I2S DMA RingBuffer: 2 x 1024 bytes)
             ▼
[ ESP32 HTTP Client ]
             │ HTTP POST /identify/stream (Transfer-Encoding: chunked)
             │ Streams 1024-byte chunks as recorded
             ▼
[ FastAPI request.stream() ]
             │ (Reads async chunks without buffering in RAM)
             ▼
[ AudioStreamSink (NamedTemporaryFile on disk) ]
             │
             ├── If Content-Type == audio/pcm: Wraps with 44-byte WAV header on disk
             └── If Content-Type == audio/wav: Writes raw bytes directly to disk
             │
             ▼
[ ShazamRecognizer.identify(file_path) ]
```

### 2.2 Mathematical Clock Anchor for Embedded Clients

The ESP32 does not continuously query the backend. When identification succeeds, the backend responds with:
```json
{
  "matched": true,
  "track": {"title": "Yellow", "artist": "Coldplay"},
  "anchor_pos_ms": 48200,
  "server_time_ms": 1728604800120,
  "lines": [
    {"t": 45000, "s": "Look at the stars"},
    {"t": 51000, "s": "Look how they shine for you"}
  ]
}
```
The ESP32 records the hardware timer $T_{\text{local}} = \text{millis}()$. At any subsequent time $t$, current playback position is:
$$\text{pos}(t) = \text{anchor\_pos\_ms} + (\text{millis}() - T_{\text{local}})$$
The microcontroller evaluates this locally at 30–60 FPS and updates its OLED/TFT display with zero network traffic.

---

## 3. Implementation Tasks

### Task 1: Streaming Audio Sink & PCM-to-WAV Stream Converter

**Files:**
- Create: [`back-end/stream_sink.py`](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/back-end/stream_sink.py)
- Test: [`back-end/tests/test_stream_sink.py`](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/back-end/tests/test_stream_sink.py)

**Interfaces:**
- Consumes: Async iterable of `bytes` chunks (`AsyncIterator[bytes]`), `content_type: str`, `sample_rate: int = 16000`, `channels: int = 1`, `bit_depth: int = 16`.
- Produces: `async def save_audio_stream(stream: AsyncIterator[bytes], content_type: str, sample_rate: int = 16000) -> tuple[str, float]` returning `(temp_file_path, duration_seconds)`.

- [ ] **Step 1: Write the failing test**

Create [`back-end/tests/test_stream_sink.py`](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/back-end/tests/test_stream_sink.py):
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
uv run --project back-end --with pytest --with anyio pytest back-end/tests/test_stream_sink.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'stream_sink'`

- [ ] **Step 3: Implement minimal code in [`back-end/stream_sink.py`](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/back-end/stream_sink.py)**

```python
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


def build_wav_header(data_size: int, sample_rate: int = 16000, channels: int = 1, bits_per_sample: int = 16) -> bytes:
    byte_rate = sample_rate * channels * (bits_per_sample // 8)
    block_align = channels * (bits_per_sample // 8)
    total_chunk_size = 36 + data_size
    return struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        total_chunk_size,
        b"WAVE",
        b"fmt ",
        16,  # PCM subchunk size
        1,   # AudioFormat (1 = PCM)
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
    """
    import anyio
    
    is_pcm = "pcm" in content_type.lower() or "raw" in content_type.lower()
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd) # Close immediately to prevent fd leaks in anyio
    bytes_written = 0
    max_bytes = 16000 * 2 * 10 # 10 seconds hard limit

    try:
        async with await anyio.open_file(path, "wb") as f:
            if is_pcm:
                # Reserve 44 bytes for WAV header, written later once data size is known
                await f.seek(44)

            async for chunk in stream:
                if chunk:
                    await f.write(chunk)
                    bytes_written += len(chunk)
                    if bytes_written > max_bytes:
                        from fastapi import HTTPException
                        raise HTTPException(status_code=413, detail="Payload Too Large")

            if is_pcm:
                # Seek back to write header with final data size
                await f.seek(0)
                header = build_wav_header(
                    data_size=bytes_written,
                    sample_rate=sample_rate,
                    channels=channels,
                    bits_per_sample=bits_per_sample,
                )
                await f.write(header)

        # Calculate duration mathematically without blocking wave.open
        bytes_per_second = sample_rate * channels * (bits_per_sample // 8)
        duration_s = bytes_written / float(bytes_per_second) if bytes_per_second else 0.0

        return path, duration_s

    except BaseException:
        if os.path.exists(path):
            os.unlink(path)
        raise
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
uv run --project back-end --with pytest --with anyio pytest back-end/tests/test_stream_sink.py -v
```
Expected: PASS (2 passed)

- [ ] **Step 5: Document task completion**
Track state in plan task checklist (do not run `git commit` unless explicitly instructed).

---

### Task 2: Backend Streaming Ingestion API (`POST /identify/stream`)

**Files:**
- Modify: [`back-end/main.py`](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/back-end/main.py)
- Test: [`back-end/tests/test_api_streaming.py`](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/back-end/tests/test_api_streaming.py)

**Interfaces:**
- Consumes: Incoming HTTP request with `request.stream()`, `request.headers.get("Content-Type")`.
- Produces: Route `POST /identify/stream` and updated `POST /identify` accepting chunked transfer encoding.

- [ ] **Step 1: Write the failing test**

Create [`back-end/tests/test_api_streaming.py`](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/back-end/tests/test_api_streaming.py):
```python
import pytest
from httpx import ASGITransport, AsyncClient
from main import app
from recognizer import Match

class DummyRecognizer:
    async def identify_file(self, file_path: str):
        return Match(title="Streaming Track", artist="IoT Artist", offset_s=15.0)

@pytest.mark.anyio
async def test_streaming_identify_endpoint(monkeypatch):
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
            "/identify/stream",
            content=chunk_generator(),
            headers={"Content-Type": "audio/pcm; rate=16000"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["matched"] is True
        assert data["recognised_as"]["title"] == "Streaming Track"
        assert data["playing"] is True
        # Verify position_ms includes match offset (15s) + clip length (1s)
        assert data["position_ms"] >= 16000
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
uv run --project back-end --with pytest --with anyio pytest back-end/tests/test_api_streaming.py -v
```
Expected: FAIL with `404 Not Found` for `/identify/stream`

- [ ] **Step 3: Implement streaming logic in [`back-end/main.py`](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/back-end/main.py)**

1. Update `recognizer.py` to allow direct file-path identification without re-writing tempfiles:
```python
# In recognizer.py, add identify_file:
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
```
2. Add route `/identify/stream` in `main.py` utilizing `save_audio_stream(request.stream(), content_type)` and `identify_file(path)` with automatic `os.unlink(path)` cleanup.
   - **Compact Mode**: Accept a `?compact=true` query parameter. If true, the route must return the output of `format_compact_status(sync)` so IoT clients don't need to make a second request.
   - **Latency Compensation**: Record `T_start = time.time()` when the stream starts. After `identify_file` returns, compute latency and add it to `offset_s`.
   - **Cleanup**: Ensure `os.unlink(path)` is inside a `finally` block to prevent temp file leaks.

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
uv run --project back-end --with pytest --with anyio pytest back-end/tests/test_api_streaming.py -v
```
Expected: PASS (1 passed)

---

### Task 3: Compact IoT Payload & Device Endpoint (`GET /device/status`)

**Files:**
- Create: [`back-end/device_api.py`](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/back-end/device_api.py)
- Modify: [`back-end/main.py`](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/back-end/main.py)
- Test: [`back-end/tests/test_device_api.py`](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/back-end/tests/test_device_api.py)

**Interfaces:**
- Produces: `GET /device/status` and `POST /device/identify` returning payloads optimized for offline sync:
  ```json
  {"m":true,"p":true,"pos":48200,"srv":1728604800120,"lines":[{"t":45000,"s":"Look at the stars"}]}
  ```

- [ ] **Step 1: Write the failing test**

Create [`back-end/tests/test_device_api.py`](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/back-end/tests/test_device_api.py):
```python
import pytest
from httpx import ASGITransport, AsyncClient
from main import app
from lyrics import TrackInfo, LyricLine

@pytest.mark.anyio
async def test_device_status_compact_payload():
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
uv run --project back-end --with pytest --with anyio pytest back-end/tests/test_device_api.py -v
```
Expected: FAIL with `404 Not Found` for `/device/status`

- [ ] **Step 3: Implement [`back-end/device_api.py`](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/back-end/device_api.py) & Mount in `main.py`**

```python
"""Compact serialization formats tailored for embedded microcontrollers (ESP32)."""

from __future__ import annotations
from synchronizer import Synchronizer

import time

def format_compact_status(sync: Synchronizer) -> dict:
    pos = sync.position_ms()
    idx = sync.current_index(pos)
    lines = sync.lines

    return {
        "m": sync.track is not None,
        "p": sync.playing,
        "pos": round(pos),
        "srv": round(time.time() * 1000),
        "idx": idx,
        "lines": [{"t": l.start_time_ms, "s": l.text} for l in lines]
    }
```

Add endpoint in `main.py`:
```python
from device_api import format_compact_status

@app.get("/device/status")
async def device_status():
    return format_compact_status(app.state.sync)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
uv run --project back-end --with pytest --with anyio pytest back-end/tests/test_device_api.py -v
```
Expected: PASS (1 passed)

---

### Task 4: ESP32 I2S DMA Simulation Test Suite

**Files:**
- Create: [`back-end/tests/test_esp32_simulator.py`](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/back-end/tests/test_esp32_simulator.py)

**Interfaces:**
- Simulates realistic ESP32 memory constraints:
  - Max buffer in RAM: 1024 bytes per iteration.
  - Realistic Wi-Fi transmission jitter (10–30 ms delay between chunks).
  - Streams 4 seconds of PCM audio without exceeding 1024 bytes heap in test runner.

- [ ] **Step 1: Write simulation test**

Create [`back-end/tests/test_esp32_simulator.py`](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/back-end/tests/test_esp32_simulator.py):
```python
import asyncio
import pytest
from httpx import ASGITransport, AsyncClient
from main import app
from recognizer import Match

class MockRecognizer:
    async def identify_file(self, file_path: str):
        return Match(title="ESP32 Verified", artist="Embedded Labs", offset_s=30.0)

@pytest.mark.anyio
async def test_esp32_dma_chunked_streaming_simulation():
    """Simulates an ESP32 streaming from an INMP441 I2S mic with 1024-byte DMA buffers."""
    app.state.recognizer = MockRecognizer()

    async def mock_find_best(title, artist):
        from lyrics import TrackInfo
        track = TrackInfo(id=123, title=title, artist=artist, album=None, duration_s=200.0, has_synced=True)
        record = {"syncedLyrics": "[00:30.00]Simulated ESP32 Lyric Line"}
        return track, record

    app.state.lyrics.find_best = mock_find_best

    # Generator simulating I2S DMA callback: 1024 bytes per tick
    async def i2s_dma_generator():
        chunk_size = 1024
        total_chunks = 32  # 32 * 1024 = 32768 bytes (~1.02 seconds at 16kHz mono)
        for _ in range(total_chunks):
            yield b"\x01\x00" * (chunk_size // 2)
            await asyncio.sleep(0.005)  # simulate DMA fill interval

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/identify/stream?compact=true",
            content=i2s_dma_generator(),
            headers={"Content-Type": "audio/pcm; rate=16000"},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["m"] is True
        assert "lines" in body
        assert body["lines"][0]["s"] == "Simulated ESP32 Lyric Line"
```

- [ ] **Step 2: Run simulation test**

Run:
```bash
uv run --project back-end --with pytest --with anyio pytest back-end/tests/test_esp32_simulator.py -v
```
Expected: PASS (1 passed)

---

### Task 5: ESP32 Firmware Reference Implementation

**Files:**
- Create: [`firmware/esp32_lyric_streamer.ino`](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/firmware/esp32_lyric_streamer.ino)
- Create: [`firmware/README.md`](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/firmware/README.md) (Pinout, wiring, build guide for Arduino / PlatformIO).

**Interfaces:**
- Produces: Complete, compilation-ready C++ reference implementation for ESP32 with:
  - FreeRTOS Task 1: I2S DMA audio capture (`i2s_read`) streaming via `HTTPClient` chunked encoding.
  - FreeRTOS Task 2: Local clock interpolation and SSD1306 / ST7789 display rendering without polling.

- [ ] **Step 1: Write firmware reference code**

Implement [`firmware/esp32_lyric_streamer.ino`](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/firmware/esp32_lyric_streamer.ino) with:
- I2S configuration for INMP441 (BCLK=14, WS=15, DIN=32).
- FreeRTOS RingBuffer (`xRingbufferCreate`) of at least 8KB to absorb Wi-Fi latency spikes.
- A custom C++ class `RingBufferStream` extending `Stream` that reads from the RingBuffer.
- Zero-heap chunked streaming HTTP client running in a separate FreeRTOS task:
  ```cpp
  RingBufferStream streamWrapper(myRingBuffer);
  client.begin("http://192.168.1.100:8000/identify/stream?compact=true");
  client.addHeader("Content-Type", "audio/pcm; rate=16000");
  client.sendRequest("POST", &streamWrapper, -1); // -1 triggers Transfer-Encoding: chunked
  ```
- Firmware must gracefully handle TCP RST / socket disconnections if the server returns 413 Payload Too Large mid-stream.
- Local anchor time calculation for zero-poll display updating.

- [ ] **Step 2: Write hardware wiring guide and memory verification document** in [`firmware/README.md`](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/firmware/README.md).

---

## 4. Verification & Validation (V&V) Matrix

| Test Suite | Target Feature | Acceptance Criteria | Execution Command |
| :--- | :--- | :--- | :--- |
| `test_stream_sink.py` | Disk streaming sink & WAV conversion | Raw PCM converted to valid RIFF/WAVE on disk; 0 bytes audio buffered in heap. | `uv run --project back-end --with pytest --with anyio pytest back-end/tests/test_stream_sink.py` |
| `test_api_streaming.py` | Route `POST /identify/stream` | Identifies song and returns sync status from chunked stream. | `uv run --project back-end --with pytest --with anyio pytest back-end/tests/test_api_streaming.py` |
| `test_device_api.py` | Route `GET /device/status` | Serializes compact JSON payload $\le 150\text{ bytes}$. | `uv run --project back-end --with pytest --with anyio pytest back-end/tests/test_device_api.py` |
| `test_esp32_simulator.py` | I2S DMA simulation | 1024-byte chunked stream successfully received and matched without timeout or memory degradation. | `uv run --project back-end --with pytest --with anyio pytest back-end/tests/test_esp32_simulator.py` |

---

## 5. Risk and Assumption Register

1. **Assumption (Confirmed)**: Shazam (`shazamio`) requires a standard audio file with headers on disk. By prepending the 44-byte WAV header on disk upon stream completion, we fulfill this requirement without buffering the stream in RAM.
2. **Risk**: Microcontroller clock drift over long songs ($\sim 1\text{ ms/s}$).
   *Mitigation*: The device automatically re-triggers a short 3.5s streaming identify check every 30–45 seconds or during detected inter-song silence.
3. **Risk**: Network disconnection during playback.
   *Mitigation*: Because the full line array and anchor timestamp are stored locally on the ESP32, playback continues rendering smoothly even if Wi-Fi temporarily drops.
