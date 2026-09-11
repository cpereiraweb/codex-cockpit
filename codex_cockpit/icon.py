"""Distinct terminal badge with a small usage bar for the GNOME panel."""
from __future__ import annotations

import math
from pathlib import Path

import cairo

from .collector import DATA_DIR

ICON_DIR = DATA_DIR / "icons"
SIZE = 64

PALETTE = {
    "ok":   (0.31, 0.66, 0.48),
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
    # A terminal silhouette remains distinct from cc-cockpit's circular gauge,
    # even when GNOME scales the badge down to 16–22 pixels.
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_width(8)
    ctx.rectangle(7, 7, 50, 50)
    ctx.set_source_rgb(0.055, 0.12, 0.14)
    ctx.fill_preserve()
    ctx.set_source_rgb(0.08, 0.76, 0.60)
    ctx.stroke()

    # High-contrast >_ mark, drawn as paths to avoid font dependencies.
    ctx.set_source_rgb(0.96, 1.0, 0.99)
    ctx.set_line_width(5)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(17, 20)
    ctx.line_to(28, 29)
    ctx.line_to(17, 38)
    ctx.stroke()
    ctx.move_to(35, 38)
    ctx.line_to(46, 38)
    ctx.stroke()

    ctx.set_line_width(4)
    ctx.set_source_rgba(0.75, 0.85, 0.85, 0.35)
    ctx.move_to(16, 49)
    ctx.line_to(48, 49)
    ctx.stroke()
    p = 0.0 if pct is None else max(0.0, min(100.0, pct)) / 100
    if p > 0:
        ctx.set_source_rgb(*PALETTE[state])
        ctx.move_to(16, 49)
        ctx.line_to(16 + 32 * p, 49)
        ctx.stroke()

    # the loose file covers the old resolver; the hicolor/ copy covers GTK4,
    # which no longer looks for icons outside a theme structure
    surf.write_to_png(str(ICON_DIR / f"{name}.png"))
    surf.write_to_png(str(themed / f"{name}.png"))
    return name


def dot(state: str, size: int = 16, ring: float | None = None) -> str:
    """Coloured dot (or progress ring) for use inside the menu."""
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    tag = f"{state}-{size}" + (f"-{int(ring)}" if ring is not None else "")
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
