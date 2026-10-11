"""Playback-position clock and current-lyric calculation.

The song's position is modelled as a simple clock:

    position = anchor_position + (now - anchor_time)     while playing

Any new information (a manual start, a recognition match, a user nudge)
just re-anchors the clock. The client never needs to stream positions.

Thread safety: load/clear atomically swap a frozen _Snapshot so readers
(status, position_ms, current_index) never see torn state even under
concurrent requests.
"""

from __future__ import annotations

import bisect
import time
from dataclasses import dataclass, field

from lyrics import LyricLine, TrackInfo


@dataclass(frozen=True)
class _Snapshot:
    """Immutable view of the synchronizer state. Swapped atomically."""
    track: TrackInfo | None = None
    lines: tuple[LyricLine, ...] = ()
    times: tuple[int, ...] = ()
    source: str = "none"
    playing: bool = False
    anchor_pos_ms: float = 0.0
    anchor_time: float = field(default_factory=time.monotonic)


class Synchronizer:
    def __init__(self) -> None:
        self._snap = _Snapshot()

    # ---- helpers -----------------------------------------------------------
    @property
    def track(self) -> TrackInfo | None:
        return self._snap.track

    @property
    def lines(self) -> tuple[LyricLine, ...]:
        return self._snap.lines

    @property
    def source(self) -> str:
        return self._snap.source

    @property
    def playing(self) -> bool:
        return self._snap.playing

    # ---- loading / control -------------------------------------------------
    def load(self, track: TrackInfo, lines: list[LyricLine], position_ms: float = 0,
             source: str = "manual", playing: bool = True) -> None:
        t = tuple(lines)
        self._snap = _Snapshot(
            track=track,
            lines=t,
            times=tuple(l.start_time_ms for l in lines),
            source=source,
            playing=playing,
            anchor_pos_ms=max(0.0, position_ms),
            anchor_time=time.monotonic(),
        )

    def set_position(self, position_ms: float, playing: bool | None = None) -> None:
        s = self._snap
        self._snap = _Snapshot(
            track=s.track, lines=s.lines, times=s.times, source=s.source,
            playing=playing if playing is not None else s.playing,
            anchor_pos_ms=max(0.0, position_ms),
            anchor_time=time.monotonic(),
        )

    def nudge(self, delta_ms: float) -> None:
        self.set_position(self.position_ms() + delta_ms)

    def pause(self) -> None:
        self.set_position(self.position_ms(), playing=False)

    def resume(self) -> None:
        self.set_position(self._snap.anchor_pos_ms, playing=True)

    def clear(self) -> None:
        self._snap = _Snapshot()

    # ---- queries -----------------------------------------------------------
    def position_ms(self) -> float:
        s = self._snap
        if not s.playing:
            return s.anchor_pos_ms
        return s.anchor_pos_ms + (time.monotonic() - s.anchor_time) * 1000

    def current_index(self, position_ms: float | None = None) -> int:
        """Index of the line being sung now, or -1 before the first line."""
        s = self._snap
        pos = self.position_ms() if position_ms is None else position_ms
        return bisect.bisect_right(s.times, pos) - 1

    def status(self) -> dict:
        s = self._snap
        pos = self.position_ms()
        idx = bisect.bisect_right(s.times, pos) - 1

        def text_at(i: int) -> str | None:
            return s.lines[i].text if 0 <= i < len(s.lines) else None

        return {
            "has_track": s.track is not None,
            "track": s.track.to_dict() if s.track else None,
            "source": s.source,
            "playing": s.playing,
            "position_ms": round(pos),
            "line_index": idx,
            "line_count": len(s.lines),
            "previous": text_at(idx - 1),
            "current": text_at(idx),
            "next": text_at(idx + 1),
            "ended": bool(s.lines) and idx == len(s.lines) - 1
            and s.track is not None
            and s.track.duration_s is not None
            and pos > s.track.duration_s * 1000 + 3000,
        }
