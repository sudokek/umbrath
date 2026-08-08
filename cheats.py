"""A debug console for manual testing, opened by typing ``topkek``.

Kept entirely out of :mod:`parser` and :mod:`game`'s command table on purpose.
Cheat verbs are matched *before* ordinary parsing and never enter
``parser.COMMANDS``, so the invariant that every real command has a handler --
and every handler has a command -- keeps holding with cheats on or off.

Nothing here reads a hardcoded list of content. ``give`` enumerates
:data:`content.ITEMS` live and ``tp`` builds its destinations from the world in
front of it, so anything added to the game shows up here without being
registered twice.
"""

from content import ITEMS, CHEST_NAMES, make_item, make_trader, roll_hoard, spawn_enemy
from models import Chest
from parser import match_target
from ui import paint

WORD = "topkek"


# --------------------------------------------------------------------------
# Handlers. Each takes (game, target) and returns the lines to show.
# --------------------------------------------------------------------------


def _give(game, target: str) -> list[str]:
    """Put any item in the registry into the player's hands."""
    names = sorted(ITEMS)
    if not target.strip() or target.strip() in {"list", "?"}:
        return _catalogue()

    if target.strip() == "all":
        for name in names:
            game.player.inventory.append(make_item(name))
        return [f"Gave all {len(names)} items."]

    name, error = match_target(target, names)
    if error:
        return [error, "Type GIVE with no argument to list everything."]

    game.player.inventory.append(make_item(name))
    return [f"Gave {name}."]


def _catalogue() -> list[str]:
    """Every item the game knows about, grouped, straight from the registry."""
    by_kind: dict[str, list[str]] = {}
    for item in ITEMS.values():
        by_kind.setdefault(item.kind, []).append(item.name)

    lines = [f"{len(ITEMS)} items in the registry:"]
    for kind in sorted(by_kind):
        lines.append(f"  {kind}: {', '.join(sorted(by_kind[kind]))}")
    return lines


def _destinations(game) -> dict[str, str]:
    """Every place ``tp`` can send you, derived from the world itself."""
    places: dict[str, str] = {}

    def note(label: str, key: str, region: int) -> None:
        """Register a landmark twice: numbered, and bare for the first hold.

        So ``forge2`` reaches Ashmoor's and a bare ``forge`` still means the one
        you start next to -- which stops being obvious the moment there is more
        than one of everything.
        """
        places[f"{label}{region}"] = key
        places.setdefault(label, key)

    for key, room in game.world.items():
        if any(enemy.boss for enemy in room.enemies):
            note("boss", key, room.region)
        if room.shrine:
            places["shrine"] = key
        if room.inn:
            note("inn", key, room.region)
        if room.shop and room.can_sell:
            note("market", key, room.region)
        if room.shop and not room.can_sell:
            note("forge", key, room.region)
        if room.key.startswith("square"):
            note("town", key, room.region)
        if room.key.startswith("cave"):
            places.setdefault(f"cave{room.region}", key)

    return places


def _tp(game, target: str) -> list[str]:
    """Teleport anywhere: a named landmark, or a raw room key."""
    places = _destinations(game)
    wanted = target.strip().lower()

    if not wanted:
        return ["tp <where>. Known: " + ", ".join(sorted(places)),
                "Any room key also works."]

    key = places.get(wanted) or (wanted if wanted in game.world else None)
    if key is None:
        name, error = match_target(wanted, sorted(places))
        key = places.get(name) if not error else None

    if key is None:
        return [f"Nowhere called {target!r}.",
                "Known: " + ", ".join(sorted(places))]

    game.player.location = key
    game.discover(key)
    room = game.world[key]
    return [f"Teleported to {room.name} (hold {room.region}, tier {room.danger})."]


def _number(target: str, default: int | None = None) -> int | None:
    """Read a whole number from a cheat argument."""
    try:
        return int(target.strip())
    except (TypeError, ValueError):
        return default


