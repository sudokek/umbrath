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
from ui import center, clear_screen, paint, right, rule, set_color

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


def _title() -> None:
    print(rule("="))
    print(center(paint("UMBRATH", "bold", "bright_red")))
    print(center(paint("a dominion is not given back; it is taken", "dim")))
    print(rule("="))


def _footer() -> None:
    """The credit line. Shown, never offered as a choice."""
    print()
    print(right(paint(CREDIT, "dim")))


def show_main_menu(has_saves: bool) -> None:
    """Draw the whole title screen, from the top of a cleared screen."""
    clear_screen()
    _title()
    print()
    for line in menu_lines(has_saves):
        print(line)
    _footer()
    print()


# --------------------------------------------------------------------------
# Screens
# --------------------------------------------------------------------------


def choose_saved_character(characters) -> Legacy | None:
    """Pick from the saved characters. None to go back."""
    clear_screen()
    print(rule("-"))
    print(paint("Your histories:", "bold"))
    for number, (_path, legacy, _when) in enumerate(characters, start=1):
        origin = chargen.get(legacy.origin)
        print(
            f"   {number}. {legacy.name} the {origin.name} "
            f"-- {legacy.runs} run(s), {legacy.victories} victory(s), "
            f"{legacy.echoes} echo(es)"
        )
    print("   b. Back")
    print(rule("-"))

    while True:
        choice = _ask()
        if not choice or choice.lower() in {"b", "back"}:
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(characters):
            return characters[int(choice) - 1][1]
        print("  No such history.")


def create_character() -> Legacy | None:
    """Ask for a name and an origin. None if the player backs out."""
    clear_screen()
    print(paint("What name will they curse?", "bold"))
    name = _ask()[:MAX_NAME]
    if not name:
        return None

    print()
    print(f"And what was {name}, before the blood?")
    print()
    for line in chargen.listing():
        print(line)

    origin = None
    while origin is None:
        choice = _ask("Choose a number> ")
        if not choice:
            return None
        origin = chargen.by_number(choice)
        if origin is None:
            print("  No such origin. Try the number beside it.")

    legacy = Legacy(name=name, origin=origin.key)

    print()
    print(rule("-"))
    print(f"{name}, {origin.name}.")
    print(f"  {origin.blurb}")
    print(f"  You begin with: {origin.summary()}")
    print(rule("-"))
    print()
    _ask("Press Enter to rise.")

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
        clear_screen()
        print(rule("-"))
        print(paint("Options", "bold"))
        for number, (name, value) in enumerate(option_rows(working), start=1):
            # Wide enough for the longest setting name, so values stay aligned.
            print(f"   {number:>2}. {name:<28} {value}")
        print("    s. Save and go back")
        print("    b. Back without saving")
        print(rule("-"))

        choice = _ask()
        if not choice or choice.lower() in {"b", "back"}:
            return settings
        if choice.lower() in {"s", "save"}:
            saveload.save_options(working)
            set_color(working.color)
            print("  Saved.")
            return working

        rows = option_rows(working)
        if not (choice.isdigit() and 1 <= int(choice) <= len(rows)):
            print("  No such option.")
            continue

        name, value = rows[int(choice) - 1]
        if isinstance(value, bool):
            setattr(working, name, not value)
            if name == "color":
                # Apply at once so the screen shows what it will look like.
                set_color(working.color)
        else:
            raw = _ask(f"  New value for {name}> ")
            try:
                new_value = int(raw)
            except ValueError:
                print("  That is not a number.")
                continue
            if name == "min_command_prefix" and not 1 <= new_value <= 10:
                print("  min_command_prefix must be between 1 and 10.")
                continue
            setattr(working, name, new_value)


def run() -> tuple[Legacy, Settings] | None:
    """Drive the title screen. Returns the character and settings to play, or None."""
    settings = saveload.load_options()
    set_color(settings.color)

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
            print(refusal(choice, bool(characters)))
            _ask("  Press Enter to continue.")
