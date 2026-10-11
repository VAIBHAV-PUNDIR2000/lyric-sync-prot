"""Compact serialization formats tailored for embedded microcontrollers (ESP32).

H1 fix: full lyrics are returned only via the separate /device/lyrics or the
initial /identify/stream?compact=true response.  GET /device/status returns
only the lightweight playback state so the ESP32 can poll cheaply.
"""

from __future__ import annotations

import time

from synchronizer import Synchronizer


def format_compact_status(sync: Synchronizer, include_lines: bool = True) -> dict:
    """Return compact status dict.

    include_lines=True  → first identification / full payload (has all lyrics).
    include_lines=False → subsequent polls (lightweight, no lyrics array).
    """
    pos = sync.position_ms()
    idx = sync.current_index(pos)
    track_id = sync.track.id if sync.track else None

    result: dict = {
        "m": sync.track is not None,
        "p": sync.playing,
        "pos": round(pos),
        "srv": time.time_ns() // 1_000_000,   # L5: guaranteed ms precision
        "idx": idx,
        "tid": track_id,                       # track id for change detection
    }
    if include_lines:
        result["lines"] = [{"t": l.start_time_ms, "s": l.text} for l in sync.lines]
    return result
