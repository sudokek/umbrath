"""Tests for the roguelike spine: regions, bosses, relics, echoes, traders."""

import os
import tempfile
import unittest
from unittest.mock import patch

import legacy as legacy_rules
import saveload
from content import FINAL_REGION, REGIONS, THEMES, make_trader
import testkit
from game import Game
from testkit import TempFileMixin, make_game
from models import Enemy, Legacy
from world import build_world


def vault_of(game: Game, region: int):
    """The boss room of a region in a live game."""
    return testkit.vault_of(game.world, region)


class WorldShapeTests(unittest.TestCase):
    """Three regions, joined in order, with nothing stranded."""

    def setUp(self):
        self.world = build_world(3)

    def test_every_region_exists(self):
        regions = {room.region for room in self.world.values()}
        self.assertEqual(regions, {spec["index"] for spec in REGIONS})

    def test_whole_world_is_reachable_from_the_start(self):
        seen, stack = {"square"}, ["square"]
        while stack:
            for target in self.world[stack.pop()].exits.values():
                if target in self.world and target not in seen:
                    seen.add(target)
                    stack.append(target)
        self.assertEqual(seen, set(self.world))

    def test_no_two_rooms_share_a_coordinate(self):
        spots = [(room.x, room.y) for room in self.world.values()]
        self.assertEqual(len(spots), len(set(spots)))

    def test_each_region_has_exactly_one_boss(self):
        for spec in REGIONS:
            bosses = [
                room
                for room in self.world.values()
                if room.region == spec["index"] and any(e.boss for e in room.enemies)
            ]
            self.assertEqual(len(bosses), 1, spec["town"])

    def test_caves_use_their_own_theme(self):
        for spec in REGIONS:
            names = {
                room.name
                for room in self.world.values()
                if room.region == spec["index"] and room.danger > 0
            }
            style = THEMES[spec["theme"]]
            allowed = set(style["room_names"]) | {
                style["entrance_name"],
                style["vault_name"],
            }
            self.assertTrue(names <= allowed, f"{spec['town']}: {names - allowed}")

    def _onward_exits(self, world, region: int) -> list[str]:
        """Directions out of a region's vault that leave the region."""
        vault = next(
            room
            for room in world.values()
            if room.region == region and any(e.boss for e in room.enemies)
        )
        return [
            direction
            for direction, target in vault.exits.items()
            if world[target].region != vault.region
        ]

    def test_every_vault_has_exactly_one_way_onward(self):
        # The boss stands on the only route to the next region, so there must be
        # exactly one -- never zero (impossible to progress) and never two.
        for seed in range(25):
            world = build_world(seed)
            for spec in REGIONS[:-1]:
                onward = self._onward_exits(world, spec["index"])
                self.assertEqual(len(onward), 1, f"seed {seed}, {spec['town']}")

    def test_the_way_onward_is_usually_east(self):
        # East is preferred so "the way east is clear" is the normal case, but
        # it is not guaranteed: freeing east is refused when that would strand
        # the vault. The game reads the real direction rather than assuming.
        directions = [
            self._onward_exits(build_world(seed), spec["index"])[0]
            for seed in range(25)
            for spec in REGIONS[:-1]
        ]
        east = directions.count("east") / len(directions)
        self.assertGreater(east, 0.7, f"east only {east:.0%} of the time")

    def test_the_last_region_has_nowhere_further_to_go(self):
        world = build_world(4)
        self.assertEqual(self._onward_exits(world, REGIONS[-1]["index"]), [])

    def test_each_town_stocks_its_own_tier_of_gear(self):
        for spec in REGIONS:
            smithy = next(
                room
                for room in self.world.values()
                if room.region == spec["index"] and room.shop and not room.can_sell
            )
            self.assertEqual([i.name for i in smithy.shop], spec["gear"])


