"""Live Codex processes on Linux, matched to rollouts through open descriptors.

Never infer a live session from an old transcript or match by cwd alone.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from .collector import CODEX_DIR


def _proc_starttime(pid: int) -> str | None:
    try:
        stat = Path(f"/proc/{pid}/stat").read_bytes()
        return stat[stat.rfind(b")") + 2:].split()[19].decode()
    except (OSError, IndexError):
        return None


def _rss_mb(pid: int) -> float:
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024
    except (OSError, ValueError, IndexError):
        pass
    return 0.0


def _is_codex(argv: list[str]) -> bool:
    if not argv:
        return False
    executable = Path(argv[0]).name
    return executable == "codex" or (executable in ("node", "nodejs") and
           len(argv) > 1 and Path(argv[1]).name == "codex.js")


def live_sessions() -> list[dict]:
    out = []
    now = time.time()
    try:
        boot = now - float(Path('/proc/uptime').read_text().split()[0])
        ticks = os.sysconf('SC_CLK_TCK')
    except (OSError, ValueError):
        return out
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        pid = int(proc.name)
        start = _proc_starttime(pid)
        try:
            argv = [v.decode(errors='replace') for v in (proc / 'cmdline').read_bytes().split(b'\0') if v]
            if not start or not _is_codex(argv):
                continue
            # The JS launcher waits for a native child. Only show native workers.
            if Path(argv[0]).name != 'codex':
                continue
            cwd = str((proc / 'cwd').resolve(strict=True))
            sid = ''
            for fd in (proc / 'fd').iterdir():
                try:
                    target = fd.resolve(strict=True)
                    if target.suffix != '.jsonl' or not target.is_relative_to(CODEX_DIR.resolve()):
                        continue
                    with target.open() as fh:
                        row = json.loads(fh.readline())
                    if row.get('type') == 'session_meta':
                        sid = row['payload'].get('id', '')
                        break
                except (OSError, ValueError, KeyError):
                    continue
            if _proc_starttime(pid) != start:
                continue
        except (OSError, ValueError):
            continue
        started = boot + int(start) / ticks
        out.append({'pid': pid, 'session_id': sid, 'name': sid[:8] if sid else f'pid {pid}',
                    'cwd': cwd, 'status': 'unknown', 'kind': 'codex',
                    'entrypoint': '', 'version': '', 'started_at': started,
                    'uptime_s': max(0, now - started), 'idle_s': 0,
                    'rss_mb': round(_rss_mb(pid), 1)})
    return sorted(out, key=lambda s: s['started_at'])
