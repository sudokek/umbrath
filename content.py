"""Item registry, hold and cave themes, enemy tables, and encounter rolls.

The setting is Umbrath, a drowned dark-fantasy realm of barrows and cold stone.
You are a vampire lord of a fallen house, clawing a dominion back out of the
mountains that swallowed it. Everything here is original to this game.

Every item is defined exactly once in ``ITEMS``; holds, cave loot, traders, and
boss drops all hand out copies via ``make_item`` so a price or damage tweak
lands everywhere at once.

The world is a run of holds, each a settlement plus a themed underdark (see
``THEMES``). A theme owns its room names, flavor text, and its own bestiary, so
the Barrow Warrens read and fight nothing like the Sporefall. Adding a hold is
an entry in ``THEMES`` and an entry in ``REGIONS``; nothing else needs to know.

All gameplay randomness flows through this module so a single
``random.seed(...)`` (see Game.__init__) makes a whole playthrough reproducible.
"""

import random
from dataclasses import replace

from models import Enemy, Item, Trader

# --------------------------------------------------------------------------
# Items
# --------------------------------------------------------------------------

# The one and only definition of each item. Each hold's tier outfits you for
# the dark behind it, in the order the holds are travelled. You are a vampire:
# what heals you is blood.
ITEMS: dict[str, Item] = {
    item.name: item
    for item in [
        # -- blood -------------------------------------------------------
        Item("blood vial", "A thumb of stolen blood. Restores 10 HP.",
             kind="potion", power=10, price=15),
        Item("vitae flask", "Thick, and still warm. Restores 25 HP.",
             kind="potion", power=25, price=40),
        Item("heart's blood", "Taken from something that fought back. Restores 50 HP.",
             kind="potion", power=50, price=110),
        Item("ichor of ages", "Black, slow, older than the hold. Restores 120 HP.",
             kind="potion", power=120, price=260),
        # -- tier 1: Greyfen ---------------------------------------------
        Item("bone dagger", "A filed rib, wickedly sharp. +3 damage.",
             kind="weapon", power=3, price=20),
        Item("grave sword", "Pulled from a barrow, still keen. +6 damage.",
             kind="weapon", power=6, price=55),
        Item("barrow axe", "Heavy, notched, and eager. +9 damage.",
             kind="weapon", power=9, price=130),
        Item("tattered shroud", "Burial linen worn as armor. Blocks 1 damage.",
             kind="armor", power=1, price=30),
        Item("gravemail", "Rusted rings off a dead soldier. Blocks 3 damage.",
             kind="armor", power=3, price=100),
        Item("rib-hook", "Barbed, and hard to pull back out. +4 damage.",
             kind="weapon", power=4, price=32),
        Item("mourning blade", "Thin, and it whistles. +7 damage.",
             kind="weapon", power=7, price=78),
        Item("cerement wrap", "Wound tight over the ribs. Blocks 2 damage.",
             kind="armor", power=2, price=58),
        # -- tier 2: Ashmoor ---------------------------------------------
        Item("wight blade", "Cold to hold, colder to be hit by. +14 damage.",
             kind="weapon", power=14, price=190),
        Item("crypt maul", "It caves in whatever it touches. +19 damage.",
             kind="weapon", power=19, price=320),
        Item("barrow plate", "Grave-iron, beaten flat. Blocks 6 damage.",
             kind="armor", power=6, price=210),
        Item("scale shroud", "Overlapping black scales. Blocks 9 damage.",
             kind="armor", power=9, price=360),
        Item("ashen pick", "Balanced for one hand and a bad mood. +11 damage.",
             kind="weapon", power=11, price=140),
        Item("slag cleaver", "Heavy as guilt. +16 damage.",
             kind="weapon", power=16, price=245),
        Item("cinder mail", "Fire-blacked rings. Blocks 7 damage.",
             kind="armor", power=7, price=265),
        # -- tier 3: Sallowmere ------------------------------------------
        Item("fen scythe", "It harvests whatever is standing. +20 damage.",
             kind="weapon", power=20, price=400),
        Item("blight cleaver", "Wet, and it does not rust. +25 damage.",
             kind="weapon", power=25, price=610),
        Item("sporeplate", "Grown rather than forged. Blocks 10 damage.",
             kind="armor", power=10, price=430),
        Item("chitin harness", "Prised off something larger. Blocks 13.",
             kind="armor", power=13, price=600),
        # -- tier 4: Wintermourn -----------------------------------------
        Item("bloodfang", "It drinks before you do. +28 damage.",
             kind="weapon", power=28, price=700),
        Item("doom glaive", "A polearm of frozen soul-iron. +36 damage.",
             kind="weapon", power=36, price=1100),
        Item("abyssal plate", "Armor out of the deep dark. Blocks 14 damage.",
             kind="armor", power=14, price=780),
        Item("carrion ward", "Warded against the pale cold. Blocks 19 damage.",
             kind="armor", power=19, price=1250),
        Item("hoarfrost spear", "Cold enough to stick to the hand. +22 damage.",
             kind="weapon", power=22, price=520),
        Item("widow's edge", "It was never meant to be put down. +32 damage.",
             kind="weapon", power=32, price=890),
        Item("glacier harness", "Ice-plate over dead leather. Blocks 16 damage.",
             kind="armor", power=16, price=940),
        # -- valuables: no use but their price ----------------------------
        Item("tarnished locket", "Someone's face, worn away. Worth coin.",
             kind="valuable", price=25),
        Item("grave-silver", "Coins left for a ferryman who never came.",
             kind="valuable", price=60),
        Item("obsidian shard", "Volcanic glass, knapped and abandoned.",
             kind="valuable", price=110),
        Item("reliquary tooth", "Not yours. Someone paid for this once.",
             kind="valuable", price=210),
        Item("amber nodule", "Something small is still screaming inside it.",
             kind="valuable", price=300),
        Item("frozen tear", "It has not melted, and it will not.",
             kind="valuable", price=380),
        Item("crown fragment", "A shard of something that ruled here.",
             kind="valuable", price=650),
        # -- relics: boss drops, kept forever -----------------------------
        Item(
            "gaunt fang",
            "Wrenched from the Barrow Gaunt's jaw. Permanently +4 damage.",
            kind="relic", power=4, price=0, effect="attack",
        ),
        Item(
            "ember heart",
            "Still burning, after everything. Permanently +25 max HP.",
            kind="relic", power=25, price=0, effect="max_hp",
        ),
        Item(
            "spore heart",
            "It beats, slowly, in your hand. Permanently +6 defense.",
            kind="relic", power=6, price=0, effect="defense",
        ),
        Item(
            "pale crown",
            "The crown that took your domain. Permanently +8 damage.",
            kind="relic", power=8, price=0, effect="attack",
        ),
    ]
}


