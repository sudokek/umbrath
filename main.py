"""Run the dark-fantasy RPG from the command line."""

import menu
import saveload
from game import Game


def main() -> None:
    """Show the main menu, then play whichever character it hands back.

    A character's name is their save slot: their Legacy -- relics, blessings,
    echoes, and how many times they have died -- is written back to
    ``saves/<name>.sav`` every time a run ends.
    """
    chosen = menu.run()
    if chosen is None:
        print("Goodbye.")
        return

    legacy, settings = chosen
    game = Game(
        legacy=legacy,
        legacy_path=saveload.character_path(legacy.name),
        settings=settings,
    )
    game.run()


if __name__ == "__main__":
    # Only auto-start when this file is run directly.
    main()
