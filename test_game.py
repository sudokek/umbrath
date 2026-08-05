"""Unit tests for the Game object: combat, economy, movement, and dispatch."""

import io
import contextlib
import unittest
from unittest.mock import patch

import parser as command_parser
from content import make_item
from game import REST_COST, Game
from models import Enemy


def make_game() -> Game:
    """Return a game with the screen-clearing turned off for quiet tests."""
    game = Game()
    game.settings.auto_clear = False
    return game


class DispatchTests(unittest.TestCase):
    """The parser's vocabulary and the game's handlers must not drift apart."""

    def test_every_parser_command_has_a_handler(self):
        game = make_game()
        self.assertEqual(set(command_parser.COMMANDS), set(game.commands))

    def test_unknown_verb_reports_invalid(self):
        game = make_game()
        game.handle_command("zzzzz")
        self.assertIn("invalid", game.message.lower())

    def test_handle_command_routes_to_action(self):
        game = make_game()
        game.handle_command("stats")
        self.assertIn("Level:", game.message)


class MovementTests(unittest.TestCase):
    """Cover moving between rooms and what blocks it."""

    def test_move_updates_location_and_discovers(self):
        game = make_game()
        game.move("north")
        self.assertEqual(game.player.location, "smithy")
        self.assertIn("smithy", game.discovered)

    def test_move_in_missing_direction_is_refused(self):
        game = make_game()
        game.player.location = "inn"
        game.move("west")
        self.assertEqual(game.player.location, "inn")
        self.assertIn("can't go", game.message)

    def test_enemy_blocks_movement(self):
        game = make_game()
        game.current_room().enemies.append(Enemy("goblin"))
        game.move("north")
        self.assertEqual(game.player.location, "square")
        self.assertIn("blocks your path", game.message)

    def test_explore_is_pointless_in_a_safe_room(self):
        game = make_game()
        game.explore()
        self.assertIn("nothing dangerous", game.message)


class CombatTests(unittest.TestCase):
    """Cover hitting, being hit, dying, and the rewards for winning."""

    def setUp(self):
        self.game = make_game()
        self.enemy = Enemy("goblin", hp=8, damage=3, gold=10, xp=14)
        self.game.current_room().enemies.append(self.enemy)

    def test_attack_damages_the_enemy(self):
        with patch("game.roll_damage", return_value=(3, False)):
            self.game.attack_target("")
        self.assertEqual(self.enemy.hp, 5)
        self.assertIn("for 3 damage", self.game.message)

    def test_critical_hit_is_announced(self):
        with patch("game.roll_damage", return_value=(6, True)):
            self.game.attack_target("")
        self.assertIn("critical", self.game.message.lower())

    def test_enemy_strikes_back_and_armor_reduces_it(self):
        self.game.player.armor = make_item("gravemail")  # blocks 3
        with patch("game.roll_damage", return_value=(4, False)):
            self.game.attack_target("")
        self.assertEqual(self.game.player.hp, 19)  # 4 damage - 3 defense = 1

    def test_incoming_damage_never_drops_below_one(self):
        self.game.player.armor = make_item("gravemail")
        with patch("game.roll_damage", return_value=(1, False)):
            self.game.attack_target("")
        self.assertEqual(self.game.player.hp, 19)

    def test_killing_awards_gold_and_xp(self):
        gold = self.game.player.gold
        with patch("game.roll_damage", return_value=(99, False)):
            self.game.attack_target("")
        self.assertEqual(self.game.player.gold, gold + 10)
        self.assertEqual(self.game.current_room().enemies, [])
        self.assertIn("14 XP", self.game.message)

    def test_enough_xp_levels_the_player_up(self):
        self.game.player.xp = 19  # one short of the 20 needed for level 2
        self.game.player.hp = 5
        with patch("game.roll_damage", return_value=(99, False)):
            self.game.attack_target("")
        self.assertEqual(self.game.player.level, 2)
        self.assertEqual(self.game.player.max_hp, 25)
        self.assertEqual(self.game.player.hp, 25)  # level up heals fully
        self.assertIn("level 2", self.game.message)

    def test_attacking_nothing_is_reported(self):
        game = make_game()
        game.attack_target("")
        self.assertIn("nothing here to attack", game.message)

    def test_death_ends_the_run_and_starts_a_new_one(self):
        self.game.player.hp = 1
        self.game.player.gold = 100
        self.game.player.level = 6
        runs_before = self.game.legacy.runs

        with patch("game.roll_damage", return_value=(1, False)):
            self.game.attack_target("")

        # The run is gone: fresh character, fresh world, back at the start.
        self.assertEqual(self.game.legacy.runs, runs_before + 1)
        self.assertEqual(self.game.player.location, "square")
        self.assertEqual(self.game.player.level, 1)
        self.assertEqual(self.game.player.gold, 20)
        self.assertEqual(self.game.player.hp, self.game.player.max_hp)
        self.assertIn("finishes you in the dark", self.game.message)
        self.assertIn("Run 1:", self.game.message)

    def test_death_banks_echoes_for_the_next_run(self):
        self.game.player.hp = 1
        with patch("game.roll_damage", return_value=(1, False)):
            self.game.attack_target("")
        self.assertGreater(self.game.legacy.echoes, 0)

    def test_dying_does_not_erase_the_enemy_for_free(self):
        # Regression: death used to clear the room and full-heal you at no cost,
        # which made walking into a monster cheaper than paying to rest.
        self.game.player.hp = 1
        self.game.player.gold = 0
        with patch("game.roll_damage", return_value=(1, False)):
            self.game.attack_target("")
        self.assertEqual(self.game.legacy.runs, 1)  # it cost you the whole run