def make_item(name: str) -> Item:
    """Return a fresh copy of a registry item, safe to hand to the player."""
    return replace(ITEMS[name])


# --------------------------------------------------------------------------
# Blessings -- permanent gifts of undeath, bought with echoes
# --------------------------------------------------------------------------

# name -> (echo cost, effect, power, description)
BLESSINGS: dict[str, tuple[int, str, int, str]] = {
    "undeath": (3, "max_hp", 8, "+8 max HP, every run from now on."),
    "bloodthirst": (4, "attack", 2, "+2 damage, every run from now on."),
    "gravewarding": (4, "defense", 2, "+2 defense, every run from now on."),
    "plunder": (2, "gold", 50, "Start each run with 50 more coin."),
}


def make_blessing(name: str) -> Item:
    """Return a blessing as a listable item priced in echoes."""
    cost, effect, power, description = BLESSINGS[name]
    return Item(
        name=name, description=description, kind="blessing",
        power=power, price=cost, effect=effect,
    )


def make_shrine_stock() -> list[Item]:
    """Everything the reliquary offers, in a stable order."""
    return [make_blessing(name) for name in BLESSINGS]


# --------------------------------------------------------------------------
# Cave themes
# --------------------------------------------------------------------------

THEMES: dict[str, dict] = {
    "barrow": {
        "cave_name": "The Barrow Warrens",
        "xp_scale": 1.0,
        "gold_scale": 1.0,
        "label": "B",
        "entrance_name": "Mouth of the Warrens",
        "entrance_description": (
            "A collapsed barrow-door, propped open by roots as thick as a man's "
            "arm. Wet air breathes out of it. EXPLORE to hunt, or press deeper."
        ),
        "room_names": [
            "Drowned Barrow", "Root Crawl", "Ossuary Steps", "Weeping Gallery",
            "Clawed Passage", "Low Sepulchre", "Palefungus Grotto", "Fallen Shaft",
            "Hall of Small Names", "Old Diggings", "The Hollow Vault", "Black Pool",
            "Dripstone Walk", "Rootbound Cleft", "Silt Basin", "The Grave Tier",
        ],
        "flavor": [
            "Water beads on the walls and runs away down into the dark.",
            "Grave-goods lie scattered. Someone robbed this a long time ago.",
            "Old bones crunch underfoot. They were not arranged. They were dropped.",
            "A draft comes from somewhere below, smelling of turned earth.",
            "Scratch marks spiral up the walls. They were made from the inside.",
            "Pale fungus glows along the seams, lighting nothing usefully.",
            "A section has fallen in. You squeeze past wet rubble.",
            "Your footsteps come back to you far too late.",
            "Rusted grave-tools lie in a heap, half-swallowed by lime.",
            "Still black water fills a shallow pool. Nothing reflects in it.",
            "Roots have punched through the ceiling and hang like nooses.",
            "The air tastes of wet copper. You find you do not mind that.",
        ],
        "enemies": {
            1: [
                ("grave rat", 5, 2, 3, 7, "Fat on whatever it finds down here."),
                ("tomb bat", 4, 2, 2, 6, "It shrieks and will not settle."),
                ("grave robber", 8, 3, 5, 12, "A living man, badly frightened, armed."),
            ],
            2: [
                ("barrow wight", 12, 4, 8, 18, "It remembers being buried, and resents it."),
                ("bone hound", 9, 5, 7, 16, "Assembled from more than one dog."),
                ("fen lurker", 14, 4, 9, 20, "Pale, boneless, patient in the shallows."),
            ],
            3: [
                ("crypt ogre", 18, 7, 12, 25, "It has been eating the barrows out."),
                ("barrow troll", 28, 10, 20, 40, "Moss-grown, and slow to accept injury."),
                ("hollow knight", 16, 11, 18, 35, "Empty armor that still keeps its oath."),
            ],
        },
        "loot": [(1, "blood vial"), (2, "bone dagger"), (2, "tattered shroud"),
                 (2, "blood vial"), (3, "grave sword"), (3, "vitae flask"),
                 (4, "gravemail"), (5, "barrow axe")],
        "vault_name": "The Gaunt's Hollow",
        "vault_description": (
            "The barrow's true floor, far below the rest. The walls are stacked "
            "bone laid in courses, and something enormous is breathing in the dark."
        ),
        "boss": ("barrow gaunt", 60, 15, 140, "gaunt fang",
                 "A blind, bloated thing of jaw and appetite. It has eaten every "
                 "other predator in these warrens, and it is still hungry."),
    },
    "ember": {
        "cave_name": "The Emberdeeps",
        "xp_scale": 0.50,
        "gold_scale": 0.45,
        "label": "E",
        "entrance_name": "The Cinder Gate",
        "entrance_description": (
            "Heat rolls up the shaft in slow waves. The rock is black glass, and "
            "far below something red keeps a slow, enormous beat."
        ),
        "room_names": [
            "Cinder Walk", "Slag Gallery", "Obsidian Shelf", "The Bellows",
            "Ashfall Hall", "Magma Vein", "Scorched Crossing", "Glasswork Cavern",
            "Furnace Throat", "Smoulder Pit", "Charred Span", "Ember Terrace",
            "The Long Burn", "Basalt Stair", "Fumarole Gap", "The Quenching Floor",
        ],
        "flavor": [
            "The floor is warm enough to feel through your boots.",
            "Ash drifts down like grey snow and settles on your shoulders.",
            "A vein of magma throbs behind a wall of thin black glass.",
            "Everything here has burned down to the same featureless char.",
            "Hot wind moans up from a crack, carrying sparks with it.",
            "Obsidian shards slide underfoot, sharp enough to open a boot.",
            "The heat shimmers until the far wall seems to swim.",
            "Bones lie fused into the rock, mouths open, already ash.",
            "Steam vents hiss in an irregular, almost conversational rhythm.",
            "Forge-marks are cut into the stone. Someone worked here once.",
            "The ceiling drips slow beads of molten glass.",
            "Too hot to stand still in, and too dark to hurry through.",
        ],
        "enemies": {
            1: [
                ("ash hound", 28, 7, 30, 50, "A lean hound of packed ash and coals."),
                ("cinder imp", 24, 8, 28, 45, "A small burning thing that finds you funny."),
                ("slagworm", 36, 6, 35, 55, "It leaves a glowing trail behind it."),
            ],
            2: [
                ("obsidian brute", 50, 15, 50, 80, "Its fists are knapped volcanic glass."),
                ("flame wisp", 34, 17, 45, 75, "A knot of fire that drifts, then strikes."),
                ("forge revenant", 62, 13, 60, 95, "A dead smith, still at the work."),
            ],
            3: [
                ("magma drake", 80, 23, 90, 140, "Low, wingless, glowing at the seams."),
                ("ash wraith", 58, 26, 85, 130, "A person-shaped absence full of hot cinders."),
                ("molten colossus", 105, 21, 110, 170, "It moves like a hill deciding to."),
            ],
        },
        "loot": [(1, "vitae flask"), (2, "wight blade"), (2, "vitae flask"),
                 (3, "barrow plate"), (3, "heart's blood"), (4, "scale shroud"),
                 (5, "crypt maul")],
        "vault_name": "The Cinder Throne",
        "vault_description": (
            "A cathedral of black glass around a lake of slow fire. The heat here "
            "is a physical weight, and something is sitting in the middle of it."
        ),
        "boss": ("cinder warden", 180, 33, 500, "ember heart",
                 "An armored shape kneeling in the fire, patient as a furnace. It "
                 "has guarded this door long enough to forget what for."),
    },
    "mire": {
        "cave_name": "The Sporefall",
        "xp_scale": 0.38,
        # Tuned down from 0.38: at that rate a full clear paid 3.2x the hold's
        # best kit, where every other hold pays about 2x.
        "gold_scale": 0.26,
        "label": "S",
        "entrance_name": "The Sallow Door",
        "entrance_description": (
            "Warm air comes up out of the ground, and it is breathing. The frame "
            "of the door has been softened by something growing through it."
        ),
        "room_names": [
            "Spore Hall", "The Soft Stair", "Bloomrot Gallery", "Fruiting Chamber",
            "The Wet Nave", "Mycelial Crawl", "Cap Forest", "The Sagging Vault",
            "Rotwood Span", "Pale Orchard", "The Breathing Floor", "Sallow Reach",
            "Hyphal Tangle", "The Quiet Feast", "Spore Cloister", "Bloom Deep",
        ],
        "flavor": [
            "Caps the size of shields lean out of the walls, faintly luminous.",
            "The floor gives underfoot, and does not spring back.",
            "Something has grown through a skeleton and kept its shape.",
            "Spores drift in the lamplight like slow, patient snow.",
            "Everything here is warm, and none of it is alive in the usual way.",
            "White threads run through the stone like veins through a hand.",
            "The air is thick enough to taste, and it tastes of turned bread.",
            "A soft rain of spores answers every step you take.",
            "The walls exhale when you press them. You stop pressing them.",
            "Fungal light, greenish and even, comes from no direction at all.",
            "There is no echo here. The growth swallows every sound whole.",
            "Old timbers stand furred and swollen, holding up nothing.",
        ],
        "enemies": {
            1: [
                ("sporeling", 45, 13, 90, 150, "Small, soft, and there are more behind it."),
                ("rot-touched", 50, 12, 95, 160, "It was a person the week before last."),
                ("husk-walker", 55, 11, 100, 165, "Hollowed out and repurposed as a stalk."),
            ],
            2: [
                ("bloom-wraith", 70, 27, 140, 220, "A cloud with intent, and a grudge."),
                ("fungal knight", 85, 22, 150, 235, "Its armour is fruiting from the inside."),
                ("mycelial brute", 100, 19, 160, 250, "Grown to a shape that could carry a fist."),
            ],
            3: [
                ("the rotting choir", 130, 34, 240, 360, "Many mouths. One appetite."),
                ("spore titan", 150, 28, 260, 380, "It sheds a generation with every step."),
                ("blight colossus", 175, 25, 280, 400, "Slow, vast, and entirely full of teeth."),
            ],
        },
        "loot": [(1, "heart's blood"), (2, "fen scythe"), (2, "amber nodule"),
                 (3, "sporeplate"), (3, "heart's blood"), (4, "chitin harness"),
                 (5, "blight cleaver")],
        "vault_name": "The Mother Bloom",
        "vault_description": (
            "The cavern has been given over entirely. Every surface is the same "
            "pale growth, and all of it leans toward the centre, where something "
            "very old is fruiting."
        ),
        "boss": ("the mother bloom", 290, 44, 900, "spore heart",
                 "It has no face to read and no limbs to watch. It simply spreads, "
                 "and everything the Sporefall was is part of it now."),
    },
    "rime": {
        "cave_name": "The Rimevault",
        "xp_scale": 0.30,
        "gold_scale": 0.32,
        "label": "R",
        "entrance_name": "The Rime Gate",
        "entrance_description": (
            "Blue ice sheathes every surface. The cold here is so complete that it "
            "stops being weather and starts being intent."
        ),
        "room_names": [
            "Frost Nave", "Glacier Crawl", "Blue Silence", "Hoarfrost Hall",
            "The Frozen Weir", "Icefall Gallery", "Rime Cloister", "Snowblind Reach",
            "The Cold Vault", "Glass Lake", "Winter's Landing", "Pale Descent",
            "The Long Cold", "Shivering Span", "Whitelock Chamber", "The Still Choir",
        ],
        "flavor": [
            "Your breath freezes and falls, tinkling, before it can rise.",
            "The ice underfoot is clear enough to show what is suspended below.",
            "Frost grows across the walls as you watch, like something feeding.",
            "It is utterly silent. Even your footsteps arrive muffled and late.",
            "Icicles hang in ranks from the ceiling, thick as a man's leg.",
            "Something is frozen into the far wall. You decide not to look closer.",
            "The cold has split the stone into neat blue-white slabs.",
            "A frozen waterfall blocks half the passage, mid-fall, mid-roar.",
            "Your fingers stopped hurting a while ago, which is worse.",
            "Old rope and pitons, iced solid. Nobody came back for them.",
            "The dark here is pale rather than black, lit by ice from below.",
            "Snow drifts indoors, which should not be possible this deep.",
        ],
        "enemies": {
            1: [
                ("frost wolf", 90, 16, 130, 190, "Lean, white, and entirely unafraid."),
                ("rime mite", 75, 18, 120, 180, "A chittering swarm that moves as one body."),
                ("snow revenant", 105, 14, 140, 200, "It was a climber once. It still climbs."),
            ],
            2: [
                ("ice spider", 130, 31, 180, 260, "Its legs click like breaking icicles."),
                ("glacier troll", 170, 29, 200, 290, "Blue-skinned, slow, impossible to discourage."),
                ("hoarfrost knight", 145, 33, 190, 280, "Frozen inside its armor, still fighting."),
            ],
            3: [
                ("winter wyrm", 210, 44, 300, 420, "It swims through solid ice like water."),
                ("void stalker", 180, 48, 280, 400, "The cold that walks between the lamps."),
                ("frozen titan", 260, 40, 330, 460, "A statue that has decided to object."),
            ],
        },
        "loot": [(1, "heart's blood"), (2, "bloodfang"), (2, "heart's blood"),
                 (3, "abyssal plate"), (3, "ichor of ages"), (4, "carrion ward"),
                 (5, "doom glaive")],
        "vault_name": "The Pale Throne",
        "vault_description": (
            "The bottom of the Rimevault, and the bottom of the world. A hall of "
            "blue ice under a ceiling too high to see, and a throne at the far end "
            "-- occupied. This is as deep as anything goes."
        ),
        "boss": ("pale king", 450, 64, 2000, "pale crown",
                 "It has sat here since before your house had a name, wearing a "
                 "crown of frozen light. It took your domain. Take it back."),
    },
}

