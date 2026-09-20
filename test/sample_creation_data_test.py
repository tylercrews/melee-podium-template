"""Tests for reusable sample creation data."""

from datetime import date
import random
import unittest

from models import TournamentFormat
from sample_creation_data import (
    SAMPLE_TOP_8_ENTRANT_POOL,
    sample_top_8_entrants,
    sample_tournament,
)


class SampleCreationDataTest(unittest.TestCase):
    def test_pool_contains_the_expected_players_and_characters(self) -> None:
        actual = {
            entrant.tag: [
                (character.melee_fighter_name, character.color)
                for character in entrant.characters
            ]
            for entrant in SAMPLE_TOP_8_ENTRANT_POOL
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

    def test_every_sample_character_requests_a_random_available_pose(self) -> None:
        self.assertTrue(
            all(
                character.pose is None
                for entrant in SAMPLE_TOP_8_ENTRANT_POOL
                for character in entrant.characters
            )
        )

    def test_random_helper_assigns_unique_values_and_orders_by_placement(self) -> None:
        entrants = sample_top_8_entrants(random.Random(42))

        self.assertEqual([entrant.placement for entrant in entrants], list(range(1, 9)))
        self.assertEqual(sorted(entrant.seed for entrant in entrants), list(range(1, 9)))
        self.assertCountEqual(
            [entrant.tag for entrant in entrants],
            [entrant.tag for entrant in SAMPLE_TOP_8_ENTRANT_POOL],
        )

    def test_seeded_random_helper_is_reproducible(self) -> None:
        first = sample_top_8_entrants(random.Random(7))
        second = sample_top_8_entrants(random.Random(7))

        self.assertEqual(first, second)

    def test_returned_character_lists_do_not_mutate_the_pool(self) -> None:
        entrants = sample_top_8_entrants(random.Random(1))

        entrants[0].characters.clear()

        self.assertTrue(all(entrant.characters for entrant in SAMPLE_TOP_8_ENTRANT_POOL))

    def test_sample_tournament_populates_every_field(self) -> None:
        tournament = sample_tournament()

        self.assertEqual(tournament.title, "Test Tournament Name")
        self.assertEqual(tournament.subtitle, "Test Tournament Subtitle")
        self.assertEqual(tournament.event, "Test Singles")
        self.assertEqual(tournament.date, date.today())
        self.assertEqual(tournament.entrants_count, 50)
        self.assertEqual(tournament.link, "start.gg/notareallink/tournamentlink")
        self.assertIs(tournament.event_format, TournamentFormat.SINGLES)


if __name__ == "__main__":
    unittest.main()
