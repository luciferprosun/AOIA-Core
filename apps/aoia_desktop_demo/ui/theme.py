"""Lightweight dark visual system for the competition demo.

System fonts only; no bundled fonts, images, or animation libraries.
"""

from __future__ import annotations

BG = "#0d1117"          # near-black charcoal
PANEL = "#161b22"        # dark slate
PANEL_ALT = "#1c2430"
ACCENT = "#22d3ee"       # cyan
ACCENT_SECONDARY = "#8b5cf6"  # restrained violet
TEXT = "#e6edf3"         # high-contrast off-white
TEXT_MUTED = "#8b949e"   # neutral grey
WARN = "#f59e0b"         # amber
ERROR = "#ef4444"        # red
BORDER = "#30363d"

FONT_FAMILY = "TkDefaultFont"
FONT_SIZE_NORMAL = 10
FONT_SIZE_SMALL = 9
FONT_SIZE_HEADING = 13


def base_font(size: int = FONT_SIZE_NORMAL, weight: str = "normal") -> tuple:
    return (FONT_FAMILY, size, weight)
