# Lyric Sync (proof of concept)

Listens to music, identifies the song, and shows time-synced lyrics. 
The system features a browser UI and an optimized backend for IoT microcontrollers (like the ESP32) with a dedicated C++ firmware implementation.

## Repository Structure

```text
front-end/index.html     browser UI (served by the backend at http://localhost:8000)
back-end/
  main.py                FastAPI endpoints
  recognizer.py          song identification (Shazam via shazamio)
  lyrics.py              LRCLIB lookup + LRC parsing
  synchronizer.py        playback clock + "which line is current"
  stream_sink.py         HTTP chunked stream receiver mapping to disk
  device_api.py          Compact JSON serializer for microcontrollers
firmware/
  src/main.cpp           PlatformIO ESP32 implementation (I2S DMA + Chunked HTTP Client)
  wokwi.toml             Wokwi Simulator configuration
ESP32/                   Native C++ tests for RingBuffer components
```

## Run the Backend

macOS / Linux:

```bash
cd back-end
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Windows (PowerShell): `py -3.12 -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt; uvicorn main:app --host 0.0.0.0 --port 8000`

Open <http://localhost:8000>.

## Two ways to use the Browser UI

1. **Manual (no recognition needed):** search a song, pick it, press play on your music at the same moment, then use **±0.5s** to line up.
2. **Automatic:** play music and press **Start listening**. It records 8 s from the mic, identifies the song, and starts the lyrics.

## API Endpoints

| Endpoint | Purpose |
| --- | --- |
| `POST /identify` | Full WAV upload (browser client). Identifies song and syncs clock. |
| `POST /identify/stream` | (IoT) Chunked `Transfer-Encoding` audio stream (avoids RAM buffering on ESP32). |
| `GET /device/status` | (IoT) Highly compact JSON status payload to minimize parsing overhead. |
| `GET /status` | Current track, position, previous/current/next line |
| `GET /lyrics` | Full timestamped lyrics of current track |

Interactive docs: <http://localhost:8000/docs>.

## Embedded Hardware Architecture (ESP32 + DWIN HMI)

The system is optimized for extreme resource constraints using the following architecture:
- **MCU**: ESP32 / ESP32-S3 (Conductor).
- **Audio Input**: INMP441 I2S Microphone.
- **Display**: 7.0 Inch DWIN DGUS II HMI LCD (800x480, Resistive Touch, 16MB Flash).
  
**RAM & CPU Optimization Strategy:**
1. **Zero-Buffering Audio**: The ESP32 does not store the audio clip. It uses a custom C++ `RingBuffer` (8 KB max footprint) wrapped in an `HTTPClient` stream to continuously POST raw PCM chunks directly to the backend (`/identify/stream`).
2. **Zero-Render Display**: Because standard SPI displays (like ST7789) consume massive CPU/RAM to push pixels at 800x480, we use a smart DWIN HMI display. The ESP32 merely sends a 30-byte hardware UART packet containing the lyric text, and the DWIN's internal T5L processor handles all font rendering and graphics. This keeps the ESP32 CPU utilization effectively at **< 1%**.

*See `docs/superpowers/plans/2026-10-11-esp32-chunked-stream-ram-optimization.md` for the full SDD and RTM.*

## Known limits

- Recognition uses `shazamio`, an **unofficial** client of Shazam's private API.
- Lyrics come from LRCLIB (community-sourced); timings may differ based on song versions.
