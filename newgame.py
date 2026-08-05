"""Character creation and save-slot selection, at the terminal.

This is the only part of the game that reads from stdin outside the main loop.
It is kept out of :mod:`game` on purpose: the Game object is constructed from a
:class:`~models.Legacy` and never prompts, which is what lets tests build one
without a console.

A character's name *is* their save slot. Two names, two separate ongoing
stories, each with its own relics, blessings, and echoes.
"""

import os

import chargen
import saveload
from models import Legacy
from ui import center, rule

SAVE_DIR = saveload.SAVE_DIR
MAX_NAME = 24


def legacy_path(name: str) -> str:
    """Where the character called ``name`` is stored."""
    return saveload.character_path(name)


def existing_characters() -> list[tuple[str, Legacy]]:
    """Every character already saved, newest-looking first by name."""
    directory = saveload.resolve_save_path(SAVE_DIR)
    if not os.path.isdir(directory):
        return []

    found = []
    for entry in sorted(os.listdir(directory)):
        if not entry.endswith(".sav"):
            continue
        legacy = saveload.load_legacy(os.path.join(SAVE_DIR, entry))
        # A file that will not parse comes back as a default Legacy; skip those
        # rather than offering the player a slot that has lost its name.
        if legacy.name and legacy.name != Legacy.name:
            found.append((entry, legacy))
    return found


def _ask(prompt: str) -> str:
    """Read one line, treating Ctrl+C/Ctrl+D as an empty answer."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def _banner() -> None:
    print(rule("="))
    print(center("UMBRATH"))
    print(center("a dominion is not given back; it is taken"))
    print(rule("="))
    print()


def choose_character() -> Legacy | None:
    """Run the title flow and return the Legacy to play, or None to quit."""
    _banner()

    saved = existing_characters()
    if saved:
        print("Your histories:")
        for number, (_, legacy) in enumerate(saved, start=1):
            origin = chargen.get(legacy.origin)
            print(
                f"  {number}. {legacy.name} the {origin.name} "
                f"-- {legacy.runs} run(s), {legacy.victories} victory(s), "
                f"{legacy.echoes} echo(es)"
            )
        print("  n. Begin a new history")
        print("  q. Leave")
        print()

        choice = _ask("> ").lower()
        if choice in {"q", "quit", "exit"}:
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(saved):
            return saved[int(choice) - 1][1]
        # Anything else falls through to making someone new.

    return create_character()


def create_character() -> Legacy | None:
    """Ask for a name and an origin. None if the player backs out."""
    print()
    print("What name will they curse?")
    name = _ask("> ")[:MAX_NAME]
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

    return legacy