class BossGateTests(unittest.TestCase):
    """A boss stands between you and the next town."""

    def setUp(self):
        self.game = make_game()
        self.vault = vault_of(self.game, 1)
        self.game.player.location = self.vault.key
        self.game.discover(self.vault.key)

    def test_the_boss_blocks_the_road_onward(self):
        self.game.move("east")
        self.assertEqual(self.game.player.location, self.vault.key)
        self.assertIn("no way past", self.game.message)

    def test_fleeing_cannot_carry_you_into_the_next_region(self):
        destination = self.game._retreat_destination(self.vault)
        self.assertIsNotNone(destination)
        self.assertEqual(self.game.world[destination].region, 1)

    def test_killing_the_boss_opens_the_way(self):
        self.game.player.bonus_attack = 10_000
        self.game.attack_target("")
        self.assertEqual(self.game.current_room().enemies, [])

        way = self.game._road_onward(self.vault)
        self.assertIsNotNone(way, "the vault has no exit out of the region")
        self.game.move(way)
        self.assertEqual(self.game.region(), 2)

    def test_the_road_out_is_announced_by_its_real_direction(self):
        self.game.player.bonus_attack = 10_000
        self.game.attack_target("")
        way = self.game._road_onward(self.vault)
        self.assertIn(f"The way {way} is clear", self.game.message)


class RelicTests(unittest.TestCase):
    """Boss relics apply at once and are kept for every later run."""

    def setUp(self):
        self.game = make_game()
        self.vault = vault_of(self.game, 1)
        self.game.player.location = self.vault.key
        self.game.player.bonus_attack = 10_000
        self.game.attack_target("")

    def test_relic_is_recorded_in_the_legacy(self):
        self.assertIn("gaunt fang", self.game.legacy.relics)

    def test_relic_bonus_applies_immediately(self):
        self.assertEqual(self.game.player.bonus_attack, 10_004)

    def test_relic_survives_a_new_run(self):
        self.game.start_run()
        self.assertEqual([r.name for r in self.game.player.relics], ["gaunt fang"])
        self.assertEqual(self.game.player.bonus_attack, 4)


class VictoryTests(unittest.TestCase):
    """Killing the last boss is the game's one ending."""

    def test_final_boss_records_a_victory_and_restarts(self):
        game = make_game()
        final = vault_of(game, FINAL_REGION)
        game.player.location = final.key
        game.player.bonus_attack = 10_000

        game.attack_target("")

        self.assertEqual(game.legacy.victories, 1)
        self.assertEqual(game.player.location, "square")  # a new run began
        self.assertIn("Sunless King is dead", game.message)


class EchoTests(unittest.TestCase):
    """Echoes are the currency of dying."""

    def test_a_finished_run_always_pays_something(self):
        self.assertGreater(legacy_rules.echoes_earned(0, 1, False), 0)

    def test_depth_and_bosses_pay_more(self):
        shallow = legacy_rules.echoes_earned(0, 1, False)
        deep = legacy_rules.echoes_earned(2, 3, False)
        self.assertGreater(deep, shallow)

    def test_victory_pays_most(self):
        self.assertGreater(
            legacy_rules.echoes_earned(3, 3, True),
            legacy_rules.echoes_earned(3, 3, False),
        )

    def test_dying_banks_echoes_and_starts_over(self):
        game = make_game()
        game.player.hp = 1
        game.current_room().enemies.append(Enemy("rat", hp=99, damage=99))
        with patch("game.roll_damage", return_value=(1, False)):
            game.attack_target("")
        self.assertEqual(game.legacy.runs, 1)
        self.assertGreater(game.legacy.echoes, 0)
        self.assertEqual(game.player.location, "square")


