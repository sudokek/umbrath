"""Run the dark-fantasy RPG from the command line."""

import newgame
from game import Game


def main() -> None:
    """Pick or create a character, then play them until they stop.

    The character's name is their save slot: their Legacy -- relics, blessings,
    echoes, and how many times they have died -- is written back to
    ``saves/<name>.sav`` every time a run ends.
    """
    legacy = newgame.choose_character()
    if legacy is None:
        print("Goodbye.")
        return

    game = Game(legacy=legacy, legacy_path=newgame.legacy_path(legacy.name))
    game.run()


if __name__ == "__main__":
    # Only auto-start when this file is run directly.
    main()
