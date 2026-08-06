"""Tests for the debug console.

Two things matter beyond the cheats working: they must not exist until asked
for, and they must not disturb the real command set when they do.
"""

import unittest

import cheats
from content import ITEMS
from models import Enemy
from testkit import make_game


class ActivationTests(unittest.TestCase):
    """Cheats are off until the word is typed, and off again after."""

    def test_cheats_start_off(self):
        self.assertFalse(make_game().cheats_on)

    def test_the_word_turns_them_on_and_off(self):
        game = make_game()
        game.handle_command(cheats.WORD)
        self.assertTrue(game.cheats_on)
        game.handle_command(cheats.WORD)
        self.assertFalse(game.cheats_on)

    def test_turning_them_on_shows_the_menu(self):
        game = make_game()
        game.handle_command(cheats.WORD)
        for verb in ("give", "tp", "hp", "reveal", "god"):
            self.assertIn(verb, game.message)

    def test_cheat_verbs_do_nothing_while_off(self):
        game = make_game()
        before = list(game.player.inventory)
        game.handle_command("give doom glaive")
        self.assertEqual(game.player.inventory, before)
        self.assertIn("invalid", game.message.lower())

    def test_cheats_shows_the_menu_again(self):
        game = make_game()
        game.handle_command(cheats.WORD)
        game.handle_command("look")
        game.handle_command("cheats")
        self.assertIn("give", game.message)


class IsolationTests(unittest.TestCase):
    """The console must not touch the real command set."""

    def test_no_cheat_verb_leaks_into_the_parser(self):
        import parser as command_parser

        overlap = set(cheats.CHEATS) & set(command_parser.COMMANDS)
        self.assertFalse(overlap, f"cheat verbs shadow real commands: {overlap}")

    def test_real_commands_still_work_with_cheats_on(self):
        game = make_game()
        game.handle_command(cheats.WORD)
        game.handle_command("stats")
        self.assertIn("Level:", game.message)

    def test_the_word_is_not_a_real_command(self):
        import parser as command_parser

        self.assertNotIn(cheats.WORD, command_parser.COMMANDS)

    def test_cheats_are_never_saved(self):
        from dataclasses import fields

        from models import Legacy, Settings

        names = {f.name for f in fields(Legacy)} | {f.name for f in fields(Settings)}
        self.assertNotIn("cheats_on", names)
        self.assertNotIn("godmode", names)


class GiveTests(unittest.TestCase):
    """give reads the registry live, so it can never go stale."""

    def setUp(self):
        self.game = make_game()
        self.game.handle_command(cheats.WORD)

    def test_every_item_in_the_registry_can_be_given(self):
        for name in ITEMS:
            game = make_game()
            game.cheats_on = True
            game.handle_command(f"give {name}")
            self.assertIn(name, [i.name for i in game.player.inventory], name)

    def test_the_catalogue_lists_the_whole_registry(self):
        self.game.handle_command("give")
        self.assertIn(str(len(ITEMS)), self.game.message)

    def test_give_all_hands_over_everything(self):
        self.game.handle_command("give all")
        held = [i.name for i in self.game.player.inventory]
        for name in ITEMS:
            self.assertIn(name, held, name)

    def test_partial_names_work(self):
        self.game.handle_command("give glaive")
        self.assertIn("doom glaive", [i.name for i in self.game.player.inventory])

    def test_an_unknown_item_is_reported(self):
        self.game.handle_command("give nonsense")
        self.assertIn("not found", self.game.message.lower())


class TeleportTests(unittest.TestCase):
    """tp builds its destinations from the world in front of it."""

    def setUp(self):
        self.game = make_game()
        self.game.cheats_on = True

    def test_every_boss_is_reachable(self):
        for region in (1, 2, 3):
            self.game.handle_command(f"tp boss{region}")
            room = self.game.current_room()
            self.assertEqual(room.region, region)
            self.assertTrue(any(e.boss for e in room.enemies), f"boss{region}")

    def test_landmarks_are_reachable(self):
        for where in ("shrine", "forge", "market", "inn", "town1", "town2", "town3"):
            self.game.handle_command(f"tp {where}")
            self.assertNotIn("Nowhere called", self.game.message, where)

    def test_a_raw_room_key_works(self):
        self.game.handle_command("tp cave1")
        self.assertEqual(self.game.player.location, "cave1")

    def test_teleporting_discovers_where_you_land(self):
        self.game.handle_command("tp boss3")
        self.assertIn(self.game.player.location, self.game.discovered)

    def test_nowhere_is_reported_with_the_options(self):
        self.game.handle_command("tp atlantis")
        self.assertIn("Nowhere called", self.game.message)


