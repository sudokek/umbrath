"""The main menu, character creation, and the Options screen.

This is the only part of the game that reads from stdin outside the main loop.
It is deliberately kept out of :mod:`game`: a Game is constructed from a
:class:`~models.Legacy` and never prompts, which is what lets tests build one
without a console.

The *logic* here -- which entries exist, which are selectable, what a keystroke
resolves to -- is separated from the *prompting*, so all of it can be tested
without feeding fake input to ``input()``.
"""

from dataclasses import fields, replace

import chargen
import saveload
from models import Legacy, Settings
from ui import (
    center,
    clear_screen,
    frame_bottom,
    frame_top,
    paint,
    right,
    rule,
    set_color,
    wrap,
    set_unicode,
)

CREDIT = "created by sudokek"
MAX_NAME = 24

# key, label, one-line description. Order is the order shown.
ENTRIES = [
    ("new", "New Game", "Rise for the first time."),
    ("continue", "Continue", "Return to your most recent character."),
    ("load", "Load", "Choose from your saved characters."),
    ("options", "Options", "Display and input settings."),
    ("exit", "Exit", "Leave Umbrath."),
]

# Entries that need at least one saved character to do anything.
NEEDS_SAVES = {"continue", "load"}


def selectable(has_saves: bool) -> list[str]:
    """Which menu keys can actually be chosen right now."""
    return [
        key for key, _label, _blurb in ENTRIES
        if has_saves or key not in NEEDS_SAVES
    ]


def resolve_any(choice: str) -> str | None:
    """Which entry a keystroke names, ignoring whether it is available.

    Kept separate from :func:`resolve` so the menu can tell "you picked
    Continue but there is nothing to continue" apart from "that is not a menu
    entry", and say something useful about each.
    """
    text = choice.strip().lower()
    if not text:
        return None

    if text.isdigit():
        index = int(text) - 1
        return ENTRIES[index][0] if 0 <= index < len(ENTRIES) else None

    for key, label, _blurb in ENTRIES:
        if text in (key, label.lower()):
            return key

    matches = [
        key for key, label, _blurb in ENTRIES if label.lower().startswith(text)
    ]
    return matches[0] if len(matches) == 1 else None


def resolve(choice: str, has_saves: bool) -> str | None:
    """Turn a keystroke into a *selectable* menu key, or None.

    Accepts the entry number, the key, the label, or an unambiguous prefix --
    the same courtesy the in-game command parser gives.
    """
    key = resolve_any(choice)
    return key if key in selectable(has_saves) else None


def refusal(choice: str, has_saves: bool) -> str:
    """Explain why a choice did nothing, rather than just repeating the menu."""
    wanted = resolve_any(choice)
    if wanted in NEEDS_SAVES and not has_saves:
        label = next(lbl for key, lbl, _b in ENTRIES if key == wanted)
        return (
            f"  {label} needs a saved character, and you have none yet. "
            "Pick New Game to make one."
        )
    return "  Choose one of the numbers above."


def menu_lines(has_saves: bool) -> list[str]:
    """The main menu as text, with unavailable entries dimmed rather than hidden.

    Showing "Continue" greyed out on a first run explains the game's shape
    better than hiding it does.
    """
    lines = []
    for number, (key, label, blurb) in enumerate(ENTRIES, start=1):
        locked = key in NEEDS_SAVES and not has_saves
        if locked:
            lines.append(
                paint(f"   {number}. {label:<10} -- no saved characters yet", "dim")
            )
        else:
            lines.append(
                f"   {paint(str(number), 'bright_cyan')}. "
                f"{paint(f'{label:<10}', 'bold')} -- {blurb}"
            )
    return lines


# --------------------------------------------------------------------------
# Prompting
# --------------------------------------------------------------------------


