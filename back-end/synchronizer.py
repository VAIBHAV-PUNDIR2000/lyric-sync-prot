"""Playback-position clock and current-lyric calculation.

The song's position is modelled as a simple clock:

    position = anchor_position + (now - anchor_time)     while playing

Any new information (a manual start, a recognition match, a user nudge)
just re-anchors the clock. The client never needs to stream positions.
"""

from __future__ import annotations

import bisect
import time

from lyrics import LyricLine, TrackInfo


class Synchronizer:
    def __init__(self) -> None:
        self.track: TrackInfo | None = None
        self.lines: list[LyricLine] = []
        self._times: list[int] = []
        self.source: str = "none"  # "manual" | "recognition" | "none"
        self.playing = False
        self._anchor_pos_ms = 0.0
        self._anchor_time = time.monotonic()

    # ---- loading / control -------------------------------------------------
    def load(self, track: TrackInfo, lines: list[LyricLine], position_ms: float = 0,
             source: str = "manual", playing: bool = True) -> None:
        self.track = track
        self.lines = lines
        self._times = [l.time_ms for l in lines]
        self.source = source
        self.set_position(position_ms, playing=playing)

    def set_position(self, position_ms: float, playing: bool | None = None) -> None:
        self._anchor_pos_ms = max(0.0, position_ms)
        self._anchor_time = time.monotonic()
        if playing is not None:
            self.playing = playing

    def nudge(self, delta_ms: float) -> None:
        self.set_position(self.position_ms() + delta_ms)

    def pause(self) -> None:
        self.set_position(self.position_ms(), playing=False)

    def resume(self) -> None:
        self.set_position(self._anchor_pos_ms, playing=True)

    def clear(self) -> None:
        self.track, self.lines, self._times = None, [], []
        self.source, self.playing = "none", False
        self.set_position(0)

    # ---- queries -----------------------------------------------------------
    def position_ms(self) -> float:
        if not self.playing:
            return self._anchor_pos_ms
        return self._anchor_pos_ms + (time.monotonic() - self._anchor_time) * 1000

    def current_index(self, position_ms: float | None = None) -> int:
        """Index of the line being sung now, or -1 before the first line."""
        pos = self.position_ms() if position_ms is None else position_ms
        return bisect.bisect_right(self._times, pos) - 1

    def status(self) -> dict:
        pos = self.position_ms()
        idx = self.current_index(pos)

        def text_at(i: int) -> str | None:
            return self.lines[i].text if 0 <= i < len(self.lines) else None

        return {
            "has_track": self.track is not None,
            "track": self.track.to_dict() if self.track else None,
            "source": self.source,
            "playing": self.playing,
            "position_ms": round(pos),
            "line_index": idx,
            "line_count": len(self.lines),
            "previous": text_at(idx - 1),
            "current": text_at(idx),
            "next": text_at(idx + 1),
            "ended": bool(self.lines) and idx == len(self.lines) - 1
            and self.track is not None
            and self.track.duration_s is not None
            and pos > self.track.duration_s * 1000 + 3000,
        }
