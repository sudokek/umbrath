"""Terminal user-interface helpers (pure ASCII, Windows-safe).

Colour is done with plain ANSI escapes, using the same virtual-terminal support
this module already switches on for clearing the screen. That means no
dependencies and nothing to install: it works in Windows Terminal, in modern
conhost, and in every Unix terminal.

Where it is not supported -- an old console, or output piped to a file -- every
paint call returns the text untouched, so the game stays perfectly readable.
The ``NO_COLOR`` convention is honoured, and Options can switch it off.
"""

import os
import re

WIDTH = 62

# Matches an ANSI escape, so text can be measured by what a reader actually
# sees rather than by how many bytes it takes to say it.
ANSI = re.compile(r"\x1b\[[0-9;]*m")

# Escape sequence: erase the whole screen, then park the cursor at the top-left.
CLEAR_SEQUENCE = "\033[2J\033[H"


def _enable_ansi() -> bool:
    """Turn on ANSI escape handling. Returns whether it can be used.

    Non-Windows terminals already understand escapes. Windows consoles need
    virtual-terminal processing switched on first; if that fails (an old
    console, or output piped to a file) we fall back to shelling out.
    """
    if os.name != "nt":
        return True

    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        enable_vt = 0x0004  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        return bool(kernel32.SetConsoleMode(handle, mode.value | enable_vt))
    except (AttributeError, OSError, ValueError):
        return False


_ANSI_READY = _enable_ansi()


def clear_screen() -> None:
    """Clear the terminal without spawning a shell process each frame."""
    if _ANSI_READY:
        print(CLEAR_SEQUENCE, end="")
    else:
        os.system("cls" if os.name == "nt" else "clear")


# --------------------------------------------------------------------------
# Colour
# --------------------------------------------------------------------------

CODES = {
    "reset": "0",
    "bold": "1",
    "dim": "2",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
    "bright_red": "91",
    "bright_green": "92",
    "bright_yellow": "93",
    "bright_magenta": "95",
    "bright_cyan": "96",
}

# Switched off by Options, or by the NO_COLOR convention, or when the terminal
# cannot render escapes at all.
_COLOR_ENABLED = _ANSI_READY and not os.environ.get("NO_COLOR")


def set_color(enabled: bool) -> None:
    """Turn colour on or off for the whole interface."""
    global _COLOR_ENABLED
    _COLOR_ENABLED = bool(enabled) and _ANSI_READY and not os.environ.get("NO_COLOR")


def color_enabled() -> bool:
    """Is colour currently being drawn?"""
    return _COLOR_ENABLED


def paint(text: str, *styles: str) -> str:
    """Wrap text in ANSI styles, or return it untouched when colour is off."""
    if not _COLOR_ENABLED or not styles:
        return text
    codes = ";".join(CODES[style] for style in styles if style in CODES)
    if not codes:
        return text
    return f"\x1b[{codes}m{text}\x1b[0m"


def visible_len(text: str) -> int:
    """Length of text as a reader sees it, ignoring any colour escapes."""
    return len(ANSI.sub("", text))


def rule(char: str = "=", style: str = "dim") -> str:
    """Return a horizontal rule the width of the interface."""
    return paint(char * WIDTH, style)


def center(text: str) -> str:
    """Center text within the interface width, ignoring colour escapes."""
    padding = max(0, WIDTH - visible_len(text))
    left = padding // 2
    return " " * left + text + " " * (padding - left)


def right(text: str) -> str:
    """Right-align text within the interface width, ignoring colour escapes."""
    return " " * max(0, WIDTH - visible_len(text)) + text


def bar(label: str, value: int, maximum: int, slots: int = 10) -> str:
    """Return a simple ASCII meter like ``HP [#####-----]``.

    The filled portion is coloured by how much is left, so a dangerous health
    bar reads as dangerous at a glance rather than needing to be counted.
    """
    fraction = 0.0 if maximum <= 0 else value / maximum
    filled = max(0, min(slots, round(slots * fraction)))

    if fraction <= 0.25:
        style = "bright_red"
    elif fraction <= 0.5:
        style = "bright_yellow"
    else:
        style = "bright_green"

    return (
        f"{label} [{paint('#' * filled, style)}"
        f"{paint('-' * (slots - filled), 'dim')}]"
    )


# Blocky 5x5 ASCII letters, enough for the two words the game ever shouts.
_GLYPHS = {
    "A": ("  #  ", " # # ", "#####", "#   #", "#   #"),
    "D": ("#### ", "#   #", "#   #", "#   #", "#### "),
    "E": ("#####", "#    ", "#### ", "#    ", "#####"),
    "I": ("#####", "  #  ", "  #  ", "  #  ", "#####"),
    "N": ("#   #", "##  #", "# # #", "#  ##", "#   #"),
    "O": (" ### ", "#   #", "#   #", "#   #", " ### "),
    "U": ("#   #", "#   #", "#   #", "#   #", " ### "),
    "W": ("#   #", "#   #", "# # #", "## ##", "#   #"),
    "Y": ("#   #", " # # ", "  #  ", "  #  ", "  #  "),
    " ": ("     ", "     ", "     ", "     ", "     "),
}

BANNER_HEIGHT = 5


def banner(text: str) -> list[str]:
    """Render short text as big ASCII letters, centered in the interface.

    Falls back to a plain centered line for anything it has no glyphs for, so a
    new message can never break the display.
    """
    text = text.upper()
    if any(char not in _GLYPHS for char in text):
        return [center(f"*** {text} ***")]

    rows = []
    for line in range(BANNER_HEIGHT):
        rows.append(center(" ".join(_GLYPHS[char][line] for char in text)).rstrip())
    return rows
