"""ASCII portraits for the player and everything that wants to kill them.

All original art, drawn for this game. Nothing here is copied, which keeps the
project's provenance clean and lets every sprite obey the constraints the
interface already has: pure ASCII (so it survives a console that cannot encode
box-drawing), a fixed height so panels never jitter, and a width that fits
beside its opponent inside 78 columns.

Sprites are keyed by **archetype**, not by creature. There are forty creatures
and three poses, and a hundred and twenty hand-drawn frames would be a hundred
and twenty thin ones. Instead a dozen-odd archetypes carry the art and every
creature resolves to one -- by an explicit entry where the name does not give it
away, and otherwise by the words in the name, so a monster added tomorrow gets a
body today without being registered in two places.

Poses are frames of a turn, not of a clock. ``attack`` is drawn on the turn a
combatant swings and ``hit`` on the turn it is wounded, so a fight animates at
exactly the rate the player types -- no sleeps, no threads, and nothing that
fights the one-redraw-per-command rule the renderer is built on.
"""

from ui import glyph, paint

POSES = ("idle", "hit", "attack")

# Every sprite is padded to this, so a panel holding one never changes height.
SPRITE_HEIGHT = 6
SPRITE_WIDTH = 22


def _art(block: str) -> list[str]:
    """Turn a drawing into padded lines of a fixed height and width."""
    lines = [line[:SPRITE_WIDTH] for line in block.strip("\n").split("\n")]
    lines = lines[:SPRITE_HEIGHT]
    # Pad upward: a creature stands on the floor of its panel, not the ceiling.
    while len(lines) < SPRITE_HEIGHT:
        lines.insert(0, "")
    return [line.ljust(SPRITE_WIDTH) for line in lines]


# --------------------------------------------------------------------------
# The player: a vampire lord, facing right, toward whatever is in the way.
# --------------------------------------------------------------------------

PLAYER = {
    "idle": _art(r"""
     .---.
    / o o \
    \  -  /
   /\_| |_/\
  /  |   |  \
     /   \
"""),
    "attack": _art(r"""
     .---.
    / O O \___
    \  ^  /   \
   /\_| |_/\   }
  /  |   |  \
     /   \
"""),
    "hit": _art(r"""
     .---.
    / x o \
    \  ~  /
   /\_| |_/\
   \ |   | /
     /   \
"""),
}


# --------------------------------------------------------------------------
# Archetypes. Enemies face left, toward the player.
# --------------------------------------------------------------------------

