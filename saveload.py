"""Save and load game state as JSON.

Static room text, exits, shops, and coordinates are recreated from
``build_world`` on load; only the parts that change during play (each room's
items and enemies, plus the player, settings, and the discovered map) are
stored and laid back over the fresh world. The cave's generator seed is saved
too, so the rebuilt world has the same layout you were standing in.

Loading is forgiving about version drift: fields the current code no longer
knows about are ignored, and anything malformed raises ``ValueError`` rather
than escaping as a raw ``TypeError``/``KeyError``.

Save files are anchored to this game's own folder (not the shell's current
directory), so ``save``/``load`` behave the same no matter where you launch
Python from. Writes are atomic: the data goes to a temporary file first and is
only swapped into place once it is fully written.
"""

import base64
import json
import os
import re
import tempfile
import zlib
from dataclasses import asdict, fields

from models import Enemy, Item, Legacy, Player, Settings
from world import DEFAULT_DUNGEON_SEED, build_world

# Directory this module lives in -- i.e. the game's folder.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Save obfuscation. This scrambles the save so it is not readable at a glance
# (no spoilers when you open the file), but it is NOT encryption: the key lives
# here in the source, because the game must read the save without a password.
# Anyone who reads this file can reverse it. Files start with MAGIC so load can
# tell an obfuscated save from a plain-JSON one.
MAGIC = "TBSV1:"
_XOR_KEY = b"textbased-save-scramble-v1"


def _xor(data: bytes) -> bytes:
    """Scramble/unscramble bytes with the repeating key (symmetric)."""
    key = _XOR_KEY
    return bytes(byte ^ key[i % len(key)] for i, byte in enumerate(data))


def _obfuscate(text: str) -> str:
    """Turn readable JSON into a single opaque, MAGIC-prefixed blob."""
    packed = _xor(zlib.compress(text.encode("utf-8"), 9))
    return MAGIC + base64.b64encode(packed).decode("ascii")


def _deobfuscate(blob: str) -> str:
    """Reverse ``_obfuscate``. Raises ValueError on a corrupt blob."""
    try:
        packed = base64.b64decode(blob[len(MAGIC):])
        return zlib.decompress(_xor(packed)).decode("utf-8")
    except (ValueError, zlib.error) as error:
        raise ValueError("save file is corrupted or not a valid save") from error


SAVE_DIR = "saves"


def slug(name: str) -> str:
    """Turn a character name into a safe filename stem.

    Names are player-supplied and land straight in a path, so everything except
    letters and digits collapses to underscores. That keeps a name like
    ``../../etc`` from ever escaping the saves folder.
    """
    cleaned = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return cleaned or "nameless"


def character_path(name: str, suffix: str = "") -> str:
    """Where the character called ``name`` keeps their files."""
    return os.path.join(SAVE_DIR, f"{slug(name)}{suffix}.sav")


def resolve_save_path(path: str) -> str:
    """Resolve a save name to an absolute path inside the game folder.

    Absolute paths are used as given; relative names land next to the game.
    """
    return path if os.path.isabs(path) else os.path.join(BASE_DIR, path)


def _as_dict(data, what: str) -> dict:
    """Return ``data`` if it is a dict, else raise a clear ValueError."""
    if not isinstance(data, dict):
        raise ValueError(f"save file has a malformed {what}")
    return data


def _from_dict(cls, data, what: str):
    """Build a dataclass from saved data, tolerating version drift.

    Keys this version of the game no longer recognizes are dropped instead of
    blowing up, and a genuinely malformed record raises ``ValueError`` so the
    caller can report it as a bad save rather than crashing.
    """
    if not isinstance(data, dict):
        raise ValueError(f"save file has a malformed {what}")

    known = {field.name for field in fields(cls)}
    try:
        return cls(**{key: value for key, value in data.items() if key in known})
    except TypeError as error:
        raise ValueError(f"save file has a malformed {what}: {error}") from error


def _write_text(payload: str, target: str) -> None:
    """Write ``payload`` to ``target`` atomically.

    The data goes to a temporary file in the same directory and is swapped into
    place only once fully written, so an interrupted write can never truncate a
    save that already exists.
    """
    directory = os.path.dirname(target) or "."
    # A per-character save lives in saves/, which may not exist on a first run.
    os.makedirs(directory, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".tmp",
        dir=directory,
        delete=False,
    )
    try:
        with handle:
            handle.write(payload)
        os.replace(handle.name, target)
    except BaseException:
        try:
            os.remove(handle.name)
        except OSError:
            pass
        raise


