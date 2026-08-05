"""Shared helpers for the test suite.

Named ``testkit`` rather than ``test_helpers`` on purpose: unittest discovers
``test*.py``, so a helper module named that way gets collected and run as if it
were a test file.

Everything here was duplicated across two or more test modules before it moved
in. Nothing game-specific belongs here -- only scaffolding.
"""

import contextlib
import io
import os
import tempfile
import unittest

import ui
from game import Game
from models import Legacy, Settings
from world import build_world

# How many generated worlds the invariant tests sweep. High enough to catch a
# layout bug, low enough that the suite still runs in seconds.
SEEDS = range(120)


# --------------------------------------------------------------------------
# Building things under test
# --------------------------------------------------------------------------


def make_game(legacy: Legacy | None = None, settings: Settings | None = None) -> Game:
    """A game that never clears the screen and never touches the real saves.

    ``legacy_path`` is deliberately left unset, so ending a run inside a test
    cannot write to the player's own save directory.
    """
    game = Game(legacy=legacy, settings=settings)
    game.settings.auto_clear = False
    return game


def worlds(limit: int | None = None):
    """Yield ``(seed, world)`` for the standard sweep."""
    for seed in list(SEEDS)[:limit]:
        yield seed, build_world(seed)


# --------------------------------------------------------------------------
# Asking questions of a world
# --------------------------------------------------------------------------


def reachable(rooms: dict, start: str = "square") -> set[str]:
    """Every room reachable from ``start`` by following exits."""
    seen, stack = {start}, [start]
    while stack:
        for target in rooms[stack.pop()].exits.values():
            if target in rooms and target not in seen:
                seen.add(target)
                stack.append(target)
    return seen


def bosses_in(world: dict, region: int) -> list:
    """Every room in a hold that holds a boss."""
    return [
        room
        for room in world.values()
        if room.region == region and any(enemy.boss for enemy in room.enemies)
    ]


def vault_of(world: dict, region: int):
    """The boss room of a hold, or None if it has none."""
    found = bosses_in(world, region)
    return found[0] if found else None


# --------------------------------------------------------------------------
# Capturing output and temporary files
# --------------------------------------------------------------------------


def capture(function, *args, **kwargs) -> str:
    """Run something and return whatever it printed."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        function(*args, **kwargs)
    return buffer.getvalue()


class TempFileMixin:
    """Gives a test case throwaway save paths that clean themselves up."""

    def temp_path(self, suffix: str = ".sav") -> str:
        """An absolute path to a file that is removed when the test ends."""
        handle, path = tempfile.mkstemp(suffix=suffix)
        os.close(handle)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        return path

    def temp_dir(self) -> str:
        """A throwaway directory, emptied and removed when the test ends."""
        directory = tempfile.mkdtemp()

        def clean():
            if not os.path.isdir(directory):
                return
            for entry in os.listdir(directory):
                os.remove(os.path.join(directory, entry))
            os.rmdir(directory)

        self.addCleanup(clean)
        return directory


class DisplayMixin:
    """Forces colour and box-drawing on, whatever terminal runs the tests.

    The interface decides at import whether the console can render escapes, so
    a test that wants to check painted output has to say so -- and put the real
    values back afterwards, since they are module globals.
    """

    def force_display(self, color: bool = True, unicode: bool = True) -> None:
        before = (ui._ANSI_READY, ui._UNICODE_READY, ui.color_enabled(), ui.unicode_enabled())

        def restore():
            ui._ANSI_READY, ui._UNICODE_READY = before[0], before[1]
            ui.set_color(before[2])
            ui.set_unicode(before[3])

        self.addCleanup(restore)
        ui._ANSI_READY = ui._UNICODE_READY = True
        ui.set_color(color)
        ui.set_unicode(unicode)


class WorldCase(unittest.TestCase):
    """Base for tests that sweep many generated worlds."""

    def assertEveryWorld(self, check, limit: int | None = None) -> None:
        """Run ``check(seed, world)`` over the sweep, naming the seed on failure."""
        for seed, world in worlds(limit):
            with self.subTest(seed=seed):
                check(seed, world)
