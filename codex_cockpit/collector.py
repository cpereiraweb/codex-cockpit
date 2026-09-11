"""Incremental, locked ingestion of Codex rollout JSONL files."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import pricing

CODEX_DIR = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "codex-cockpit"
EVENTS_FILE = DATA_DIR / "events.ndjson"
STATE_FILE = DATA_DIR / "state.json"

SCHEMA = 2


@dataclass(slots=True)
class Event:
    k: str      # stable session/timestamp/cumulative-usage key
    t: float    # epoch seconds (UTC)
    m: str      # model
    i: int      # input tokens
    o: int      # output tokens
    cw: int     # cache write input tokens
    r: int      # cache read
    c: float    # API-equivalent cost in USD
    s: str      # sessionId
    p: str      # project cwd
    x: int      # 1 = sidechain (subagent)
    ef: str     # effort

    def to_json(self) -> str:
        return json.dumps(self.__dict__ if not hasattr(self, "__slots__") else {
            f: getattr(self, f) for f in self.__slots__
        }, separators=(",", ":"))

    @property
    def tokens(self) -> int:
        return self.i + self.o + self.cw + self.r


def _load_state() -> dict:
    try:
        st = json.loads(STATE_FILE.read_text())
        if st.get("schema") == SCHEMA:
            return st
    except (OSError, ValueError):
        pass
    return {"schema": SCHEMA, "files": {}}


def _save_state(state: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state))
    tmp.replace(STATE_FILE)


def load_events() -> list[Event]:
    """Reads the consolidated history."""
    events: list[Event] = []
    if not EVENTS_FILE.exists():
        return events
    with EVENTS_FILE.open(errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                events.append(Event(**d))
            except (ValueError, TypeError):
                continue
    return events


def _read_new_lines(path: Path, offset: int) -> tuple[list[bytes], int]:
    """Reads only what was appended, never a half-written line."""
    size = path.stat().st_size
    if size < offset:            # truncated or rotated -> reprocess
        offset = 0
    if size == offset:
        return [], offset
    with path.open("rb") as fh:
        fh.seek(offset)
        chunk = fh.read(size - offset)
    end = chunk.rfind(b"\n")
    if end == -1:
        return [], offset        # no complete line yet
    complete = chunk[: end + 1]
    return complete.splitlines(), offset + len(complete)


def rollout_paths():
    for directory in ("sessions", "archived_sessions"):
        yield from (CODEX_DIR / directory).rglob("*.jsonl")


def parse_row(d: dict, ctx: dict) -> Event | None:
    """Update persistent metadata and emit only new cumulative token usage."""
    if not isinstance(d, dict):
        return None
    p = d.get("payload")
    if not isinstance(p, dict):
        return None
    kind = d.get("type")
    if kind == "session_meta":
        ctx.update(session=p.get("id", ""), cwd=p.get("cwd", ""),
                   subagent=isinstance(p.get("source"), dict) and "subagent" in p["source"])
    elif kind == "turn_context":
        ctx.update(model=p.get("model", ""), effort=p.get("effort") or p.get("reasoning_effort", ""),
                   cwd=p.get("cwd") or ctx.get("cwd", ""))
    elif kind == "event_msg" and p.get("type") == "token_count":
        try:
            epoch = datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00")).timestamp()
        except (KeyError, TypeError, ValueError):
            return None
        from . import panel
        panel.record_codex(p, ctx, epoch)
        info = p.get("info") or {}
        total = info.get("total_token_usage")
        if not isinstance(total, dict) or not ctx.get("session"):
            return None
        fields = ("input_tokens", "output_tokens", "cached_input_tokens", "cache_write_input_tokens")
        try:
            current = {k: max(0, int(total.get(k) or 0)) for k in fields}
        except (TypeError, ValueError):
            return None
        previous = ctx.get("usage", {})
        # A reset establishes a new baseline; repeated snapshots emit nothing.
        reset = any(current[k] < previous.get(k, 0) for k in fields)
        delta = {k: current[k] - (0 if reset else previous.get(k, 0)) for k in fields}
        ctx["usage"] = current
        if not any(delta.values()):
            return None
        read = min(delta["cached_input_tokens"], delta["input_tokens"])
        write = min(delta["cache_write_input_tokens"], delta["input_tokens"] - read)
        inp, out = delta["input_tokens"] - read - write, delta["output_tokens"]
        model = ctx.get("model", "")
        key = f"{ctx['session']}:{d['timestamp']}:{current}"
        return Event(key, epoch, model, inp, out, write, read,
                     round(pricing.cost(model, inp, out, write, read), 6),
                     ctx['session'], ctx.get('cwd', ''), int(ctx.get('subagent', False)),
                     ctx.get('effort', ''))
    return None


def refresh() -> tuple[list[Event], int]:
    # Tray, HTTP and CLI may collect concurrently. Serialize the entire transaction.
    import fcntl
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with (DATA_DIR / "collector.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _refresh()


def _refresh() -> tuple[list[Event], int]:
    state = _load_state()
    events = load_events()
    seen = {e.k for e in events}
    new = []
    paths = sorted(rollout_paths())
    for path in paths:
        key = str(path)
        info = state["files"].get(key, {"offset": 0})
        try:
            if path.stat().st_size < info.get("offset", 0):
                info = {"offset": 0}
            lines, offset = _read_new_lines(path, info.get("offset", 0))
        except OSError:
            continue
        ctx = info.setdefault("context", {})
        for raw in lines:
            try:
                ev = parse_row(json.loads(raw), ctx)
            except (ValueError, TypeError, AttributeError):
                continue
            if ev is not None and ev.k not in seen:
                seen.add(ev.k)
                new.append(ev)
        info.update(offset=offset)
        state["files"][key] = info
    if new:
        with EVENTS_FILE.open("a") as fh:
            for ev in sorted(new, key=lambda e: e.t):
                fh.write(ev.to_json() + "\n")
        events.extend(new)
    alive = {str(p) for p in paths}
    state["files"] = {k: v for k, v in state["files"].items() if k in alive}
    _save_state(state)
    # Reprice retained history when the user adds a previously unknown model.
    for e in events:
        e.c = round(pricing.cost(e.m, e.i, e.o, e.cw, e.r), 6)
    return sorted(events, key=lambda e: e.t), len(new)


def utc_now() -> float:
    return datetime.now(timezone.utc).timestamp()