def _read_text(target: str) -> str:
    """Read a save file, un-scrambling it if it was written obfuscated."""
    with open(target, "r", encoding="utf-8") as handle:
        contents = handle.read()
    # Auto-detect: obfuscated saves start with MAGIC; older saves are plain JSON.
    return _deobfuscate(contents) if contents.startswith(MAGIC) else contents


def save_legacy(legacy: Legacy, path: str) -> str:
    """Write the cross-run Legacy to its own small file."""
    target = resolve_save_path(path)
    _write_text(_obfuscate(json.dumps(asdict(legacy), indent=2)), target)
    return target


def load_legacy(path: str) -> Legacy:
    """Read the Legacy file, or return a fresh one if there isn't a usable one.

    A missing or damaged Legacy is not worth refusing to start over: the game
    quietly begins a first run rather than reporting an error nobody can fix.
    """
    try:
        data = json.loads(_read_text(resolve_save_path(path)))
    except (OSError, ValueError):
        return Legacy()

    try:
        loaded = _from_dict(Legacy, data, "legacy")
    except ValueError:
        return Legacy()

    # Guard the containers: a hand-edited file must not crash a run later.
    if not isinstance(loaded.relics, list):
        loaded.relics = []
    if not isinstance(loaded.blessings, dict):
        loaded.blessings = {}
    return loaded


OPTIONS_PATH = os.path.join(SAVE_DIR, "options.sav")


def save_options(settings: Settings, path: str = OPTIONS_PATH) -> str:
    """Write the menu's Options screen to disk. Returns the path written."""
    target = resolve_save_path(path)
    _write_text(_obfuscate(json.dumps(asdict(settings), indent=2)), target)
    return target


def load_options(path: str = OPTIONS_PATH) -> Settings:
    """Read saved Options, or return the defaults if there aren't usable ones.

    Bad options are not worth refusing to start over: the game quietly falls
    back to defaults rather than reporting an error at the title screen.
    """
    try:
        data = json.loads(_read_text(resolve_save_path(path)))
        return _from_dict(Settings, data, "options")
    except (OSError, ValueError):
        return Settings()


def list_characters(directory: str = SAVE_DIR) -> list[tuple[str, Legacy, float]]:
    """Every saved character as ``(path, legacy, last_played)``, newest first.

    ``last_played`` is the save file's modification time, which is what makes
    "Continue" mean the character you actually played last.
    """
    root = resolve_save_path(directory)
    if not os.path.isdir(root):
        return []

    found = []
    for entry in sorted(os.listdir(root)):
        if not entry.endswith(".sav") or entry == os.path.basename(OPTIONS_PATH):
            continue
        path = os.path.join(directory, entry)
        legacy = load_legacy(path)
        # A file that will not parse comes back as a default Legacy. Skip those
        # rather than offering a slot that has lost its name.
        if not legacy.name or legacy.name == Legacy.name:
            continue
        found.append((path, legacy, os.path.getmtime(resolve_save_path(path))))

    found.sort(key=lambda row: row[2], reverse=True)
    return found


def _serialize(game) -> dict:
    """Convert a game into a plain dictionary ready for JSON."""
    player = game.player
    return {
        # Regenerating the cave from this seed restores the exact same layout.
        "dungeon_seed": game.dungeon_seed,
        # Everything that outlives the run, plus where this run had got to.
        "legacy": asdict(game.legacy),
        "bosses_killed": game.bosses_killed,
        "region_reached": game.region_reached,
        "player": {
            "name": player.name,
            "hp": player.hp,
            "max_hp": player.max_hp,
            "gold": player.gold,
            "level": player.level,
            "xp": player.xp,
            "location": player.location,
            "bonus_attack": player.bonus_attack,
            "bonus_max_hp": player.bonus_max_hp,
            "bonus_defense": player.bonus_defense,
            "relics": [asdict(item) for item in player.relics],
            "inventory": [asdict(item) for item in player.inventory],
            # Gear is stored by name and re-linked to the inventory on load.
            "weapon": player.weapon.name if player.weapon else None,
            "armor": player.armor.name if player.armor else None,
        },
        "settings": asdict(game.settings),
        "discovered": sorted(game.discovered),
        "rooms": {
            key: {
                "items": [asdict(item) for item in room.items],
                "enemies": [asdict(enemy) for enemy in room.enemies],
            }
            for key, room in game.world.items()
        },
    }