# The three holds, in the order you travel them. Each sits in its own wide band
# of the coordinate grid so its underdark can sprawl in any direction without
# ever colliding with a neighbour's.
REGIONS = [
    {
        "index": 1,
        "approach_name": (
            "Forest Path"
        ),
        "approach_description": (
            "Tall trees crowd the trail. {town} lies west; a dark barrow-door yawns to the east."
        ),
        "town": "Greyfen",
        "theme": "barrow",
        "x": 0,
        "rooms": 14,
        "gear": ["bone dagger", "rib-hook", "grave sword", "mourning blade",
                 "barrow axe", "tattered shroud", "cerement wrap", "gravemail"],
        "potions": ["blood vial", "vitae flask"],
    },
    {
        "index": 2,
        "approach_name": (
            "The Ash Road"
        ),
        "approach_description": (
            "The road runs over cracked grey flats where nothing grows. West is {town}; east, the ground glows faintly where it splits open."
        ),
        "road_name": (
            "The Long Road East"
        ),
        "road_description": (
            "Days of walking behind you, and {previous} far out of sight. The land here is grey and warm underfoot. {town} waits east, its chimneys smudging the sky."
        ),
        "town": "Ashmoor",
        "theme": "ember",
        "x": 60,
        "rooms": 18,
        "gear": ["ashen pick", "wight blade", "slag cleaver", "crypt maul",
                 "cinder mail", "barrow plate", "scale shroud"],
        "potions": ["blood vial", "vitae flask", "heart's blood"],
    },
    {
        "index": 3,
        "approach_name": (
            "The Sallow Track"
        ),
        "approach_description": (
            "The track sinks as it goes. {town} is west, on firmer ground; east, "
            "the reeds give way and something underneath is breathing."
        ),
        "road_name": (
            "The Sinking Road"
        ),
        "road_description": (
            "The road east of {previous} loses its stones a mile at a time. "
            "{town} stands on stilts at the end of it, over water that is not "
            "quite water."
        ),
        "town": "Sallowmere",
        "theme": "mire",
        "x": 120,
        "rooms": 20,
        "gear": ["slag cleaver", "fen scythe", "blight cleaver",
                 "scale shroud", "sporeplate", "chitin harness"],
        "potions": ["vitae flask", "heart's blood"],
    },
    {
        "index": 4,
        "approach_name": (
            "The White Pass"
        ),
        "approach_description": (
            "A knife-edge pass between white walls, the wind screaming through it. {town} is west. East, the ice goes down."
        ),
        "road_name": (
            "The Climbing Road"
        ),
        "road_description": (
            "The road climbs, and keeps climbing. Behind you the ash country; ahead, {town}, white-roofed and half-buried, at the edge of the permanent snow."
        ),
        "town": "Wintermourn",
        "theme": "rime",
        "x": 180,
        "rooms": 22,
        "gear": ["hoarfrost spear", "bloodfang", "widow's edge", "doom glaive",
                 "glacier harness", "abyssal plate", "carrion ward"],
        "potions": ["vitae flask", "heart's blood", "ichor of ages"],
    },
]

