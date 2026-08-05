"""Properties that must hold for every world the generator can produce.

The rest of the suite tests behaviour on one or two seeds. This file tests
*invariants* over many, which is what actually stops structural bugs coming
back: every regression this project has hit -- stranded vaults, colliding
rooms, unreachable holds, a road that led nowhere -- is a property below that
would have failed on some seed long before a player found it.

Keep SEEDS high enough to be worth running and low enough to stay fast.
"""

import unittest

import chargen
from chargen import BUDGET, ORIGINS
from content import FINAL_REGION, ITEMS, REGIONS, THEMES
from dungeon import OPPOSITE, STEPS
from legacy import bonuses, new_player
from map_render import LABEL_WIDTH, build_map
from models import Legacy
from ui import WIDTH as UI_WIDTH
from testkit import SEEDS, bosses_in, reachable as walk, vault_of
from world import build_world, region_bounds

class WorldIntegrityTests(unittest.TestCase):
    """Structural guarantees for every generated world."""

    def test_every_room_is_reachable(self):
        for seed in SEEDS:
            world = build_world(seed)
            missing = set(world) - walk(world)
            self.assertFalse(missing, f"seed {seed} stranded {sorted(missing)[:5]}")

    def test_no_two_rooms_share_a_square(self):
        for seed in SEEDS:
            world = build_world(seed)
            spots = [(room.x, room.y) for room in world.values()]
            self.assertEqual(len(spots), len(set(spots)), f"seed {seed}")

    def test_adjacent_exits_are_mutual_and_correctly_placed(self):
        # Long roads between holds are journeys, not corridors, so only rooms
        # that actually sit next to each other are checked for geometry.
        for seed in SEEDS:
            world = build_world(seed)
            for key, room in world.items():
                for direction, target in room.exits.items():
                    other = world.get(target)
                    if other is None:
                        continue
                    dx, dy = STEPS[direction]
                    if (room.x + dx, room.y + dy) != (other.x, other.y):
                        continue  # a long road; geometry does not apply
                    self.assertEqual(
                        other.exits.get(OPPOSITE[direction]),
                        key,
                        f"seed {seed}: {key} -{direction}-> {target} not mutual",
                    )

    def test_every_exit_points_at_a_real_room(self):
        for seed in SEEDS:
            world = build_world(seed)
            for key, room in world.items():
                for direction, target in room.exits.items():
                    self.assertIn(target, world, f"seed {seed}: {key}.{direction}")

    def test_no_room_exits_into_itself(self):
        for seed in SEEDS:
            world = build_world(seed)
            for key, room in world.items():
                self.assertNotIn(key, room.exits.values(), f"seed {seed}: {key}")

    def test_holds_never_overlap_each_others_ground(self):
        for seed in SEEDS:
            world = build_world(seed)
            for spec in REGIONS:
                min_x, max_x, min_y, max_y = region_bounds(spec["index"])
                for room in world.values():
                    if room.region != spec["index"] or room.danger == 0:
                        continue
                    self.assertTrue(
                        min_x <= room.x <= max_x and min_y <= room.y <= max_y,
                        f"seed {seed}: {room.key} escaped its hold",
                    )

    def test_every_room_has_a_name_a_description_and_a_fitting_label(self):
        for seed in SEEDS:
            for room in build_world(seed).values():
                self.assertTrue(room.name.strip(), room.key)
                self.assertTrue(room.description.strip(), room.key)
                self.assertLessEqual(len(room.label), LABEL_WIDTH, room.key)
                self.assertNotIn("*", room.label, room.key)


class ProgressionInvariantTests(unittest.TestCase):
    """You can always finish, and never skip ahead."""

    def test_every_hold_has_exactly_one_boss(self):
        for seed in SEEDS:
            world = build_world(seed)
            for spec in REGIONS:
                self.assertEqual(
                    len(bosses_in(world, spec["index"])), 1,
                    f"seed {seed}, {spec['town']}",
                )

    def test_the_only_way_onward_is_through_the_boss(self):
        for seed in SEEDS:
            world = build_world(seed)
            for spec in REGIONS[:-1]:
                region = spec["index"]
                crossings = [
                    (room.key, direction)
                    for room in world.values()
                    if room.region == region
                    for direction, target in room.exits.items()
                    if world[target].region > region
                ]
                self.assertEqual(len(crossings), 1, f"seed {seed}, {spec['town']}")
                self.assertEqual(crossings[0][0], vault_of(world, region).key)

    def test_the_whole_game_is_completable_without_backtracking_out(self):
        # The vault holds both the boss and the road out, so finishing a hold
        # never *requires* walking back through it.
        for seed in SEEDS:
            world = build_world(seed)
            for spec in REGIONS[:-1]:
                vault = vault_of(world, spec["index"])
                onward = [
                    t for t in vault.exits.values()
                    if world[t].region > vault.region
                ]
                self.assertEqual(len(onward), 1, f"seed {seed}, {spec['town']}")

    def test_the_final_hold_leads_nowhere_further(self):
        for seed in SEEDS:
            world = build_world(seed)
            for room in world.values():
                if room.region != FINAL_REGION:
                    continue
                for target in room.exits.values():
                    self.assertLessEqual(world[target].region, FINAL_REGION)

    def test_holds_get_harder_in_order(self):
        # Each hold's bestiary must out-hit the one before it at every tier.
        for tier in (1, 2, 3):
            worst = 0
            for spec in REGIONS:
                pool = THEMES[spec["theme"]]["enemies"][tier]
                strength = min(hp + dmg * 3 for _n, hp, dmg, *_r in pool)
                self.assertGreater(
                    strength, worst, f"{spec['town']} tier {tier} is not harder"
                )
                worst = strength

    def test_each_hold_sells_stronger_gear_than_the_last(self):
        best = 0
        for spec in REGIONS:
            weapons = [ITEMS[n] for n in spec["gear"] if ITEMS[n].kind == "weapon"]
            strongest = max(w.power for w in weapons)
            self.assertGreater(strongest, best, spec["town"])
            best = strongest


