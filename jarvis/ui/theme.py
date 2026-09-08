"""UI theme (re-exports the central colour palette from config).

Supports both a light (default) and a dark palette, switchable at runtime via
`theme.set_mode("light" | "dark")`.  All consumer modules read colours through
this module's attributes (e.g. ``theme.ACCENT``), so once the globals are
reassigned the next read picks up the new palette.  Import via::

    from jarvis.ui import theme
    theme.set_mode("dark")

Each mode is a plain dict; `set_mode` copies the chosen palette onto this
module's attributes so existing attribute-style access keeps working.
"""

from config import config

FONT_FAMILY = config.FONT_FAMILY
FONT_MONO = config.FONT_MONO

# ---------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------
_light = {
    "BG": "#ffffff",
    "PANEL": "#f4f7fc",
    "PANEL_2": "#eef3fa",
    "INPUT_BG": "#f2f6fb",
    "ACCENT": "#1e6fff",
    "ACCENT_SUB": "#a9c7ff",
    "ACCENT_WARN": config.ACCENT_WARN,
    "ACCENT_OK": config.ACCENT_OK,
    "ACCENT_ERR": config.ACCENT_ERR,
    "TEXT": "#0f2550",
    "MUTED": "#5b6b87",
    "BORDER": "#d7e2f2",
    "HOVER_BG": "#e6eefb",
    "CORNER": "#000002",
    "BODY": "#ffffff",
    "BODY_RAISED": "#fbfdff",
    "GLASS": "#f4f7fc",
    "GLASS_2": "#e9f1fb",
    "GLASS_3": "#e2ebf8",
    "GLASS_BORDER": "#d7e2f2",
    "GLASS_BORDER_HOT": "#1e6fff",
    "USER_BUBBLE": "#1e6fff",
    "USER_BUBBLE_EDGE": "#2f7bff",
    "AI_BUBBLE": "#eef3fa",
    "AI_BUBBLE_EDGE": "#d7e2f2",
    "CHIP": "#eef3fa",
    "VIS_IDLE": "#a9c7ff",
    "VIS_THINK": "#1e6fff",
    "VIS_SPEAK": "#1e6fff",
    "VIS_LISTEN": "#1e6fff",
}

_dark = {
    "BG": "#0b0f19",
    "PANEL": "#111827",
    "PANEL_2": "#1a2332",
    "INPUT_BG": "#0f1622",
    "ACCENT": "#3b82f6",
    "ACCENT_SUB": "#7fb0ff",
    "ACCENT_WARN": "#f59e0b",
    "ACCENT_OK": "#22c55e",
    "ACCENT_ERR": "#f87171",
    "TEXT": "#e2e8f0",
    "MUTED": "#94a3b8",
    "BORDER": "#2e3d5c",
    "HOVER_BG": "#1c2740",
    "CORNER": "#000002",
    "BODY": "#0b0f19",
    "BODY_RAISED": "#111827",
    "GLASS": "#101826",
    "GLASS_2": "#182233",
    "GLASS_3": "#1f2b3f",
    "GLASS_BORDER": "#2e3d5c",
    "GLASS_BORDER_HOT": "#3b82f6",
    "USER_BUBBLE": "#2f6fed",
    "USER_BUBBLE_EDGE": "#4a82ff",
    "AI_BUBBLE": "#1a2436",
    "AI_BUBBLE_EDGE": "#2e3d5c",
    "CHIP": "#141d2e",
    "VIS_IDLE": "#7fb0ff",
    "VIS_THINK": "#3b82f6",
    "VIS_SPEAK": "#3b82f6",
    "VIS_LISTEN": "#3b82f6",
}

PALETTES = {"light": _light, "dark": _dark}

_current_mode = "light"


def set_mode(mode: str) -> None:
    """Switch the active palette to ``light`` or ``dark``."""
    global _current_mode
    mode = mode if mode in PALETTES else "light"
    _current_mode = mode
    palette = PALETTES[mode]
    globals().update(palette)
    _refresh_derived()


def current_mode() -> str:
    return _current_mode


def is_dark() -> bool:
    return _current_mode == "dark"


def toggle() -> str:
    """Flip to the other mode and return the new mode name."""
    set_mode("dark" if current_mode() != "dark" else "light")
    return current_mode()


# ---------------------------------------------------------------------
# Typography (shared across both palettes)
# ---------------------------------------------------------------------
SEA = "Inter"
APP_TITLE = (SEA, 15, "bold")
APP_SUB = (SEA, 9)
CHIP_STATE = (SEA, 11, "bold")
CHIP_HINT = (SEA, 9)
HEADER = (SEA, 12, "bold")
HEADER_HINT = (SEA, 9)
ACTION_LABEL = (SEA, 11)
ACTION_ICON = (SEA, 12)
CHAT_LABEL = (SEA, 8, "bold")
CHAT_BODY = (SEA, 11)
CHAT_SYSTEM = (SEA, 9)
TIME = (SEA, 11)
STATUS = (SEA, 10)
CHAT_BODY_ALT = (SEA, 11)


def _refresh_derived():
    globals()["ACCENT_LABEL"] = globals().get("ACCENT", _light["ACCENT"])


# Load the default (light) palette and derive the composite styles.
set_mode("light")