def save_game(game, path: str) -> str:
    """Write the game state to ``path``. Returns the absolute path written."""
    target = resolve_save_path(path)
    directory = os.path.dirname(target) or "."

    text = json.dumps(_serialize(game), indent=2)
    if getattr(game.settings, "obfuscate_saves", True):
        payload = _obfuscate(text)
    else:
        payload = text

    # Write to a temp file in the same directory, then atomically replace, so a
    # failure never leaves a half-written save behind.
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".tmp",
        dir=directory,
        delete=False,
    )
    try:
        with handle:
            handle.write(payload)
        os.replace(handle.name, target)
    except BaseException:
        try:
            os.remove(handle.name)
        except OSError:
            pass
        raise

    return target


def load_game(game, path: str) -> str:
    """Load game state from ``path`` and apply it to ``game`` in place.

    Returns the absolute path read. Raises ``ValueError`` if the file is not a
    valid save.
    """
    target = resolve_save_path(path)
    contents = _read_text(target)

    try:
        data = json.loads(contents)
    except json.JSONDecodeError as error:
        raise ValueError("save file is not valid JSON") from error

    try:
        player_data = data["player"]
        settings_data = data["settings"]
        rooms_data = data["rooms"]
        discovered = set(data["discovered"])
    except (KeyError, TypeError) as error:
        raise ValueError("save file is missing required fields") from error

    if not isinstance(rooms_data, dict):
        raise ValueError("save file has a malformed room list")

    # Saves written before seeds were recorded fall back to the default cave.
    seed = data.get("dungeon_seed", DEFAULT_DUNGEON_SEED)
    if not isinstance(seed, int) or isinstance(seed, bool):
        seed = DEFAULT_DUNGEON_SEED

    world = build_world(seed)
    for key, room_state in rooms_data.items():
        if key not in world:
            continue
        world[key].items = [
            _from_dict(Item, item, "item") for item in room_state.get("items", [])
        ]
        world[key].enemies = [
            _from_dict(Enemy, enemy, "enemy") for enemy in room_state.get("enemies", [])
        ]

    inventory = [
        _from_dict(Item, item, "item") for item in player_data.get("inventory", [])
    ]
    relics = [
        _from_dict(Item, item, "relic") for item in player_data.get("relics", [])
    ]

    # Gear is stored by name, so drop those strings before building the Player
    # and re-link them to the real inventory items afterwards.
    player_fields = {
        key: value
        for key, value in _as_dict(player_data, "player").items()
        if key not in {"weapon", "armor", "inventory", "relics"}
    }
    player = _from_dict(
        Player,
        {**player_fields, "inventory": inventory, "relics": relics},
        "player",
    )

    def find(name):
        if name is None:
            return None
        return next((item for item in inventory if item.name == name), None)

    player.weapon = find(player_data.get("weapon"))
    player.armor = find(player_data.get("armor"))

    # Never leave the player standing in, or remembering, a room that this
    # version of the world no longer has.
    if player.location not in world:
        player.location = Player.location
    discovered = {key for key in discovered if key in world}

    # A save from before Legacy existed simply starts one.
    legacy_data = data.get("legacy")
    loaded_legacy = (
        _from_dict(Legacy, legacy_data, "legacy")
        if isinstance(legacy_data, dict)
        else Legacy()
    )

    # Only commit to the loaded state once everything parsed successfully.
    game.dungeon_seed = seed
    game.world = world
    game.player = player
    game.settings = _from_dict(Settings, settings_data, "settings")
    game.discovered = discovered or {player.location}
    game.legacy = loaded_legacy
    game.bosses_killed = _as_int(data.get("bosses_killed"), 0)
    game.region_reached = _as_int(data.get("region_reached"), 1)

    return target


def _as_int(value, default: int) -> int:
    """Coerce a saved value to an int, falling back when it is not one."""
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return value
