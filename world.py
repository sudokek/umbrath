"""Build and return the game's world data.

The world is three regions travelled in order, each a hand-authored town plus a
generated cave (see ``dungeon.generate_cave``). A region's cave ends in a vault
guarded by a boss; kill it and the road east opens onto the next town. Beat the
third and the game is over.

    Greenhollow --> Hollow Deeps --> Ashford --> Emberdeep --> Frostmere --> The Rime

Each region occupies its own band of the coordinate grid (``REGIONS[n]["x"]``),
far enough apart that no two regions' rooms can ever collide. The long roads
between them are not drawn as map corridors -- they are journeys, not corridors.

``Game.__init__`` rolls a fresh seed for each new run -- so every playthrough
has new cave layouts -- and stores it in the save file, which is all it takes to
rebuild the identical world on load.
"""

from content import (
    REGIONS,
    make_shop_gear,
    make_shop_potions,
    make_shrine_stock,
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
    tag = town[:3]

    rooms = {
        keys["square"]: Room(
            key=keys["square"],
            name=f"{town} Square",
            description=(
                f"The heart of {town}. Roads run out in every direction and a "
                "mossy fountain trickles in the middle."
            ),
            x=origin,
            y=0,
            label="Sqr" if region == 1 else tag,
            exits={
                "west": keys["market"],
                "north": keys["smithy"],
                "south": keys["inn"],
                "east": keys["forest"],
            },
            region=region,
        ),
        keys["market"]: Room(
            key=keys["market"],
            name=f"{town} Market",
            description=(
                "Traders hawk potions and trinkets under sagging awnings. "
                "A sign reads: BUY and SELL here."
            ),
            x=origin - 1,
            y=0,
            label="Mkt",
            exits={"east": keys["square"]},
            shop=make_shop_potions(region),
            can_sell=True,
            region=region,
        ),
        keys["smithy"]: Room(
            key=keys["smithy"],
            name=f"The {town} Smithy",
            description=(
                "Heat rolls off the forge. Weapons and armor hang on the wall, "
                "each with a price."
            ),
            x=origin,
            y=1,
            label="Smt",
            exits={"south": keys["square"]},
            shop=make_shop_gear(region),
            region=region,
        ),
        keys["inn"]: Room(
            key=keys["inn"],
            name=f"The {town} Inn",
            description=(
                "A warm common room with a crackling hearth. You can REST here "
                "to heal, for a price."
            ),
            x=origin,
            y=-1,
            label="Inn",
            exits={"north": keys["square"]},
            inn=True,
            region=region,
        ),
        keys["forest"]: Room(
            key=keys["forest"],
            name=_approach_name(region),
            description=_approach_description(region, town),
            x=origin + 1,
            y=0,
            label="For" if region == 1 else "Way",
            exits={"west": keys["square"], "east": cave_key(region)},
            region=region,
        ),
    }

    # The shrine only stands in the first town -- the one you always wake in.
    if region == 1:
        rooms[keys["shrine"]] = Room(
            key=keys["shrine"],
            name="The Shrine of Echoes",
            description=(
                "A cold little shrine of stacked stones, older than the village. "
                "The dead leave echoes here, and the shrine will trade them for "
                "something that lasts. BUY a blessing, if you have the echoes."
            ),
            x=origin,
            y=-2,
            label="Shr",
            exits={"north": keys["inn"]},
            shrine=True,
            region=region,
        )
        rooms[keys["inn"]].exits["south"] = keys["shrine"]

    return rooms


def _approach_name(region: int) -> str:
    """Name of the room between a town and its cave."""
    return {1: "Forest Path", 2: "The Ash Road", 3: "The White Pass"}.get(
        region, "The Way Out"
    )


def _approach_description(region: int, town: str) -> str:
    """Flavor for the room between a town and its cave."""
    return {
        1: (
            f"Tall trees crowd the trail. {town} lies west; a dark cave mouth "
            "yawns to the east."
        ),
        2: (
            "The road runs over cracked grey flats where nothing grows. West is "
            f"{town}; east, the ground glows faintly where it splits open."
        ),
        3: (
            "A knife-edge pass between white walls, the wind screaming through "
            f"it. {town} is west. East, the ice goes down."
        ),
    }.get(region, f"The road out of {town}.")


def build_road(region: int) -> Room:
    """The long road arriving at region ``region`` from the cave before it.

    Roads sit just west of their town and are quiet places -- no danger, but a
    likely spot to meet someone else walking them.
    """
    spec = region_by_index(region)
    keys = town_keys(region)
    previous = region_by_index(region - 1)

    return Room(
        key=keys["road"],
        name=_road_name(region),
        description=_road_description(region, spec["town"], previous["town"]),
        x=spec["x"] - 3,
        y=0,
        label="Rd" + str(region),
        exits={"east": keys["square"]},
        region=region,
    )


def _road_name(region: int) -> str:
    return {2: "The Long Road East", 3: "The Climbing Road"}.get(region, "The Road")


def _road_description(region: int, town: str, previous: str) -> str:
    return {
        2: (
            f"Days of walking behind you, and {previous} far out of sight. The "
            f"land here is grey and warm underfoot. {town} waits east, its "
            "chimneys smudging the sky."
        ),
        3: (
            f"The road climbs, and keeps climbing. Behind you the ash country; "
            f"ahead, {town}, white-roofed and half-buried, at the edge of the "
            "permanent snow."
        ),
    }.get(region, f"The road to {town}.")


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
