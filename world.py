"""Build and return the game's world data.

The world is three holds travelled in order, each a hand-authored settlement
plus a generated underdark (see ``dungeon.generate_cave``). A hold's cave ends
in a vault guarded by a boss; kill it and the road onward opens. Beat the third
and the game is over.

    Greyfen --> Barrow Warrens --> Ashmoor --> Emberdeeps --> Wintermourn --> Rimevault

Every hold's prose lives in ``content.REGIONS`` beside its gear and bestiary, so
adding a fourth is a data change rather than four more functions. Each occupies
its own band of the coordinate grid, far enough apart that no two holds' rooms
can ever collide. The long roads
between them are not drawn as map corridors -- they are journeys, not corridors.

``Game.__init__`` rolls a fresh seed for each new run -- so every playthrough
has new cave layouts -- and stores it in the save file, which is all it takes to
rebuild the identical world on load.
"""

from content import (
    REGIONS,
    make_shop_gear,
    make_shop_potions,
    region_by_index,
)
from dungeon import OPPOSITE, generate_cave
from models import Room

DEFAULT_DUNGEON_SEED = 1

# How many rooms sit between a hold and its cave entrance.
CAVE_OFFSET = 2

# Each hold owns a band of the grid this wide, measured from its square. A cave
# may sprawl anywhere inside its own band and can never reach a neighbour's, so
# regions stay visually and logically separate however wildly they grow.
BAND_WEST = 6
BAND_EAST = 40
BAND_HEIGHT = 14


def town_keys(region: int) -> dict[str, str]:
    """Room keys for a region's town.

    Region 1 keeps the original unsuffixed keys ("square", "inn", ...) so old
    saves, tests, and muscle memory all still point at the right rooms.
    """
    suffix = "" if region == 1 else f"_{region}"
    return {
        name: f"{name}{suffix}"
        for name in ("square", "market", "smithy", "inn", "forest", "shrine", "road")
    }


def cave_key(region: int) -> str:
    """Entrance room key for a region's cave."""
    return f"cave{region}"


def region_bounds(region: int) -> tuple[int, int, int, int]:
    """The ``(min_x, max_x, min_y, max_y)`` box a hold's cave must stay inside."""
    origin = region_by_index(region)["x"]
    return (
        origin - BAND_WEST,
        origin + BAND_EAST,
        -BAND_HEIGHT,
        BAND_HEIGHT,
    )


def build_town(region: int = 1) -> dict[str, Room]:
    """Create one region's fixed town and approach.

    Layout (x grows east, y grows north)::

                       [Smt]
                         |
        [Mkt]--[Sqr]--[For]--> cave (generated)
                         |
                       [Inn]
                         |
                       [Shr]   (region 1 only)
    """
    spec = region_by_index(region)
    keys = town_keys(region)
    origin = spec["x"]
    town = spec["town"]
    rooms: dict[str, Room] = {}

    def place(slot: str, dx: int, dy: int, label: str, name: str,
              description: str, **extra) -> None:
        """Add one room of this hold, filling in what every room shares."""
        rooms[keys[slot]] = Room(
            key=keys[slot],
            name=name,
            description=description,
            x=origin + dx,
            y=dy,
            label=label,
            region=region,
            **extra,
        )

    place(
        "square", 0, 0, "Sqr" if region == 1 else town[:3],
        f"{town} Square",
        f"The heart of {town}. Roads run out in every direction and a mossy "
        "fountain trickles in the middle.",
        exits={
            "west": keys["market"],
            "north": keys["smithy"],
            "south": keys["inn"],
            "east": keys["forest"],
        },
    )
    place(
        "market", -1, 0, "Mkt",
        f"{town} Market",
        "Traders hawk blood and trinkets under sagging awnings. "
        "A sign reads: BUY and SELL here.",
        exits={"east": keys["square"]},
        shop=make_shop_potions(region),
        can_sell=True,
    )
    place(
        "smithy", 0, 1, "Smt",
        f"The {town} Charnel Forge",
        "Heat rolls off the forge. Weapons and armor hang on the wall, each "
        "with a price.",
        exits={"south": keys["square"]},
        shop=make_shop_gear(region),
    )
    place(
        "inn", 0, -1, "Inn",
        f"The {town} Inn",
        "A warm common room with a crackling hearth. You can REST here to "
        "heal, for a price.",
        exits={"north": keys["square"]},
        inn=True,
    )
    place(
        "forest", 1, 0, "For" if region == 1 else "Way",
        spec["approach_name"],
        spec["approach_description"].format(town=town),
        exits={"west": keys["square"], "east": cave_key(region)},
    )

    # The shrine only stands in the first hold -- the one you always wake in.
    if region == 1:
        place(
            "shrine", 0, -2, "Shr",
            "The Shrine of Echoes",
            "A cold little shrine of stacked stones, older than the village. "
            "The dead leave echoes here, and the shrine will trade them for "
            "something that lasts. BUY a blessing, if you have the echoes.",
            exits={"north": keys["inn"]},
            shrine=True,
        )
        rooms[keys["inn"]].exits["south"] = keys["shrine"]

    return rooms


