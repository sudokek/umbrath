"""Unit tests for the command parser."""

import unittest

from parser import (
    COMMANDS,
    fuzzy_match,
    get_help_text,
    get_settings_help_text,
    match_target,
    match_unique_prefix,
    parse_command,
)


class ParseCommandTests(unittest.TestCase):
    """Cover the main verb-resolution paths of parse_command."""

    def test_exact_command(self):
        self.assertEqual(parse_command("north"), ("north", "", None))

    def test_unique_prefix(self):
        verb, _, error = parse_command("nor")
        self.assertEqual(verb, "north")
        self.assertIsNone(error)

    def test_verb_and_target_split(self):
        self.assertEqual(parse_command("take potion"), ("take", "potion", None))

    def test_single_letter_alias(self):
        verb, _, error = parse_command("n")
        self.assertEqual(verb, "north")
        self.assertIsNone(error)

    def test_gameplay_aliases(self):
        self.assertEqual(parse_command("a")[0], "attack")
        self.assertEqual(parse_command("m")[0], "map")
        self.assertEqual(parse_command("x")[0], "explore")
        self.assertEqual(parse_command("r")[0], "rest")

    def test_alias_disabled_is_too_short(self):
        verb, _, error = parse_command("n", allow_single_letter_aliases=False)
        self.assertEqual(verb, "")
        self.assertIn("too short", error.lower())

    def test_exit_synonym_resolves_to_quit(self):
        self.assertEqual(parse_command("exit"), ("quit", "", None))

    def test_empty_input(self):
        self.assertEqual(parse_command(""), ("", "", "Invalid command."))

    def test_prefix_too_short(self):
        verb, _, error = parse_command("no")
        self.assertEqual(verb, "")
        self.assertIn("too short", error.lower())

    def test_ambiguous_prefix(self):
        # "lo" matches both "look" and "load".
        verb, _, error = parse_command("lo", min_command_prefix=2)
        self.assertEqual(verb, "")
        self.assertIn("ambiguous", error.lower())

    def test_typo_is_corrected(self):
        verb, _, error = parse_command("eaxmine")
        self.assertEqual(verb, "examine")
        self.assertIsNone(error)

    def test_typo_correction_can_be_disabled(self):
        verb, _, error = parse_command("eaxmine", typo_correction=False)
        self.assertEqual(verb, "")
        self.assertIn("invalid", error.lower())


class MatchUniquePrefixTests(unittest.TestCase):
    """Cover the lower-level prefix matcher directly."""

    def test_exact_match_bypasses_length_rule(self):
        self.assertEqual(match_unique_prefix("go", ["go", "gone"]), ("go", None))

    def test_ambiguous_returns_marker(self):
        self.assertEqual(
            match_unique_prefix("g", ["go", "gone"], require_prefix_length=False),
            (None, "ambiguous"),
        )

    def test_no_match_returns_none(self):
        self.assertEqual(match_unique_prefix("zzz", ["go", "gone"]), (None, None))


class MatchTargetTests(unittest.TestCase):
    """Cover target (item/enemy name) resolution."""

    def test_exact(self):
        self.assertEqual(match_target("potion", ["potion"]), ("potion", None))

    def test_unique_prefix(self):
        self.assertEqual(match_target("pot", ["potion"]), ("potion", None))

    def test_ambiguous(self):
        name, error = match_target("s", ["sword", "shield"])
        self.assertIsNone(name)
        self.assertIn("ambiguous", error.lower())

    def test_typo(self):
        self.assertEqual(match_target("potin", ["potion"]), ("potion", None))

    def test_not_found(self):
        name, error = match_target("dragon", ["potion"])
        self.assertIsNone(name)
        self.assertIn("not found", error.lower())

    def test_missing_target(self):
        name, error = match_target("", ["potion"])
        self.assertIsNone(name)
        self.assertIn("missing", error.lower())


class TwoWordNameTests(unittest.TestCase):
    """Items have two-word names; players type whichever word is distinctive."""

    BLOOD = ["blood vial", "vitae flask", "heart's blood", "grave sword"]

    def test_the_second_word_matches(self):
        # Regression: matching was prefix-only on the whole name, so `use vial`
        # failed while `use blood` worked -- a distinction nobody should learn.
        self.assertEqual(match_target("vial", self.BLOOD)[0], "blood vial")
        self.assertEqual(match_target("flask", self.BLOOD)[0], "vitae flask")
        self.assertEqual(match_target("sword", self.BLOOD)[0], "grave sword")

    def test_the_first_word_still_matches(self):
        self.assertEqual(match_target("vitae", self.BLOOD)[0], "vitae flask")
        self.assertEqual(match_target("grave", self.BLOOD)[0], "grave sword")

    def test_a_whole_name_still_wins_outright(self):
        self.assertEqual(match_target("blood vial", self.BLOOD)[0], "blood vial")

    def test_duplicates_are_not_ambiguous_with_themselves(self):
        # Regression: carrying three of the same vial made `use vial` report
        # "Ambiguous target: blood vial, blood vial, blood vial".
        pack = ["blood vial", "blood vial", "blood vial"]
        self.assertEqual(match_target("vial", pack), ("blood vial", None))
        self.assertEqual(match_target("blood", pack), ("blood vial", None))

    def test_real_ambiguity_still_reports_the_candidates(self):
        name, error = match_target("b", ["blood vial", "bone dagger"])
        self.assertIsNone(name)
        self.assertIn("blood vial", error)
        self.assertIn("bone dagger", error)


class FuzzyMatchTests(unittest.TestCase):
    """Cover the typo-correction helper."""

    def test_matches_close_word(self):
        self.assertEqual(fuzzy_match("eaxmine", COMMANDS.keys()), "examine")

    def test_disabled_returns_none(self):
        self.assertIsNone(fuzzy_match("eaxmine", COMMANDS.keys(), enabled=False))


class HelpTextTests(unittest.TestCase):
    """Sanity-check the generated help text."""

    def test_help_lists_new_commands(self):
        text = get_help_text()
        for command in ("examine", "drop", "use", "attack", "stats", "save", "load"):
            self.assertIn(command, text)

    def test_help_lists_gameplay_commands(self):
        text = get_help_text()
        for command in ("equip", "flee", "explore", "buy", "sell", "rest", "map"):
            self.assertIn(command, text)

    def test_help_shows_exit_synonym(self):
        self.assertIn("exit", get_help_text())

    def test_settings_help_is_nonempty(self):
        self.assertTrue(get_settings_help_text().strip())


if __name__ == "__main__":
    unittest.main()
