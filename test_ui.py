"""Tests for the terminal helpers, especially colour and alignment.

Colour is optional decoration: it must never change what the layout measures,
and it must vanish cleanly on a terminal that cannot render it.
"""

import unittest

import ui
from ui import WIDTH


class ColorTests(unittest.TestCase):
    """Painting text, and not painting it."""

    def setUp(self):
        # Pretend the terminal understands escapes, whatever is really running
        # the tests, then restore afterwards.
        self._was_ready = ui._ANSI_READY
        self._was_enabled = ui.color_enabled()
        ui._ANSI_READY = True
        ui.set_color(True)
        self.addCleanup(self._restore)

    def _restore(self):
        ui._ANSI_READY = self._was_ready
        ui.set_color(self._was_enabled)

    def test_paint_wraps_and_resets(self):
        painted = ui.paint("hi", "red")
        self.assertTrue(painted.startswith("\x1b["))
        self.assertTrue(painted.endswith("\x1b[0m"))
        self.assertIn("hi", painted)

    def test_paint_combines_styles(self):
        self.assertEqual(ui.paint("x", "bold", "red"), "\x1b[1;31mx\x1b[0m")

    def test_unknown_style_is_ignored_rather_than_crashing(self):
        self.assertEqual(ui.paint("x", "chartreuse"), "x")

    def test_no_styles_returns_plain_text(self):
        self.assertEqual(ui.paint("x"), "x")

    def test_disabling_colour_returns_plain_text(self):
        ui.set_color(False)
        self.assertEqual(ui.paint("x", "red"), "x")
        self.assertNotIn("\x1b", ui.bar("HP", 3, 10))

    def test_colour_stays_off_when_the_terminal_cannot_render_it(self):
        ui._ANSI_READY = False
        ui.set_color(True)
        self.assertFalse(ui.color_enabled())
        self.assertEqual(ui.paint("x", "red"), "x")


class AlignmentTests(unittest.TestCase):
    """Colour must not disturb the layout."""

    def setUp(self):
        self._was_ready = ui._ANSI_READY
        self._was_enabled = ui.color_enabled()
        ui._ANSI_READY = True
        ui.set_color(True)
        self.addCleanup(self._restore)

    def _restore(self):
        ui._ANSI_READY = self._was_ready
        ui.set_color(self._was_enabled)

    def test_visible_len_ignores_escapes(self):
        self.assertEqual(ui.visible_len(ui.paint("seven!!", "red")), 7)

    def test_centered_coloured_text_is_still_the_interface_width(self):
        for text in ("UMBRATH", "a much longer subtitle than that one", ""):
            line = ui.center(ui.paint(text, "bold", "cyan"))
            self.assertEqual(ui.visible_len(line), WIDTH, repr(text))

    def test_right_aligned_coloured_text_is_still_the_interface_width(self):
        line = ui.right(ui.paint("created by sudokek", "dim"))
        self.assertEqual(ui.visible_len(line), WIDTH)

    def test_centering_matches_the_plain_version(self):
        plain = ui.center("UMBRATH")
        coloured = ui.center(ui.paint("UMBRATH", "red"))
        self.assertEqual(
            len(plain) - len(plain.lstrip()), len(coloured) - len(coloured.lstrip())
        )

    def test_rule_is_the_interface_width(self):
        self.assertEqual(ui.visible_len(ui.rule("=")), WIDTH)


class BarTests(unittest.TestCase):
    """The health meter."""

    def setUp(self):
        ui.set_color(False)
        self.addCleanup(lambda: ui.set_color(True))

    def test_bar_fills_proportionally(self):
        self.assertEqual(ui.bar("HP", 10, 10), "HP [##########]")
        self.assertEqual(ui.bar("HP", 0, 10), "HP [----------]")
        self.assertEqual(ui.bar("HP", 5, 10), "HP [#####-----]")

    def test_bar_survives_a_zero_maximum(self):
        self.assertEqual(ui.bar("HP", 0, 0), "HP [----------]")

    def test_bar_clamps_out_of_range_values(self):
        self.assertEqual(ui.bar("HP", 99, 10), "HP [##########]")
        self.assertEqual(ui.bar("HP", -5, 10), "HP [----------]")

    def test_bar_width_is_constant_however_hurt_you_are(self):
        widths = {ui.visible_len(ui.bar("HP", n, 20)) for n in range(0, 21)}
        self.assertEqual(len(widths), 1)


class BannerTests(unittest.TestCase):
    """The big ASCII shouts."""

    def test_known_words_render_as_block_letters(self):
        lines = ui.banner("YOU DIED")
        self.assertEqual(len(lines), ui.BANNER_HEIGHT)
        self.assertTrue(any("#" in line for line in lines))

    def test_unknown_letters_fall_back_instead_of_crashing(self):
        lines = ui.banner("Zzz?")
        self.assertEqual(len(lines), 1)
        self.assertIn("ZZZ?", lines[0])


if __name__ == "__main__":
    unittest.main()