SPRITES: dict[str, dict[str, list[str]]] = {
    "vermin": {
        "idle": _art(r"""
       ,--.
    ,-'    `.
   (  o   o  )
    `--.__.--'
      ''  ''
"""),
        "attack": _art(r"""
       ,--.
  <,-'      `.
 <(   o   o   )
    `--vvvv--'
      ''  ''
"""),
        "hit": _art(r"""
       ,--.
    ,-'    `.
   (  x   x  )
     `-.__.-'
       `  `
"""),
    },
    "flier": {
        "idle": _art(r"""
    \        /
   \ \      / /
    \_\(oo)/_/
       `--'
"""),
        "attack": _art(r"""
  \_          _/
    \_\(OO)/_/
  <<<  `\/'
       /  \
"""),
        "hit": _art(r"""
     \      /
      \(xx)/
       `--'
        ||
"""),
    },
    "mortal": {
        "idle": _art(r"""
       ,---.
      ( o o )
     __\ - /__
    /   | |   \
        | |
       _/ \_
"""),
        "attack": _art(r"""
  \    ,---.
   \__( o o )
     __\ ^ /__
    /   | |   \
        | |
       _/ \_
"""),
        "hit": _art(r"""
       ,---.
      ( x o )
     __\ ~ /__
    /   | |   \
       /   \
      _/   \_
"""),
    },
    "undead": {
        "idle": _art(r"""
       .-'-.
      ( o o )
       \ ~ /
      /|] [|\
       | | |
      _/   \_
"""),
        "attack": _art(r"""
  \\   .-'-.
   \\_( O O )
       \ V /
      /|] [|\
       | | |
      _/   \_
"""),
        "hit": _art(r"""
       .-'-.
      ( x x )
       \ _ /
      /|] [|\
      /  |  \
     _/     \_
"""),
    },
    "beast": {
        "idle": _art(r"""
     /\__/\
    ( o  o )___
     >  ..    _\
    (  ____  )
     || || ||
"""),
        "attack": _art(r"""
    /\__/\
   ( O  O )____
  <  VVVV     _\
   (  ____   )
    || || ||
"""),
        "hit": _art(r"""
     /\__/\
    ( x  x )___
     >  __    _\
    (  ____  )
     |'  '| |
"""),
    },
    "brute": {
        "idle": _art(r"""
      .-------.
     ( o     o )
      \   _   /
    ___|;;;;;|___
   /   |     |   \
       |_| |_|
"""),
        "attack": _art(r"""
  \   .-------.
   \_( O     O )
      \  ###  /
    ___|;;;;;|___
   /   |     |   \
       |_| |_|
"""),
        "hit": _art(r"""
      .-------.
     ( x     x )
      \   ~   /
    ___|;;;;;|___
   /  /|     |\  \
      |_| |_|
"""),
    },
    "armored": {
        "idle": _art(r"""
      .-=====-.
     [  o | o  ]
      \  ===  /
     [|#######|]
      |# | | #|
     _|_|   |_|_
"""),
        "attack": _art(r"""
 \=\  .-=====-.
  \=\[  O | O  ]
      \  ===  /
     [|#######|]
      |# | | #|
     _|_|   |_|_
"""),
        "hit": _art(r"""
      .-=/ /=-.
     [  x | x  ]
      \  ===  /
     [|##/ /#|]
      |# | | #|
     _|_|   |_|_
"""),
    },
    "spirit": {
        "idle": _art(r"""
       .~~~~.
     ,'  ..  `.
    (   (oo)   )
     `. `--' ,'
       ~~~~~~
        ' '
"""),
        "attack": _art(r"""
  ~~~~ .~~~~.
 ~~~ ,'  ..  `.
  ~~(   (OO)   )
     `. \\//' ,'
       ~~~~~~
"""),
        "hit": _art(r"""
       . ~~ .
      '  ..  `
      (  xx  )
       `.__,'
         ~~
"""),
    },
    "arachnid": {
        "idle": _art(r"""
   \  \    /  /
    \__\__/__/
    /(o o  o)\
   /  \____/  \
  /    |  |    \
"""),
        "attack": _art(r"""
  \\ \  \  /  /
   \\_\__\/__/
  <<</(O O  O)\
    /  \VVV/  \
   /    |  |   \
"""),
        "hit": _art(r"""
    \       /
     \__ __/
     /(x x)\
    /  \__/ \
     |      |
"""),
    },
    "drake": {
        "idle": _art(r"""
       ___
     /`. .'\__
    ( (o o)   `\
     \  VV  ____/
     /_/  \_\
"""),
        "attack": _art(r"""
  ~~~~   ___
 ~~~~  /`. .'\__
 ~~~  ( (O O)   `\
       \ WWW  ____/
       /_/  \_\
"""),
        "hit": _art(r"""
       ___
     /`. .'\__
    ( (x x)   `\
     \  __  ____/
     /_/  \_\
"""),
    },
    "fungal": {
        "idle": _art(r"""
     .-~~~~~-.
   .'  o   o  `.
  (   .-----.   )
   `-'  | |  `-'
        | |
       _|_|_
"""),
        "attack": _art(r"""
    ..-~~~~~-..
  .' ' o   o ' `.
 (  ' .-----. '  )
  `-'   |||   `-'
    .   | |   .
       _|_|_
"""),
        "hit": _art(r"""
     .-~~ ~~-.
   .'  x   x  `.
  (   .-- --.   )
   `-'  | |  `-'
       /   \
      _|   |_
"""),
    },
    # ---- bosses, each its own thing -------------------------------------
    "gaunt": {
        "idle": _art(r"""
     _________
   /\  O   O  /\
  /  \/\/\/\/\/ \
  \  /\/\/\/\/\ /
   \/_________\/
"""),
        "attack": _art(r"""
    ___________
  /\ \/ O   O \/ /\
 /  \/\/\/\/\/\/  \
 \  /\/\/\/\/\/\  /
  \/___________\/
    V V V V V
"""),
        "hit": _art(r"""
     _________
   /\  x   x  /\
  /  \_/\_/\_/ \
  \  /~\/~\/~\ /
   \/_________\/
"""),
    },
    "warden": {
        "idle": _art(r"""
     /\=======/\
    [  (*) (*)  ]
     \  #####  /
    [|#/|###|\#|]
     |#| | | |#|
    _|_|_   _|_|_
"""),
        "attack": _art(r"""
 ###  /\=====/\
  ## [  (*) (*) ]
 ###  \  WWWW  /
     [|#/|##|\#|]
      |#| || |#|
     _|_|_  _|_|_
"""),
        "hit": _art(r"""
     /\==/ /==/\
    [  x   x    ]
     \  #/ /#  /
    [|#/|# #|\#|]
     |#| | | |#|
    _|_|_   _|_|_
"""),
    },
    "bloom": {
        "idle": _art(r"""
   .-~~~~~~~~~-.
 .'  o   o   o  `.
(  .-~-. .-~-.    )
 `-'   |_|   `--~'
   .   | |   .
  _|___|_|___|_
"""),
        "attack": _art(r"""
 ..-~~~~~~~~~-..
.' ' O   O   O '`.
(  '.-~-. .-~-.' )
 `-' ' |_| ' `--~'
  . .  | |  . .
 _|___ |_| ___|_
"""),
        "hit": _art(r"""
   .-~~ ~~~ ~~-.
 .'  x   x   x  `.
(  .-~-. .- -.    )
 `-'   |_|   `--~'
    /  | |  \
  _|__ |_| __|_
"""),
    },
    "king": {
        "idle": _art(r"""
   \|/ /\ \|/
    .--------.
   (  *    *  )
    \  ____  /
   /|________|\
   ||   ||   ||
"""),
        "attack": _art(r"""
  \\|/ /\ \|//
 ** .--------. **
 ** (  *   *  ) **
     \  WWW  /
    /|_______|\
    ||  ||  ||
"""),
        "hit": _art(r"""
   \|/ /\ \|/
    .--------.
   (  x    x  )
    \  ____  /
   /|__/ /___|\
   ||   ||   ||
"""),
    },
}

