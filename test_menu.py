"""Tests for the main menu, its options screen, and save-slot listing.

The menu's decision-making is separated from its prompting, so everything here
runs without feeding fake keystrokes to ``input()``.
"""

import contextlib
import io
import os
import tempfile
import time
import unittest
import unittest.mock

import chargen
import menu
import saveload
from models import Legacy, Settings
from ui import WIDTH, visible_len


class MenuChoiceTests(unittest.TestCase):
    """Turning a keystroke into a menu action."""

    def test_numbers_pick_entries_in_order(self):
        expected = [key for key, _label, _blurb in menu.ENTRIES]
        for number, key in enumerate(expected, start=1):
            self.assertEqual(menu.resolve(str(number), has_saves=True), key)

    def test_names_and_prefixes_work(self):
        self.assertEqual(menu.resolve("new", has_saves=True), "new")
        self.assertEqual(menu.resolve("New Game", has_saves=True), "new")
        self.assertEqual(menu.resolve("opt", has_saves=True), "options")
        self.assertEqual(menu.resolve("EXIT", has_saves=True), "exit")

    def test_nonsense_resolves_to_nothing(self):
        for junk in ("", "   ", "99", "0", "-1", "zzz"):
            self.assertIsNone(menu.resolve(junk, has_saves=True), junk)

    def test_continue_and_load_are_locked_without_saves(self):
        for key in ("continue", "load", "2", "3"):
            self.assertIsNone(menu.resolve(key, has_saves=False), key)

    def test_the_rest_still_works_without_saves(self):
        self.assertEqual(menu.resolve("1", has_saves=False), "new")
        self.assertEqual(menu.resolve("4", has_saves=False), "options")
        self.assertEqual(menu.resolve("5", has_saves=False), "exit")

    def test_selectable_reflects_whether_saves_exist(self):
        self.assertEqual(menu.selectable(False), ["new", "options", "exit"])
        self.assertEqual(
            menu.selectable(True), ["new", "continue", "load", "options", "exit"]
        )


class MenuDisplayTests(unittest.TestCase):
    """What the title screen shows."""

    def test_every_entry_is_listed_either_way(self):
        for has_saves in (True, False):
            text = "\n".join(menu.menu_lines(has_saves))
            for _key, label, _blurb in menu.ENTRIES:
                self.assertIn(label, text, f"has_saves={has_saves}")

    def test_locked_entries_say_why(self):
        text = "\n".join(menu.menu_lines(has_saves=False))
        self.assertIn("no saved characters yet", text)

    def test_credit_is_shown_but_is_not_a_choice(self):
        # It must never be selectable, by number or by name.
        self.assertNotIn(menu.CREDIT.lower(), [k for k, _l, _b in menu.ENTRIES])
        self.assertIsNone(menu.resolve(menu.CREDIT, has_saves=True))
        self.assertIsNone(menu.resolve("sudokek", has_saves=True))
        self.assertIsNone(menu.resolve("created", has_saves=True))

    def test_menu_lines_fit_the_interface_width(self):
        from ui import WIDTH

        for line in menu.menu_lines(True) + menu.menu_lines(False):
            self.assertLessEqual(len(line), WIDTH, line)


class ScreenModelTests(unittest.TestCase):
    """Every screen clears and draws once; notices survive to be read."""

    def setUp(self):
        menu.notify("")  # start from a clean slate

    def _draw(self, *blocks) -> str:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            menu.screen(*blocks)
        return buffer.getvalue()

    def test_a_screen_clears_before_drawing(self):
        # Without this, each screen piles up under the last one.
        with unittest.mock.patch("menu.clear_screen") as cleared:
            self._draw("hello")
        cleared.assert_called_once()

    def test_a_notice_appears_on_the_next_screen(self):
        menu.notify("watch out")
        self.assertIn("watch out", self._draw("body"))

    def test_a_notice_is_shown_only_once(self):
        # Regression: messages used to be printed and then wiped by the next
        # clear, so the player never saw them. Now they ride the next draw --
        # but exactly one draw.
        menu.notify("watch out")
        self.assertIn("watch out", self._draw("body"))
        self.assertNotIn("watch out", self._draw("body"))

    def test_none_blocks_are_skipped(self):
        text = self._draw("first", None, "second")
        self.assertIn("first", text)
        self.assertIn("second", text)

    def test_screens_do_not_print_anything_else(self):
        self.assertEqual(self._draw("only this").strip(), "only this")


