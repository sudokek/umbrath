# Umbrath

A terminal roguelike. You are a vampire lord of a fallen house, clawing a
dominion back out of the mountains that swallowed it — three holds, three
underdarks, and a thing on a frozen throne at the bottom of the world.

Dying is not the end. It is the loop.

## Requirements

- **Python 3.10 or newer** (the code uses `X | Y` type-union syntax).

No third-party packages — everything uses the standard library.

## Running

```bash
python main.py
```

You'll be asked for a name and an origin. After that, type commands at the `>`
prompt. Press **Enter on an empty line to repeat your last command** (handy for
grinding). `Ctrl+C`, `quit`, or `exit` leaves.

## Making a character

Your **name is your save slot** — two names are two separate ongoing stories,
each with its own relics, blessings, echoes, and death count, kept in
`saves/<name>.sav`.

Then you pick what you were before the blood. Six origins, deliberately very
different and deliberately worth the same:

| Origin | Plays like |
|---|---|
| **Vaelric Scion** | Old money. Starts rich and armed. |
| **Nachtkin** | Feral. A huge pile of HP and a bite. |
| **Mourncaller** | Grave-scholar. Hits hardest out of the gate. |
| **Ironbound** | Dead soldier. Armored, hard to move. |
| **Thirstborn** | Glass cannon. Vicious, fragile, drinks a lot. |
| **Graveborn** | No lineage, no weakness. A bit of everything. |

That balance is enforced, not eyeballed: every bonus has a point cost, each
origin is built to the same 24-point budget, and a test fails the build if one
drifts off it. Adding a new race is one entry in `chargen.py` that totals the
budget.

## The shape of the world

Three holds, travelled in order. Each is a settlement plus an underdark, and
each underdark ends in a boss standing in the doorway to the next hold.

```
  Greyfen ──> The Barrow Warrens ──> Ashmoor ──> The Emberdeeps ──> Wintermourn ──> The Rimevault
   (hold)        wet stone, bone      (hold)      ash and fire        (hold)        ice and silence
                       |                               |                                  |
                 BARROW GAUNT                    CINDER WARDEN                       PALE KING
                 drops a relic                   drops a relic                       you win
```

Each hold sells a better tier of gear than the last and fights harder than the
last. You cannot skip ahead: the only route onward runs out of the vault, the
boss is standing on it, and fleeing will never carry you past one.

### The loop

1. **Hold** — buy weapons and armor at the charnel forge, blood at the night
   market, sleep at the inn.
2. **Underdark** — `explore` to turn up monsters or loose coin. Deeper rooms
   are more dangerous and pay better.
3. **Grow** — coin buys gear, kills buy levels.
4. **Boss** — when you can take it, kill the thing in the vault. It drops a
   **relic** and opens the road on.
5. **Repeat**, one hold richer and one hold harder.

Clear a hold thoroughly — every room, every spawn, all the loot — and you come
out at roughly the right level for its boss with about twice the coin its best
kit costs. Enough to be ready; not enough to trivialise it. A full sweep of all
three lands you near level 21, which is where the Pale King becomes winnable.

### Dying

When you hit zero, **the run is over**. The coin, the gear, the levels, and the
caves themselves are gone — the next run generates a whole new world.

What you keep:

- **Relics** — every boss drops one, permanently. The gaunt fang is +4 damage in
  *every* future run.
- **Echoes** — the currency of dying. Every finished run pays out, more for
  bosses killed and holds reached.
- **Blessings** — spent at the **Shrine of Echoes** beneath the Greyfen inn:
  `undeath` (+8 max HP), `bloodthirst` (+2 damage), `gravewarding` (+2 defense),
  `plunder` (+50 starting coin). They stack, forever.

Your Legacy is written to your save slot whenever a run ends. `legacy` shows it.

### Winning

Kill the **Pale King** at the bottom of the Rimevault. That is the ending, and
it is the only one.

## The underdarks

Generated fresh every run, and each draws its rooms, flavour, and bestiary from
its own theme — they never read alike:

- **The Barrow Warrens** — flooded crypts, roots through the ceiling, bones that
  were dropped rather than laid. Grave robbers, barrow wights, hollow knights.
- **The Emberdeeps** — black glass and slow fire, ash falling like grey snow,
  forge-marks cut by someone long gone. Ash hounds, forge revenants, magma drakes.
- **The Rimevault** — blue ice and total silence, frozen waterfalls, things
  suspended in the floor. Frost wolves, hoarfrost knights, winter wyrms.

Caves sprawl in **every** direction — they are meant to be easy to get lost in
and satisfying to learn. You map them by walking them. Roughly 80% of rooms have
more than one way out, so getting lost is a "which way was it?" problem rather
than a series of dead-end round trips. Going back through a cave is always a
choice you make to farm loot or easier kills, never something the game forces.

### Wandering traders

Now and then someone is on the road with their packs open. They carry two or
three one-off items at a markup, sometimes gear from the *next* hold. Buy it and
it's gone; leave the room and so are they. `talk` to hear them out. They pay
better than a hold's market when you're selling.

