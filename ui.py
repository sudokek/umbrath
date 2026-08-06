"""Terminal user-interface helpers: colour, box-drawing, and layout.

Everything here is written with bytes the terminal already understands, so the
game stays a ``git clone`` and ``python main.py`` with nothing to install.

Two things do the visual work, and both degrade rather than break:

* **Colour** -- 24-bit ANSI where the terminal advertises it (``COLORTERM``),
  falling back to the 16 basic colours, and to no colour at all on a console
  that cannot render escapes or when ``NO_COLOR`` is set.
* **Box-drawing** -- real line characters for frames and map corridors, falling
  back to ``-`` and ``|`` when the console's encoding cannot carry them.

Both are detected at import, can be forced either way from Options, and are
measured with :func:`visible_len` so the layout is identical whichever is in
use.
"""

import os
import re
import sys

WIDTH = 62

# Matches an ANSI escape, so text can be measured by what a reader actually
# sees rather than by how many bytes it takes to say it.
ANSI = re.compile(r"\x1b\[[0-9;]*m")

# Escape sequence: erase the whole screen, then park the cursor at the top-left.
# Erase the screen, erase the *scrollback*, then home the cursor. The 3J is the
# part that matters: without it "clearing" only pushes the old frame up out of
# view, and every previous turn is still there to scroll back through.
CLEAR_SEQUENCE = "\033[2J\033[3J\033[H"

# The alternate screen buffer -- the same thing vim and less use. While it is
# active the terminal has no scrollback at all, and leaving it puts back
# whatever the player had on screen before the game started.
ENTER_FULLSCREEN = "\033[?1049h"
EXIT_FULLSCREEN = "\033[?1049l"


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


# --------------------------------------------------------------------------
# Box drawing
# --------------------------------------------------------------------------

# Real line characters, and the ASCII the game falls back to. The keys are the
# same either way, so drawing code never has to ask which set is in use.
GLYPHS = {
    "unicode": {
        "h": "─", "v": "│",
        "tl": "┌", "tr": "┐", "bl": "└", "br": "┘",
        "lt": "├", "rt": "┤", "cross": "┼",
        "heavy_h": "━", "dot": "·", "block": "█",
    },
    "ascii": {
        "h": "-", "v": "|",
        "tl": "+", "tr": "+", "bl": "+", "br": "+",
        "lt": "+", "rt": "+", "cross": "+",
        "heavy_h": "=", "dot": ".", "block": "#",
    },
}


def _unicode_safe() -> bool:
    """Can this console actually print box-drawing characters?

    Windows consoles still run on legacy code pages in places, where printing a
    box character raises or turns into mojibake. Rather than guess from the
    platform, try to encode one and believe the answer. stdout is nudged to
    UTF-8 first, which is enough on any modern terminal.
    """
    stream = sys.stdout
    encoding = getattr(stream, "encoding", None)

    if encoding and encoding.lower().replace("-", "") not in {"utf8", "utf16", "utf32"}:
        try:
            stream.reconfigure(encoding="utf-8")
            encoding = "utf-8"
        except (AttributeError, OSError, ValueError):
            pass

    try:
        "".join(GLYPHS["unicode"].values()).encode(encoding or "ascii")
        return True
    except (LookupError, UnicodeEncodeError):
        return False


_UNICODE_READY = _unicode_safe()
_UNICODE_ENABLED = _UNICODE_READY


def set_unicode(enabled: bool) -> None:
    """Turn box-drawing characters on or off for the whole interface."""
    global _UNICODE_ENABLED
    _UNICODE_ENABLED = bool(enabled) and _UNICODE_READY


def unicode_enabled() -> bool:
    """Are box-drawing characters currently being drawn?"""
    return _UNICODE_ENABLED


def glyph(name: str) -> str:
    """One drawing character, from whichever set is currently in use."""
    return GLYPHS["unicode" if _UNICODE_ENABLED else "ascii"][name]


def clear_screen() -> None:
    """Clear the terminal, scrollback included, without spawning a shell."""
    if _ANSI_READY:
        print(CLEAR_SEQUENCE, end="", flush=True)
    else:
        os.system("cls" if os.name == "nt" else "clear")


_fullscreen = False


def enter_fullscreen() -> None:
    """Switch to the alternate screen buffer, if the terminal has one.

    This is what actually makes old turns unreachable: on the alternate buffer
    there is no scrollback to scroll, so a cleared frame is gone rather than
    merely out of view. Safe to call twice.
    """
    global _fullscreen
    if _ANSI_READY and not _fullscreen:
        print(ENTER_FULLSCREEN, end="", flush=True)
        _fullscreen = True
        clear_screen()


def exit_fullscreen() -> None:
    """Return to the normal buffer, restoring whatever was on screen before.

    Must run even when the game crashes, or the player is left on an empty
    alternate buffer with no obvious way back.
    """
    global _fullscreen
    if _ANSI_READY and _fullscreen:
        print(EXIT_FULLSCREEN, end="", flush=True)
        _fullscreen = False


# --------------------------------------------------------------------------
# Colour
# --------------------------------------------------------------------------