class ScreenFitTests(unittest.TestCase):
    """Nothing may overflow the frame, sideways or downwards."""

    TERMINAL_ROWS = 24

    def test_the_origin_chooser_fits_a_standard_terminal(self):
        # Regression: six origins at four lines each ran to 30 rows and pushed
        # the question off the top of an 80x24 screen.
        rows = len(chargen.listing()) + 3  # frame top, bottom, prompt
        self.assertLessEqual(rows, self.TERMINAL_ROWS, f"{rows} rows")

    def test_the_options_screen_fits_a_standard_terminal(self):
        rows = len(menu.option_rows(Settings())) + 6
        self.assertLessEqual(rows, self.TERMINAL_ROWS, f"{rows} rows")

    def test_the_main_menu_fits_a_standard_terminal(self):
        rows = len(menu.menu_lines(True)) + 8
        self.assertLessEqual(rows, self.TERMINAL_ROWS, f"{rows} rows")

    def test_no_chooser_line_is_wider_than_the_frame(self):
        for line in chargen.listing():
            self.assertLessEqual(visible_len(line), WIDTH, repr(line))

    def test_truncation_never_exceeds_the_width_it_was_given(self):
        # The ellipsis counts toward the budget; forgetting that was enough to
        # break the frame by one column.
        for width in range(4, 40):
            for text in ("short", "a much longer piece of text than that", "x" * 80):
                self.assertLessEqual(len(chargen._fit(text, width)), width)

    def test_wrapped_prose_never_exceeds_the_frame(self):
        from ui import wrap

        for origin in chargen.ORIGINS.values():
            for line in wrap(origin.blurb).splitlines():
                self.assertLessEqual(visible_len(line), WIDTH, origin.name)


class OptionsTests(unittest.TestCase):
    """Options are editable and persist between launches."""

    def _temp_path(self) -> str:
        handle, path = tempfile.mkstemp(suffix=".sav")
        os.close(handle)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        return path

    def test_every_setting_is_offered(self):
        from dataclasses import fields

        names = [name for name, _value in menu.option_rows(Settings())]
        self.assertEqual(names, [f.name for f in fields(Settings)])

    def test_options_round_trip(self):
        path = self._temp_path()
        settings = Settings(show_map=False, min_command_prefix=2)
        saveload.save_options(settings, path)
        self.assertEqual(saveload.load_options(path), settings)

    def test_missing_options_fall_back_to_defaults(self):
        self.assertEqual(saveload.load_options("no_such_options.sav"), Settings())

    def test_corrupt_options_fall_back_to_defaults(self):
        path = self._temp_path()
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("not a save")
        self.assertEqual(saveload.load_options(path), Settings())

    def test_saved_options_reach_the_game(self):
        from game import Game

        settings = Settings(show_map=False, auto_clear=False)
        game = Game(settings=settings)
        self.assertFalse(game.settings.show_map)
        self.assertFalse(game.settings.auto_clear)


class CharacterListingTests(unittest.TestCase):
    """Continue and Load read the same list, newest first."""

    def setUp(self):
        self.directory = tempfile.mkdtemp()
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        for entry in os.listdir(self.directory):
            os.remove(os.path.join(self.directory, entry))
        os.rmdir(self.directory)

    def _write(self, name: str) -> None:
        path = os.path.join(self.directory, f"{saveload.slug(name)}.sav")
        saveload.save_legacy(Legacy(name=name, origin="graveborn"), path)

    def test_empty_directory_lists_nothing(self):
        self.assertEqual(saveload.list_characters(self.directory), [])

    def test_characters_are_listed_newest_first(self):
        self._write("Older Vane")
        time.sleep(0.01)  # so the modification times differ
        self._write("Newer Corvath")

        names = [legacy.name for _p, legacy, _t in saveload.list_characters(self.directory)]
        self.assertEqual(names[0], "Newer Corvath")
        self.assertIn("Older Vane", names)

    def test_the_options_file_is_not_offered_as_a_character(self):
        saveload.save_options(
            Settings(), os.path.join(self.directory, "options.sav")
        )
        self._write("Real Character")
        names = [legacy.name for _p, legacy, _t in saveload.list_characters(self.directory)]
        self.assertEqual(names, ["Real Character"])

    def test_unreadable_slots_are_skipped_not_offered(self):
        with open(os.path.join(self.directory, "broken.sav"), "w") as handle:
            handle.write("garbage")
        self._write("Good One")
        names = [legacy.name for _p, legacy, _t in saveload.list_characters(self.directory)]
        self.assertEqual(names, ["Good One"])


if __name__ == "__main__":
    unittest.main()