class FleeTests(unittest.TestCase):
    """Fleeing is a gamble that leaves the monster alive."""

    def setUp(self):
        self.game = make_game()
        self.game.player.location = "cave1"
        self.game.discover("cave1")
        self.enemy = Enemy("orc", hp=18, damage=6)
        self.game.current_room().enemies.append(self.enemy)

    def test_successful_flee_retreats_but_leaves_the_enemy(self):
        with patch("game.roll", return_value=0.0):
            self.game.flee()
        self.assertEqual(self.game.player.location, "forest")
        self.assertIn(self.enemy, self.game.world["cave1"].enemies)
        self.assertEqual(self.game.player.hp, 20)

    def test_failed_flee_costs_a_hit_and_keeps_you_in_place(self):
        with patch("game.roll", return_value=0.99), \
                patch("game.roll_damage", return_value=(6, False)):
            self.game.flee()
        self.assertEqual(self.game.player.location, "cave1")
        self.assertEqual(self.game.player.hp, 14)

    def test_retreat_prefers_the_safer_room(self):
        destination = self.game._retreat_destination(self.game.current_room())
        self.assertEqual(self.game.world[destination].danger, 0)

    def test_fleeing_nothing_is_reported(self):
        game = make_game()
        game.flee()
        self.assertIn("nothing to flee", game.message)


class ItemTests(unittest.TestCase):
    """Cover taking, dropping, using, and equipping."""

    def test_take_and_drop_round_trip(self):
        game = make_game()
        game.current_room().items.append(make_item("grave sword"))
        game.take_item("grave sword")
        self.assertEqual([i.name for i in game.player.inventory], ["blood vial", "grave sword"])

        game.drop_item("grave sword")
        self.assertEqual([i.name for i in game.player.inventory], ["blood vial"])
        self.assertEqual([i.name for i in game.current_room().items], ["grave sword"])

    def test_dropping_equipped_gear_unequips_it(self):
        game = make_game()
        game.player.inventory.append(make_item("grave sword"))
        game.equip_item("grave sword")
        self.assertEqual(game.player.attack_power(), 6)

        game.drop_item("grave sword")
        self.assertIsNone(game.player.weapon)
        self.assertEqual(game.player.attack_power(), 2)  # back to fists

    def test_equip_armor_raises_defense(self):
        game = make_game()
        game.player.inventory.append(make_item("tattered shroud"))
        game.equip_item("tattered shroud")
        self.assertEqual(game.player.defense(), 1)

    def test_potions_are_not_equippable(self):
        game = make_game()
        game.equip_item("blood vial")
        self.assertIn("can't equip", game.message)

    def test_using_a_potion_heals_and_consumes_it(self):
        game = make_game()
        game.player.hp = 5
        game.use_item("blood vial")
        self.assertEqual(game.player.hp, 15)
        self.assertEqual(game.player.inventory, [])

    def test_healing_is_capped_at_max_hp(self):
        game = make_game()
        game.use_item("blood vial")
        self.assertEqual(game.player.hp, 20)
        self.assertIn("already full", game.message)

    def test_unknown_item_reports_error(self):
        game = make_game()
        game.take_item("dragon")
        self.assertIn("not found", game.message.lower())

    def test_examine_describes_an_enemy(self):
        game = make_game()
        game.current_room().enemies.append(Enemy("goblin", description="Nasty."))
        game.examine_target("goblin")
        self.assertEqual(game.message, "Nasty.")