FINAL_REGION = REGIONS[-1]["index"]


def region_by_index(index: int) -> dict:
    """Return the region definition with this 1-based index."""
    for region in REGIONS:
        if region["index"] == index:
            return region
    return REGIONS[-1]


# --------------------------------------------------------------------------
# Enemies
# --------------------------------------------------------------------------


def theme_style(theme: str) -> dict:
    """The style block for a theme, falling back to the first hold's."""
    return THEMES.get(theme, THEMES["barrow"])


def region_style(region: int) -> dict:
    """The style block for a hold, by its 1-based index."""
    return theme_style(region_by_index(region)["theme"])


def xp_value(hp: int, damage: int) -> int:
    """Derive an enemy's XP reward from how tough it is to kill."""
    return hp + damage * 2


def _scaled(value: int, scale: float) -> int:
    """Apply a hold's reward scale, never rounding a reward away to nothing."""
    return max(1, int(round(value * scale)))


def _make_enemy(style, name, hp, damage, gold, description, **extra) -> Enemy:
    """Build an enemy with its hold's reward scaling already applied.

    Trash and bosses differ only in their stats and whether a relic falls out,
    so both come through here and neither can forget to scale.
    """
    return Enemy(
        name=name,
        hp=hp,
        max_hp=hp,
        damage=damage,
        gold=_scaled(gold, style["gold_scale"]),
        xp=_scaled(xp_value(hp, damage), style["xp_scale"]),
        description=description,
        **extra,
    )


