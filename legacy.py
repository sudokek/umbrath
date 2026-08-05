"""Turn a :class:`~models.Legacy` into the bonuses a fresh run starts with.

A run is disposable: gold, gear, levels, and the caves themselves are gone the
moment you die. The Legacy is what is not -- relics prised off bosses and
blessings bought with echoes. Everything in here is about converting that
permanent record into the numbers a new Player begins with.
"""

import chargen
from content import BLESSINGS, ITEMS, make_item
from models import BASE_MAX_HP, Legacy, Player

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
    player.gold = Player.gold + totals["gold"]

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
