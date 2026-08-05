"""Procedurally generate the underdark beneath each hold.

A cave is grown as a random walk with frequent branches and loops, so every run
has a different shape while staying fully connected and always reachable from
the entrance. Generation uses its own ``random.Random(seed)`` instance so it
never disturbs the game's global RNG -- the same seed always rebuilds the
identical cave, which is what lets a save file restore its dungeons by storing
one number.

Caves sprawl in **every** direction, not just deeper east. They are meant to be
easy to get lost in and satisfying to learn -- you map them by walking them.

Two structural rules keep that from turning into busywork:

* **Loops.** Some rooms join up with a neighbour they already sit beside, so a
  cave is a network rather than a pure tree of dead ends. Getting lost should
  mean "which way was it?", not "reverse out of this branch, again".
* **The road onward is at the bottom.** The vault holds the boss *and* the way
  to the next hold, so finishing a cave never *requires* walking back through
  it. Going back is a choice you make to farm loot or easier kills.

Danger scales with distance from the entrance, so pushing deeper is riskier and
more rewarding.
"""

import random

from content import make_boss, make_item, theme_style
# Labels have to fit the renderer's box, so it owns the width.
from map_render import LABEL_WIDTH
from models import Room

OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}
STEPS = {"north": (0, 1), "south": (0, -1), "east": (1, 0), "west": (-1, 0)}

DEFAULT_ROOM_COUNT = 14

# Chance of adding an extra corridor between two rooms that already sit next to
# each other. Enough that caves are networks rather than trees, low enough that
# they still have shape worth learning.
LOOP_CHANCE = 0.28

# Chance any given room holds loot. Tuned with the rest of the economy so a
# player who clears a hold completely can afford that hold's gear.
LOOT_CHANCE = 0.55


def _danger_for_depth(depth: int) -> int:
    """Map distance-from-entrance to a local danger tier (1-3)."""
    if depth <= 2:
        return 1
    if depth <= 5:
        return 2
    return 3


def _label_for(prefix: str, depth: int, danger: int) -> str:
    """Build a map label like ``B1`` or ``E7!`` for deadly rooms.

    High danger is marked with "!" and never "*": the map uses ``*Lbl*`` for
    you-are-here, so a "*" inside a label renders as an unreadable ``*E7**``.
    """
    capped = min(depth, 9)
    label = f"{prefix}{capped}!" if danger == 3 else f"{prefix}{capped}"
    return label[:LABEL_WIDTH]


def generate_cave(
    seed: int,
    entrance_key: str = "cave1",
    entrance_x: int = 2,
    entrance_y: int = 0,
    attach_from: str = "forest",
    room_count: int = DEFAULT_ROOM_COUNT,
    theme: str = "barrow",
    region: int = 1,
    onward: str | None = None,
    reserved: set[tuple[int, int]] | None = None,
    bounds: tuple[int, int, int, int] | None = None,
) -> dict[str, Room]:
    """Build a connected, themed cave of ``room_count`` rooms.

    ``reserved`` lists grid squares already used by the rest of the world, and
    ``bounds`` is the ``(min_x, max_x, min_y, max_y)`` box this cave must stay
    inside; together they let a cave sprawl freely without ever colliding with a
    hold or another region. ``onward`` is the road to the next hold, opened from
    the vault.
    """
    rng = random.Random(seed)
    style = theme_style(theme)
    prefix = style["label"]
    reserved = reserved or set()

    entrance = Room(
        key=entrance_key,
        name=style["entrance_name"],
        description=style["entrance_description"],
        x=entrance_x,
        y=entrance_y,
        label=f"{prefix}0",
        exits={"west": attach_from},
        danger=1,
        region=region,
        theme=theme,
    )

    rooms: dict[str, Room] = {entrance_key: entrance}
    taken: dict[tuple[int, int], str] = {(entrance_x, entrance_y): entrance_key}
    depths: dict[str, int] = {entrance_key: 0}

    def free(spot: tuple[int, int]) -> bool:
        """Is this grid square available to build on?"""
        if spot in taken or spot in reserved:
            return False
        if bounds is None:
            return True
        min_x, max_x, min_y, max_y = bounds
        return min_x <= spot[0] <= max_x and min_y <= spot[1] <= max_y

    # Grow from a frontier of rooms that still have space to expand.
    frontier = [entrance_key]
    index = 1

    while len(rooms) < room_count and frontier:
        # Favor the newest rooms so the cave tunnels outward, but often reach
        # back to an older room so it branches instead of forming one corridor.
        if len(frontier) > 1 and rng.random() < 0.35:
            source_key = rng.choice(frontier[:-1])
        else:
            source_key = frontier[-1]

        source = rooms[source_key]
        options = [
            (direction, (source.x + dx, source.y + dy))
            for direction, (dx, dy) in STEPS.items()
            if free((source.x + dx, source.y + dy))
        ]

        if not options:
            frontier.remove(source_key)
            continue

        direction, (nx, ny) = rng.choice(options)
        key = f"{entrance_key}_r{index}"
        index += 1

        depth = depths[source_key] + 1
        danger = _danger_for_depth(depth)
        rooms[key] = Room(
            key=key,
            name=rng.choice(style["room_names"]),
            description=rng.choice(style["flavor"]),
            x=nx,
            y=ny,
            label=_label_for(prefix, depth, danger),
            exits={OPPOSITE[direction]: source_key},
            danger=danger,
            region=region,
            theme=theme,
        )

        source.exits[direction] = key
        taken[(nx, ny)] = key
        depths[key] = depth
        frontier.append(key)

    _add_loops(rooms, taken, entrance_key, rng)
    _scatter_loot(rooms, depths, entrance_key, style, rng)
    _build_vault(rooms, depths, entrance_key, style, prefix, theme, onward)
    return rooms


