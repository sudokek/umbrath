# Umbrath

A terminal roguelike. You are a vampire lord of a fallen house, clawing a
dominion back out of the mountains that swallowed it — three holds, three
underdarks, and a thing on a frozen throne at the bottom of the world.

Dying is not the end. It is the loop.

## Requirements

- **Python 3.10 or newer** (the code uses `X | Y` type-union syntax).

**No third-party packages, and nothing to install.** Clone it and run it. Every
visual effect is written with bytes the terminal already understands, so there
is no dependency to vendor, pin, or download.

### How it looks

- **24-bit colour** where the terminal advertises it (Windows Terminal, most
  modern Unix terminals), falling back to the 16 basic colours, and to no colour
  at all where escapes are unsupported or `NO_COLOR` is set.
- **Box-drawing characters** for the frame and the map's corridors, falling back
  to `-` and `|` automatically when the console's encoding cannot carry them.
- The health bar runs green → amber → red as you get hurt; bosses shout in
  bright red.

Both are detected at startup and can be forced either way from **Options**
(`color`, `line_drawing`). Layout is measured ignoring colour escapes, so the
interface is exactly 62 columns wide however it is drawn.

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
2. **Underdark** — `explore` to turn up monsters or loose coin, and `open` any
   chest you find. Deeper rooms are more dangerous and pay better.
3. **Grow** — coin buys gear, kills buy levels.
4. **Boss** — when you can take it, kill the thing in the vault. It drops a
   **relic** and opens the road on.
5. **Repeat**, one hold richer and one hold harder.

Clear a hold thoroughly — every room, every spawn, all the loot — and you come
out at roughly the right level for its boss with about twice the coin its best
kit costs. Enough to be ready; not enough to trivialise it. A full sweep of all
three lands you near level 21, which is where the Pale King becomes winnable.

### Dying

When you hit zero, **the run is over**. The gear is gone, and so are the caves —
the next run generates a whole new world.

What you keep:

- **Relics** — every boss drops one, permanently. The gaunt fang is +4 damage in
  *every* future run.
- **Echoes** — the currency of dying. Every finished run pays out, more for
  bosses killed and holds reached.
- **Blessings** — spent at the **Shrine of Echoes** beneath the Greyfen inn:
  `undeath` (+8 max HP), `bloodthirst` (+2 damage), `gravewarding` (+2 defense),
  `plunder` (+50 starting coin). They stack, forever.
- **A third of your best level**, and **a quarter of the coin on your corpse** —
  both hard-capped at level 6 and 200 coin.

That last one is deliberately bounded. The point of a head start is to skip
re-proving Greyfen, which you have already proved; the point of the cap is that
Ashmoor and Wintermourn — where runs actually end — stay exactly as dangerous on
run twenty as on run two. Measured at the cap:

| Hold | A capped level-6 start |
|---|---|
| **Greyfen** | kills a mid-tier enemy in 2 swings, dies in 10 — walkable |
| **Ashmoor** | kills in 7, dies in 3 — still lethal |
| **Wintermourn** | kills in 21, dies in 1 — still lethal |

The coin cap covers 154% of Greyfen's best weapon, 62% of Ashmoor's, and 18% of
Wintermourn's. It plateaus around run nine and never grows again.

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

### Loot

Every item in the game comes out of one **weighted drop table**, gated by which
hold you have reached *and* how dangerous the room is. Deeper unlocks strictly
more; the first hold can never drop a doom glaive.

- **Loose loot** lies in rooms, scattered at generation.
- **Chests** are rarer and worth walking for: they hold several rolls at once,
  and the deeper they sit the more they hold. `open` one and it tips onto the
  floor for you to `take` from. You cannot open one with something still alive
  in the room.
- **Valuables** — lockets, grave-silver, a crown fragment — do nothing but sell.
  They are how a deep run turns into next run's weapon.

**Forges roll their stock per run.** A charnel forge shows five pieces out of
its hold's tier rather than the whole catalogue, so two runs shop differently —
but it is always guaranteed to carry at least one weapon and one piece of
armour, because a hold that cannot arm you is a hold that cannot be played.

### Wandering traders

Now and then someone is on the road with their packs open. They carry two or
three one-off items at a markup, sometimes gear from the *next* hold. Buy it and
it's gone; leave the room and so are they. `talk` to hear them out. They pay
better than a hold's market when you're selling.

### Blood

You are a vampire; what heals you is blood, and running out is how runs end.
Four grades exist, from the `blood vial` (10 HP) up to the `ichor of ages`
(120 HP), sold at any hold's night market.

Reaching for it is meant to be effortless:

- **`drink`** on its own opens the smallest vial that covers the wound — no
  wasting an ichor of ages to top up three points.
- Any word of an item's name works, so `use vial`, `use flask`, and
  `use blood vial` all do the same thing.
- The status bar shows how many you are carrying, and the screen tells you to
  drink when you are badly hurt.

### Combat

Every hit lands within ±25% of your attack power, and one in ten is a
**critical** that doubles it. Armor subtracts from incoming damage, but a hit
always does at least 1.

A fight is four verbs, and which one is right changes turn to turn:

| | |
|---|---|
| `attack` | Hit it. The default, and repeatable with Enter. |
| `guard` | Brace. Halves the next blow; if nothing lands, your next swing hits 50% harder. |
| `feed` | Drain an enemy already below 35%. Kills it and heals you for 60% of its health — **but pays no XP**. |
| `flee` | Leave. ~70% success, and the enemy recovers fully while you are gone. |

Two things stop `attack` being the answer every time:

