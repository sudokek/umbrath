"""Character creation: who you were before the blood took you.

An origin is a starting package -- stats, coin, and gear. They are meant to feel
very different and be worth the same, so the choice is about how you want to
play rather than which one is best.

That is enforced rather than eyeballed. Every bonus has a point cost (see
``COSTS``), each origin is built to the same ``BUDGET``, and a test fails the
build if any of them drifts off it. Adding a race is a matter of appending one
entry that totals the budget.
"""

from dataclasses import dataclass

from content import ITEMS
from ui import fit as _fit

# What one point of each bonus is worth. Attack and defense are scarce and
# compound with everything else, so they cost the most; HP and coin are cheap
# and plentiful. Items are priced at a tenth of their shop value.
COSTS = {
    "attack": 3.0,
    "defense": 3.0,
    "max_hp": 1.0,
    "gold": 0.1,
    "item": 0.1,
}

# Every origin is built to exactly this many points.
BUDGET = 24.0


@dataclass(frozen=True)
class Origin:
    """One playable background: a name, a story, and a starting package."""

    key: str
    name: str
    blurb: str
    # A short line for the chooser, where the full blurb will not fit. Falls
    # back to the blurb so a new origin can omit it.
    tagline: str = ""
    attack: int = 0
    max_hp: int = 0
    defense: int = 0
    gold: int = 0
    items: tuple[str, ...] = ()

    def cost(self) -> float:
        """Total point value of this package, for balance checking."""
        total = (
            self.attack * COSTS["attack"]
            + self.defense * COSTS["defense"]
            + self.max_hp * COSTS["max_hp"]
            + self.gold * COSTS["gold"]
        )
        total += sum(ITEMS[name].price * COSTS["item"] for name in self.items)
        return round(total, 3)

    def summary(self) -> str:
        """One-line description of what this origin actually gives you.

        Repeated items are counted rather than listed, so "3x vitae flask" does
        not run off the edge of the frame as "vitae flask, vitae flask, ...".
        """
        parts = []
        if self.attack:
            parts.append(f"{self.attack:+d} dmg")
        if self.defense:
            parts.append(f"{self.defense:+d} def")
        if self.max_hp:
            parts.append(f"{self.max_hp:+d} HP")
        if self.gold:
            parts.append(f"{self.gold:+d} coin")

        counts: dict[str, int] = {}
        for name in self.items:
            counts[name] = counts.get(name, 0) + 1
        for name, count in counts.items():
            parts.append(f"{count}x {name}" if count > 1 else name)

        return ", ".join(parts) if parts else "nothing but your teeth"


# Six ways to have died. Each totals BUDGET points -- see the test that proves it.
ORIGINS: dict[str, Origin] = {
    origin.key: origin
    for origin in [
        Origin(
            key="vaelric",
            tagline="Old money, buried where the title cannot reach.",
            name="Vaelric Scion",
            blurb=(
                "You were born to the house that owned this valley. The title is "
                "worthless now; the buried money is not."
            ),
            max_hp=4,
            gold=150,
            items=("bone dagger", "blood vial", "blood vial"),
        ),
        Origin(
            key="nachtkin",
            tagline="Raised feral. Hard to kill, harder to be near.",
            name="Nachtkin",
            blurb=(
                "You came up feral in the deep woods and were never taught to "
                "hide it. Hard to kill, and hard to be near."
            ),
            attack=2,
            max_hp=18,
        ),
        Origin(
            key="mourncaller",
            tagline="Studied the grave long before it took you.",
            name="Mourncaller",
            blurb=(
                "You studied the grave long before it took you. What answers when "
                "you call is not always what you asked for."
            ),
            attack=5,
            max_hp=4,
            gold=50,
        ),
        Origin(
            key="ironbound",
            tagline="Died in armour and declined to take it off.",
            name="Ironbound",
            blurb=(
                "You died in someone else's war, in someone else's armor, and "
                "simply declined to stop wearing it."
            ),
            defense=4,
            max_hp=8,
            gold=40,
        ),
        Origin(
            key="thirstborn",
            tagline="Turned last winter, and still starving.",
            name="Thirstborn",
            blurb=(
                "Turned last winter, and still starving. Fast, vicious, and far "
                "too easy to put down if the blood runs out."
            ),
            attack=4,
            max_hp=-6,
            gold=60,
            items=("vitae flask", "vitae flask", "vitae flask"),
        ),
        Origin(
            key="graveborn",
            tagline="Clawed up through your own grave-dirt.",
            name="Graveborn",
            blurb=(
                "A commoner who clawed up through their own grave-dirt. No "
                "lineage, no schooling, no particular weakness either."
            ),
            attack=2,
            defense=2,
            max_hp=6,
            gold=60,
        ),
    ]
}

DEFAULT_ORIGIN = "graveborn"

# What a character has before creation picks something -- and the graceful
# landing for a save naming an origin this version no longer ships. It grants
# nothing, so an unknown origin can never silently hand out someone else's kit.
UNBOUND = Origin(
    key="",
    name="Unbound",
    blurb="No history worth the telling. Yet.",
)


def find(key: str) -> Origin | None:
    """Look up an origin, or None if this version does not have it."""
    return ORIGINS.get(key)


def get(key: str) -> Origin:
    """Look up an origin for display, falling back to :data:`UNBOUND`.

    Save files name their origin as a string, so this must survive a file that
    references a background this version no longer has.
    """
    return ORIGINS.get(key, UNBOUND)


def listing(width: int = 62) -> list[str]:
    """The character-creation menu, two lines per origin.

    Deliberately compact: six origins at four lines each overflowed a standard
    24-row terminal and pushed the question off the top of the screen. Two lines
    each keeps the whole choice visible at once, which is the only way to
    actually compare them.
    """
    lines = []
    for number, origin in enumerate(ORIGINS.values(), start=1):
        head = f"  {number}. {origin.name:<13} "
        lines.append(head + _fit(origin.summary(), width - len(head)))
        lines.append(f"     {_fit(origin.tagline or origin.blurb, width - 5)}")
    return lines




def by_number(choice: str) -> Origin | None:
    """Resolve a menu choice: a number, a key, or a name. None if no match."""
    text = choice.strip().lower()
    if not text:
        return None

    if text.isdigit():
        index = int(text) - 1
        origins = list(ORIGINS.values())
        return origins[index] if 0 <= index < len(origins) else None

    for origin in ORIGINS.values():
        if origin.key == text or origin.name.lower() == text:
            return origin

    # Accept an unambiguous prefix, the same courtesy the command parser gives.
    matches = [o for o in ORIGINS.values() if o.name.lower().startswith(text)]
    return matches[0] if len(matches) == 1 else None
