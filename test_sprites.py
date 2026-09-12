"""Tests for the sprite library and the panelled interface it sits in.

Two kinds of promise are checked here. The sprites must cover every creature in
the game in every pose, at a fixed size -- otherwise a panel changes height as
the player walks, or a monster turns up with no body. And the screen must be
exactly one width, always, because the whole thing is one drawn box and a single
mis-measured line puts a border in the wrong column.
"""

import unittest

import sprites
from content import THEMES
from models import Enemy
from testkit import DisplayMixin, capture, make_game
from ui import WIDTH, visible_len


def every_creature() -> set[str]:
    """Every enemy and boss name the content tables can produce."""
    names = set()
    for theme in THEMES.values():
        for pool in theme["enemies"].values():
            names |= {row[0] for row in pool}
        names.add(theme["boss"][0])
    return names


class CoverageTests(unittest.TestCase):
    """Every creature has a body, and every body has every pose."""

    def test_every_creature_resolves_to_a_real_archetype(self):
        for name in every_creature():
            self.assertIn(sprites.archetype(name), sprites.SPRITES, name)

    def test_every_archetype_has_all_three_poses(self):
        for kind, poses in sprites.SPRITES.items():
            for pose in sprites.POSES:
                self.assertIn(pose, poses, f"{kind} is missing {pose}")

    def test_the_player_has_all_three_poses(self):
        for pose in sprites.POSES:
            self.assertIn(pose, sprites.PLAYER, pose)

    def test_every_boss_has_art_of_its_own(self):
        # A boss wearing a common archetype would read as just another monster.
        bosses = {theme["boss"][0] for theme in THEMES.values()}
        shared = {sprites.archetype(name) for name in every_creature() - bosses}
        for boss in bosses:
            self.assertNotIn(sprites.archetype(boss), shared, boss)

    def test_every_archetype_is_reachable_by_some_creature(self):
        used = {sprites.archetype(name) for name in every_creature()}
        unused = set(sprites.SPRITES) - used
        self.assertFalse(unused, f"art nothing can wear: {sorted(unused)}")

    def test_every_archetype_has_a_tint(self):
        for kind in sprites.SPRITES:
            self.assertIn(kind, sprites.TINTS, kind)


class GeometryTests(unittest.TestCase):
    """A sprite is a fixed size, so the panel holding it never jitters."""

    def test_every_frame_is_the_declared_height(self):
        for kind, poses in sprites.SPRITES.items():
            for pose, art in poses.items():
                self.assertEqual(len(art), sprites.SPRITE_HEIGHT, f"{kind}/{pose}")

    def test_every_frame_is_the_declared_width(self):
        for kind, poses in sprites.SPRITES.items():
            for pose, art in poses.items():
                for line in art:
                    self.assertEqual(len(line), sprites.SPRITE_WIDTH, f"{kind}/{pose}")

    def test_the_player_is_the_same_size(self):
        for pose, art in sprites.PLAYER.items():
            self.assertEqual(len(art), sprites.SPRITE_HEIGHT, pose)
            for line in art:
                self.assertEqual(len(line), sprites.SPRITE_WIDTH, pose)

    def test_sprites_are_pure_ascii(self):
        # They have to survive a console that cannot encode box-drawing, which
        # is the same reason the frame has an ASCII fallback.
        for poses in [*sprites.SPRITES.values(), sprites.PLAYER]:
            for pose, art in poses.items():
                for line in art:
                    self.assertTrue(line.isascii(), f"{pose}: {line!r}")

    def test_two_sprites_fit_side_by_side_in_a_panel(self):
        from ui import INNER, side_by_side

        for name in every_creature():
            paired = side_by_side(
                sprites.for_player("attack", tint=False),
                sprites.for_enemy(name, "attack", tint=False),
                gap=10,
            )
            for line in paired:
                self.assertLessEqual(visible_len(line), INNER, name)


class PoseTests(unittest.TestCase):
    """Poses are frames of a turn, set by what happened and cleared by the draw."""

    def _fight(self):
        game = make_game()
        game.player.location = "cave1"
        enemy = Enemy("barrow wight", hp=40, max_hp=40, damage=4)
        game.current_room().enemies.append(enemy)
        return game, enemy

    def test_attacking_poses_you_swinging_and_it_reeling(self):
        game, _enemy = self._fight()
        game.attack_target("")
        self.assertEqual(game.poses["player"], "attack")

    def test_guarding_poses_you_braced(self):
        game, _enemy = self._fight()
        game.guard()
        self.assertEqual(game.poses["player"], "hit")

    def test_feeding_poses_you_lunging(self):
        game, enemy = self._fight()
        enemy.hp = 4
        game.feed()
        self.assertEqual(game.poses["player"], "attack")

    def test_a_wind_up_poses_it_coiled(self):
        from unittest.mock import patch

        game, enemy = self._fight()
        with patch("game.roll", return_value=0.0):
            game._enemy_strikes(enemy)
        self.assertEqual(game.poses["enemy"], "attack")

    def test_the_draw_puts_everything_back_to_idle(self):
        game, _enemy = self._fight()
        game.attack_target("")
        capture(game.render)
        self.assertEqual(game.poses, {"player": "idle", "enemy": "idle"})


class ScreenTests(DisplayMixin, unittest.TestCase):
    """The screen is one drawn box, so every line is exactly one width."""

    def setUp(self):
        self.force_display()

    def _lines(self, game) -> list[str]:
        return [line for line in capture(game.render).splitlines() if line.strip()]

    def test_every_line_is_the_interface_width_while_exploring(self):
        game = make_game()
        game.say("a message long enough that the panel has to wrap it somewhere")
        for line in self._lines(game):
            self.assertEqual(visible_len(line), WIDTH, repr(line))

    def test_every_line_is_the_interface_width_in_a_fight(self):
        for name in sorted(every_creature()):
            game = make_game()
            game.player.location = "cave1"
            game.current_room().enemies.append(
                Enemy(name, hp=30, max_hp=60, damage=5)
            )
            for pose in sprites.POSES:
                game.poses = {"player": pose, "enemy": pose}
                for line in self._lines(game):
                    self.assertEqual(visible_len(line), WIDTH, f"{name}/{pose}")

    def test_every_line_is_the_interface_width_without_colour_or_lines(self):
        import ui

        self.force_display(color=False, unicode=False)
        game = make_game()
        game.player.location = "cave1"
        game.current_room().enemies.append(Enemy("pale king", hp=9, max_hp=450, boss=True))
        for line in self._lines(game):
            self.assertEqual(ui.visible_len(line), WIDTH, repr(line))

    def test_a_fight_shows_the_duel_instead_of_the_map(self):
        game = make_game()
        game.player.location = "cave1"
        game.current_room().enemies.append(Enemy("grave rat", hp=5, max_hp=5))
        text = capture(game.render)
        self.assertIn("GRAVE RAT", text)
        self.assertNotIn("the map", text)

    def test_turning_sprites_off_brings_the_map_back(self):
        game = make_game()
        game.settings.show_sprites = False
        game.player.location = "cave1"
        game.current_room().enemies.append(Enemy("grave rat", hp=5, max_hp=5))
        self.assertIn("the map", capture(game.render))

    def test_the_screen_fits_a_reasonable_terminal(self):
        game = make_game()
        game.player.location = "cave1"
        game.current_room().enemies.append(Enemy("grave rat", hp=5, max_hp=5))
        fight = len(capture(game.render).splitlines())

        explore = len(capture(make_game().render).splitlines())
        self.assertLessEqual(max(fight, explore), 30, "the screen is getting tall")


if __name__ == "__main__":
    unittest.main()