**Enemies telegraph.** A quarter of the time an ordinary enemy winds up instead
of striking — it costs them the turn, and the blow that follows hits more than
twice as hard. The screen shouts about it. Keep swinging and it can end you
outright; `guard` halves it. Bosses never telegraph, because a boss does not
need the help.

**Feeding is a real cost.** Every fight ends on the same question: finish it
with the blade for the experience, or drink it for the health. You cannot have
both, and which you need depends on how the rest of the hold has gone.

Drinking blood takes your turn too, so healing mid-fight is a decision rather
than a free action. And `flee` heals the enemy: you cannot chip a boss down by
running away and coming back.

### Levelling

Killing something awards XP based on how tough it was. Level `N` costs `20 × N`
XP; each level grants **+5 max HP**, **+1 damage**, and a full heal on the spot.

## The map

ASCII, drawn every turn, showing only what you've found:

```
      [Smt]
        │
[Mkt]─[Sqr]─[For]─*B0*─[ ? ]
        │
      [Inn]
        │
      [Shr]
```

- `[Abc]` visited · `*Abc*` you are here · `[ ? ]` seen but not entered
- Cave labels carry their theme and depth: `B3` is three rooms into the Barrow
  Warrens, `E7!` is a deadly room deep in the Emberdeeps, `R!!` is a vault.

It is a **camera**, not the whole world: a fixed 7×5 window centred on you that
scrolls as you move, so the display never grows. Corridors running off the edge
are drawn as stubs, and `(map continues: ...)` names the directions where
explored rooms lie off-screen.

## Cheats, for testing

Type **`topkek`** at the prompt to open a debug console. Type it again to close
it. Cheats are never saved, and their verbs live outside the normal command
table, so turning them on cannot shadow or break a real command.

Once on, the screen says so and these work from anywhere:

| | |
|---|---|
| `give <item\|all>` | Any item — read **live** from the registry, so it never goes stale. `give` alone lists everything. |
| `tp <where>` | `boss1`–`boss3`, `town1`–`town3`, `shrine`, `forge`, `market`, `inn`, or any raw room key. |
| `hp <n\|max>` / `maxhp <n>` | Set current or maximum health. |
| `level <n>` | Jump to a level, applying every level-up on the way. |
| `gold <n>` / `echoes <n>` | Set coin, or echoes for testing the shrine. |
| `relic <name>` | Grant a relic permanently, as a boss kill would. |
| `spawn <tier>` | Put an enemy here at a tier you choose. |
| `wound <pct>` | Set the enemy's health % — `wound 20` to test `feed`. |
| `windup` | Force a telegraph, to test `guard`. |
| `kill` | Remove what's here, no rewards. |
| `chest <tier>` / `trader` | Drop a chest or a trader here. |
| `reveal` | Discover the whole map. |
| `god` | Take no damage. |
| `where` | Dump the room's raw state and the dungeon seed. |
| `cheats` | Show the list again. |

`give` and `tp` both build their options from the game in front of them — the
item catalogue comes straight from `content.ITEMS` and the teleport list is
derived from the world, so anything you add shows up without being registered
in two places.

## Commands

| Command | Aliases | What it does |
|---------|---------|--------------|
| `north` / `south` / `east` / `west` | `n` / `s` / `e` / `w` | Move between rooms. |
| `look` | `l` | Redraw the screen. |
| `map` | `m` | Show the discovered map. |
| `explore` | `x` | Search a dangerous area for enemies or coin. |
| `attack [enemy]` | `a` | Hit the enemy here (auto-targets; repeat with Enter). |
| `flee` | | Try to escape the current fight. |
| `guard` | `g` | Brace: halve the next blow, then hit harder. |
| `feed` | `f` | Drain a badly wounded enemy. Heals you; no XP. |
| `examine <thing>` | | Describe an item, relic, ware, or enemy. |
| `take` / `drop <item>` | `t` | Pick up / put down an item. |
| `open` | `o` | Force a chest and tip it onto the floor. |
| `use <item>` | `drink` | Drink blood. Bare `drink` picks one for you. |
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
| `menu.py` | Main menu, save slots, character creation, Options. |
| `chargen.py` | Origins and the point budget that keeps them equal. |
| `game.py` | Main loop, rendering, and every command action. |
| `models.py` | `Item`, `Enemy`, `Trader`, `Room`, `Player`, `Legacy`, `Settings`. |
| `legacy.py` | Turns a Legacy into the bonuses a new run starts with. |
| `world.py` | Builds the three holds, their roads, and their bounds. |
| `dungeon.py` | Generates one themed underdark from a seed. |
| `content.py` | Items, themes, bestiaries, shops, traders, rolls. |
| `map_render.py` | Draws the ASCII map camera. |
| `parser.py` | Turns typed text into commands. |
| `cheats.py` | The debug console (see below). |
| `saveload.py` | Saves, the Legacy file, scrambling, version tolerance. |
| `ui.py` | Terminal helpers and the big ASCII banners. |
| `testkit.py` | Shared test scaffolding (not collected: unittest globs `test*.py`). |
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

## Licence

**All rights reserved.** © 2026 sudokek.

The source is public so that it can be read, but **no licence is granted**: you
may not use, copy, modify, or redistribute it, in whole or in part, without
written permission. Reading it, learning from it, and asking questions about it
are all welcome — shipping it is not.

This is deliberate rather than an oversight. A commercial release may follow, so
the rights are being kept open. (GitHub's own terms still allow viewing and
forking within GitHub; nothing beyond that is permitted.)

If you want to use something here, ask.
