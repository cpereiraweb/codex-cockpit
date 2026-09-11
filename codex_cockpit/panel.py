"""Latest rate limits and context observations from local Codex rollouts."""
from __future__ import annotations

import json
import time
from pathlib import Path

from .collector import DATA_DIR

SNAPSHOT = DATA_DIR / "panel.json"
HISTORY = DATA_DIR / "panel-history.ndjson"
WINDOWS = {"block": "five_hour", "week": "seven_day"}


def load() -> dict:
    try:
        return json.loads(SNAPSHOT.read_text())
    except (OSError, ValueError):
        return {}


def window(name: str, now: float | None = None, snapshot: dict | None = None) -> dict | None:
    """Official data for 'block' or 'week', or None when absent or expired."""
    now = now or time.time()
    snap = snapshot if snapshot is not None else load()
    data = (snap.get("rate_limits") or {}).get(WINDOWS.get(name, name))
    if not data:
        return None
    resets_at = data.get("resets_at")
    if not resets_at or resets_at <= now:
        return None
    return {
        "pct": float(data.get("used_percentage") or 0.0),
        "resets_at": float(resets_at),
        "captured_at": data.get("at", snap.get("at", 0.0)),
        "age_s": max(0.0, now - data.get("at", snap.get("at", 0.0))),
    }


def contexts(snapshot: dict | None = None) -> dict:
    snap = snapshot if snapshot is not None else load()
    return snap.get("sessions") or {}


def record_codex(payload: dict, ctx: dict, at: float) -> None:
    """Normalize by duration, not position: primary can be the weekly limit."""
    snap = load()
    changed = False
    limits = payload.get("rate_limits") or {}
    if limits.get("limit_id") in (None, "codex"):
        for slot in ("primary", "secondary"):
            entry = limits.get(slot)
            if not isinstance(entry, dict):
                continue
            name = {300: "five_hour", 10080: "seven_day"}.get(entry.get("window_minutes"))
            if not name:
                continue
            try:
                pct, reset = float(entry["used_percent"]), float(entry["resets_at"])
            except (KeyError, TypeError, ValueError):
                continue
            if not (0 <= pct <= 100 and 0 < reset < float('inf')):
                continue
            old = snap.setdefault("rate_limits", {}).get(name, {})
            if at < old.get("at", 0):
                continue
            snap["rate_limits"][name] = {"used_percentage": pct, "resets_at": reset, "at": at}
            snap["at"] = max(at, snap.get("at", 0))
            changed = True
    info = payload.get("info") or {}
    sid = ctx.get("session")
    if sid and info and at >= snap.get("sessions", {}).get(sid, {}).get("at", 0):
        last = info.get("last_token_usage") or {}
        size = info.get("model_context_window")
        # Last request tokens, never the cumulative session total.
        used = (last.get("input_tokens") or 0) + (last.get("output_tokens") or 0)
        snap.setdefault("sessions", {})[sid] = {
            "at": at, "model": ctx.get("model", ""), "context_size": size,
            "context_pct": min(100, 100 * used / size) if size else None,
            "input_tokens": last.get("input_tokens"), "cwd": ctx.get("cwd", ""),
        }
        changed = True
    if not changed:
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = SNAPSHOT.with_suffix(".tmp")
    tmp.write_text(json.dumps(snap))
    tmp.replace(SNAPSHOT)
    _append_history(snap.get("at", at), snap.get("rate_limits", {}))


def _append_history(now: float, limits: dict) -> None:
    """One line per change, so the official curve can be plotted later."""
    row = {"at": round(now, 1)}
    for key, source in WINDOWS.items():
        data = limits.get(source) or {}
        if data:
            row[key] = round(float(data.get("used_percentage") or 0), 2)
            row[f"{key}_resets_at"] = data.get("resets_at")
    if len(row) == 1:
        return
    try:
        with HISTORY.open() as fh:
            last = None
            for line in fh:
                last = line
        if last:
            prev = json.loads(last)
            if all(prev.get(k) == row.get(k) for k in ("block", "week", "block_resets_at", "week_resets_at")):
                return   # nothing changed
    except (OSError, ValueError):
        pass
    with HISTORY.open("a") as fh:
        fh.write(json.dumps(row, separators=(",", ":")) + "\n")
