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
        "lines": [{"t": l.time_ms, "s": l.text} for l in lines]
    }
