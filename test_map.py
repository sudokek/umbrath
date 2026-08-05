"""Unit tests for the ASCII map renderer."""

import re
import unittest

from map_render import BOX_WIDTH, GRID_HEIGHT, LABEL_WIDTH, _box, build_map
from ui import glyph
from ui import WIDTH as UI_WIDTH
from world import build_world


class BuildMapTests(unittest.TestCase):
    """Cover how discovered/undiscovered rooms and markers are drawn."""

    def setUp(self):
        self.world = build_world()

    def test_current_room_is_marked(self):
        text = "\n".join(build_map(self.world, {"square"}, "square"))
        self.assertIn("*Sqr*", text)
        self.assertIn("YOU ARE HERE", text)

    def test_visited_room_uses_brackets(self):
        text = "\n".join(build_map(self.world, {"square", "forest"}, "forest"))
        self.assertIn("[Sqr]", text)  # visited but not current
        self.assertIn("*For*", text)  # current

    def test_unexplored_neighbor_shown_as_question(self):
        # From the square you can see exits, but neighbors are not visited yet.
        text = "\n".join(build_map(self.world, {"square"}, "square"))
        self.assertIn("[ ? ]", text)

    def test_connectors_present(self):
        # The corridor character depends on whether the console can draw lines,
        # so ask the interface rather than hardcoding one.
        text = "\n".join(build_map(self.world, {"square", "forest"}, "square"))
        self.assertIn(glyph("h"), text)  # square--forest horizontal link


class BoxAlignmentTests(unittest.TestCase):
    """Short labels must not shrink a box and knock the grid out of line."""

    def test_box_is_always_the_same_width(self):
        for label in ("", "C1", "Sqr", "toolong"):
            self.assertEqual(len(_box(label, ("[", "]"))), BOX_WIDTH)

    def test_every_room_label_fits_the_box(self):
        for room in build_world().values():
            self.assertLessEqual(len(room.label), LABEL_WIDTH, room.key)

    def test_cave_rooms_have_no_gap_before_connectors(self):
        # Regression: 2-character cave labels used to render "[C1] -[C2]".
        world = build_world()
        cave = [key for key in world if key.startswith("cave1")]
        text = "\n".join(build_map(world, set(cave) | {"forest"}, cave[0]))
        dash = re.escape(glyph("h"))
        self.assertIsNone(re.search(rf"[\]*] +{dash}", text), text)
        self.assertIsNone(re.search(rf"{dash} +[\[*]", text), text)


class ViewportTests(unittest.TestCase):
    """The map is a fixed-size camera that follows the player."""

    def setUp(self):
        self.world = build_world(1)
        self.everything = set(self.world)

    def _grid(self, current):
        """The drawn grid rows (the canvas, above the caption)."""
        # Sliced by height rather than by a blank line: blank rows are a normal
        # part of the canvas when a corner of the window is empty.
        return build_map(self.world, self.everything, current)[:GRID_HEIGHT]

    def test_block_height_is_constant_wherever_you_stand(self):
        heights = {len(build_map(self.world, self.everything, key)) for key in self.world}
        self.assertEqual(len(heights), 1, f"map block height varied: {heights}")

    def test_grid_never_exceeds_ui_width(self):
        for key in self.world:
            for line in self._grid(key):
                self.assertLessEqual(len(line), UI_WIDTH, f"{key}: {line!r}")

    def test_player_is_marked_in_every_view(self):
        # Labels vary in width (H0 vs H7!), so compare against the drawn box
        # rather than assuming the label fills it.
        for key in self.world:
            text = "\n".join(self._grid(key))
            marker = _box(self.world[key].label, ("*", "*"))
            self.assertIn(marker, text, key)

    def test_distant_rooms_are_clipped_out(self):
        # Standing in town, the far end of the world must not be drawn.
        far = max(self.world.values(), key=lambda room: room.x)
        text = "\n".join(self._grid("market"))
        self.assertNotIn(_box(far.label, ("[", "]")), text)

    def test_offscreen_hint_appears_and_names_directions(self):
        lines = build_map(self.world, self.everything, "market")
        hint = [line for line in lines if line.startswith("(map continues")]
        self.assertTrue(hint, lines)
        self.assertIn("east", hint[0])  # the cave lies east of town

    def test_no_offscreen_hint_when_everything_fits(self):
        # Only the square discovered: its neighbors all sit inside the window.
        lines = build_map(self.world, {"square"}, "square")
        self.assertFalse([l for l in lines if l.startswith("(map continues")], lines)

    def test_labels_never_collide_with_the_you_marker(self):
        # A "*" inside a label would render as an unreadable "*C7**".
        for room in self.world.values():
            self.assertNotIn("*", room.label, room.key)


if __name__ == "__main__":
    unittest.main()