def _hp(game, target: str) -> list[str]:
    """Set current HP. ``hp max`` tops up; ``hp 1`` puts you on the edge."""
    if target.strip() in {"max", "full", ""}:
        game.player.hp = game.player.max_hp
    else:
        value = _number(target)
        if value is None:
            return ["hp <number|max>"]
        game.player.hp = max(0, min(value, game.player.max_hp))
    return [f"HP set to {game.player.hp}/{game.player.max_hp}."]


def _maxhp(game, target: str) -> list[str]:
    """Set maximum HP, and heal to it."""
    value = _number(target)
    if value is None or value < 1:
        return ["maxhp <number>"]
    game.player.max_hp = value
    game.player.hp = value
    return [f"Max HP set to {value}."]


def _level(game, target: str) -> list[str]:
    """Jump to a level, applying every level-up along the way."""
    value = _number(target)
    if value is None or value < 1:
        return ["level <number>"]

    player = game.player
    while player.level > value:
        player.level -= 1
        player.max_hp -= 5
    while player.level < value:
        player.level += 1
        player.max_hp += 5
    player.hp = player.max_hp
    return [f"Level set to {player.level} (max HP {player.max_hp})."]


def _gold(game, target: str) -> list[str]:
    """Set coin."""
    value = _number(target)
    if value is None:
        return ["gold <number>"]
    game.player.gold = max(0, value)
    return [f"Coin set to {game.player.gold}."]


def _echoes(game, target: str) -> list[str]:
    """Set echoes, for testing the shrine."""
    value = _number(target)
    if value is None:
        return ["echoes <number>"]
    game.legacy.echoes = max(0, value)
    return [f"Echoes set to {game.legacy.echoes}."]


def _relic(game, target: str) -> list[str]:
    """Grant a relic permanently, as a boss kill would."""
    relics = sorted(name for name, item in ITEMS.items() if item.kind == "relic")
    if not target.strip():
        return ["relic <name>. Known: " + ", ".join(relics)]

    name, error = match_target(target, relics)
    if error:
        return [error, "Known: " + ", ".join(relics)]
    return game._claim_relic(name) or [f"Already carrying {name}."]


def _spawn(game, target: str) -> list[str]:
    """Put an enemy in this room, at a tier you choose."""
    room = game.current_room()
    tier = _number(target, 1) or 1
    theme = room.theme or "barrow"
    enemy = spawn_enemy(theme, max(1, min(3, tier)))
    room.enemies.append(enemy)
    return [f"Spawned {enemy.name} ({enemy.hp} HP, {enemy.damage} dmg)."]


def _kill(game, target: str) -> list[str]:
    """Remove whatever is here, without the fight or the rewards."""
    room = game.current_room()
    if not room.enemies:
        return ["Nothing here to kill."]
    gone = [enemy.name for enemy in room.enemies]
    room.enemies.clear()
    return [f"Removed: {', '.join(gone)}."]


def _wound(game, target: str) -> list[str]:
    """Set the enemy here to a percentage of its health.

    Mostly for FEED, which only unlocks below 35%.
    """
    room = game.current_room()
    if not room.enemies:
        return ["Nothing here to wound."]

    percent = _number(target, 20) or 20
    enemy = room.enemies[0]
    enemy.hp = max(1, int((enemy.max_hp or enemy.hp) * percent / 100))
    return [f"{enemy.name} set to {enemy.hp}/{enemy.max_hp} ({percent}%)."]


def _windup(game, target: str) -> list[str]:
    """Force the enemy here to telegraph, for testing GUARD."""
    room = game.current_room()
    if not room.enemies:
        return ["Nothing here to wind up."]
    room.enemies[0].winding_up = True
    return [f"{room.enemies[0].name} is now winding up."]


def _chest(game, target: str) -> list[str]:
    """Drop a chest here, rolled at a tier you choose."""
    room = game.current_room()
    tier = _number(target, max(1, room.danger)) or 1
    tier = max(1, min(3, tier))
    room.chest = Chest(
        name=CHEST_NAMES[0],
        contents=roll_hoard(room.region, tier, count=1 + tier),
    )
    return [f"Chest here, tier {tier}: "
            + ", ".join(item.name for item in room.chest.contents)]


