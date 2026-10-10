# Project Handoff

## Overview
Lyric Sync is a proof-of-concept application that listens to music, identifies the song via Shazamio, fetches synchronized lyrics from LRCLIB, and displays time-synced lyrics in a browser UI or for an IoT device via REST API.

## Environment Details
- **Python Version**: CPython 3.12.14
- **Virtual Environment Path**: [back-end/.venv](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/back-end/.venv)
- **Dependency File**: [back-end/requirements.txt](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/back-end/requirements.txt)
- **Installed Packages**: `fastapi`, `uvicorn[standard]`, `httpx`, `shazamio`, and required dependencies.

## Current Service Status
- **Application Process**: Running via Uvicorn on `0.0.0.0:8000`
- **Frontend URL**: [http://localhost:8000](http://localhost:8000)
- **API Status Endpoint**: [http://localhost:8000/status](http://localhost:8000/status)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Verification**: Confirmed working (`HTTP 200` on both `/` and `/status` with `recognizer_available: true`).

## How to Run / Manage Manually
```bash
cd back-end
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Custom Skills Configured
- **`engineering-planning-standards`**:
  - Global Path: [~/.gemini/config/skills/engineering-planning-standards/SKILL.md](file:///home/nicolas/.gemini/config/skills/engineering-planning-standards/SKILL.md)
  - Workspace Path: [.agents/skills/engineering-planning-standards/SKILL.md](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/.agents/skills/engineering-planning-standards/SKILL.md)
  - Purpose: Enforces reference documentation standards for engineering planning agents based on SAE ARP4754B, RTCA DO-178C, NASA Systems Engineering Handbook, Requirements Traceability Matrices (RTM), System Design Descriptions (SDD), Verification & Validation (V&V) plans, and structured assurance cases.

---

## Active Development Branch (Oct 11, 2026)
- **Branch**: `feature/esp32-chunked-stream-ram-optimization`
- **Objective**: Overcome the ~250 KB RAM barrier on microcontrollers by implementing HTTP chunked streaming directly from I2S DMA buffers, raw PCM ingestion, and driftless local anchor synchronization.
- **Implementation Plan**: [`docs/superpowers/plans/2026-10-11-esp32-chunked-stream-ram-optimization.md`](file:///home/nicolas/ssd/Stuff/vibe-coding/lyric-sync-prot/docs/superpowers/plans/2026-10-11-esp32-chunked-stream-ram-optimization.md)
- **Status**: Plan finalized with RTM, SDD, V&V matrices, and bite-sized TDD tasks. Ready for implementation.
