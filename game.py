"""Run the main game loop and apply player actions.

Every action method does one thing: change state and leave a line in
``self.message``. The loop in ``run`` is the only place that redraws, so no
action has to remember to.

One consequence is worth knowing before reading an action: :meth:`Game.pick`
reports its own failure. An action that cannot find what the player named
returns without saying anything itself, because ``pick`` has already left the
reason in the message.

A *run* is one attempt: one world, one Player, from Greyfen to whatever
kills you. Dying ends the run and starts a new one -- but the
:class:`~models.Legacy` survives, so every attempt begins a little stronger than
the last.
"""

import os
import random
from dataclasses import asdict, replace

import cheats
import legacy as legacy_rules
import saveload
from content import (
    ENTER_ENCOUNTER_CHANCE,
    FEED_RATE,
    FEED_THRESHOLD,
    GUARD_REDUCTION,
    GUARD_RIPOSTE,
    WINDUP_CHANCE,
    WINDUP_MULTIPLIER,
    EXPLORE_ENEMY_CHANCE,
    EXPLORE_GOLD_CHANCE,
    FINAL_REGION,
    FLEE_SUCCESS_CHANCE,
    TRADER_BUY_RATE,
    TRADER_CHANCE,
    find_gold,
    make_item,
    make_shrine_stock,
    make_trader,
    roll,
    roll_damage,
    spawn_enemy,
)
from map_render import build_map
from models import Item, Legacy, Room, Settings
from parser import get_help_text, get_settings_help_text, match_target, parse_command
from ui import (
    bar,
    banner,
    center,
    clear_screen,
    paint,
    rule,
    set_color,
    set_unicode,
    wrap,
)
from world import build_world

DEFAULT_SAVE_PATH = "savegame.sav"
LEGACY_PATH = "legacy.sav"
REST_COST = 10
MAX_DUNGEON_SEED = 1_000_000


