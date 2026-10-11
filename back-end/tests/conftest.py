"""L1: Make tests runnable from any working directory by adding back-end/ to sys.path."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
