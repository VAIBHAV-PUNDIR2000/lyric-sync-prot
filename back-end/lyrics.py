"""Lyrics lookup (LRCLIB) and LRC parsing.

LRCLIB is a free public API, no key needed: https://lrclib.net/docs
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

LRCLIB_BASE = "https://lrclib.net/api"
USER_AGENT = "lyric-sync-prot/0.1 (local proof of concept)"

# [mm:ss], [mm:ss.xx] or [mm:ss.xxx]
_TIMESTAMP = re.compile(r"\[(\d+):(\d{1,2})(?:[.:](\d{1,3}))?\]")


@dataclass
class LyricLine:
    start_time_ms: int
    text: str


@dataclass
class TrackInfo:
    id: int | None
    title: str
    artist: str
    album: str | None
    duration_s: float | None
    has_synced: bool

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def parse_lrc(lrc: str) -> list[LyricLine]:
    """Parse LRC text into time-sorted lines.

    Handles multiple timestamps per line ("[00:10.00][01:20.00]chorus") and
    skips metadata tags like [ar:...] / [ti:...]. Empty-text lines are kept
    (they mark instrumental gaps) so the display can clear correctly.
    """
    lines: list[LyricLine] = []
    for raw in lrc.splitlines():
        stamps = list(_TIMESTAMP.finditer(raw))
        if not stamps:
            continue
        text = raw[stamps[-1].end():].strip()
        for m in stamps:
            minutes, seconds, frac = m.group(1), m.group(2), m.group(3) or "0"
            millis = int(frac.ljust(3, "0")[:3])
            t = (int(minutes) * 60 + int(seconds)) * 1000 + millis
            lines.append(LyricLine(t, text))
    lines.sort(key=lambda l: l.start_time_ms)
    return lines


def _track_from_record(rec: dict) -> TrackInfo:
    return TrackInfo(
        id=rec.get("id"),
        title=rec.get("trackName") or rec.get("name") or "Unknown",
        artist=rec.get("artistName") or "Unknown",
        album=rec.get("albumName"),
        duration_s=rec.get("duration"),
        has_synced=bool(rec.get("syncedLyrics")),
    )


class LyricsService:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=LRCLIB_BASE,
            headers={"User-Agent": USER_AGENT},
            timeout=15.0,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def search(self, query: str | None = None, *, title: str | None = None,
                     artist: str | None = None) -> list[tuple[TrackInfo, dict]]:
        """Return (TrackInfo, raw record) pairs, synced-lyrics results first.

        Raises httpx.HTTPError on network / API failures (H4: callers handle it).
        """
        params: dict[str, str] = {}
        if query:
            params["q"] = query
        if title:
            params["track_name"] = title
        if artist:
            params["artist_name"] = artist
        if not params:
            return []
        r = await self._client.get("/search", params=params)
        r.raise_for_status()
        records = r.json()
        records.sort(key=lambda rec: not rec.get("syncedLyrics"))
        return [(_track_from_record(rec), rec) for rec in records]

    async def get_by_id(self, lrclib_id: int) -> tuple[TrackInfo, dict]:
        r = await self._client.get(f"/get/{lrclib_id}")
        r.raise_for_status()
        rec = r.json()
        return _track_from_record(rec), rec

    async def find_best(self, title: str, artist: str) -> tuple[TrackInfo, dict] | None:
        """Best synced-lyrics match for a recognised song, or None."""
        results = await self.search(title=title, artist=artist)
        if not results:
            results = await self.search(query=f"{artist} {title}")
        for track, rec in results:
            if track.has_synced:
                return track, rec
        return results[0] if results else None
