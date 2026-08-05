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
from ui import WIDTH, center, right, rule

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


def resolve(choice: str, has_saves: bool) -> str | None:
    """Turn a keystroke into a menu key, or None if it means nothing.

    Accepts the entry number, the key, the label, or an unambiguous prefix --
    the same courtesy the in-game command parser gives.
    """
    text = choice.strip().lower()
    if not text:
        return None

    allowed = selectable(has_saves)

    if text.isdigit():
        index = int(text) - 1
        if 0 <= index < len(ENTRIES):
            key = ENTRIES[index][0]
            return key if key in allowed else None
        return None

    for key, label, _blurb in ENTRIES:
        if text in (key, label.lower()):
            return key if key in allowed else None

    matches = [
        key for key, label, _blurb in ENTRIES
        if label.lower().startswith(text) and key in allowed
    ]
    return matches[0] if len(matches) == 1 else None


def menu_lines(has_saves: bool) -> list[str]:
    """The main menu as text, with unavailable entries marked rather than hidden.

    Showing "Continue" greyed out on a first run explains the game's shape
    better than hiding it does.
    """
    lines = []
    for number, (key, label, blurb) in enumerate(ENTRIES, start=1):
        if key in NEEDS_SAVES and not has_saves:
            lines.append(f"   {number}. {label:<10} -- no saved characters yet")
        else:
            lines.append(f"   {number}. {label:<10} -- {blurb}")
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
    print(center("UMBRATH"))
    print(center("a dominion is not given back; it is taken"))
    print(rule("="))


def _footer() -> None:
    """The credit line. Shown, never offered as a choice."""
    print()
    print(right(CREDIT))


def show_main_menu(has_saves: bool) -> None:
    """Draw the whole title screen."""
    print()
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
    print()
    print(rule("-"))
    print("Your histories:")
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
    print()
    print("What name will they curse?")
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
        print()
        print(rule("-"))
        print("Options")
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
            print("  Saved.")
            return working

        rows = option_rows(working)
        if not (choice.isdigit() and 1 <= int(choice) <= len(rows)):
            print("  No such option.")
            continue

        name, value = rows[int(choice) - 1]
        if isinstance(value, bool):
            setattr(working, name, not value)
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

    while True:
        characters = saveload.list_characters()
        show_main_menu(bool(characters))

        key = resolve(_ask(), bool(characters))

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
            print("  Choose one of the numbers above.")