class CaveShapeTests(unittest.TestCase):
    """Caves should be explorable, not exhausting."""

    def test_caves_rarely_force_you_to_reverse(self):
        # Most rooms should offer more than one way out, so getting lost is a
        # navigation puzzle rather than a series of dead-end round trips.
        multi = total = 0
        for seed in SEEDS:
            for room in build_world(seed).values():
                if room.danger == 0:
                    continue
                total += 1
                multi += len(room.exits) > 1
        self.assertGreater(multi / total, 0.75, f"only {multi / total:.0%} have 2+ exits")

    def test_caves_use_all_four_directions(self):
        directions = set()
        for seed in SEEDS:
            world = build_world(seed)
            for room in world.values():
                if room.danger == 0:
                    continue
                directions |= {
                    d for d, t in room.exits.items()
                    if world[t].region == room.region
                }
        self.assertEqual(directions, set(STEPS))


class MapInvariantTests(unittest.TestCase):
    """The map must stay inside its frame wherever you stand."""

    def test_map_never_overflows_the_interface_width(self):
        for seed in list(SEEDS)[:20]:
            world = build_world(seed)
            everything = set(world)
            for key in world:
                for line in build_map(world, everything, key):
                    self.assertLessEqual(len(line), UI_WIDTH, f"{key}: {line!r}")

    def test_map_block_is_a_constant_height(self):
        for seed in list(SEEDS)[:20]:
            world = build_world(seed)
            everything = set(world)
            heights = {len(build_map(world, everything, key)) for key in world}
            self.assertEqual(len(heights), 1, f"seed {seed}: {heights}")


class OriginBalanceTests(unittest.TestCase):
    """Origins must differ in feel and match in strength."""

    def test_every_origin_costs_the_same(self):
        for origin in ORIGINS.values():
            self.assertAlmostEqual(origin.cost(), BUDGET, places=2, msg=origin.name)

    def test_origins_are_actually_different(self):
        shapes = {
            (o.attack, o.max_hp, o.defense, o.gold, o.items) for o in ORIGINS.values()
        }
        self.assertEqual(len(shapes), len(ORIGINS))

    def test_every_origin_starting_item_exists(self):
        for origin in ORIGINS.values():
            for name in origin.items:
                self.assertIn(name, ITEMS, f"{origin.name}: {name}")

    def test_no_origin_leaves_you_unable_to_survive_a_hit(self):
        for key in ORIGINS:
            player = new_player(Legacy(name="T", origin=key))
            self.assertGreaterEqual(player.max_hp, 5, key)
            self.assertGreater(player.attack_power(), 0, key)

    def test_an_unknown_origin_grants_nothing_rather_than_someone_elses_kit(self):
        totals = bonuses(Legacy(name="T", origin="origin_from_the_future"))
        self.assertEqual(totals, {"attack": 0, "max_hp": 0, "defense": 0, "gold": 0})

    def test_unknown_origin_still_displays(self):
        self.assertEqual(chargen.get("nope").name, "Unbound")


class SaveNameTests(unittest.TestCase):
    """A character's name becomes a filename, so it must be sanitised."""

    def test_names_cannot_escape_the_saves_folder(self):
        import os

        import saveload

        for nasty in ("../../etc/passwd", "..\\..\\windows", "/root", "a/b/c"):
            path = saveload.character_path(nasty)
            self.assertEqual(os.path.dirname(path), saveload.SAVE_DIR, nasty)
            self.assertNotIn("..", path, nasty)

    def test_empty_or_symbol_names_still_produce_a_file(self):
        import saveload

        for odd in ("", "   ", "!!!", "***"):
            self.assertTrue(saveload.character_path(odd).endswith(".sav"), repr(odd))

    def test_different_names_get_different_files(self):
        import saveload

        a = saveload.character_path("Alaric Vane")
        b = saveload.character_path("Selene Corvath")
        self.assertNotEqual(a, b)


if __name__ == "__main__":
    unittest.main()
