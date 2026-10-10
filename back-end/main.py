"""HTTP API for lyric-sync. The browser UI and the future IoT device both use it.

Run:  uvicorn main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from lyrics import LyricsService, parse_lrc
from recognizer import RecognitionUnavailable, build_recognizer, wav_duration_s
from synchronizer import Synchronizer

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "front-end"


class SelectBody(BaseModel):
    lrclib_id: int
    position_ms: float = 0


class SyncBody(BaseModel):
    position_ms: float


class NudgeBody(BaseModel):
    delta_ms: float


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.lyrics = LyricsService()
    app.state.sync = Synchronizer()
    app.state.recognizer = build_recognizer()
    yield
    await app.state.lyrics.aclose()


app = FastAPI(title="lyric-sync", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])


def _load_track(app: FastAPI, track, record: dict, position_ms: float, source: str) -> None:
    synced = record.get("syncedLyrics")
    if not synced:
        raise HTTPException(422, f"'{track.title}' has no time-synced lyrics on LRCLIB.")
    lines = parse_lrc(synced)
    if not lines:
        raise HTTPException(422, "Could not parse the synced lyrics.")
    app.state.sync.load(track, lines, position_ms=position_ms, source=source)


# ---------------------------------------------------------------- lyrics ----
@app.get("/search")
async def search(q: str):
    """Search LRCLIB. Used by the manual-start flow in the UI."""
    try:
        results = await app.state.lyrics.search(query=q)
    except httpx.HTTPError as e:
        raise HTTPException(502, f"LRCLIB request failed: {e}")
    return [t.to_dict() for t, _ in results[:15]]


@app.post("/select")
async def select(body: SelectBody):
    """Load a track from LRCLIB and start the clock at `position_ms`."""
    try:
        track, record = await app.state.lyrics.get_by_id(body.lrclib_id)
    except httpx.HTTPError as e:
        raise HTTPException(502, f"LRCLIB request failed: {e}")
    _load_track(app, track, record, body.position_ms, "manual")
    return app.state.sync.status()


@app.get("/lyrics")
async def lyrics():
    """Full timestamped lyrics for the current track."""
    sync: Synchronizer = app.state.sync
    return {
        "track": sync.track.to_dict() if sync.track else None,
        "lines": [{"time_ms": l.time_ms, "text": l.text} for l in sync.lines],
    }


# --------------------------------------------------------------- recognise ----
@app.post("/identify")
async def identify(request: Request):
    """Body: raw WAV bytes (16-bit PCM, mono; 16 kHz recommended).

    Identifies the song, loads its lyrics and syncs the clock to where the
    song is *now* (match offset + clip length + processing time).
    """
    received_at = time.monotonic()
    recognizer = app.state.recognizer
    if recognizer is None:
        raise HTTPException(501, "No recognizer available. pip install shazamio, "
                                 "or use the search box to start manually.")
    wav = await request.body()
    try:
        clip_s = wav_duration_s(wav)
    except Exception:
        raise HTTPException(400, "Body must be a valid WAV file.")

    try:
        match = await recognizer.identify(wav)
    except RecognitionUnavailable as e:
        raise HTTPException(502, str(e))
    if match is None:
        return {"matched": False, "message": "Couldn't recognise that. Try again with "
                                            "more of the song, closer to the speaker."}

    try:
        found = await app.state.lyrics.find_best(match.title, match.artist)
    except httpx.HTTPError as e:
        raise HTTPException(502, f"LRCLIB request failed: {e}")
    if not found:
        return {"matched": True, "lyrics_found": False, "title": match.title,
                "artist": match.artist, "message": "Recognised, but no lyrics on LRCLIB."}

    track, record = found
    # Where the song is right now: start-of-clip offset, plus the clip itself,
    # plus time we've spent since the audio finished arriving.
    position_ms = (match.offset_s + clip_s) * 1000 + (time.monotonic() - received_at) * 1000
    try:
        _load_track(app, track, record, position_ms, "recognition")
    except HTTPException as e:
        return {"matched": True, "lyrics_found": False, "title": match.title,
                "artist": match.artist, "message": e.detail}
    return {"matched": True, "lyrics_found": True, "recognised_as":
            {"title": match.title, "artist": match.artist}, **app.state.sync.status()}


# ------------------------------------------------------------------- sync ----
@app.post("/sync")
async def sync(body: SyncBody):
    """Set the current playback position (e.g. from a new recognition match)."""
    app.state.sync.set_position(body.position_ms, playing=True)
    return app.state.sync.status()


@app.post("/nudge")
async def nudge(body: NudgeBody):
    """Shift the position by delta_ms to fix a small offset by ear."""
    app.state.sync.nudge(body.delta_ms)
    return app.state.sync.status()


@app.post("/pause")
async def pause():
    app.state.sync.pause()
    return app.state.sync.status()


@app.post("/resume")
async def resume():
    app.state.sync.resume()
    return app.state.sync.status()


@app.post("/clear")
async def clear():
    app.state.sync.clear()
    return app.state.sync.status()


@app.get("/status")
async def status():
    s = app.state.sync.status()
    s["recognizer_available"] = app.state.recognizer is not None
    return s


# --------------------------------------------------------------- frontend ----
@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(FRONTEND_DIR / "index.html", headers={"Cache-Control": "no-store"})


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
