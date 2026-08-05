"""Unit tests for the procedural cave generator."""

import unittest

from dungeon import DEFAULT_ROOM_COUNT, OPPOSITE, STEPS, generate_cave
from map_render import LABEL_WIDTH
from testkit import reachable as _walk


class GenerationTests(unittest.TestCase):
    """Every generated cave must be connected, sized, and well-formed."""

    def test_same_seed_gives_identical_cave(self):
        a = generate_cave(1234)
        b = generate_cave(1234)
        self.assertEqual(sorted(a), sorted(b))
        for key in a:
            self.assertEqual(a[key].name, b[key].name, key)
            self.assertEqual((a[key].x, a[key].y), (b[key].x, b[key].y), key)
            self.assertEqual(a[key].exits, b[key].exits, key)

    def test_different_seeds_give_different_caves(self):
        shapes = set()
        for seed in range(6):
            rooms = generate_cave(seed)
            shapes.add(tuple(sorted((r.x, r.y) for r in rooms.values())))
        self.assertGreater(len(shapes), 1, "generator produced identical layouts")

    def test_requested_room_count(self):
        for seed in range(5):
            self.assertEqual(len(generate_cave(seed)), DEFAULT_ROOM_COUNT, seed)

    def test_every_room_is_reachable_from_the_entrance(self):
        for seed in range(8):
            rooms = generate_cave(seed)
            self.assertEqual(_walk(rooms, "cave1"), set(rooms), f"seed {seed}")

    def test_no_two_rooms_share_a_coordinate(self):
        for seed in range(8):
            rooms = generate_cave(seed)
            spots = [(room.x, room.y) for room in rooms.values()]
            self.assertEqual(len(spots), len(set(spots)), f"seed {seed}")

    def test_exits_are_mutual_and_geometrically_correct(self):
        for seed in range(5):
            rooms = generate_cave(seed)
            for key, room in rooms.items():
                for direction, target in room.exits.items():
                    if target not in rooms:  # the exit back to town
                        continue
                    other = rooms[target]
                    self.assertEqual(
                        other.exits.get(OPPOSITE[direction]),
                        key,
                        f"seed {seed}: {key} -{direction}-> {target} not mutual",
                    )
                    dx, dy = STEPS[direction]
                    self.assertEqual(
                        (room.x + dx, room.y + dy),
                        (other.x, other.y),
                        f"seed {seed}: {key} -{direction}-> {target} misplaced",
                    )

    def test_entrance_links_back_to_town(self):
        rooms = generate_cave(3)
        self.assertEqual(rooms["cave1"].exits.get("west"), "forest")

    def test_labels_fit_the_map_box(self):
        for seed in range(5):
            for room in generate_cave(seed).values():
                self.assertLessEqual(len(room.label), LABEL_WIDTH, room.key)
                self.assertNotIn("*", room.label, room.key)

    def test_danger_increases_with_depth(self):
        rooms = generate_cave(11)
        entrance = rooms["cave1"]
        deepest = max(rooms.values(), key=lambda r: abs(r.x - entrance.x) + abs(r.y - entrance.y))
        self.assertGreaterEqual(deepest.danger, entrance.danger)

    def test_caves_grow_in_every_direction(self):
        # Caves used to be forced eastward. They now sprawl, so across a handful
        # of seeds rooms should appear on all four sides of the entrance.
        seen = set()
        for seed in range(12):
            rooms = generate_cave(seed)
            entrance = rooms["cave1"]
            for room in rooms.values():
                if room.x > entrance.x:
                    seen.add("east")
                if room.x < entrance.x:
                    seen.add("west")
                if room.y > entrance.y:
                    seen.add("north")
                if room.y < entrance.y:
                    seen.add("south")
        self.assertEqual(seen, {"north", "south", "east", "west"})

    def test_caves_respect_the_bounds_they_are_given(self):
        bounds = (0, 6, -3, 3)
        for seed in range(10):
            rooms = generate_cave(seed, entrance_x=3, entrance_y=0, bounds=bounds)
            for room in rooms.values():
                self.assertTrue(0 <= room.x <= 6, f"{room.key} x={room.x}")
                self.assertTrue(-3 <= room.y <= 3, f"{room.key} y={room.y}")

    def test_caves_never_build_on_reserved_squares(self):
        reserved = {(4, 0), (4, 1), (5, 0)}
        for seed in range(10):
            rooms = generate_cave(seed, reserved=set(reserved))
            spots = {(room.x, room.y) for room in rooms.values()}
            self.assertFalse(spots & reserved, f"seed {seed}")

    def test_most_rooms_have_more_than_one_way_out(self):
        # Loops are what stop a cave being a tree of dead ends you must reverse
        # out of. Getting lost should be "which way?", not "walk it all back".
        multi = total = 0
        for seed in range(20):
            for room in generate_cave(seed).values():
                total += 1
                multi += len(room.exits) > 1
        self.assertGreater(multi / total, 0.75, "too many dead ends")


if __name__ == "__main__":
    unittest.main()