def _add_loops(
    rooms: dict[str, Room],
    taken: dict[tuple[int, int], str],
    entrance_key: str,
    rng: random.Random,
) -> None:
    """Join rooms that already sit next to each other, so the cave has circuits.

    Without this a cave is a tree: every wrong turn has to be reversed. With it
    most rooms have two or more ways out and you can usually loop around.
    """
    for key in [k for k in rooms if k != entrance_key]:
        room = rooms[key]
        for direction, (dx, dy) in STEPS.items():
            if direction in room.exits:
                continue
            neighbor_key = taken.get((room.x + dx, room.y + dy))
            if not neighbor_key or rng.random() >= LOOP_CHANCE:
                continue
            room.exits[direction] = neighbor_key
            rooms[neighbor_key].exits[OPPOSITE[direction]] = key


def _scatter_loot(
    rooms: dict[str, Room],
    depths: dict[str, int],
    entrance_key: str,
    style: dict,
    rng: random.Random,
) -> None:
    """Seed loot through the cave, weighted toward the depths."""
    for key, room in rooms.items():
        if key == entrance_key:
            continue
        depth = depths[key]
        candidates = [name for min_depth, name in style["loot"] if min_depth <= depth]
        if candidates and rng.random() < LOOT_CHANCE:
            room.items.append(make_item(rng.choice(candidates)))


def _reachable(rooms: dict[str, Room], start: str, goal: str) -> bool:
    """Is ``goal`` still reachable from ``start`` using only exits inside the cave?"""
    seen, stack = {start}, [start]
    while stack:
        for target in rooms[stack.pop()].exits.values():
            if target == goal:
                return True
            if target in rooms and target not in seen:
                seen.add(target)
                stack.append(target)
    return False


def _build_vault(
    rooms: dict[str, Room],
    depths: dict[str, int],
    entrance_key: str,
    style: dict,
    prefix: str,
    theme: str,
    onward: str | None,
) -> None:
    """Turn the furthest room into the boss vault, in place."""
    deepest = max(depths, key=lambda key: depths[key])
    if deepest == entrance_key:
        return

    vault = rooms[deepest]
    vault.name = style["vault_name"]
    vault.description = style["vault_description"]
    vault.label = f"{prefix}!!"[:LABEL_WIDTH]
    vault.danger = 3
    vault.enemies.append(make_boss(theme))

    # The best gear in the hold, as the reward for the fight.
    vault.items.append(make_item(style["loot"][-1][1]))

    # The road onward exists from the start -- but the boss is standing on it.
    if onward:
        _attach_onward(rooms, vault, onward, entrance_key)


def _try_direction(
    rooms: dict[str, Room],
    vault: Room,
    onward: str,
    entrance_key: str,
    direction: str,
) -> bool:
    """Put the road out on ``direction`` if that strands nothing. Did it work?"""
    if direction not in vault.exits:
        vault.exits[direction] = onward
        return True

    target = vault.exits[direction]
    if target not in rooms:
        return False

    # The direction is taken. Try closing that corridor -- but only keep the
    # change if the vault itself is still reachable from the entrance
    # afterwards. Checking the far room is not enough: this corridor may be the
    # vault's only way in, and closing it would strand the boss behind a wall.
    del vault.exits[direction]
    back = rooms[target].exits.pop(OPPOSITE[direction], None)

    if _reachable(rooms, entrance_key, vault.key):
        vault.exits[direction] = onward
        return True

    if back is not None:
        rooms[target].exits[OPPOSITE[direction]] = back
    vault.exits[direction] = target
    return False


def _attach_onward(
    rooms: dict[str, Room],
    vault: Room,
    onward: str,
    entrance_key: str,
) -> None:
    """Open a door from the vault to the road out, without stranding any room.

    Tries east first so "the way east is open" is the usual case, displacing an
    existing corridor when another passage already makes it redundant. Only when
    east genuinely cannot be freed does it fall back to another compass point.
    """
    if _try_direction(rooms, vault, onward, entrance_key, "east"):
        return

    for direction in ("north", "south", "west"):
        if _try_direction(rooms, vault, onward, entrance_key, direction):
            return