class ShrineTests(unittest.TestCase):
    """The shrine turns echoes into permanent power."""

    def setUp(self):
        self.game = make_game(Legacy(echoes=10))
        self.game.player.location = "shrine"

    def test_listing_shows_the_blessings(self):
        self.game.buy_item("")
        self.assertIn("undeath", self.game.message)

    def test_buying_a_blessing_spends_echoes_and_raises_the_stat(self):
        before = self.game.player.max_hp
        self.game.buy_item("undeath")
        self.assertEqual(self.game.legacy.echoes, 7)
        self.assertEqual(self.game.player.max_hp, before + 8)
        self.assertEqual(self.game.legacy.blessings["undeath"], 1)

    def test_a_blessing_you_cannot_afford_changes_nothing(self):
        self.game.legacy.echoes = 1
        self.game.buy_item("undeath")
        self.assertEqual(self.game.legacy.echoes, 1)
        self.assertEqual(self.game.legacy.blessings, {})

    def test_blessings_apply_to_the_next_run(self):
        self.game.buy_item("undeath")
        self.game.start_run()
        self.assertEqual(self.game.player.max_hp, 28)

    def test_blessings_stack(self):
        self.game.buy_item("undeath")
        self.game.buy_item("undeath")
        self.game.start_run()
        self.assertEqual(self.game.player.max_hp, 36)


class TraderTests(unittest.TestCase):
    """Wandering traders carry one-off stock and do not wait around."""

    def setUp(self):
        self.game = make_game()
        self.room = self.game.current_room()
        self.room.trader = make_trader(1)
        self.game.player.gold = 100_000

    def test_talking_reports_the_stock(self):
        self.game.talk("")
        self.assertIn(self.room.trader.name, self.game.message)
        self.assertIn("On offer", self.game.message)

    def test_talking_to_nobody_is_reported(self):
        self.room.trader = None
        self.game.talk("")
        self.assertIn("nobody here", self.game.message)

    def test_buying_takes_the_item_off_the_road(self):
        name = self.room.trader.stock[0].name
        self.game.buy_item(name)
        self.assertIn(name, [i.name for i in self.game.player.inventory])
        self.assertNotIn(name, [i.name for i in self.room.trader.stock])

    def test_the_trader_is_gone_once_you_leave(self):
        self.game.move("east")
        self.assertIsNone(self.room.trader)

    def test_traders_charge_more_than_a_town_shop(self):
        from content import ITEMS

        for item in self.room.trader.stock:
            self.assertGreater(item.price, ITEMS[item.name].price)


class LegacyFileTests(TempFileMixin, unittest.TestCase):
    """The Legacy is the one thing that persists on its own."""

    def test_legacy_round_trips(self):
        original = Legacy(
            runs=4, victories=1, echoes=9, relics=["gaunt fang"],
            blessings={"undeath": 2}, best_region=3,
        )
        path = self.temp_path()
        saveload.save_legacy(original, path)
        self.assertEqual(saveload.load_legacy(path), original)

    def test_a_missing_legacy_starts_a_fresh_one(self):
        self.assertEqual(saveload.load_legacy("no_such_legacy.sav"), Legacy())

    def test_a_corrupt_legacy_starts_a_fresh_one(self):
        path = self.temp_path()
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("not a save at all")
        self.assertEqual(saveload.load_legacy(path), Legacy())

    def test_ending_a_run_writes_the_legacy(self):
        path = self.temp_path()
        game = make_game()
        game.legacy_path = path
        game.end_run(victory=False, epitaph="done")
        self.assertEqual(saveload.load_legacy(path).runs, 1)

    def test_a_game_without_a_path_never_writes(self):
        game = make_game()  # legacy_path stays None
        game.end_run(victory=False, epitaph="done")
        self.assertEqual(game.legacy.runs, 1)  # tracked, just not persisted


class RunStateSaveTests(unittest.TestCase):
    """A mid-run save carries the run and the legacy together."""

    def test_progress_and_legacy_survive_a_save(self):
        handle, path = tempfile.mkstemp(suffix=".sav")
        os.close(handle)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))

        game = make_game(Legacy(echoes=5, relics=["gaunt fang"]))
        game.bosses_killed = 1
        game.region_reached = 2
        saveload.save_game(game, path)

        loaded = make_game()
        saveload.load_game(loaded, path)

        self.assertEqual(loaded.legacy.echoes, 5)
        self.assertEqual(loaded.legacy.relics, ["gaunt fang"])
        self.assertEqual(loaded.bosses_killed, 1)
        self.assertEqual(loaded.region_reached, 2)
        self.assertEqual([r.name for r in loaded.player.relics], ["gaunt fang"])


if __name__ == "__main__":
    unittest.main()