def build_road(region: int) -> Room:
    """The long road arriving at hold ``region`` from the cave before it.

    Roads sit just west of their hold and are quiet places -- no danger, but a
    likely spot to meet someone else walking them.
    """
    spec = region_by_index(region)
    keys = town_keys(region)
    previous = region_by_index(region - 1)

    return Room(
        key=keys["road"],
        name=spec["road_name"],
        description=spec["road_description"].format(
            town=spec["town"], previous=previous["town"]
        ),
        x=spec["x"] - 3,
        y=0,
        label=f"Rd{region}",
        exits={"east": keys["square"]},
        region=region,
    )


def build_world(dungeon_seed: int = DEFAULT_DUNGEON_SEED) -> dict[str, Room]:
    """Create the full world: three towns, three caves, and the roads between.

    The same ``dungeon_seed`` always produces the same caves, so a save file
    only needs to store the seed to restore every layout exactly.
    """
    world: dict[str, Room] = {}

    # Holds and roads first: a cave's vault needs the next hold's road to
    # already exist before it can open a door onto it.
    for spec in REGIONS:
        region = spec["index"]
        world.update(build_town(region))
        if region > 1:
            world[town_keys(region)["road"]] = build_road(region)

    # Caves sprawl in every direction, so every square already spoken for --
    # by a hold, a road, or a previously generated cave -- has to be off limits.
    reserved = {(room.x, room.y) for room in world.values()}

    for spec in REGIONS:
        region = spec["index"]

        # The vault's exit is the road to the next hold -- with the boss
        # standing in the doorway. The last cave has nowhere further to go.
        onward = (
            town_keys(region + 1)["road"]
            if region < REGIONS[-1]["index"]
            else None
        )

        cave = generate_cave(
            # Offset per region so the three caves are shaped differently
            # even though one seed drives them all.
            seed=dungeon_seed + region * 7919,
            entrance_key=cave_key(region),
            entrance_x=spec["x"] + CAVE_OFFSET,
            entrance_y=0,
            attach_from=town_keys(region)["forest"],
            room_count=spec["rooms"],
            theme=spec["theme"],
            region=region,
            onward=onward,
            reserved=reserved,
            bounds=region_bounds(region),
        )
        world.update(cave)
        reserved |= {(room.x, room.y) for room in cave.values()}

        # Let the road lead back to the vault it came from, so the world can be
        # walked in both directions. The two rooms are regions apart on the
        # grid, so the map draws no corridor -- correctly, since it is a journey.
        if onward:
            vault = next(
                (
                    room
                    for room in cave.values()
                    if onward in room.exits.values()
                ),
                None,
            )
            if vault is not None:
                back = OPPOSITE[
                    next(d for d, t in vault.exits.items() if t == onward)
                ]
                world[onward].exits[back] = vault.key

    return world
