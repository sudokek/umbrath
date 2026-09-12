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

Five rules keep the art in the register the rest of the game is written in, all
of them learned by drawing it the wrong way round first:

* **No round eyes.** A pair of round, symmetrical ``o``s reads as cute whatever
  body it is mounted on -- the difference between a horror and a mascot lives
  almost entirely in the eyes. Faces here are hollows, slits and brow-shadow, or
  simply absent.
* **Wounds are damage, not cartoon death.** ``hit`` never draws ``x`` for eyes.
  It shears the body with a stroke that is not in the idle frame.
* **A blow moves things.** ``hit`` shifts the whole sprite one column *away* from
  its opponent and ``attack`` shifts it one column *toward*, so a trade of blows
  reads as recoil and lunge rather than two statues swapping faces.
* **Mass over detail.** At six rows there is no room for a face worth drawing, so
  silhouette and weight do the work: ``%`` for rot and fur and hide, ``#`` for
  plate and stone, ``|`` for ribs and gills.
* **Every row of one creature shares a centre.** Six lines drawn by eye come out
  a column apart and the result looks broken rather than drawn -- the jaw sits
  off the skull, the shoulders off the hips. This is the failure no test catches,
  because every line is still the right length.
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
# The player: a cloaked lord, facing right, toward whatever is in the way.
# The hood holds a shadow where a face would be; on the swing it opens.
# --------------------------------------------------------------------------

PLAYER = {
    "idle": _art(r"""
        ,-.
      ,/%%%\.
     //  _  \\
     '|%%%%%|'
      |%|  |%|
      _/   \_
"""),
    "attack": _art(r"""
         ,-.
       ,/%%%\.
      //  \/  \\__
      '|%%%%%|'  \====
       |%|  |%|
       _/   \_
"""),
    "hit": _art(r"""
       ,-.
     ,/%% \.
    //  \  \\
    '|%%/ %|'
     |%|  |%|
     \_   _/
"""),
}


# --------------------------------------------------------------------------
# Archetypes. Enemies face left, toward the player.
# --------------------------------------------------------------------------

