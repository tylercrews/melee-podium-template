"""Tests for reusable entrant pools."""

import random
import unittest

from default_entrants import DEFAULT_TOP_8_ENTRANT_POOL, random_top_8_entrants


class DefaultTop8EntrantsTest(unittest.TestCase):
    def test_pool_contains_the_expected_players_and_characters(self) -> None:
        actual = {
            entrant.tag: [
                (character.melee_fighter_name, character.color)
                for character in entrant.characters
            ]
            for entrant in DEFAULT_TOP_8_ENTRANT_POOL
        }

        self.assertEqual(
            actual,
            {
                "C9 | Mang0": [("Fox", "default"), ("Falco", "default")],
                "Armada": [("Peach", "default")],
                "GG | PPMD": [("Falco", "green"), ("Marth", "default")],
                "Cody": [("Fox", "green")],
                "Zain": [("Marth", "red")],
                "Mew2King": [("Sheik", "green"), ("Marth", "black")],
                "Liquid | Hungrybox": [("Jigglypuff", "green")],
                "TSM | Leffen": [("Fox", "default")],
            },
        )

    def test_random_helper_assigns_unique_values_and_orders_by_placement(self) -> None:
        entrants = random_top_8_entrants(random.Random(42))

        self.assertEqual([entrant.placement for entrant in entrants], list(range(1, 9)))
        self.assertEqual(sorted(entrant.seed for entrant in entrants), list(range(1, 9)))
        self.assertCountEqual(
            [entrant.tag for entrant in entrants],
            [entrant.tag for entrant in DEFAULT_TOP_8_ENTRANT_POOL],
        )

    def test_seeded_random_helper_is_reproducible(self) -> None:
        first = random_top_8_entrants(random.Random(7))
        second = random_top_8_entrants(random.Random(7))

        self.assertEqual(first, second)

    def test_returned_character_lists_do_not_mutate_the_pool(self) -> None:
        entrants = random_top_8_entrants(random.Random(1))

        entrants[0].characters.clear()

        self.assertTrue(all(entrant.characters for entrant in DEFAULT_TOP_8_ENTRANT_POOL))


if __name__ == "__main__":
    unittest.main()