def spawn_enemy(theme: str, tier: int) -> Enemy:
    """Create a random enemy from ``theme``'s bestiary at danger ``tier``."""
    style = theme_style(theme)
    pools = style["enemies"]
    pool = pools.get(tier) or pools[max(pools)]
    name, hp, damage, gold_min, gold_max, description = random.choice(pool)
    return _make_enemy(
        style, name, hp, damage, random.randint(gold_min, gold_max), description
    )


def make_boss(theme: str) -> Enemy:
    """Create the boss that guards ``theme``'s vault."""
    style = theme_style(theme)
    name, hp, damage, gold, relic, description = style["boss"]
    return _make_enemy(
        style, name, hp, damage, gold, description, boss=True, relic=relic
    )


# How much loose coin scales by hold, indexed by hold number. Deeper holds pay
# more per find, but the per-theme ``gold_scale`` above keeps totals in check.
# Clamped to its own length so adding a hold cannot silently reuse the last
# entry -- or read off the end.
GOLD_BY_REGION = (1, 1, 3, 5, 7)


def find_gold(tier: int, region: int = 1) -> int:
    """Return a random amount of loose coin found while exploring."""
    scale = GOLD_BY_REGION[min(max(region, 1), len(GOLD_BY_REGION) - 1)]
    return random.randint(3 * tier, 8 * tier) * scale