### Combat

Every hit lands within ±25% of your attack power, and one in ten is a
**critical** that doubles it. Armor subtracts from incoming damage, but a hit
always does at least 1.

`flee` succeeds about 70% of the time and retreats you to the safest adjacent
room *in the same hold*. Fail, and the enemy gets a free swing. Either way the
monster stays where it is.

### Levelling

Killing something awards XP based on how tough it was. Level `N` costs `20 × N`
XP; each level grants **+5 max HP**, **+1 damage**, and a full heal on the spot.

## The map

ASCII, drawn every turn, showing only what you've found:

```
      [Smt]
        |
[Mkt]-[Sqr]-[For]-*B0*-[ ? ]
        |
      [Inn]
        |
      [Shr]
```

- `[Abc]` visited · `*Abc*` you are here · `[ ? ]` seen but not entered
- Cave labels carry their theme and depth: `B3` is three rooms into the Barrow
  Warrens, `E7!` is a deadly room deep in the Emberdeeps, `R!!` is a vault.

It is a **camera**, not the whole world: a fixed 7×5 window centred on you that
scrolls as you move, so the display never grows. Corridors running off the edge
are drawn as stubs, and `(map continues: ...)` names the directions where
explored rooms lie off-screen.

## Commands

| Command | Aliases | What it does |
|---------|---------|--------------|
| `north` / `south` / `east` / `west` | `n` / `s` / `e` / `w` | Move between rooms. |
| `look` | `l` | Redraw the screen. |
| `map` | `m` | Show the discovered map. |
| `explore` | `x` | Search a dangerous area for enemies or coin. |
| `attack [enemy]` | `a` | Hit the enemy here (auto-targets; repeat with Enter). |
| `flee` | | Try to escape the current fight. |
| `examine <thing>` | | Describe an item, relic, ware, or enemy. |
| `take` / `drop <item>` | `t` | Pick up / put down an item. |
| `use <item>` | | Drink blood, mostly. |
| `equip <item>` | | Equip a weapon or armor. |
| `talk` | | Speak to a wandering trader. |
| `buy [item]` | | Buy from a forge, market, trader, or shrine. |
| `sell <item>` | | Sell at a market, or to a trader. |
| `rest` | `r` | Pay to fully heal at the inn. |
| `inventory` | `i` | Show what you're carrying. |
| `stats` | | Level, XP, HP, coin, gear, relics, location. |
| `legacy` | | Relics, blessings, and echoes kept between runs. |
| `save [file]` / `load [file]` | | Save / load (defaults to your character's slot). |
| `help` | `h` | List all commands. |
| `settings` | | View or change settings (below). |
| `quit` | `q`, `exit` | Leave. |

Most commands accept an unambiguous prefix (`exp` for `explore`) and tolerate
minor typos.

### Saving

`save` writes to `saves/<name>_run.sav` — your character's own slot, so two
characters never overwrite each other. Saves are scrambled by default so opening
the file doesn't spoil the cave layouts; `settings toggle obfuscate_saves` gives
plain, readable JSON instead. Loading auto-detects either format and tolerates
saves written by an older version.

### Settings

```
settings                              # show all settings
settings toggle show_map              # flip a boolean
settings set min_command_prefix 2     # change a number (1-10)
```

## Project layout

| File | Role |
|------|------|
| `main.py` | Entry point: pick a character, then play. |
| `newgame.py` | Title screen, save slots, character creation. |
| `chargen.py` | Origins and the point budget that keeps them equal. |
| `game.py` | Main loop, rendering, and every command action. |
| `models.py` | `Item`, `Enemy`, `Trader`, `Room`, `Player`, `Legacy`, `Settings`. |
| `legacy.py` | Turns a Legacy into the bonuses a new run starts with. |
| `world.py` | Builds the three holds, their roads, and their bounds. |
| `dungeon.py` | Generates one themed underdark from a seed. |
| `content.py` | Items, themes, bestiaries, shops, traders, rolls. |
| `map_render.py` | Draws the ASCII map camera. |
| `parser.py` | Turns typed text into commands. |
| `saveload.py` | Saves, the Legacy file, scrambling, version tolerance. |
| `ui.py` | Terminal helpers and the big ASCII banners. |
| `test_*.py` | Unit tests, including `test_invariants.py`. |

## Running the tests

```bash
python -m unittest
```

`test_invariants.py` is the one that matters most: it asserts properties over
**120 generated worlds** — every room reachable, no two rooms on the same
square, exits mutual, holds never overlapping, exactly one boss per hold and
exactly one way past it, difficulty rising in order, the map never overflowing
its frame, and every origin costing the same. Every structural bug this project
has hit is a property in there now, so it cannot come back quietly.

## Tip: reproducible runs

`GAME_SEED` makes a whole playthrough deterministic — layouts, encounters, loot,
and damage rolls all follow from it:

```bash
GAME_SEED=7 python main.py
```
