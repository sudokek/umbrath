"""Parse player input using unique prefix matching and typo tolerance."""

from difflib import get_close_matches

COMMANDS = {
    "north": {"help": "Move north."},
    "south": {"help": "Move south."},
    "east": {"help": "Move east."},
    "west": {"help": "Move west."},
    "look": {"help": "Redraw the current room."},
    "inventory": {"help": "Show what you are carrying."},
    "examine": {"help": "Inspect something more closely."},
    "take": {"help": "Pick up an item."},
    "drop": {"help": "Drop an item."},
    "use": {"help": "Drink blood to heal. Bare 'drink' picks one for you."},
    "equip": {"help": "Equip a weapon or armor."},
    "attack": {"help": "Attack the enemy here (repeat with Enter)."},
    "flee": {"help": "Escape combat, retreating to safety."},
    "explore": {"help": "Search a dangerous area for enemies or loot."},
    "talk": {"help": "Speak to a wandering trader."},
    "buy": {"help": "Buy from a shop, trader, or shrine (no item = list)."},
    "sell": {"help": "Sell an item where trading is allowed."},
    "rest": {"help": "Pay to fully heal at an inn."},
    "stats": {"help": "Show player stats and gear."},
    "legacy": {"help": "Show relics, blessings, and echoes kept between runs."},
    "map": {"help": "Show the map of discovered areas."},
    "save": {"help": "Save your game to a file."},
    "load": {"help": "Load a saved game from a file."},
    "help": {"help": "Show this help list."},
    "settings": {"help": "View or change game settings."},
    "quit": {"help": "Exit the game."},
}

MANUAL_ALIASES = {
    "n": "north",
    "s": "south",
    "e": "east",
    "w": "west",
    "i": "inventory",
    "l": "look",
    "t": "take",
    "a": "attack",
    "x": "explore",
    "m": "map",
    "r": "rest",
    "h": "help",
    "q": "quit",
}

# Whole-word synonyms that resolve to a real command without taking part in
# prefix matching (so "exit" does not fight "examine" for the "ex" prefix).
SYNONYMS = {
    "exit": "quit",
    # You are a vampire; what you use is blood. "drink" is the word players
    # reach for, and bare "drink" heals with the best-suited vial you carry.
    "drink": "use",
}


def get_help_text() -> str:
    """Build the general help screen from command metadata."""
    lines = ["Commands:"]
    reverse_aliases = {}

    for alias, command in MANUAL_ALIASES.items():
        reverse_aliases.setdefault(command, []).append(alias)

    for synonym, command in SYNONYMS.items():
        reverse_aliases.setdefault(command, []).append(synonym)

    for name in sorted(COMMANDS):
        aliases = reverse_aliases.get(name, [])
        alias_text = f" ({', '.join(aliases)})" if aliases else ""
        help_text = COMMANDS[name].get("help", "No description.")
        lines.append(f"- {name}{alias_text}: {help_text}")

    return "\n".join(lines)


def get_settings_help_text() -> str:
    """Build help text only for the settings command."""
    lines = [
        "Settings usage:",
        "- settings",
        "- settings toggle auto_clear",
        "- settings set min_command_prefix 2",
    ]
    return "\n".join(lines)


def normalize_text(text: str) -> str:
    """Normalize raw input before parsing."""
    return " ".join(text.lower().strip().split())


def match_unique_prefix(
    text: str,
    choices: list[str] | set[str],
    *,
    min_length: int = 3,
    require_prefix_length: bool = True,
) -> tuple[str | None, str | None]:
    """Resolve text against choices using unique prefix matching."""
    choices = sorted(choices)

    if text in choices:
        return text, None

    if require_prefix_length and len(text) < min_length:
        return None, "too_short"

    matches = [choice for choice in choices if choice.startswith(text)]

    if len(matches) == 1:
        return matches[0], None

    if len(matches) > 1:
        return None, "ambiguous"

    return None, None


def fuzzy_match(
    word: str,
    choices: list[str] | set[str],
    *,
    enabled: bool = True,
    cutoff: float = 0.80,
) -> str | None:
    """Return one close match for a minor typo, if enabled."""
    if not enabled:
        return None

    matches = get_close_matches(word, list(choices), n=1, cutoff=cutoff)
    return matches[0] if matches else None


def parse_command(
    text: str,
    *,
    min_command_prefix: int = 3,
    require_prefix_length: bool = True,
    allow_single_letter_aliases: bool = True,
    typo_correction: bool = True,
) -> tuple[str, str, str | None]:
    """Parse input into verb, target text, and optional parse error."""
    text = normalize_text(text)
    if not text:
        return "", "", "Invalid command."

    parts = text.split(maxsplit=1)
    raw_verb = parts[0]
    target = parts[1] if len(parts) > 1 else ""

    if allow_single_letter_aliases and raw_verb in MANUAL_ALIASES:
        return MANUAL_ALIASES[raw_verb], target, None

    if raw_verb in SYNONYMS:
        return SYNONYMS[raw_verb], target, None

    verb, error = match_unique_prefix(
        raw_verb,
        COMMANDS.keys(),
        min_length=min_command_prefix,
        require_prefix_length=require_prefix_length,
    )
    if verb:
        return verb, target, None

    if error == "ambiguous":
        return "", target, f"Ambiguous command: {raw_verb}"

    if error == "too_short":
        return "", target, f"Command too short: {raw_verb}"

    typo_match = fuzzy_match(
        raw_verb,
        COMMANDS.keys(),
        enabled=typo_correction,
    )
    if typo_match:
        return typo_match, target, None

    return "", target, f"Invalid command: {raw_verb}"


def match_target(
    text: str,
    choices: list[str],
    *,
    typo_correction: bool = True,
) -> tuple[str | None, str | None]:
    """Resolve an item or target name from the local visible choices."""
    text = normalize_text(text)
    if not text:
        return None, "Missing target."

    if text in choices:
        return text, None

    # Choices come straight from an inventory, which can hold three of the same
    # vial. Without collapsing duplicates, carrying two blood vials made
    # `use vial` report itself as ambiguous with itself.
    choices = list(dict.fromkeys(choices))

    matches = [choice for choice in choices if choice.startswith(text)]

    # Items have two-word names, and the word players reach for is usually the
    # second one -- "vial", "flask", "sword". Without this, `use vial` failed
    # while `use blood` worked, which is not a distinction anyone should have to
    # learn.
    if not matches:
        matches = [
            choice
            for choice in choices
            if any(word.startswith(text) for word in choice.split())
        ]

    if len(matches) == 1:
        return matches[0], None

    if len(matches) > 1:
        return None, f"Ambiguous target: {text} ({', '.join(sorted(matches))})"

    typo_match = fuzzy_match(text, choices, enabled=typo_correction, cutoff=0.75)
    if typo_match:
        return typo_match, None

    return None, f"Target not found: {text}"