def _trader(game, target: str) -> list[str]:
    """Put a wandering trader here."""
    room = game.current_room()
    room.trader = make_trader(room.region)
    return [f"{room.trader.name} is here with "
            + ", ".join(item.name for item in room.trader.stock)]


def _reveal(game, target: str) -> list[str]:
    """Discover the whole world, so the map shows everything."""
    game.discovered = set(game.world)
    return [f"Revealed all {len(game.world)} rooms."]


def _god(game, target: str) -> list[str]:
    """Toggle taking no damage."""
    game.godmode = not getattr(game, "godmode", False)
    return [f"God mode {'ON -- nothing can hurt you' if game.godmode else 'OFF'}."]


def _where(game, target: str) -> list[str]:
    """Dump everything about where you are standing."""
    room = game.current_room()
    return [
        f"key={room.key}  hold={room.region}  tier={room.danger}  theme={room.theme}",
        f"exits={room.exits}",
        f"items={[i.name for i in room.items]}",
        f"enemies={[(e.name, e.hp, e.max_hp) for e in room.enemies]}",
        f"chest={room.chest.name if room.chest else None}"
        f"  opened={room.chest.opened if room.chest else '-'}",
        f"dungeon_seed={game.dungeon_seed}",
    ]


# name -> (handler, one-line help). Order is the order shown.
CHEATS: dict[str, tuple] = {
    "give": (_give, "give <item|all>   any item, live from the registry"),
    "tp": (_tp, "tp <where>        boss1-3, town1-3, shrine, forge, or a room key"),
    "hp": (_hp, "hp <n|max>        set current health"),
    "maxhp": (_maxhp, "maxhp <n>         set maximum health"),
    "level": (_level, "level <n>         jump to a level"),
    "gold": (_gold, "gold <n>          set coin"),
    "echoes": (_echoes, "echoes <n>        set echoes, for the shrine"),
    "relic": (_relic, "relic <name>      grant a relic permanently"),
    "spawn": (_spawn, "spawn <tier>      put an enemy here"),
    "wound": (_wound, "wound <pct>       set the enemy's health % (FEED needs <35)"),
    "windup": (_windup, "windup            force a telegraph, to test GUARD"),
    "kill": (_kill, "kill              remove what is here, no rewards"),
    "chest": (_chest, "chest <tier>      drop a chest here"),
    "trader": (_trader, "trader            put a trader here"),
    "reveal": (_reveal, "reveal            discover the whole map"),
    "god": (_god, "god               toggle taking no damage"),
    "where": (_where, "where             dump this room's raw state"),
    "cheats": (None, "cheats            show this list again"),
}


def menu_lines() -> list[str]:
    """The cheat menu, shown when cheats turn on and by ``cheats``."""
    lines = [
        paint("== CHEATS ON ==", "bold", "bright_magenta"),
        "Usable from anywhere, at the normal prompt:",
        "",
    ]
    lines += [f"  {help_text}" for _handler, help_text in CHEATS.values()]
    lines += ["", f"  {WORD}            turn cheats back off"]
    return lines


def handle(game, text: str) -> list[str] | None:
    """Try to run ``text`` as a cheat.

    Returns the lines to show, or None if this was not a cheat -- in which case
    the caller carries on and parses it as an ordinary command.
    """
    stripped = text.strip().lower()

    if stripped == WORD:
        game.cheats_on = not getattr(game, "cheats_on", False)
        if game.cheats_on:
            return menu_lines()
        return [paint("== CHEATS OFF ==", "dim")]

    if not getattr(game, "cheats_on", False):
        return None

    parts = stripped.split(maxsplit=1)
    verb = parts[0]
    target = parts[1] if len(parts) > 1 else ""

    if verb not in CHEATS:
        return None

    if verb == "cheats":
        return menu_lines()

    handler, _help = CHEATS[verb]
    return handler(game, target)