# --------------------------------------------------------------------------
# The drop table
# --------------------------------------------------------------------------

# One table behind every piece of loot in the game: scattered cave items, chest
# contents, and what a trader happens to be carrying.
#
# Each row is (item name, weight, first hold, first tier). A row is eligible
# once you have reached its hold *and* the room is at least that dangerous, so
# depth and progress both gate what can appear. Weight is relative within
# whatever is eligible -- blood is common, the best weapon in a hold is not.
DROPS: list[tuple[str, int, int, int]] = [
    # name                     weight  hold  tier
    ("blood vial",                 30,    1,    1),
    ("tarnished locket",           18,    1,    1),
    ("bone dagger",                14,    1,    1),
    ("cerement wrap",              12,    1,    1),
    ("tattered shroud",            12,    1,    1),
    ("rib-hook",                   12,    1,    2),
    ("grave-silver",               12,    1,    2),
    ("vitae flask",                18,    1,    2),
    ("grave sword",                10,    1,    2),
    ("mourning blade",              8,    1,    3),
    ("gravemail",                   8,    1,    3),
    ("barrow axe",                  4,    1,    3),

    ("vitae flask",                24,    2,    1),
    ("obsidian shard",             16,    2,    1),
    ("ashen pick",                 12,    2,    1),
    ("heart's blood",              16,    2,    2),
    ("wight blade",                10,    2,    2),
    ("cinder mail",                10,    2,    2),
    ("reliquary tooth",            10,    2,    2),
    ("barrow plate",                8,    2,    3),
    ("slag cleaver",                7,    2,    3),
    ("scale shroud",                5,    2,    3),
    ("crypt maul",                  3,    2,    3),

    ("heart's blood",              22,    3,    1),
    ("amber nodule",               16,    3,    1),
    ("fen scythe",                 12,    3,    1),
    ("sporeplate",                 10,    3,    2),
    ("reliquary tooth",            10,    3,    2),
    ("heart's blood",              14,    3,    2),
    ("chitin harness",              7,    3,    3),
    ("blight cleaver",              5,    3,    3),

    ("heart's blood",              22,    4,    1),
    ("frozen tear",                16,    4,    1),
    ("hoarfrost spear",            12,    4,    1),
    ("ichor of ages",              14,    4,    2),
    ("crown fragment",             10,    4,    2),
    ("bloodfang",                   8,    4,    2),
    ("glacier harness",             8,    4,    2),
    ("abyssal plate",               6,    4,    3),
    ("widow's edge",                5,    4,    3),
    ("carrion ward",                4,    4,    3),
    ("doom glaive",                 2,    4,    3),
]


