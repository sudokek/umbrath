"""Define the core data models used by the game."""

from dataclasses import dataclass, field


@dataclass
class Item:
    """Store an item and any stats that make it useful.

    ``kind`` is one of "weapon", "armor", "potion", "relic", "blessing", or
    "misc". ``power`` means weapon damage, armor defense, or potion healing
    depending on ``kind``. ``price`` is the gold cost when sold in a shop.

    Relics and blessings carry a permanent bonus instead: ``effect`` names the
    stat they raise ("attack", "max_hp", "defense", or "gold") and ``power`` is
    how much.
    """

    name: str
    description: str = "An ordinary item."
    kind: str = "misc"
    power: int = 0
    price: int = 0
    effect: str = ""


@dataclass
class Enemy:
    """Store a creature the player can fight."""

    name: str
    hp: int = 5
    damage: int = 2
    gold: int = 0
    xp: int = 0
    description: str = "A hostile creature."
    boss: bool = False
    # Name of the relic this enemy drops when killed (bosses only).
    relic: str = ""


@dataclass
class Trader:
    """A wandering merchant who turns up somewhere and moves on.

    Traders carry a small, one-off stock: buying an item removes it for good,
    which is what makes running into one feel like luck rather than shopping.
    """

    name: str
    greeting: str = "Care to trade?"
    stock: list[Item] = field(default_factory=list)


@dataclass
class Room:
    """Store all data for one location in the world.

    ``x``/``y`` place the room on the map grid. ``label`` is the 3-character
    tag drawn on the map. ``danger`` above 0 marks a place where random enemies
    appear (1-3, local to the cave's theme). ``shop`` lists items for sale;
    ``can_sell`` allows selling here; ``inn`` allows resting; ``shrine`` allows
    spending echoes on permanent blessings.
    """

    key: str
    name: str
    description: str
    x: int = 0
    y: int = 0
    label: str = "?"
    exits: dict[str, str] = field(default_factory=dict)
    items: list[Item] = field(default_factory=list)
    enemies: list[Enemy] = field(default_factory=list)
    danger: int = 0
    shop: list[Item] = field(default_factory=list)
    can_sell: bool = False
    inn: bool = False
    shrine: bool = False
    trader: Trader | None = None
    # Which region (1-3) this room belongs to, and which cave theme styles it.
    region: int = 1
    theme: str = ""


# Leveling. Each level costs ``XP_PER_LEVEL * level`` XP and grants
# ``HP_PER_LEVEL`` max HP plus +1 damage on every hit, so training pays off
# even before you can afford the next weapon.
XP_PER_LEVEL = 20
HP_PER_LEVEL = 5
BASE_MAX_HP = 20


@dataclass
class Player:
    """Store the player's current stats, gear, and position.

    ``bonus_*`` fields hold everything carried over between runs -- relics
    looted from bosses and blessings bought at the shrine. They are recomputed
    from the :class:`Legacy` at the start of each run rather than being earned
    inside it.
    """

    name: str = "Hero"
    hp: int = 20
    max_hp: int = 20
    gold: int = 20
    level: int = 1
    xp: int = 0
    inventory: list[Item] = field(default_factory=list)
    weapon: Item | None = None
    armor: Item | None = None
    location: str = "square"
    # Permanent, cross-run bonuses.
    relics: list[Item] = field(default_factory=list)
    bonus_attack: int = 0
    bonus_max_hp: int = 0
    bonus_defense: int = 0

    def attack_power(self) -> int:
        """Damage dealt per hit (weapon or fists, plus level and relics)."""
        base = self.weapon.power if self.weapon else 2
        return base + self.level - 1 + self.bonus_attack

    def defense(self) -> int:
        """Damage blocked per hit (armor plus relics)."""
        base = self.armor.power if self.armor else 0
        return base + self.bonus_defense

    def xp_to_next(self) -> int:
        """XP required to reach the next level."""
        return XP_PER_LEVEL * self.level

    def add_xp(self, amount: int) -> int:
        """Award XP and apply any levels earned. Returns levels gained.

        Leveling up raises max HP and heals to full -- a reward you feel
        immediately in the middle of a fight.
        """
        self.xp += amount
        gained = 0
        while self.xp >= self.xp_to_next():
            self.xp -= self.xp_to_next()
            self.level += 1
            self.max_hp += HP_PER_LEVEL
            self.hp = self.max_hp
            gained += 1
        return gained


@dataclass
class Legacy:
    """The character, and everything of theirs that survives death.

    A run ends when you die, but the Legacy does not: your name and origin, the
    relics prised off bosses, and the blessings bought with echoes all carry
    into every future run. That is what makes the next attempt shorter than the
    last. The name is also the save-file name, so each character is their own
    ongoing story.
    """

    name: str = "Nameless"
    # Empty until character creation picks one; see ``chargen.UNBOUND``.
    origin: str = ""
    runs: int = 0
    victories: int = 0
    echoes: int = 0
    # Relic item names, looked up in ``content.ITEMS``.
    relics: list[str] = field(default_factory=list)
    # Blessing name -> how many times it has been bought.
    blessings: dict[str, int] = field(default_factory=dict)
    best_region: int = 1


@dataclass
class Settings:
    """Store user-facing game settings in one easy place."""

    auto_clear: bool = True
    show_room_items: bool = True
    show_room_exits: bool = True
    show_move_message: bool = True
    show_map: bool = True
    obfuscate_saves: bool = True
    typo_correction: bool = True
    require_prefix_length: bool = True
    min_command_prefix: int = 3
    allow_single_letter_aliases: bool = True
