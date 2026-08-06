"""Run the dark-fantasy RPG from the command line."""

import menu
import saveload
import ui
from game import Game


def main() -> None:
    """Show the main menu, then play whichever character it hands back.

    A character's name is their save slot: their Legacy -- relics, blessings,
    echoes, and how many times they have died -- is written back to
    ``saves/<name>.sav`` every time a run ends.

    The whole session runs on the terminal's alternate screen buffer, so a
    cleared frame is genuinely gone rather than pushed up into scrollback, and
    quitting hands the terminal back exactly as it was found.
    """
    ui.enter_fullscreen()
    try:
        chosen = menu.run()
        if chosen is None:
            return

        legacy, settings = chosen
        game = Game(
            legacy=legacy,
            legacy_path=saveload.character_path(legacy.name),
            settings=settings,
        )
        game.run()
    finally:
        # Even on a crash. Leaving the player stranded on an empty alternate
        # buffer, with their own shell apparently gone, is far worse than any
        # traceback they might have seen instead.
        ui.exit_fullscreen()

    print("Goodbye.")


if __name__ == "__main__":
    # Only auto-start when this file is run directly.
    main()