SPRITES: dict[str, dict[str, list[str]]] = {
    "vermin": {
        "idle": _art(r"""
         ___
      ,-'%%%'-.
    <%%%%%%%%%%%\,
     `-''-----''-'
        "     "
"""),
        "attack": _art(r"""
        ___
     ,-'%%%'-.
 <<<%%%%%%%%%%%\,
    `-''-----''-'
       "     "
"""),
        "hit": _art(r"""
          ___
       ,-'%% '-.
     <%%%/%%%%%%\,
      `-''-----''-'
         "     "
"""),
    },
    "flier": {
        "idle": _art(r"""
    \\        //
     \\__,__//
       )%%%(
        `"`
"""),
        "attack": _art(r"""
  \\_         _//
   \\__,__,__//
  <<  )%%%(
      /`\
"""),
        "hit": _art(r"""
     \\        //
      \\__,__//
        )%/(
         `
"""),
    },
    "mortal": {
        "idle": _art(r"""
         ,--.
        /^^^^\
       _\____/_
      /  |%%%|  \
         |% %|
        _/   \_
"""),
        "attack": _art(r"""
        ,--.
   ____/^^^^\
 <_____\____/_
     /  |%%%|  \
        |% %|
       _/   \_
"""),
        "hit": _art(r"""
          ,--.
         /^^ \
        _\_/__/_
       /  |%/%|  \
          |% %|
         \_   _/
"""),
    },
    "undead": {
        "idle": _art(r"""
       .--------.
       /\_/  \_/\
       \   __   /
       /|]####[|\
        || |  ||
       _//    \\_
"""),
        "attack": _art(r"""
  \\   .--------.
   \\  /\_/  \_/\
      \  VVV   /
      /|]####[|\
       || |  ||
      _//    \\_
"""),
        "hit": _art(r"""
        .--------.
        /\_/  \_ /
        \  _/_   /
        /|]#/##[|\
        /|  ||  |\
        _//    \\_
"""),
    },
    "beast": {
        "idle": _art(r"""
     /\_/\
    /  -  \_____
   < \^^^/ %%%%%\
     \_______%%%/
      ||  ||  ||
"""),
        "attack": _art(r"""
    /\_/\
   /  =  \_____
<<<VVVVVV %%%%%\
    \_______%%%%/
     ||  ||  ||
"""),
        "hit": _art(r"""
      /\_/\
     /  \  \_____
    < \_/ %/%%%%%\
      \____%%%%%%/
       |'  |'  ||
"""),
    },
    "brute": {
        "idle": _art(r"""
       .%%%%%%%.
      %%%\   /%%%
      %%%%%^%%%%%
     %%%%%%%%%%%%%
      %%%%   %%%%
       '''   '''
"""),
        "attack": _art(r"""
 __   .%%%%%%%.
(%%\ %%%\   /%%%
 \%%%%%%%%V%%%%%
    %%%%%%%%%%%%%
     %%%%   %%%%
      '''   '''
"""),
        "hit": _art(r"""
        .%%%%%%%.
       %%%\   /%%%
       %%%%/ %%%%%
      %%%%%/%%%%%%%
       %%%/   %%%%
        '''   '''
"""),
    },
    "armored": {
        "idle": _art(r"""
       .=======.
      [|-------|]
       \#######/
      [|#|###|#|]
       |#| | |#|
      _|_|   |_|_
"""),
        "attack": _art(r"""
      .=======.
 /=/ [|-------|]
/=/   \#######/
     [|#|###|#|]
      |#| | |#|
     _|_|   |_|_
"""),
        "hit": _art(r"""
        .==/ /==.
       [|--/ ---|]
        \##/ ###/
       [|#|/##|#|]
        |#| | |#|
       _|_|   |_|_
"""),
    },
    "spirit": {
        "idle": _art(r"""
        ,~~~~~,
       /       \
      (   ___   )
       \  ~~~  /
        ~~ ~ ~~
          ~ ~
"""),
        "attack": _art(r"""
  ~~   ,~~~~~,
 ~~~  /       \
  ~~ (   \_/   )
      \  ~~~  /
     ~~~ ~ ~ ~~~
"""),
        "hit": _art(r"""
         ,~~ ~~,
        /   _   \
       (  ~   ~  )
        \  ~ ~  /
         ~  ~  ~
"""),
    },
    "arachnid": {
        "idle": _art(r"""
   \  \       /  /
    \__\_____/__/
    /%%%%%%%%%%%\
   /  \%%%%%%%/  \
   |   |     |   |
"""),
        "attack": _art(r"""
  \  \      /  /
   \__\____/__/
VV /%%%%%%%%%%\
VV/  \%%%%%%/  \
  |   |    |   |
"""),
        "hit": _art(r"""
    \ \       / /
     \_\_____/_/
     /%%/%%%%%%\
    /  \%%%%%/  \
    |   |    |  |
"""),
    },
    "drake": {
        "idle": _art(r"""
        ______
      /'------'\_
   <( -   %%%%%%%\
      \VV  %%%%%%/
       /_/   \_\
"""),
        "attack": _art(r"""
       ______
     /'------'\_
~~<( =   %%%%%%%\
    /WW  %%%%%%/
      /_/   \_\
"""),
        "hit": _art(r"""
         ______
       /'--- -'\_
    <( \   %%/%%%\
       \/   %%%%%/
        /_/   \_\
"""),
    },
    "fungal": {
        "idle": _art(r"""
        .-~~~-.
      .'|||||||'.
     ( ||||||||| )
      `-._____.-'
          | |
         _|_|_
"""),
        "attack": _art(r"""
   .  . .-~~~-. .  .
   .  .'|||||||'. .
     ( ||||||||| )
   '  `-._____.-'  '
      .   | |   .
         _|_|_
"""),
        "hit": _art(r"""
         .-~~ -.
       .'|||| |'.
      ( ||/||||| )
       `-.__ __.-'
           | |
          _|_|_
"""),
    },
    # ---- bosses, each its own thing -------------------------------------
    "gaunt": {
        "idle": _art(r"""
         ,-----,
       /|\_/ \_/|\
       \|  ===  |/
        |#|||||#|
        |#|   |#|
       _|'|   |'|_
"""),
        "attack": _art(r"""
  \\    ,-----,
   \\ /|\_/ \_/|\
      \|  VVV  |/
       |#|||||#|
       |#|   |#|
      _|'|   |'|_
"""),
        "hit": _art(r"""
          ,-----,
        /|\_/ \_ |\
        \| =/=   |/
         |#||/||#|
         |#|   |#|
        _|'|   |'|_
"""),
    },
    "warden": {
        "idle": _art(r"""
       /\=====/\
      [|--- ---|]
       \##^^^##/
      [|#/|#|\#|]
       |#| | |#|
      _|_|_ _|_|_
"""),
        "attack": _art(r"""
  ^^  /\=====/\
 ^^^ [|--- ---|]
  ^^  \##WWW##/
     [|#/|#|\#|]
      |#| | |#|
     _|_|_ _|_|_
"""),
        "hit": _art(r"""
        /\=/ /=/\
       [|-- / --|]
        \##^/^##/
       [|#/|#|\#|]
        |#| | |#|
       _|_|_ _|_|_
"""),
    },
    "bloom": {
        "idle": _art(r"""
     .-~~~~~~~~~-.
   .'||||||||||||'.
  ( ||| .-~-. ||| )
   `-.__|   |__.-'
     .   |   |   .
    _|___|___|___|_
"""),
        "attack": _art(r"""
 .   .-~~~~~~~~~-.  .
 . .'||||||||||||'. .
  ( ||| .-~-. ||| )
 ' `-.__|   |__.-' '
     .   |   |   .
    _|___|___|___|_
"""),
        "hit": _art(r"""
      .-~~~~ ~~~~-.
    .'|||||| |||||'.
   ( ||| ./ -. ||| )
    `-.__| /  |_.-'
      .   |   |   .
     _|___|___|___|_
"""),
    },
    "king": {
        "idle": _art(r"""
       \|/ /^\ \|/
       .---------.
       /|\_/ \_/|\
       \|  ===  |/
     /|#|#######|#|\
     _|_|#|   |#|_|_
"""),
        "attack": _art(r"""
  \\   \|/ /^\ \|/
   \\  .---------.
      /|\_/ \_/|\
      \|  VVV  |/
    /|#|#######|#|\
    _|_|#|   |#|_|_
"""),
        "hit": _art(r"""
        \|/ / \ \|/
        .---------.
        /|\_/ \_ |\
        \|  =/=  |/
      /|#|###/###|#|\
      _|_|#|   |#|_|_
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

# What a creature is drawn in, by archetype. The common bestiary stays at the
# muted end of the palette -- stone, bone, old blood -- so that the four bosses
# are the only things on screen lit brightly.
TINTS = {
    "vermin": "stone",
    "flier": "stone",
    "mortal": "bone",
    "undead": "bone",
    "beast": "stone",
    "brute": "green",
    "armored": "cyan",
    "spirit": "magenta",
    "arachnid": "stone",
    "drake": "red",
    "fungal": "green",
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
    return [paint(line, "blood") for line in art]


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
