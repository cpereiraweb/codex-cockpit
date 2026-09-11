"""Manual reference calibration for Codex usage windows."""
from __future__ import annotations

import json
import time
from statistics import median

from .collector import DATA_DIR

FILE = DATA_DIR / "calibration.json"
KEEP = 20
WINDOWS = ("block", "week")


def load() -> dict:
    try:
        data = json.loads(FILE.read_text())
    except (OSError, ValueError):
        return {w: [] for w in WINDOWS}
    return {w: list(data.get(w, [])) for w in WINDOWS}


def save(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(data, indent=2))


def add(window: str, usd: float, pct: float) -> float:
    """Records a sample and returns the newly implied ceiling."""
    if window not in WINDOWS:
        raise ValueError(f"window must be one of {WINDOWS}")
    if not 0 < pct <= 100:
        raise ValueError("the percentage must be between 0 and 100")
    data = load()
    implied = usd / (pct / 100)
    data[window].append({"at": time.time(), "usd": round(usd, 4),
                         "pct": pct, "implied": round(implied, 2)})
    data[window] = data[window][-KEEP:]
    save(data)
    return ceiling(window, data)


def ceiling(window: str, data: dict | None = None) -> float | None:
    data = data if data is not None else load()
    values = [s["implied"] for s in data.get(window, []) if s.get("implied")]
    return round(median(values), 2) if values else None


def clear(window: str | None = None) -> None:
    data = load()
    for w in (WINDOWS if window is None else (window,)):
        data[w] = []
    save(data)
