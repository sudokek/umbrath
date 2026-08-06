"""Turn a :class:`~models.Legacy` into the bonuses a fresh run starts with.

A run is disposable: gold, gear, levels, and the caves themselves are gone the
moment you die. The Legacy is what is not -- relics prised off bosses and
blessings bought with echoes. Everything in here is about converting that
permanent record into the numbers a new Player begins with.
"""

import chargen
from content import BLESSINGS, ITEMS, make_item
from models import BASE_MAX_HP, HP_PER_LEVEL, Legacy, Player

# Echoes are the currency of dying. A run always leaves at least one behind, so
# even a disastrous attempt buys a sliver of the next one.
ECHOES_PER_RUN = 1
ECHOES_PER_BOSS = 3
ECHOES_PER_REGION = 2
ECHOES_FOR_VICTORY = 10


def echoes_earned(bosses_killed: int, region_reached: int, victory: bool) -> int:
    """How many echoes a finished run is worth."""
    total = ECHOES_PER_RUN
    total += ECHOES_PER_BOSS * bosses_killed
    total += ECHOES_PER_REGION * max(0, region_reached - 1)
    if victory:
        total += ECHOES_FOR_VICTORY
    return total


# What survives a death, and the ceiling on it.
#
# The point of a head start is to skip re-proving Greyfen, which you have
# already proved. The point of the cap is that holds two and three -- where runs
# actually end -- must stay exactly as dangerous on run twenty as on run two.
# So both inheritances plateau: they are generous early and irrelevant later.
INHERITED_COIN_SHARE = 0.25
INHERITED_COIN_CAP = 200

INHERITED_LEVEL_SHARE = 0.34
INHERITED_LEVEL_CAP = 6


def inherited_coin(legacy: Legacy) -> int:
    """Coin carried out of the last run, capped."""
    return min(INHERITED_COIN_CAP, int(legacy.hoard * INHERITED_COIN_SHARE))


def inherited_level(legacy: Legacy) -> int:
    """The level a new run starts at, capped.

    Deliberately a third of your best and never above ``INHERITED_LEVEL_CAP``:
    enough to walk through the Barrow Warrens without re-grinding them, nowhere
    near enough to matter against the Cinder Warden.
    """
    return max(1, min(INHERITED_LEVEL_CAP, int(legacy.best_level * INHERITED_LEVEL_SHARE)))


def bonuses(legacy: Legacy) -> dict[str, int]:
    """Sum every permanent bonus a Legacy grants into one stat block.

    Three sources feed in: the origin you were created with, relics looted from
    bosses, and blessings bought with echoes.
    """
    totals = {"attack": 0, "max_hp": 0, "defense": 0, "gold": 0}

    origin = chargen.find(legacy.origin)
    if origin is not None:
        totals["attack"] += origin.attack
        totals["max_hp"] += origin.max_hp
        totals["defense"] += origin.defense
        totals["gold"] += origin.gold

    for name in legacy.relics:
        relic = ITEMS.get(name)
        if relic and relic.effect in totals:
            totals[relic.effect] += relic.power

    for name, count in legacy.blessings.items():
        spec = BLESSINGS.get(name)
        if spec:
            _cost, effect, power, _description = spec
            if effect in totals:
                totals[effect] += power * count

    return totals


def new_player(legacy: Legacy) -> Player:
    """Build the Player a new run starts with, Legacy bonuses already applied."""
    totals = bonuses(legacy)
    player = Player()

    player.name = legacy.name or Player.name
    player.bonus_attack = totals["attack"]
    player.bonus_defense = totals["defense"]
    player.bonus_max_hp = totals["max_hp"]
    # Never let an origin's HP penalty leave a character unable to take a hit.
    player.max_hp = max(5, BASE_MAX_HP + totals["max_hp"])
    player.hp = player.max_hp
    player.gold = Player.gold + totals["gold"] + inherited_coin(legacy)

    # Start at a fraction of the best level ever reached, capped. Levelling up
    # is what grants the HP and damage, so this is applied by living through
    # those levels rather than by assigning a number.
    for _ in range(inherited_level(legacy) - 1):
        player.level += 1
        player.max_hp += HP_PER_LEVEL
    player.hp = player.max_hp

    # Relics are carried, not re-earned: they show up in hand at the start.
    player.relics = [make_item(name) for name in legacy.relics if name in ITEMS]

    # The origin's kit is re-issued every run -- it is who you are, not loot.
    origin = chargen.find(legacy.origin)
    if origin is not None:
        for name in origin.items:
            if name in ITEMS:
                player.inventory.append(make_item(name))

    return player


def describe(legacy: Legacy) -> list[str]:
    """Human-readable summary of everything carried between runs."""
    totals = bonuses(legacy)
    origin = chargen.get(legacy.origin)
    lines = [
        f"{legacy.name}, {origin.name}",
        f"  {origin.blurb}",
        "",
        f"Runs: {legacy.runs}   Victories: {legacy.victories}   "
        f"Echoes: {legacy.echoes}",
        f"Furthest hold reached: {legacy.best_region}",
        "",
    ]

    if legacy.relics:
        lines.append("Relics:")
        for name in legacy.relics:
            relic = ITEMS.get(name)
            lines.append(f"- {name}: {relic.description if relic else 'unknown'}")
    else:
        lines.append("Relics: none yet. Bosses drop them.")

    if legacy.blessings:
        lines.append("Blessings:")
        for name, count in sorted(legacy.blessings.items()):
            lines.append(f"- {name} x{count}")
    else:
        lines.append("Blessings: none yet. Buy them at the Shrine of Echoes.")

    lines.append("")
    # Signed formatting, so an origin's HP penalty reads "-6" and not "+-6".
    lines.append(
        f"Carried into every run: {totals['attack']:+d} damage, "
        f"{totals['max_hp']:+d} max HP, {totals['defense']:+d} defense, "
        f"{totals['gold']:+d} starting coin."
    )
    return lines