CODES = {
    "reset": "0",
    "bold": "1",
    "dim": "2",
    "italic": "3",
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

# Where the terminal advertises 24-bit colour, named styles are drawn from this
# palette instead of the 16 basic ones. Chosen to suit a game about barrows,
# ash, and ice: desaturated stone with a few things that glow.
TRUECOLOR = {
    "red": (155, 45, 45),
    "green": (110, 150, 85),
    "yellow": (200, 165, 90),
    "blue": (85, 115, 165),
    "magenta": (150, 95, 160),
    "cyan": (110, 160, 175),
    "white": (215, 210, 200),
    "bright_red": (215, 65, 55),
    "bright_green": (150, 200, 115),
    "bright_yellow": (240, 205, 115),
    "bright_magenta": (205, 135, 215),
    "bright_cyan": (150, 210, 225),
    # Frame and furniture, with no 16-colour equivalent worth naming.
    "stone": (120, 115, 110),
    "blood": (135, 25, 30),
    "bone": (200, 195, 175),
}


def _truecolor_available() -> bool:
    """Does the terminal advertise 24-bit colour?

    Windows Terminal sets neither COLORTERM nor TERM, but has supported
    truecolor since it shipped, so WT_SESSION counts as a yes.
    """
    if os.environ.get("COLORTERM", "").lower() in {"truecolor", "24bit"}:
        return True
    return bool(os.environ.get("WT_SESSION"))


_TRUECOLOR = _truecolor_available()

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


def _code_for(style: str) -> str | None:
    """The escape parameters for one style name, or None if it is unknown."""
    if _TRUECOLOR and style in TRUECOLOR:
        red, green, blue = TRUECOLOR[style]
        return f"38;2;{red};{green};{blue}"
    return CODES.get(style)


def paint(text: str, *styles: str) -> str:
    """Wrap text in ANSI styles, or return it untouched when colour is off.

    Named colours resolve to the 24-bit palette where the terminal supports it
    and to the 16 basic colours otherwise, so calling code never has to care.
    """
    if not _COLOR_ENABLED or not styles:
        return text
    resolved = [_code_for(style) for style in styles]
    codes = ";".join(code for code in resolved if code)
    if not codes:
        return text
    return f"\x1b[{codes}m{text}\x1b[0m"


def visible_len(text: str) -> int:
    """Length of text as a reader sees it, ignoring any colour escapes."""
    return len(ANSI.sub("", text))


def rule(char: str = "=", style: str = "stone") -> str:
    """Return a horizontal rule the width of the interface.

    The legacy ``"="``/``"-"`` arguments are read as *weight* rather than taken
    literally, so existing callers get a proper drawn line where the console can
    show one and their original character where it cannot.
    """
    drawn = {"=": glyph("heavy_h"), "-": glyph("h")}.get(char, char)
    return paint(drawn * WIDTH, style)


def frame_top(title: str = "", style: str = "stone") -> str:
    """The top edge of a panel, optionally with a title set into it."""
    return _edge(glyph("tl"), glyph("tr"), title, style)


def frame_bottom(title: str = "", style: str = "stone") -> str:
    """The bottom edge of a panel."""
    return _edge(glyph("bl"), glyph("br"), title, style)


def frame_divider(title: str = "", style: str = "stone") -> str:
    """A divider between two sections of the same panel."""
    return _edge(glyph("lt"), glyph("rt"), title, style)


def _edge(left: str, right: str, title: str, style: str) -> str:
    """One horizontal edge of a panel, with an optional inset title."""
    horizontal = glyph("h")
    plain = paint(left + horizontal * (WIDTH - 2) + right, style)

    if not title:
        return plain

    label = f" {title} "
    room = WIDTH - 2 - len(label)
    if room < 2:
        return plain

    lead = 2
    return (
        paint(left + horizontal * lead, style)
        + paint(label, "bone", "bold")
        + paint(horizontal * (room - lead) + right, style)
    )


def center(text: str) -> str:
    """Center text within the interface width, ignoring colour escapes."""
    padding = max(0, WIDTH - visible_len(text))
    left = padding // 2
    return " " * left + text + " " * (padding - left)


def right(text: str) -> str:
    """Right-align text within the interface width, ignoring colour escapes."""
    return " " * max(0, WIDTH - visible_len(text)) + text


ELLIPSIS = "..."


def fit(text: str, width: int) -> str:
    """Trim text to a column, breaking at a word and marking the cut.

    The result is never wider than ``width``: the ellipsis counts toward the
    budget, and one column of overflow is all it takes to break a frame.
    """
    if len(text) <= width:
        return text
    clipped = text[: max(0, width - len(ELLIPSIS))]
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return clipped.rstrip() + ELLIPSIS


def wrap(text: str, indent: str = "  ") -> str:
    """Fold prose to the interface width so it can never break a frame.

    Plain text only -- wrapping would count colour escapes as characters, so
    paint the result rather than the input.
    """
    words = text.split()
    if not words:
        return indent

    lines, current = [], indent
    for word in words:
        candidate = word if current.strip() == "" else f"{current} {word}"
        if len(candidate) > WIDTH and current.strip():
            lines.append(current)
            current = f"{indent}{word}"
        else:
            current = candidate if current.strip() else f"{indent}{word}"
    lines.append(current)
    return "\n".join(lines)


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