class EconomyTests(unittest.TestCase):
    """Cover buying, selling, and resting."""

    def test_buying_deducts_gold_and_leaves_the_shop_stocked(self):
        game = make_game()
        game.player.location = "smithy"
        game.player.gold = 100
        game.buy_item("bone dagger")
        self.assertEqual(game.player.gold, 80)
        self.assertIn("bone dagger", [i.name for i in game.player.inventory])
        self.assertIn("bone dagger", [i.name for i in game.current_room().shop])

    def test_buying_what_you_cannot_afford_changes_nothing(self):
        game = make_game()
        game.player.location = "smithy"
        game.player.gold = 5
        game.buy_item("barrow axe")
        self.assertEqual(game.player.gold, 5)
        self.assertEqual([i.name for i in game.player.inventory], ["blood vial"])

    def test_bought_item_is_a_copy_not_the_shop_instance(self):
        game = make_game()
        game.player.location = "smithy"
        game.player.gold = 100
        game.buy_item("bone dagger")
        bought = game.player.inventory[-1]
        stock = next(i for i in game.current_room().shop if i.name == "bone dagger")
        self.assertIsNot(bought, stock)

    def test_empty_buy_lists_the_wares(self):
        game = make_game()
        game.player.location = "smithy"
        game.buy_item("")
        self.assertIn("For sale:", game.message)

    def test_selling_pays_half_and_unequips(self):
        game = make_game()
        game.player.location = "market"
        game.player.inventory.append(make_item("grave sword"))
        game.equip_item("grave sword")
        gold = game.player.gold
        game.sell_item("grave sword")
        self.assertEqual(game.player.gold, gold + 27)  # 55 // 2
        self.assertIsNone(game.player.weapon)

    def test_selling_is_refused_outside_a_buying_shop(self):
        game = make_game()
        game.sell_item("blood vial")
        self.assertIn("can't sell", game.message)

    def test_rest_heals_at_the_inn_for_gold(self):
        game = make_game()
        game.player.location = "inn"
        game.player.hp = 3
        gold = game.player.gold
        game.rest()
        self.assertEqual(game.player.hp, game.player.max_hp)
        self.assertEqual(game.player.gold, gold - REST_COST)

    def test_rest_is_refused_elsewhere(self):
        game = make_game()
        game.player.hp = 3
        game.rest()
        self.assertEqual(game.player.hp, 3)
        self.assertIn("only rest at the Inn", game.message)

    def test_rest_is_refused_without_the_fee(self):
        game = make_game()
        game.player.location = "inn"
        game.player.hp = 3
        game.player.gold = 2
        game.rest()
        self.assertEqual(game.player.hp, 3)
        self.assertIn("Resting costs", game.message)


class SettingsCommandTests(unittest.TestCase):
    """Cover the settings sub-commands."""

    def test_toggle_flips_a_boolean(self):
        game = make_game()
        game.handle_settings_command("toggle show_map")
        self.assertFalse(game.settings.show_map)

    def test_toggle_rejects_a_non_boolean(self):
        game = make_game()
        game.handle_settings_command("toggle min_command_prefix")
        self.assertIn("not a toggle", game.message)

    def test_set_changes_a_number(self):
        game = make_game()
        game.handle_settings_command("set min_command_prefix 2")
        self.assertEqual(game.settings.min_command_prefix, 2)

    def test_set_rejects_an_out_of_range_prefix(self):
        game = make_game()
        game.handle_settings_command("set min_command_prefix 0")
        self.assertEqual(game.settings.min_command_prefix, 3)

    def test_set_rejects_unparseable_values(self):
        game = make_game()
        game.handle_settings_command("set min_command_prefix banana")
        self.assertEqual(game.settings.min_command_prefix, 3)
        self.assertIn("Invalid value", game.message)

    def test_unknown_setting_is_reported(self):
        game = make_game()
        game.handle_settings_command("toggle nonsense")
        self.assertIn("Unknown setting", game.message)

    def test_bare_settings_lists_them_all(self):
        game = make_game()
        game.handle_settings_command("")
        self.assertIn("auto_clear", game.message)


class RenderTests(unittest.TestCase):
    """The screen draw should be self-contained and consume the message."""

    def _draw(self, game) -> str:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            game.render()
        return buffer.getvalue()

    def test_render_shows_status_room_and_message(self):
        game = make_game()
        game.say("hello there")
        text = self._draw(game)
        self.assertIn("Greyfen Square", text)
        self.assertIn("HP [", text)  # the ASCII meter
        self.assertIn("Lv 1", text)
        self.assertIn("hello there", text)

    def test_message_is_cleared_after_being_shown(self):
        game = make_game()
        game.say("one-shot")
        self._draw(game)
        self.assertEqual(game.message, "")
        self.assertNotIn("one-shot", self._draw(game))

    def test_map_command_is_silent_when_the_map_is_already_shown(self):
        game = make_game()
        game.show_map()
        self.assertEqual(game.message, "")

    def test_map_command_prints_the_map_when_it_is_hidden(self):
        game = make_game()
        game.settings.show_map = False
        game.show_map()
        self.assertIn("YOU ARE HERE", game.message)


if __name__ == "__main__":
    unittest.main()
