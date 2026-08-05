"""Terminal user-interface helpers (pure ASCII, Windows-safe)."""

import os

WIDTH = 62

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


def rule(char: str = "=") -> str:
    """Return a horizontal rule the width of the interface."""
    return char * WIDTH


def center(text: str) -> str:
    """Center a short piece of text within the interface width."""
    return text.center(WIDTH)


def right(text: str) -> str:
    """Right-align a short piece of text within the interface width."""
    return text.rjust(WIDTH)


def bar(label: str, value: int, maximum: int, slots: int = 10) -> str:
    """Return a simple ASCII meter like ``HP [#####-----]``."""
    filled = 0 if maximum <= 0 else round(slots * value / maximum)
    filled = max(0, min(slots, filled))
    return f"{label} [{'#' * filled}{'-' * (slots - filled)}]"


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
