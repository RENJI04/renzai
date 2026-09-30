from __future__ import annotations

import sys
from pathlib import Path

API_SOURCE = Path(__file__).parents[1] / "src"
WORKER_SOURCE = Path(__file__).parents[3] / "workers" / "src"
for source in (API_SOURCE, WORKER_SOURCE):
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))