def _ask(prompt: str = "> ") -> str:
    """Read one line, treating Ctrl+C/Ctrl+D as an empty answer."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return ""


# Everything the menu wants to tell the player between screens. It is drawn as
# part of the *next* screen rather than printed after the current one, which is
# the same trick game.py plays with self.message: without it a message printed
# at the bottom of a loop is wiped by the clear at the top of the next pass,
# and the player never sees it.
_notice = ""


def notify(text: str) -> None:
    """Queue a line to appear on the next screen drawn."""
    global _notice
    _notice = text


def screen(*blocks: str | None) -> None:
    """Draw one whole screen: clear, print the blocks, then any pending notice.

    Every menu screen goes through here, so no screen can accumulate under
    another one and no message can be shown too briefly to read.
    """
    global _notice
    clear_screen()
    for block in blocks:
        if block is not None:
            print(block)
    if _notice:
        print()
        print(paint(_notice, "bright_yellow"))
        _notice = ""


def _title_block() -> str:
    """The banner, as one block of text."""
    return "\n".join([
        rule("="),
        center(paint("UMBRATH", "bold", "bright_red")),
        center(paint("a dominion is not given back; it is taken", "dim")),
        rule("="),
    ])


def show_main_menu(has_saves: bool) -> None:
    """Draw the whole title screen, from the top of a cleared screen."""
    screen(
        _title_block(),
        "",
        "\n".join(menu_lines(has_saves)),
        "",
        right(paint(CREDIT, "dim")),
    )


# --------------------------------------------------------------------------
# Screens
# --------------------------------------------------------------------------


def choose_saved_character(characters) -> Legacy | None:
    """Pick from the saved characters. None to go back."""
    while True:
        rows = []
        for number, (_path, legacy, _when) in enumerate(characters, start=1):
            origin = chargen.get(legacy.origin)
            rows.append(
                f"   {paint(str(number), 'bright_cyan')}. "
                f"{paint(legacy.name, 'bold')} the {origin.name} "
                f"-- {legacy.runs} run(s), {legacy.victories} victory(s), "
                f"{legacy.echoes} echo(es)"
            )
        rows.append("   b. Back")

        screen(
            frame_top("Your histories"),
            "\n".join(rows),
            frame_bottom(),
        )

        choice = _ask()
        if not choice or choice.lower() in {"b", "back"}:
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(characters):
            return characters[int(choice) - 1][1]
        notify("  No such history.")


def _ask_name() -> str | None:
    """First screen of creation: the name. None if the player backs out."""
    screen(
        frame_top("A new history"),
        "",
        center(paint("What name will they curse?", "bold")),
        "",
        center(paint("(blank to go back)", "dim")),
        "",
        frame_bottom(),
    )
    return _ask()[:MAX_NAME] or None


def _ask_origin(name: str):
    """Second screen: the origin. None if the player backs out.

    Redrawn whole on a bad answer, so the list is always on screen next to the
    question rather than scrolled off above it.
    """
    while True:
        screen(
            frame_top(f"What was {name}, before the blood?"),
            "\n".join(chargen.listing()),
            frame_bottom(),
        )
        choice = _ask("Choose a number> ")
        if not choice:
            return None
        origin = chargen.by_number(choice)
        if origin is not None:
            return origin
        notify("  No such origin. Pick one of the numbers above.")


def _confirm_character(name: str, origin) -> None:
    """Third screen: what they have become."""
    screen(
        frame_top("Risen"),
        "",
        center(paint(f"{name}, {origin.name}", "bold", "bright_red")),
        "",
        wrap(origin.blurb),
        "",
        wrap(f"You begin with: {origin.summary()}"),
        "",
        frame_bottom(),
    )
    _ask("Press Enter to rise.")


def create_character() -> Legacy | None:
    """Ask for a name and an origin. None if the player backs out.

    Three screens rather than one: together they ran to thirty lines, which
    scrolled the question off the top of a standard terminal.
    """
    name = _ask_name()
    if not name:
        return None

    origin = _ask_origin(name)
    if origin is None:
        return None

    legacy = Legacy(name=name, origin=origin.key)
    _confirm_character(name, origin)

    # Write the slot straight away so Continue works before the first death.
    saveload.save_legacy(legacy, saveload.character_path(name))
    return legacy


def option_rows(settings: Settings) -> list[tuple[str, object]]:
    """Every editable setting as ``(name, value)``, in declaration order."""
    return [(field.name, getattr(settings, field.name)) for field in fields(settings)]


def edit_options(settings: Settings) -> Settings:
    """The Options screen. Returns the settings to keep."""
    working = replace(settings)

    while True:
        rows = []
        for number, (name, value) in enumerate(option_rows(working), start=1):
            # Wide enough for the longest setting name, so values stay aligned.
            shown = paint("on", "bright_green") if value is True else (
                paint("off", "dim") if value is False else paint(str(value), "bone")
            )
            rows.append(f"   {paint(f'{number:>2}', 'bright_cyan')}. {name:<28} {shown}")
        rows.append("")
        rows.append("    s. Save and go back")
        rows.append("    b. Back without saving")

        screen(
            frame_top("Options"),
            "\n".join(rows),
            frame_bottom(),
        )

        choice = _ask()
        if not choice or choice.lower() in {"b", "back"}:
            return settings
        if choice.lower() in {"s", "save"}:
            saveload.save_options(working)
            set_color(working.color)
            set_unicode(working.line_drawing)
            notify("  Saved.")
            return working

        rows = option_rows(working)
        if not (choice.isdigit() and 1 <= int(choice) <= len(rows)):
            notify("  No such option.")
            continue

        name, value = rows[int(choice) - 1]
        if isinstance(value, bool):
            setattr(working, name, not value)
            if name == "color":
                # Apply at once so the screen shows what it will look like.
                set_color(working.color)
            elif name == "line_drawing":
                set_unicode(working.line_drawing)
        else:
            raw = _ask(f"  New value for {name}> ")
            try:
                new_value = int(raw)
            except ValueError:
                notify("  That is not a number.")
                continue
            if name == "min_command_prefix" and not 1 <= new_value <= 10:
                notify("  min_command_prefix must be between 1 and 10.")
                continue
            setattr(working, name, new_value)


def run() -> tuple[Legacy, Settings] | None:
    """Drive the title screen. Returns the character and settings to play, or None."""
    settings = saveload.load_options()
    set_color(settings.color)
    set_unicode(settings.line_drawing)

    while True:
        characters = saveload.list_characters()
        show_main_menu(bool(characters))

        choice = _ask()
        key = resolve(choice, bool(characters))

        if key == "exit":
            return None
        if key == "new":
            legacy = create_character()
            if legacy is not None:
                return legacy, settings
        elif key == "continue":
            # list_characters is newest-first, so this is the last one played.
            return characters[0][1], settings
        elif key == "load":
            legacy = choose_saved_character(characters)
            if legacy is not None:
                return legacy, settings
        elif key == "options":
            settings = edit_options(settings)
        elif key is None:
            notify(refusal(choice, bool(characters)))
