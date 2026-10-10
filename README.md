# Lyric Sync (proof of concept)

Listens to music, identifies the song, and shows time-synced lyrics in a browser.
The browser is just one client of the HTTP API; a future Raspberry Pi / ESP32 can call the same endpoints.

```
front-end/index.html     browser UI (served by the backend at http://localhost:8000)
back-end/
  main.py                FastAPI endpoints
  recognizer.py          song identification (swappable; currently Shazam via shazamio)
  lyrics.py              LRCLIB lookup + LRC parsing
  synchronizer.py        playback clock + "which line is current"
  requirements.txt
```

## Run it

macOS / Linux:

```bash
cd back-end
python3.12 -m venv .venv          # 3.10–3.13 all fine
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Windows (PowerShell): `py -3.12 -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt; uvicorn main:app --host 0.0.0.0 --port 8000`

Open <http://localhost:8000>.

## Two ways to use it

1. **Manual (no recognition needed):** search a song, pick it, press play on your music at the same moment,
   then use **±0.5s** to line up. This tests lyrics + sync on their own.
2. **Automatic:** play music near your computer and press **Start listening**. It records 8 s from the
   mic, identifies the song, and starts the lyrics at the matching position. It then re-checks every 30 s
   to correct drift and catch song changes (press **Stop listening** to end). A level bar shows what the
   mic hears. Allow mic access when asked (works on `localhost`). If it's a little early/late, use **±0.5s**.

## API (what the IoT device will call)

| Endpoint | Purpose |
| --- | --- |
| `POST /identify` | Body = raw WAV (16-bit mono, 16 kHz ideal). Identifies the song, loads lyrics, syncs the clock |
| `GET /status` | Current track, position, previous/current/next line |
| `GET /lyrics` | Full timestamped lyrics of current track |
| `GET /search?q=` · `POST /select` | Manual track choice (`{"lrclib_id": 123, "position_ms": 0}`) |
| `POST /sync` · `/nudge` · `/pause` · `/resume` · `/clear` | Clock control |

Interactive docs: <http://localhost:8000/docs>. Quick device-style test:

```bash
curl -X POST http://localhost:8000/identify -H 'Content-Type: audio/wav' --data-binary @clip.wav
```

## Moving to hardware later

Run with `--host 0.0.0.0` (already above), find your PC's LAN IP, and have the device POST WAV clips to
`http://<pc-ip>:8000/identify` and poll `GET /status`. You may need to allow port 8000 through the firewall.

## Known limits

- Recognition uses `shazamio`, an **unofficial** client of Shazam's private API. Fine for a prototype,
  may break, and not suitable for a shipped product. Replace it by implementing `Recognizer` in `recognizer.py`.
- Lyrics come from LRCLIB (community-sourced); some songs have no synced lyrics or timings that differ from
  your version of the track (live, remaster, radio edit). That's what the nudge buttons are for.
- One song/session at a time; state lives in memory and resets when the server restarts.
