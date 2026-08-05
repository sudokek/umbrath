"""Unit tests for saving and loading, including save obfuscation."""

import json
import os
import tempfile
import unittest

import saveload
from content import make_item
from game import Game


class SaveLoadTests(unittest.TestCase):
    """Round-trip saves in both obfuscated and plain modes."""

    def _temp_path(self) -> str:
        """Return an absolute temp path that is cleaned up after the test."""
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        return path

    def _read(self, path: str) -> str:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()

    def test_obfuscated_save_is_not_readable_but_round_trips(self):
        game = Game()
        game.player.gold = 999
        game.settings.obfuscate_saves = True
        path = self._temp_path()

        saveload.save_game(game, path)

        contents = self._read(path)
        self.assertTrue(contents.startswith(saveload.MAGIC))
        self.assertNotIn("gold", contents)  # no plaintext spoilers
        self.assertNotIn("goblin", contents)

        loaded = Game()
        saveload.load_game(loaded, path)
        self.assertEqual(loaded.player.gold, 999)

    def test_plain_save_is_human_readable_and_round_trips(self):
        game = Game()
        game.player.gold = 42
        game.settings.obfuscate_saves = False
        path = self._temp_path()

        saveload.save_game(game, path)

        contents = self._read(path)
        self.assertIn("gold", contents)  # readable on purpose
        json.loads(contents)  # valid plain JSON

        loaded = Game()
        saveload.load_game(loaded, path)
        self.assertEqual(loaded.player.gold, 42)

    def test_corrupt_obfuscated_save_raises_valueerror(self):
        path = self._temp_path()
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(saveload.MAGIC + "not-valid-base64-data!!!")

        with self.assertRaises(ValueError):
            saveload.load_game(Game(), path)

    def test_progress_survives_a_round_trip(self):
        game = Game()
        game.settings.obfuscate_saves = False
        game.player.level = 4
        game.player.xp = 12
        game.player.max_hp = 35
        game.player.inventory.append(make_item("grave sword"))
        game.equip_item("grave sword")
        path = self._temp_path()

        saveload.save_game(game, path)
        loaded = Game()
        saveload.load_game(loaded, path)

        self.assertEqual(loaded.player.level, 4)
        self.assertEqual(loaded.player.xp, 12)
        self.assertEqual(loaded.player.max_hp, 35)
        # Gear is stored by name and must be re-linked to a real inventory item.
        self.assertEqual(loaded.player.weapon.name, "grave sword")
        self.assertIn(loaded.player.weapon, loaded.player.inventory)


class DungeonSeedTests(unittest.TestCase):
    """The cave layout must be random per game and stable across a save."""

    def test_new_games_get_different_caves(self):
        seeds = {Game().dungeon_seed for _ in range(8)}
        self.assertGreater(len(seeds), 1)

    def test_saved_seed_rebuilds_the_same_cave(self):
        game = Game()
        before = {key: room.name for key, room in game.world.items()}

        fd, path = tempfile.mkstemp(suffix=".sav")
        os.close(fd)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        saveload.save_game(game, path)

        loaded = Game()
        saveload.load_game(loaded, path)

        self.assertEqual(loaded.dungeon_seed, game.dungeon_seed)
        self.assertEqual({k: r.name for k, r in loaded.world.items()}, before)


class SaveCompatibilityTests(unittest.TestCase):
    """Loading must survive version drift instead of crashing the game."""

    def _write_save(self, mutate) -> str:
        game = Game()
        game.settings.obfuscate_saves = False
        fd, path = tempfile.mkstemp(suffix=".sav")
        os.close(fd)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))

        saveload.save_game(game, path)
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        mutate(data)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        return path

    def test_unknown_setting_is_ignored(self):
        def add_setting(data):
            data["settings"]["setting_from_the_future"] = True

        loaded = Game()
        saveload.load_game(loaded, self._write_save(add_setting))
        self.assertFalse(hasattr(loaded.settings, "setting_from_the_future"))

    def test_unknown_item_field_is_ignored(self):
        def add_field(data):
            data["player"]["inventory"][0]["sparkles"] = True

        loaded = Game()
        saveload.load_game(loaded, self._write_save(add_field))
        self.assertEqual(loaded.player.inventory[0].name, "blood vial")

    def test_missing_player_field_falls_back_to_the_default(self):
        def drop_hp(data):
            del data["player"]["hp"]

        loaded = Game()
        saveload.load_game(loaded, self._write_save(drop_hp))
        self.assertEqual(loaded.player.hp, 20)

    def test_malformed_record_raises_valueerror_not_typeerror(self):
        def break_item(data):
            data["player"]["inventory"][0] = {"description": "no name field"}

        with self.assertRaises(ValueError):
            saveload.load_game(Game(), self._write_save(break_item))

    def test_stale_location_falls_back_to_the_square(self):
        def move_nowhere(data):
            data["player"]["location"] = "room_that_no_longer_exists"
            data["discovered"].append("also_gone")

        loaded = Game()
        saveload.load_game(loaded, self._write_save(move_nowhere))
        self.assertEqual(loaded.player.location, "square")
        self.assertNotIn("also_gone", loaded.discovered)


if __name__ == "__main__":
    unittest.main()
