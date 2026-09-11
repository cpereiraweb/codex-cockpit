"""Blue terminal mark with the original circular consumption gauge."""
from __future__ import annotations

import math
from pathlib import Path

import cairo

from .collector import DATA_DIR

ICON_DIR = DATA_DIR / "icons"
SIZE = 64

PALETTE = {
    "ok":   (0.22, 0.55, 0.98),
    "warn": (0.85, 0.64, 0.25),
    "crit": (0.85, 0.34, 0.34),
    "idle": (0.55, 0.58, 0.65),
}


def state_for(pct: float | None, warn: float, crit: float) -> str:
    if pct is None:
        return "idle"
    if pct >= crit:
        return "crit"
    if pct >= warn:
        return "warn"
    return "ok"


def render(pct: float | None, state: str, seq: int) -> str:
    """Writes the PNG and returns the name (no extension) for AppIndicator.

    The name changes on every render because the indicator ignores a file whose
    name did not change - its cache does not notice a rewrite at the same path.
    """
    themed = ICON_DIR / "hicolor" / f"{SIZE}x{SIZE}" / "apps"
    themed.mkdir(parents=True, exist_ok=True)
    for old in list(ICON_DIR.glob("codex-cockpit-*.png")) + list(themed.glob("codex-cockpit-*.png")):
        old.unlink(missing_ok=True)

    name = f"codex-cockpit-{seq % 1000}"
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, SIZE, SIZE)
    ctx = cairo.Context(surf)
    # No box or decorative outline: only the original consumption ring and
    # a blue terminal mark. The arc still changes colour at warning thresholds.
    cx = cy = SIZE / 2
    radius = 25
    ctx.set_line_width(7)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_source_rgba(0.40, 0.58, 0.80, 0.30)
    ctx.arc(cx, cy, radius, 0, 2 * math.pi)
    ctx.stroke()
    p = 0.0 if pct is None else max(0.0, min(100.0, pct)) / 100
    if p > 0:
        ctx.set_source_rgb(*PALETTE[state])
        ctx.arc(cx, cy, radius, -math.pi / 2, -math.pi / 2 + 2 * math.pi * p)
        ctx.stroke()

    ctx.set_source_rgb(0.22, 0.55, 0.98)
    ctx.set_line_width(4)
    ctx.move_to(21, 23)
    ctx.line_to(29, 31)
    ctx.line_to(21, 39)
    ctx.stroke()
    ctx.move_to(35, 39)
    ctx.line_to(43, 39)
    ctx.stroke()

    # the loose file covers the old resolver; the hicolor/ copy covers GTK4,
    # which no longer looks for icons outside a theme structure
    surf.write_to_png(str(ICON_DIR / f"{name}.png"))
    surf.write_to_png(str(themed / f"{name}.png"))
    return name


def dot(state: str, size: int = 16, ring: float | None = None) -> str:
    """Coloured dot (or progress ring) for use inside the menu."""
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    tag = f"blue-v2-{state}-{size}" + (f"-{int(ring)}" if ring is not None else "")
    path = ICON_DIR / f"dot-{tag}.png"
    if path.exists():
        return str(path)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = cairo.Context(surf)
    cr, cg, cb = PALETTE[state]
    c = size / 2
    if ring is None:
        ctx.set_source_rgb(cr, cg, cb)
        ctx.arc(c, c, size * 0.30, 0, 2 * math.pi)
        ctx.fill()
    else:
        r = size * 0.36
        ctx.set_line_width(size * 0.16)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_source_rgba(cr, cg, cb, 0.28)
        ctx.arc(c, c, r, 0, 2 * math.pi)
        ctx.stroke()
        p = max(0.0, min(100.0, ring)) / 100
        if p > 0:
            ctx.set_source_rgb(cr, cg, cb)
            ctx.arc(c, c, r, -math.pi / 2, -math.pi / 2 + 2 * math.pi * p)
            ctx.stroke()
    surf.write_to_png(str(path))
    return str(path)