def eligible_drops(region: int, tier: int) -> list[tuple[str, int]]:
    """Every drop that can appear at this hold and danger, with its weight."""
    return [
        (name, weight)
        for name, weight, min_region, min_tier in DROPS
        if min_region <= region and min_tier <= tier
    ]


def roll_loot(region: int = 1, tier: int = 1) -> Item:
    """Draw one item from the drop table, weighted, for this depth."""
    rows = eligible_drops(region, tier) or eligible_drops(1, 1)
    names = [name for name, _weight in rows]
    weights = [weight for _name, weight in rows]
    return make_item(random.choices(names, weights=weights, k=1)[0])


CHEST_NAMES = [
    "iron-bound chest",
    "grave-cache",
    "sealed coffer",
    "looter's stash",
    "warped strongbox",
]


def roll_hoard(region: int = 1, tier: int = 1, count: int = 3) -> list[Item]:
    """Draw several items for a chest. Deeper chests hold more."""
    return [roll_loot(region, tier) for _ in range(max(1, count))]


# --------------------------------------------------------------------------
# Wandering traders
# --------------------------------------------------------------------------

TRADER_NAMES = [
    "Pell the Bent",
    "Old Marrow",
    "Quill, of no fixed road",
    "the Sisters Vane",
    "the Tallow Man",
    "Hesk Roadworn",
]

TRADER_GREETINGS = [
    "Long way from anywhere, my lord. Lucky for you I carry my shop.",
    "Don't ask where I got it. Ask what it costs.",
    "You look like someone who'll need this before the week is out.",
    "I only come through the once. Buy now, or wonder later.",
    "Coin first. Questions are extra.",
    "I know what you are. I don't much care, so long as you're paying.",
]