class Game:
    """Coordinate world data, player state, settings, and commands.

    ``legacy_path`` is the only thing that touches the disk on its own: when it
    is set (main.py sets it; tests do not), the Legacy is written every time a
    run ends, so progress between runs survives closing the game.
    """

    def __init__(
        self,
        legacy: Legacy | None = None,
        legacy_path: str | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Initialize settings, the Legacy, and the first run.

        ``settings`` comes from the main menu's Options screen when there is
        one; tests and direct callers get the defaults.
        """
        seed = os.environ.get("GAME_SEED")
        if seed is not None:
            # Optional hook so a whole playthrough can be made reproducible.
            random.seed(seed)

        self.settings = settings if settings is not None else Settings()
        set_color(self.settings.color)
        set_unicode(self.settings.line_drawing)
        self.legacy = legacy if legacy is not None else Legacy()
        self.legacy_path = legacy_path
        self.running = True
        # Debug console, opened by typing the word. Off by default, never
        # saved, and its verbs live outside parser.COMMANDS so the
        # command-parity invariant holds either way.
        self.cheats_on = False
        self.godmode = False
        self.message = ""
        # Set when a run ends: a full screen the loop shows, and pauses on,
        # before play resumes. Empty at every other moment.
        self.interlude: list[str] = []
        self.last_command = ""
        self.commands = self._build_commands()
        self.start_run()

    # -- runs --------------------------------------------------------------

    def start_run(self) -> None:
        """Begin a fresh attempt: new caves, new Player, same Legacy."""
        # A fresh world every run. The seed is saved, and regenerating from it
        # rebuilds the identical layout on load.
        self.dungeon_seed = random.randrange(MAX_DUNGEON_SEED)
        self.world: dict[str, Room] = build_world(self.dungeon_seed)
        self.player = legacy_rules.new_player(self.legacy)
        self.player.inventory.append(make_item("blood vial"))  # a starter potion
        self.discovered: set[str] = {self.player.location}
        self.bosses_killed = 0
        self.region_reached = 1

    def current_room(self) -> Room:
        """Return the room where the player currently stands."""
        return self.world[self.player.location]

    def region(self) -> int:
        """Which hold the player is standing in."""
        return self.current_room().region

    def end_run(self, victory: bool, epitaph: str) -> None:
        """Close out the run, bank the echoes, and start the next one."""
        earned = legacy_rules.echoes_earned(
            self.bosses_killed, self.region_reached, victory
        )
        self.legacy.runs += 1
        self.legacy.echoes += earned
        self.legacy.best_region = max(self.legacy.best_region, self.region_reached)
        self.legacy.best_level = max(self.legacy.best_level, self.player.level)
        self.legacy.hoard = self.player.gold
        if victory:
            self.legacy.victories += 1

        summary = [
            epitaph,
            "",
            f"Run {self.legacy.runs}: reached hold {self.region_reached}, "
            f"killed {self.bosses_killed} boss(es).",
            f"You carry {earned} echo(es) out of it. ({self.legacy.echoes} saved.)",
            "Spend them at the Shrine of Echoes, below the Greyfen inn.",
            "",
            f"The grave keeps most of it. You rise at level "
            f"{legacy_rules.inherited_level(self.legacy)} with "
            f"{legacy_rules.inherited_coin(self.legacy)} coin.",
        ]

        self._save_legacy()

        # Shown as a screen of its own before the next world is built. Without
        # this the banner was queued as an ordinary message and drawn by the
        # next redraw -- underneath a level-1 stat bar in Greyfen Square, so the
        # payoff for a twenty-level run read as a footnote to a new one.
        self.interlude = summary

        self.start_run()
        self.say("A new night, and the same road out of Greyfen.")

    def _save_legacy(self) -> None:
        """Persist the Legacy, if this game was given somewhere to put it."""
        if not self.legacy_path:
            return
        try:
            saveload.save_legacy(self.legacy, self.legacy_path)
        except OSError:
            # Losing the meta-save is not worth crashing a run over.
            pass

    # -- helpers -----------------------------------------------------------

    def discover(self, key: str) -> None:
        """Mark a room as seen so it appears on the map."""
        self.discovered.add(key)

    def say(self, *lines: str | None) -> None:
        """Set the message shown under the room, one entry per line.

        ``None`` entries are dropped, so a caller can pass an optional line
        without building the list by hand. Empty strings are kept: they are how
        the longer messages space themselves out.
        """
        self.message = "\n".join(line for line in lines if line is not None)

    def _find_by_name(self, items: list[Item], name: str) -> Item | None:
        """Return the first item whose name matches, or None."""
        for item in items:
            if item.name == name:
                return item
        return None

    def pick(self, raw_target: str, items: list[Item]) -> Item | None:
        """Match raw text to one of ``items``, reporting the failure itself.

        Returns None when nothing matched, having already left the reason in
        the message -- so every caller is `item = self.pick(...)` followed by
        `if item is None: return`, instead of unpacking a tuple seven times.
        """
        name, error = match_target(
            raw_target,
            [item.name for item in items],
            typo_correction=self.settings.typo_correction,
        )
        if error:
            self.say(error)
            return None
        return self._find_by_name(items, name)

    # -- rendering ---------------------------------------------------------

    def render(self) -> None:
        """Clear the screen and redraw the whole interface."""
        if self.settings.auto_clear:
            clear_screen()

        room = self.current_room()
        player = self.player
        weapon = player.weapon.name if player.weapon else "fists"
        armor = player.armor.name if player.armor else "none"

        print(rule("="))
        print(center(
            f"{paint(player.name, 'bold')}   Lv {player.level}   "
            f"{bar('HP', player.hp, player.max_hp)} {player.hp}/{player.max_hp}   "
            f"Gold {paint(str(player.gold), 'yellow')}"
        ))
        print(center(
            f"Weapon: {weapon} (ATK {player.attack_power()})   "
            f"Armor: {armor} (DEF {player.defense()})   "
            f"XP {player.xp}/{player.xp_to_next()}"
        ))
        vials = len(self.blood())
        print(center(
            f"Hold {room.region}/{FINAL_REGION}   "
            f"Blood {paint(str(vials), 'bright_red' if vials else 'dim')}   "
            f"Echoes {self.legacy.echoes}   Relics {len(player.relics)}"
        ))
        if self.cheats_on:
            print(center(paint(
                f"cheats on -- type CHEATS for the list, {cheats.WORD} to stop",
                "bright_magenta",
            )))
        print(rule("="))

        if self.settings.show_map:
            print()
            for line in build_map(self.world, self.discovered, player.location):
                print(line)

        print()
        print(rule("-"))
        print(paint(f"== {room.name} ==", "bold", "bright_cyan"))
        print(wrap(room.description, indent=""))

        if self.settings.show_room_items and room.items:
            print("You see:", paint(", ".join(i.name for i in room.items), "green"))

        if room.chest and not room.chest.opened:
            print(paint(f"A {room.chest.name} sits here, shut. (OPEN it.)", "bright_yellow"))

        if room.shrine:
            print("Blessings:", ", ".join(
                f"{i.name} ({i.price} echoes)" for i in make_shrine_stock()
            ))
        elif room.shop:
            print("For sale:", ", ".join(f"{i.name} ({i.price}g)" for i in room.shop))

        if room.trader:
            print(paint(f"* {room.trader.name} is here, packs open. "
                        "(TALK, or BUY/SELL)", "bright_magenta"))

        if room.inn:
            print(f"Rest here to fully heal for {REST_COST} gold.")

        if room.enemies:
            enemy = room.enemies[0]
            marker = "###" if enemy.boss else "!!"
            style = ("bold", "bright_red") if enemy.boss else ("red",)
            print(paint(f"{marker} {enemy.name.upper()} -- {enemy.hp} HP {marker}", *style))
            if enemy.winding_up:
                print(paint("   >> IT IS WINDING UP. GUARD, DRINK, OR RUN. <<", "bold", "bright_yellow"))
            elif self.can_feed_on(enemy):
                print(paint("   it is failing -- you could FEED", "bright_magenta"))

        if self.settings.show_room_exits:
            print("Exits:", ", ".join(room.exits.keys()))

        hint = self._hint()
        if hint:
            print(paint(hint, "bright_yellow"))

        print(rule("-"))

        if self.message:
            print(self.message)
            self.message = ""

    def _hint(self) -> str | None:
        """A nudge when the player is in trouble and has an answer to hand.

        Only shown when it is actionable: badly hurt with blood in the pack, or
        badly hurt with none and standing somewhere that sells it.
        """
        player = self.player
        if player.hp > player.max_hp * 0.4:
            return None
        if self.blood():
            return "You are badly hurt. Type DRINK to open a vial."
        if self.current_room().shop:
            return "You are badly hurt, and out of blood. BUY some."
        return "You are badly hurt, with nothing to drink. Retreat to a hold."

    # -- movement & encounters --------------------------------------------

    def _regroup(self, room: Room) -> None:
        """Let a room's enemies recover once the player is no longer in it.

        Without this the dominant strategy against anything big is to swing
        once, walk out, walk back, and repeat: enemy HP lived in the room and
        nothing ever restored it, so every boss could be chipped down for free
        by a player with patience and no gear.
        """
        for enemy in room.enemies:
            if enemy.max_hp:
                enemy.hp = enemy.max_hp

    def _maybe_encounter_on_enter(self) -> str | None:
        """Possibly spawn an enemy, or a trader, on entering a room."""
        room = self.current_room()

        if room.danger > 0 and not room.enemies and roll() < ENTER_ENCOUNTER_CHANCE:
            enemy = spawn_enemy(room.theme, room.danger)
            room.enemies.append(enemy)
            return f"A {enemy.name} lunges from the shadows!"

        if self._trader_may_appear(room) and roll() < TRADER_CHANCE:
            room.trader = make_trader(room.region)
            return f"{room.trader.name}, a wandering trader, has stopped here."

        return None

    def _trader_may_appear(self, room: Room) -> bool:
        """Traders turn up on quiet ground, never in a shop or a fight."""
        return not (room.enemies or room.trader or room.shop or room.shrine or room.inn)

    def move(self, direction: str) -> None:
        """Move the player if the way is clear and the direction exists."""
        room = self.current_room()

        if room.enemies:
            blocker = room.enemies[0]
            if blocker.boss:
                self.say(
                    f"The {blocker.name} fills the doorway. There is no way past "
                    "it but through."
                )
            else:
                self.say(f"The {blocker.name} blocks your path! Attack it or flee.")
            return

        if direction not in room.exits:
            self.say(f"You can't go {direction} from here.")
            return

        # Traders do not wait around: leave, and they have moved on.
        room.trader = None

        self._regroup(room)
        self.player.location = room.exits[direction]
        self.discover(self.player.location)
        self.region_reached = max(self.region_reached, self.region())

        moved = f"You go {direction}." if self.settings.show_move_message else None
        self.say(moved, self._maybe_encounter_on_enter())

    def explore(self) -> None:
        """Actively search a dangerous room for enemies or loot."""
        room = self.current_room()

        if room.danger == 0:
            self.say("There is nothing dangerous to explore here.")
            return

        if room.enemies:
            self.say(f"Deal with the {room.enemies[0].name} first!")
            return

        chance = roll()
        if chance < EXPLORE_ENEMY_CHANCE:
            enemy = spawn_enemy(room.theme, room.danger)
            room.enemies.append(enemy)
            self.say(f"You disturb a {enemy.name}! It attacks!")
        elif chance < EXPLORE_GOLD_CHANCE:
            found = find_gold(room.danger, room.region)
            self.player.gold += found
            self.say(f"You scavenge {found} gold from the rubble.")
        else:
            self.say("You search the dark but find nothing.")

    # -- combat ------------------------------------------------------------

    def _award_xp(self, amount: int) -> list[str]:
        """Grant XP and describe any levels gained."""
        if not self.player.add_xp(amount):
            return []
        return [
            f"You reach level {self.player.level}! "
            f"Max HP is now {self.player.max_hp}, and you feel fully restored."
        ]

    def attack_target(self, raw_target: str) -> None:
        """Strike the enemy in the room. Repeatable and auto-targeted."""
        room = self.current_room()
        if not room.enemies:
            self.say("There is nothing here to attack.")
            return

        enemy = room.enemies[0]
        weapon = self.player.weapon.name if self.player.weapon else "fists"

        power = self.player.attack_power()
        riposte = ""
        if self.player.guarding:
            # The guard was never spent, so the opening it bought is still here.
            self.player.guarding = False
            power = int(power * GUARD_RIPOSTE)
            riposte = "Out of your guard, "

        damage, critical = roll_damage(power)
        enemy.hp -= damage
        opener = riposte or ("A critical strike! " if critical else "")
        lines = [
            f"{opener}You hit the {enemy.name} with your {weapon} for {damage} damage."
        ]

        if enemy.hp <= 0:
            self._kill(room, enemy, lines)
            return

        lines.append(self._enemy_strikes(enemy))

        if self.player.hp <= 0:
            self._die(enemy, lines)
            return

        self.say(*lines)

    def _kill(self, room: Room, enemy, lines: list[str]) -> None:
        """Resolve an enemy's death: loot, XP, and any boss consequences."""
        room.enemies.remove(enemy)
        self.player.gold += enemy.gold
        lines.append(
            f"The {enemy.name} falls! You loot {enemy.gold} gold "
            f"and gain {enemy.xp} XP."
        )
        lines.extend(self._award_xp(enemy.xp))

        if not enemy.boss:
            self.say(*lines)
            return

        self.bosses_killed += 1
        lines.append("")
        lines.extend(self._claim_relic(enemy.relic))

        if room.region >= FINAL_REGION:
            self._win(enemy, lines)
            return

        lines.append("")
        way = self._road_onward(room)
        lines.append(
            f"The way {way} is clear. A road leads out of the dark toward the "
            "next town."
            if way
            else "Something has changed. A way out of the dark stands open."
        )
        self.say(*lines)

    def _road_onward(self, room: Room) -> str | None:
        """Which exit of ``room`` leaves this region, if any."""
        for direction, target in room.exits.items():
            if self.world[target].region != room.region:
                return direction
        return None

    def _claim_relic(self, name: str) -> list[str]:
        """Take a boss's relic: applied now, and kept for every run after."""
        if not name:
            return []

        relic = make_item(name)

        # Relics are carried, not re-earned. new_player already folded every
        # relic in the Legacy into the bonus_* fields at the start of this run,
        # so applying it again on a re-kill made every replay quietly stronger
        # than the Legacy screen claimed.
        if name in self.legacy.relics:
            return [
                f"The {relic.name} you already carry answers the corpse.",
                "  Nothing new comes loose.",
            ]

        self.player.relics.append(relic)
        self.legacy.relics.append(name)
        self._apply_bonus(relic.effect, relic.power)
        self._save_legacy()

        return [
            f"You pry loose the {relic.name}.",
            f"  {relic.description}",
            "  It is yours for good -- death cannot take a relic.",
        ]

    def _apply_bonus(self, effect: str, power: int) -> None:
        """Apply a permanent stat bonus to the player standing here now."""
        player = self.player
        if effect == "attack":
            player.bonus_attack += power
        elif effect == "defense":
            player.bonus_defense += power
        elif effect == "max_hp":
            player.bonus_max_hp += power
            player.max_hp += power
            player.hp += power
        elif effect == "gold":
            player.gold += power

    def _enemy_strikes(self, enemy) -> str:
        """Apply one hit from ``enemy`` to the player and describe it.

        Three things can happen, and which one is the whole reason a fight has
        turns in it: the enemy winds up (costing it this turn but promising a
        heavy blow), it lands a wind-up it started, or it hits normally.
        """
        if enemy.winding_up:
            enemy.winding_up = False
            damage, critical = roll_damage(int(enemy.damage * WINDUP_MULTIPLIER))
            opener = "The blow lands like a falling wall! "
        elif not enemy.boss and roll() < WINDUP_CHANCE:
            enemy.winding_up = True
            return (
                f"The {enemy.name} draws back for something heavy. "
                "(GUARD, or get out of the way.)"
            )
        else:
            damage, critical = roll_damage(enemy.damage)
            opener = "A vicious blow! " if critical else ""

        if self.godmode:
            return f"The {enemy.name} strikes, and it does not matter."

        incoming = max(1, damage - self.player.defense())
        guarded = ""
        if self.player.guarding:
            self.player.guarding = False
            incoming = max(1, int(incoming * GUARD_REDUCTION))
            guarded = " You take it on your guard."

        self.player.hp -= incoming
        return f"{opener}The {enemy.name} strikes for {incoming} damage.{guarded}"

    def guard(self) -> None:
        """Brace for the next blow, and hit harder once it has landed."""
        room = self.current_room()
        if not room.enemies:
            self.say("There is nothing here to guard against.")
            return

        enemy = room.enemies[0]
        self.player.guarding = True
        lines = ["You set yourself, and wait."]
        lines.append(self._enemy_strikes(enemy))

        if self.player.hp <= 0:
            self._die(enemy, lines)
            return
        self.say(*lines)

    def can_feed_on(self, enemy) -> bool:
        """Is this enemy weak enough to drain?"""
        return bool(enemy.max_hp) and enemy.hp <= enemy.max_hp * FEED_THRESHOLD

    def feed(self) -> None:
        """Drain a badly wounded enemy: it dies, you heal, you gain no XP.

        This is the one decision every fight ends on. Finishing a thing with the
        blade pays experience; drinking it pays health. You cannot have both.
        """
        room = self.current_room()
        if not room.enemies:
            self.say("There is nothing here to feed on.")
            return

        enemy = room.enemies[0]
        if not self.can_feed_on(enemy):
            self.say(
                f"The {enemy.name} is still too strong to hold still.",
                f"Wear it down below {int(FEED_THRESHOLD * 100)}% first.",
            )
            return

        healed = min(
            int(enemy.max_hp * FEED_RATE), self.player.max_hp - self.player.hp
        )
        self.player.hp += healed
        room.enemies.remove(enemy)
        self.player.gold += enemy.gold

        self.say(
            f"You take the {enemy.name} by the throat and drink.",
            f"It goes limp. You recover {healed} HP and take {enemy.gold} coin.",
            "No experience -- that was a meal, not a fight.",
        )

    def _die(self, enemy, lines: list[str]) -> None:
        """End the run in defeat."""
        self.player.hp = 0
        epitaph = "\n".join(
            lines
            + [
                "",
                *banner("YOU DIED"),
                "",
                f"The {enemy.name} finishes you in the dark.",
            ]
        )
        self.end_run(victory=False, epitaph=epitaph)

    def _win(self, enemy, lines: list[str]) -> None:
        """End the run in victory -- the only ending this world has.

        The villain is named from the thing that actually died. Hard-coding it
        is how the ending came to announce "the Sunless King", a boss this game
        has not had since the reskin.
        """
        epitaph = "\n".join(
            lines
            + [
                "",
                *banner("YOU WIN"),
                "",
                f"The {enemy.name.title()} is dead, and the deep is quiet for the",
                "first time in living memory. You climb back toward the light.",
            ]
        )
        self.end_run(victory=True, epitaph=epitaph)

    def _retreat_destination(self, room: Room) -> str | None:
        """Pick the safest neighbouring room to retreat into.

        Prefers calmer rooms, then ones already on your map, then whichever
        lies furthest back toward town. Rooms in another region are never
        offered: fleeing must not carry you past a boss you did not beat.
        """
        neighbors = [
            self.world[key]
            for key in room.exits.values()
            if self.world[key].region == room.region
        ]
        if not neighbors:
            return None
        neighbors.sort(
            key=lambda other: (
                other.danger,
                0 if other.key in self.discovered else 1,
                other.x,
                other.key,
            )
        )
        return neighbors[0].key

    def flee(self) -> None:
        """Try to break away from a fight. Failure costs you a free hit."""
        room = self.current_room()
        if not room.enemies:
            self.say("There is nothing to flee from.")
            return

        enemy = room.enemies[0]
        destination = self._retreat_destination(room)
        if destination is None:
            self.say("There is nowhere to run!")
            return

        if roll() >= FLEE_SUCCESS_CHANCE:
            lines = [f"You turn to run, but the {enemy.name} is faster."]
            lines.append(self._enemy_strikes(enemy))
            if self.player.hp <= 0:
                self._die(enemy, lines)
                return
            self.say(*lines)
            return

        # The enemy is left alive and in place -- fleeing buys distance, not a
        # win, and it recovers while you are gone.
        self._regroup(room)
        self.player.location = destination
        self.discover(destination)
        self.say(
            f"You break away from the {enemy.name} and retreat to "
            f"{self.world[destination].name}. It is still back there, waiting."
        )

    # -- items & gear ------------------------------------------------------

    def open_chest(self) -> None:
        """Open the chest here, tipping everything in it onto the floor.

        Contents were rolled when the cave was built, from the drop table at
        this room's danger -- so what is inside is worth exactly as much as the
        walk it took to reach it.
        """
        room = self.current_room()
        chest = room.chest

        if chest is None:
            self.say("There is nothing here to open.")
            return
        if chest.opened:
            self.say(f"The {chest.name} is already open, and already empty.")
            return
        if room.enemies:
            self.say(f"Not with the {room.enemies[0].name} still standing.")
            return

        chest.opened = True
        room.items.extend(chest.contents)
        haul = [item.name for item in chest.contents]
        chest.contents = []

        self.say(
            f"You force the {chest.name}.",
            "Inside: " + (", ".join(haul) if haul else "nothing but dust"),
            "(TAKE what you want.)" if haul else None,
        )

    def take_item(self, raw_target: str) -> None:
        """Pick up an item from the current room."""
        room = self.current_room()
        item = self.pick(raw_target, room.items)
        if item is None:
            return
        room.items.remove(item)
        self.player.inventory.append(item)
        self.say(f"You take the {item.name}.")

    def _unequip_if_held(self, item: Item) -> None:
        """Clear a gear slot when the item filling it leaves the inventory."""
        if self.player.weapon is item:
            self.player.weapon = None
        if self.player.armor is item:
            self.player.armor = None

    def drop_item(self, raw_target: str) -> None:
        """Drop an item from the inventory into the current room."""
        item = self.pick(raw_target, self.player.inventory)
        if item is None:
            return
        self.player.inventory.remove(item)
        self._unequip_if_held(item)
        self.current_room().items.append(item)
        self.say(f"You drop the {item.name}.")

    def examine_target(self, raw_target: str) -> None:
        """Describe an item, relic, trader, or enemy you can see."""
        room = self.current_room()
        descriptions: dict[str, str] = {}
        for item in room.items:
            descriptions[item.name] = item.description
        for item in self.player.inventory:
            descriptions.setdefault(item.name, item.description)
        for item in self.player.relics:
            descriptions.setdefault(item.name, item.description)
        if room.trader:
            for item in room.trader.stock:
                descriptions.setdefault(item.name, item.description)
        for enemy in room.enemies:
            descriptions[enemy.name] = enemy.description

        name, error = match_target(
            raw_target,
            list(descriptions),
            typo_correction=self.settings.typo_correction,
        )
        self.say(error if error else descriptions[name])

    def blood(self) -> list[Item]:
        """Everything in the pack that can be drunk, weakest first."""
        return sorted(
            (item for item in self.player.inventory if item.kind == "potion"),
            key=lambda item: item.power,
        )

    def _best_blood(self) -> Item | None:
        """The vial to drink right now: the smallest that would not be wasted.

        Drinking an ichor of ages to top up three points is a waste, so this
        reaches for the weakest one that covers the wound, and only falls back
        to the strongest when nothing covers it.
        """
        missing = self.player.max_hp - self.player.hp
        carried = self.blood()
        if not carried:
            return None
        enough = [item for item in carried if item.power >= missing]
        return enough[0] if enough else carried[-1]

    def use_item(self, raw_target: str) -> None:
        """Drink blood. With no target, pick the vial that best fits the wound."""
        if not raw_target.strip():
            if self.player.hp >= self.player.max_hp:
                self.say("You are whole. Save it for when you are not.")
                return
            item = self._best_blood()
            if item is None:
                self.say(
                    "You carry nothing to drink.",
                    "Blood is sold at the night market in any hold.",
                )
                return
        else:
            item = self.pick(raw_target, self.player.inventory)
            if item is None:
                return

        if item.kind != "potion":
            self.say(f"Nothing happens when you use the {item.name}.")
            return

        healed = min(item.power, self.player.max_hp - self.player.hp)
        self.player.hp += healed
        self.player.inventory.remove(item)

        if healed > 0:
            lines = [f"You drink the {item.name} and recover {healed} HP."]
        else:
            lines = [f"You drink the {item.name}, but you are already full."]

        # Drinking takes the turn. Without this you could out-heal anything in
        # the game for free, and no fight could ever be lost while blood held.
        room = self.current_room()
        if room.enemies:
            lines.append(self._enemy_strikes(room.enemies[0]))
            if self.player.hp <= 0:
                self._die(room.enemies[0], lines)
                return

        self.say(*lines)

    def equip_item(self, raw_target: str) -> None:
        """Equip a weapon or armor from the inventory."""
        item = self.pick(raw_target, self.player.inventory)
        if item is None:
            return

        if item.kind == "weapon":
            self.player.weapon = item
            self.say(f"You equip the {item.name}. (ATK {self.player.attack_power()})")
        elif item.kind == "armor":
            self.player.armor = item
            self.say(f"You equip the {item.name}. (DEF {self.player.defense()})")
        else:
            self.say(f"You can't equip the {item.name}.")

    # -- economy -----------------------------------------------------------

    def talk(self, raw_target: str) -> None:
        """Hear out the trader standing here."""
        trader = self.current_room().trader
        if not trader:
            self.say("There is nobody here to talk to.")
            return

        lines = [f'{trader.name}: "{trader.greeting}"', ""]
        if trader.stock:
            lines.append("On offer:")
            for item in trader.stock:
                lines.append(f"- {item.name}: {item.price} gold  ({item.description})")
            lines.append("")
            lines.append("They only carry the one of each, and they do not wait.")
        else:
            lines.append("Their packs are empty. You have already cleaned them out.")
        self.say(*lines)

    def buy_item(self, raw_target: str) -> None:
        """Buy from a shop, a shrine, or a wandering trader."""
        room = self.current_room()

        if room.chest and not room.chest.opened:
            print(paint(f"A {room.chest.name} sits here, shut. (OPEN it.)", "bright_yellow"))

        if room.shrine:
            self._buy_blessing(raw_target)
            return

        stock = list(room.shop)
        trader = room.trader
        if trader:
            stock += trader.stock

        if not stock:
            self.say("There is nothing to buy here.")
            return

        if not raw_target.strip():
            lines = ["For sale:"]
            for item in stock:
                lines.append(f"- {item.name}: {item.price} gold  ({item.description})")
            self.say(*lines)
            return

        item = self.pick(raw_target, stock)
        if item is None:
            return

        if self.player.gold < item.price:
            self.say(
                f"The {item.name} costs {item.price} gold; you have {self.player.gold}."
            )
            return

        self.player.gold -= item.price
        # Identity, not equality: a shop and a trader can carry items that
        # compare equal, and `in` would take the wrong one off the trader.
        from_trader = trader is not None and any(item is s for s in trader.stock)
        if from_trader:
            # A trader's stock is one-of-a-kind: buying it takes it off the road.
            trader.stock.remove(item)
            self.player.inventory.append(item)
            self.say(f"You buy the {item.name} from {trader.name} for {item.price} gold.")
        else:
            self.player.inventory.append(replace(item))
            self.say(f"You buy the {item.name} for {item.price} gold.")

    def _buy_blessing(self, raw_target: str) -> None:
        """Spend echoes at the shrine on a permanent upgrade."""
        stock = make_shrine_stock()

        if not raw_target.strip():
            lines = [f"You have {self.legacy.echoes} echo(es). The shrine offers:"]
            for item in stock:
                owned = self.legacy.blessings.get(item.name, 0)
                have = f"  (owned x{owned})" if owned else ""
                lines.append(f"- {item.name}: {item.price} echoes  {item.description}{have}")
            self.say(*lines)
            return

        item = self.pick(raw_target, stock)
        if item is None:
            return

        if self.legacy.echoes < item.price:
            self.say(
                f"The {item.name} blessing costs {item.price} echoes; "
                f"you have {self.legacy.echoes}. Echoes come from finished runs."
            )
            return

        self.legacy.echoes -= item.price
        self.legacy.blessings[item.name] = self.legacy.blessings.get(item.name, 0) + 1
        self._apply_bonus(item.effect, item.power)
        self._save_legacy()
        self.say(
            f"The stones take your echoes. {item.description}",
            f"({self.legacy.echoes} echo(es) left.)",
        )

    def sell_item(self, raw_target: str) -> None:
        """Sell an item at a shop that buys, or to a trader."""
        room = self.current_room()
        trader = room.trader

        if not room.can_sell and not trader:
            self.say("You can't sell anything here.")
            return

        item = self.pick(raw_target, self.player.inventory)
        if item is None:
            return

        # Traders know what deep loot is worth, and pay accordingly.
        rate = TRADER_BUY_RATE if trader and not room.can_sell else 0.5
        price = max(1, int(item.price * rate))

        self.player.inventory.remove(item)
        self._unequip_if_held(item)
        self.player.gold += price
        buyer = f" to {trader.name}" if trader and not room.can_sell else ""
        self.say(f"You sell the {item.name}{buyer} for {price} gold.")

    def rest(self) -> None:
        """Pay to fully heal at an inn."""
        room = self.current_room()
        if not room.inn:
            self.say("You can only rest at the Inn.")
        elif self.player.hp >= self.player.max_hp:
            self.say("You are already fully rested.")
        elif self.player.gold < REST_COST:
            self.say(f"Resting costs {REST_COST} gold; you have {self.player.gold}.")
        else:
            self.player.gold -= REST_COST
            self.player.hp = self.player.max_hp
            self.say(f"You rest by the fire and recover fully. (-{REST_COST} gold)")

    # -- information -------------------------------------------------------

    def show_inventory(self) -> None:
        """Display the player's inventory."""
        if self.player.inventory:
            self.say("Inventory: " + ", ".join(
                item.name for item in self.player.inventory
            ))
        else:
            self.say("Your inventory is empty.")

    def show_stats(self) -> None:
        """Display the player's current stats and gear."""
        player = self.player
        weapon = player.weapon.name if player.weapon else "fists"
        armor = player.armor.name if player.armor else "none"
        relics = ", ".join(item.name for item in player.relics) or "none"
        self.say(
            f"{player.name}\n"
            f"Level: {player.level}  ({player.xp}/{player.xp_to_next()} XP)\n"
            f"HP:    {player.hp}/{player.max_hp}\n"
            f"Gold:  {player.gold}\n"
            f"Weapon: {weapon} (ATK {player.attack_power()})\n"
            f"Armor:  {armor} (DEF {player.defense()})\n"
            f"Relics: {relics}\n"
            f"Where: {self.current_room().name} (hold {self.region()})\n"
            f"Items: {len(player.inventory)}"
        )

    def show_legacy(self) -> None:
        """Display everything that survives death."""
        self.say(*legacy_rules.describe(self.legacy))

    def show_map(self) -> None:
        """Force the map to display (useful when show_map is off)."""
        if not self.settings.show_map:
            self.say(*build_map(self.world, self.discovered, self.player.location))

    def show_help(self) -> None:
        """Display the general command list."""
        self.say(get_help_text())

    # -- persistence -------------------------------------------------------

    def default_save_path(self) -> str:
        """Where ``save`` writes when given no filename.

        Keyed to the character's name, so two characters never overwrite each
        other's run.
        """
        if self.legacy.name and self.legacy.name != Legacy.name:
            return saveload.character_path(self.legacy.name, "_run")
        return DEFAULT_SAVE_PATH

    def save_game(self, raw_target: str) -> None:
        """Save the current game to a file."""
        path = raw_target.strip() or self.default_save_path()
        try:
            written = saveload.save_game(self, path)
            self.say(f"Game saved to {written}.")
        except PermissionError:
            target = saveload.resolve_save_path(path)
            self.say(
                f"Could not save: permission denied writing {target}.",
                "Close the file if it's open elsewhere, or try a different name "
                "like: save mygame.sav",
            )
        except OSError as error:
            self.say(f"Could not save game: {error}")

    def load_game(self, raw_target: str) -> None:
        """Load a saved game from a file."""
        path = raw_target.strip() or DEFAULT_SAVE_PATH
        try:
            loaded = saveload.load_game(self, path)
            self.say(f"Game loaded from {loaded}.")
        except FileNotFoundError:
            self.say(f"No save file found at {saveload.resolve_save_path(path)}.")
        except (OSError, ValueError) as error:
            self.say(f"Could not load game: {error}")

    # -- settings ----------------------------------------------------------

    def show_settings(self) -> None:
        """Display all current settings and settings usage."""
        lines = ["Settings:"]
        for name, value in asdict(self.settings).items():
            lines.append(f"- {name}: {value}")
        lines.append("")
        lines.append(get_settings_help_text())
        self.say(*lines)

    def set_setting(self, name: str, value: str) -> None:
        """Set one setting by name from a string value."""
        if not hasattr(self.settings, name):
            self.say(f"Unknown setting: {name}")
            return

        current_value = getattr(self.settings, name)

        if isinstance(current_value, bool):
            normalized = value.lower()
            if normalized in {"on", "true", "yes", "1"}:
                setattr(self.settings, name, True)
            elif normalized in {"off", "false", "no", "0"}:
                setattr(self.settings, name, False)
            else:
                self.say(f"Invalid value for {name}: {value}")
                return
        elif isinstance(current_value, int):
            try:
                new_value = int(value)
            except ValueError:
                self.say(f"Invalid value for {name}: {value}")
                return
            if name == "min_command_prefix" and not 1 <= new_value <= 10:
                self.say("min_command_prefix must be between 1 and 10.")
                return
            setattr(self.settings, name, new_value)
        else:
            setattr(self.settings, name, value)

        self.say(f"{name} set to {getattr(self.settings, name)}")

    def toggle_setting(self, name: str) -> None:
        """Flip one boolean setting by name."""
        if not hasattr(self.settings, name):
            self.say(f"Unknown setting: {name}")
            return

        current_value = getattr(self.settings, name)
        if not isinstance(current_value, bool):
            self.say(f"{name} is not a toggle.")
            return

        setattr(self.settings, name, not current_value)
        self.say(f"{name} set to {getattr(self.settings, name)}")

    def handle_settings_command(self, target: str) -> None:
        """Handle settings subcommands."""
        parts = target.split()
        if not parts:
            self.show_settings()
        elif parts[0] == "toggle" and len(parts) == 2:
            self.toggle_setting(parts[1])
        elif parts[0] == "set" and len(parts) >= 3:
            self.set_setting(parts[1], " ".join(parts[2:]))
        else:
            self.say(get_settings_help_text())

    def quit_game(self) -> None:
        """Stop the main loop."""
        self.running = False
        self._save_legacy()
        print("Goodbye.")

    # -- dispatch & loop ---------------------------------------------------

    def _build_commands(self) -> dict:
        """Map every verb the parser knows to the action that performs it.

        Keys here must match ``parser.COMMANDS`` exactly -- a test enforces it,
        so a new command can never be typed but not handled (or vice versa).
        Every handler takes the target text, even when it ignores it.
        """
        return {
            "north": lambda target: self.move("north"),
            "south": lambda target: self.move("south"),
            "east": lambda target: self.move("east"),
            "west": lambda target: self.move("west"),
            "look": lambda target: None,  # the redraw below is the whole action
            "examine": self.examine_target,
            "take": self.take_item,
            "open": lambda target: self.open_chest(),
            "drop": self.drop_item,
            "use": self.use_item,
            "equip": self.equip_item,
            "attack": self.attack_target,
            "flee": lambda target: self.flee(),
            "guard": lambda target: self.guard(),
            "feed": lambda target: self.feed(),
            "explore": lambda target: self.explore(),
            "talk": self.talk,
            "buy": self.buy_item,
            "sell": self.sell_item,
            "rest": lambda target: self.rest(),
            "inventory": lambda target: self.show_inventory(),
            "stats": lambda target: self.show_stats(),
            "legacy": lambda target: self.show_legacy(),
            "map": lambda target: self.show_map(),
            "save": self.save_game,
            "load": self.load_game,
            "help": lambda target: self.show_help(),
            "settings": self.handle_settings_command,
            "quit": lambda target: self.quit_game(),
        }

    def handle_command(self, text: str) -> None:
        """Parse input and dispatch it to the correct game action.

        Cheat verbs are tried first and never reach the parser, so turning the
        debug console on cannot shadow or break a real command.
        """
        cheated = cheats.handle(self, text)
        if cheated is not None:
            self.say(*cheated)
            return

        verb, target, error = parse_command(
            text,
            min_command_prefix=self.settings.min_command_prefix,
            require_prefix_length=self.settings.require_prefix_length,
            allow_single_letter_aliases=self.settings.allow_single_letter_aliases,
            typo_correction=self.settings.typo_correction,
        )

        if error:
            self.say(error)
            return

        action = self.commands.get(verb)
        if action is None:
            self.say(f"Invalid command: {text}")
            return

        action(target)

    def _show_interlude(self) -> None:
        """Draw the end of a run as its own screen, and wait to be read."""
        if self.settings.auto_clear:
            clear_screen()
        print(rule("="))
        for line in self.interlude:
            print(line)
        print(rule("="))
        self.interlude = []
        try:
            input("\nPress Enter to rise again. ")
        except (EOFError, KeyboardInterrupt):
            self.running = False

    def run(self) -> None:
        """Start the game and keep reading commands until quit."""
        self.render()

        while self.running:
            try:
                raw = input("\n> ")
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye.")
                self._save_legacy()
                break

            command = raw.strip()
            if not command:
                # Empty Enter repeats the last command -- handy for grinding.
                if not self.last_command:
                    continue
                command = self.last_command
            else:
                self.last_command = command

            self.handle_command(command)

            if self.interlude:
                self._show_interlude()

            # One redraw per command, here and nowhere else.
            if self.running:
                self.render()