class StateTests(unittest.TestCase):
    """The knobs that make a specific situation reproducible."""

    def setUp(self):
        self.game = make_game()
        self.game.cheats_on = True

    def test_hp_and_maxhp(self):
        self.game.handle_command("maxhp 200")
        self.assertEqual(self.game.player.max_hp, 200)
        self.game.handle_command("hp 7")
        self.assertEqual(self.game.player.hp, 7)
        self.game.handle_command("hp max")
        self.assertEqual(self.game.player.hp, 200)

    def test_hp_cannot_exceed_the_maximum(self):
        self.game.handle_command("hp 99999")
        self.assertEqual(self.game.player.hp, self.game.player.max_hp)

    def test_level_applies_the_health_that_comes_with_it(self):
        self.game.handle_command("level 10")
        self.assertEqual(self.game.player.level, 10)
        self.assertEqual(self.game.player.max_hp, 20 + 5 * 9)

    def test_level_can_go_back_down(self):
        self.game.handle_command("level 10")
        self.game.handle_command("level 2")
        self.assertEqual(self.game.player.level, 2)
        self.assertEqual(self.game.player.max_hp, 25)

    def test_gold_and_echoes(self):
        self.game.handle_command("gold 1234")
        self.assertEqual(self.game.player.gold, 1234)
        self.game.handle_command("echoes 42")
        self.assertEqual(self.game.legacy.echoes, 42)

    def test_relic_grants_permanently(self):
        self.game.handle_command("relic gaunt fang")
        self.assertIn("gaunt fang", self.game.legacy.relics)

    def test_reveal_discovers_everything(self):
        self.game.handle_command("reveal")
        self.assertEqual(self.game.discovered, set(self.game.world))

    def test_god_mode_stops_damage(self):
        self.game.handle_command("god")
        self.game.player.location = "cave1"
        enemy = Enemy("troll", hp=99, max_hp=99, damage=99)
        self.game.current_room().enemies.append(enemy)
        before = self.game.player.hp
        self.game._enemy_strikes(enemy)
        self.assertEqual(self.game.player.hp, before)

    def test_where_reports_the_seed(self):
        self.game.handle_command("where")
        self.assertIn(str(self.game.dungeon_seed), self.game.message)


class EncounterTests(unittest.TestCase):
    """Setting up the exact situation a feature needs testing in."""

    def setUp(self):
        self.game = make_game()
        self.game.cheats_on = True
        self.game.handle_command("tp cave1")

    def test_spawn_puts_an_enemy_here(self):
        self.game.handle_command("spawn 2")
        self.assertTrue(self.game.current_room().enemies)

    def test_wound_sets_up_a_feed(self):
        self.game.handle_command("spawn 1")
        self.game.handle_command("wound 20")
        enemy = self.game.current_room().enemies[0]
        self.assertTrue(self.game.can_feed_on(enemy))

    def test_windup_sets_up_a_guard(self):
        self.game.handle_command("spawn 1")
        self.game.handle_command("windup")
        self.assertTrue(self.game.current_room().enemies[0].winding_up)

    def test_kill_clears_the_room(self):
        self.game.handle_command("spawn 3")
        self.game.handle_command("kill")
        self.assertEqual(self.game.current_room().enemies, [])

    def test_chest_drops_one_here(self):
        self.game.handle_command("chest 3")
        chest = self.game.current_room().chest
        self.assertIsNotNone(chest)
        self.assertTrue(chest.contents)

    def test_trader_puts_one_here(self):
        self.game.handle_command("trader")
        self.assertIsNotNone(self.game.current_room().trader)


class MenuTests(unittest.TestCase):
    """The list the console shows describes what it actually has."""

    def test_every_cheat_is_documented_in_the_menu(self):
        menu = "\n".join(cheats.menu_lines())
        for verb in cheats.CHEATS:
            self.assertIn(verb, menu, verb)

    def test_every_documented_cheat_has_a_handler(self):
        for verb, (handler, help_text) in cheats.CHEATS.items():
            self.assertTrue(help_text.strip(), verb)
            if verb != "cheats":  # handled inline
                self.assertTrue(callable(handler), verb)

    def test_the_menu_says_how_to_leave(self):
        self.assertIn(cheats.WORD, "\n".join(cheats.menu_lines()))


if __name__ == "__main__":
    unittest.main()