# Traders charge a premium for the convenience, and pay better than a hold's
# market when buying -- they know what deep loot is worth.
TRADER_MARKUP = 1.35
TRADER_BUY_RATE = 0.75

# Chance a trader is waiting when you walk into a room that could hold one.
TRADER_CHANCE = 0.09


def make_trader(region: int) -> Trader:
    """Roll a wandering trader stocked for ``region`` (and a peek at the next)."""
    here = region_by_index(region)
    pool = list(here["gear"]) + list(here["potions"])

    # A tempting taste of the next hold's gear, at a price.
    if region < FINAL_REGION:
        pool += region_by_index(region + 1)["gear"]

    picks = random.sample(pool, k=min(3, len(pool)))
    stock = []
    for name in picks:
        item = make_item(name)
        item.price = max(1, round(item.price * TRADER_MARKUP))
        stock.append(item)

    return Trader(
        name=random.choice(TRADER_NAMES),
        greeting=random.choice(TRADER_GREETINGS),
        stock=stock,
    )


# --------------------------------------------------------------------------
# Encounter and combat rolls
# --------------------------------------------------------------------------

# Chance an enemy is already waiting when you step into a dangerous room.
ENTER_ENCOUNTER_CHANCE = 0.35

# When you actively explore a dangerous room: below the first threshold you find
# an enemy, below the second you find coin, otherwise nothing.
EXPLORE_ENEMY_CHANCE = 0.60
EXPLORE_GOLD_CHANCE = 0.85

# Feeding: you may drain an enemy already this badly hurt, which kills it and
# heals you, but you get no XP for a kill you did not earn in the fight.
FEED_THRESHOLD = 0.35
FEED_RATE = 0.6

# Guarding halves the next blow and leaves you open to strike harder after it.
GUARD_REDUCTION = 0.5
GUARD_RIPOSTE = 1.5

# Chance an enemy telegraphs a heavy blow instead of striking normally, and
# what that blow multiplies its damage by when it lands.
WINDUP_CHANCE = 0.25
WINDUP_MULTIPLIER = 2.2

# Fleeing is a gamble, not a guarantee: fail and you eat a free hit.
FLEE_SUCCESS_CHANCE = 0.70

# Every hit lands somewhere in +/-25% of its base damage, and one in ten hits
# is a critical that doubles it. Keeps fights from being pure arithmetic.
DAMAGE_SPREAD = 0.25
CRIT_CHANCE = 0.10
CRIT_MULTIPLIER = 2


def roll() -> float:
    """Return a random float in [0, 1). Wrapper keeps RNG use in one place."""
    return random.random()


def roll_damage(base: int) -> tuple[int, bool]:
    """Roll one hit from ``base`` damage. Returns (damage, was_critical)."""
    low = max(1, round(base * (1 - DAMAGE_SPREAD)))
    high = max(low, round(base * (1 + DAMAGE_SPREAD)))
    damage = random.randint(low, high)
    critical = random.random() < CRIT_CHANCE
    if critical:
        damage *= CRIT_MULTIPLIER
    return damage, critical


# --------------------------------------------------------------------------
# Holds
# --------------------------------------------------------------------------


# How many pieces a forge puts out at once. Fewer than the tier holds, so two
# runs shop differently, and enough that there is always a choice to make.
FORGE_STOCK = 5


def make_shop_potions(region: int = 1) -> list[Item]:
    """Stock for a hold's night market. Blood is never rationed."""
    return [make_item(name) for name in region_by_index(region)["potions"]]


def make_shop_gear(region: int = 1) -> list[Item]:
    """Stock for a hold's charnel forge, drawn fresh for this run.

    A forge shows a subset of its tier rather than the whole catalogue, so what
    is on the wall is part of what makes one run differ from the next. It is
    guaranteed to carry at least one weapon and one piece of armour: a hold that
    cannot arm you is a hold that cannot be played through.
    """
    pool = [make_item(name) for name in region_by_index(region)["gear"]]
    weapons = [item for item in pool if item.kind == "weapon"]
    armour = [item for item in pool if item.kind == "armor"]

    stock = []
    if weapons:
        stock.append(random.choice(weapons))
    if armour:
        stock.append(random.choice(armour))

    rest = [item for item in pool if item not in stock]
    random.shuffle(rest)
    stock += rest[: max(0, FORGE_STOCK - len(stock))]

    # Cheapest first, so the wall reads as a ladder.
    return sorted(stock, key=lambda item: item.price)