# When an archetype cannot be worked out, everything still gets a body.
FALLBACK = "mortal"

# Creatures whose name does not give them away. Checked before the keywords.
BY_NAME = {
    "barrow gaunt": "gaunt",
    "cinder warden": "warden",
    "the mother bloom": "bloom",
    "pale king": "king",
    "grave robber": "mortal",
    "rot-touched": "mortal",
    "husk-walker": "undead",
    "fen lurker": "spirit",
    "slagworm": "drake",
    "the rotting choir": "spirit",
    "void stalker": "spirit",
    "cinder imp": "vermin",
    "ice spider": "arachnid",
    "rime spider": "arachnid",
}

# Otherwise the name says what it is. Order matters: the first match wins.
BY_KEYWORD = (
    ("rat", "vermin"),
    ("mite", "vermin"),
    ("sporeling", "vermin"),
    ("bat", "flier"),
    ("wisp", "flier"),
    ("wolf", "beast"),
    ("hound", "beast"),
    ("spider", "arachnid"),
    ("drake", "drake"),
    ("wyrm", "drake"),
    ("worm", "drake"),
    ("knight", "armored"),
    ("golem", "armored"),
    ("revenant", "undead"),
    ("wight", "undead"),
    ("skeleton", "undead"),
    ("wraith", "spirit"),
    ("stalker", "spirit"),
    ("choir", "spirit"),
    ("bloom", "fungal"),
    ("spore", "fungal"),
    ("mycelial", "fungal"),
    ("fungal", "fungal"),
    ("ogre", "brute"),
    ("troll", "brute"),
    ("brute", "brute"),
    ("titan", "brute"),
    ("colossus", "brute"),
)

# What a creature is drawn in, by archetype.
TINTS = {
    "vermin": "stone",
    "flier": "stone",
    "mortal": "bone",
    "undead": "bone",
    "beast": "stone",
    "brute": "green",
    "armored": "bright_cyan",
    "spirit": "bright_magenta",
    "arachnid": "magenta",
    "drake": "bright_red",
    "fungal": "bright_green",
    "gaunt": "blood",
    "warden": "bright_red",
    "bloom": "bright_green",
    "king": "bright_cyan",
}


def archetype(name: str) -> str:
    """Which body a creature wears -- by name first, then by keyword."""
    lowered = name.lower()
    if lowered in BY_NAME:
        return BY_NAME[lowered]
    for word, kind in BY_KEYWORD:
        if word in lowered:
            return kind
    return FALLBACK


def for_enemy(name: str, pose: str = "idle", tint: bool = True) -> list[str]:
    """The sprite for a creature, in a pose, ready to print."""
    kind = archetype(name)
    art = SPRITES[kind].get(pose) or SPRITES[kind]["idle"]
    if not tint:
        return list(art)
    return [paint(line, TINTS.get(kind, "white")) for line in art]


def for_player(pose: str = "idle", tint: bool = True) -> list[str]:
    """The player's own sprite."""
    art = PLAYER.get(pose) or PLAYER["idle"]
    if not tint:
        return list(art)
    return [paint(line, "bright_red") for line in art]


def meter(value: int, maximum: int, width: int = 14) -> str:
    """A health bar sized for a duel panel, coloured by how much is left."""
    fraction = 0.0 if maximum <= 0 else max(0.0, min(1.0, value / maximum))
    filled = round(width * fraction)
    style = "bright_green" if fraction > 0.5 else (
        "bright_yellow" if fraction > 0.25 else "bright_red"
    )
    full, empty = glyph("block") * filled, glyph("dot") * (width - filled)
    # Painting an empty string still emits the escapes, which show up as stray
    # bytes in a bar that happens to be full or empty.
    return (paint(full, style) if full else "") + (paint(empty, "dim") if empty else "")
