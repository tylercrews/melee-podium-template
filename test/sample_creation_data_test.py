"""Tests for reusable sample creation data."""

from datetime import date
import random
import unittest

from models import TournamentFormat
from sample_creation_data import (
    SAMPLE_TEAM_COLORS,
    SAMPLE_TOP_8_ENTRANT_POOL,
    SAMPLE_TOP_25_ENTRANT_POOL,
    SAMPLE_TOP_16_ENTRANT_POOL,
    SAMPLE_TOP_32_ENTRANT_POOL,
    sample_doubles_teams,
    sample_top_16_entrants,
    sample_top_32_entrants,
    sample_top_8_teams,
    sample_top_16_teams,
    sample_clapping_top_8_entrants,
    sample_singles_entrants,
    sample_top_4_teams,
    sample_top_8_entrants,
    sample_tournament,
)


class SampleCreationDataTest(unittest.TestCase):
    def test_clapping_demo_has_unique_players_and_seeds_with_varied_lower_characters(self):
        entrants = sample_clapping_top_8_entrants(random.Random(42))
        self.assertEqual([entrant.placement for entrant in entrants], list(range(1, 9)))
        self.assertEqual(sorted(entrant.seed for entrant in entrants), list(range(1, 9)))
        self.assertEqual(len({entrant.tag for entrant in entrants}), 8)
        self.assertEqual(
            [entrant.characters[0].melee_fighter_name for entrant in entrants[4:]],
            ["Ice Climbers", "Fox", "Falco", "Pikachu"],
        )
        self.assertEqual(entrants[6].characters[0].color, "green")
        self.assertEqual(len(entrants[6].characters), 2)

    def test_clapping_demo_is_reproducible_without_mutating_the_pool(self):
        first = sample_clapping_top_8_entrants(random.Random(42))
        second = sample_clapping_top_8_entrants(random.Random(42))
        self.assertEqual(first, second)
        first[-1].characters.clear()
        self.assertTrue(all(entrant.characters for entrant in SAMPLE_TOP_25_ENTRANT_POOL))

    def test_extended_sample_helper_returns_unique_sorted_entrants(self) -> None:
        placements = (1, 2, 3, 4, 5, 5, 7, 7, 9, 9, 9, 9, 13, 13, 13, 13)
        entrants = sample_singles_entrants(
            16,
            random.Random(42),
            placements=placements,
        )

        self.assertEqual(tuple(item.placement for item in entrants), placements)
        self.assertEqual(len({item.tag for item in entrants}), 16)
        self.assertEqual(sorted(item.seed for item in entrants), list(range(1, 17)))
        self.assertEqual(len(SAMPLE_TOP_25_ENTRANT_POOL), 25)

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
                "C9 | Mang0": [("Fox", "red"), ("Falco", "default")],
                "[A] | Armada": [("Peach", "default"), ("Fox", "red")],
                "EG | PPMD": [("Falco", "green"), ("Marth", "default")],
                "Cody": [("Fox", "green")],
                "SR | Zain": [("Marth", "red")],
                "Mew2King": [("Sheik", "red"), ("Marth", "black"), ("Fox", "green")],
                "Liquid | Hungrybox": [("Jigglypuff", "green")],
                "TSM | Leffen": [("Fox", "default"), ("Sheik", "white")],
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

    def test_different_rng_seeds_change_result_order_and_seeding(self) -> None:
        first = sample_top_8_entrants(random.Random(7))
        second = sample_top_8_entrants(random.Random(8))

        self.assertNotEqual(
            [(entrant.tag, entrant.seed) for entrant in first],
            [(entrant.tag, entrant.seed) for entrant in second],
        )

    def test_returned_character_lists_do_not_mutate_the_pool(self) -> None:
        entrants = sample_top_8_entrants(random.Random(1))

        entrants[0].characters.clear()

        self.assertTrue(all(entrant.characters for entrant in SAMPLE_TOP_8_ENTRANT_POOL))

    def test_team_helper_pairs_every_entrant_once_in_placement_order(self) -> None:
        teams = sample_top_4_teams(random.Random(42))
        members = [
            member
            for team in teams
            for member in (team.entrant_1, team.entrant_2)
        ]

        self.assertEqual([team.placement for team in teams], list(range(1, 5)))
        self.assertEqual(sorted(team.seed for team in teams), list(range(1, 5)))
        self.assertCountEqual(
            [member.tag for member in members],
            [entrant.tag for entrant in SAMPLE_TOP_8_ENTRANT_POOL],
        )
        self.assertEqual(len({member.tag for member in members}), 8)
        self.assertTrue(
            all(team.team_color in SAMPLE_TEAM_COLORS for team in teams)
        )
        self.assertTrue(
            all(
                character.pose is None
                for member in members
                for character in member.characters
            )
        )

    def test_seeded_team_helper_is_reproducible(self) -> None:
        first = sample_top_4_teams(random.Random(7))
        second = sample_top_4_teams(random.Random(7))

        self.assertEqual(first, second)

    def test_team_character_lists_do_not_mutate_the_pool(self) -> None:
        teams = sample_top_4_teams(random.Random(1))

        teams[0].entrant_1.characters.clear()

        self.assertTrue(all(entrant.characters for entrant in SAMPLE_TOP_8_ENTRANT_POOL))

    def test_expanded_rosters_preserve_original_eight_and_rapmonster(self):
        original = {entrant.tag for entrant in SAMPLE_TOP_8_ENTRANT_POOL}
        self.assertIn("TSM | Leffen", original)
        self.assertNotIn("Envy | Wizzrobe", original)
        expected_additions = [
            "Axe", "Wizzrobe", "aMSa", "S2J", "Plup", "Lucky", "n0ne", "SFAT",
            "Fiction", "Shroomed", "moky", "Trif", "Colbol", "PewPewU", "Westballz",
            "lloD", "ChuDat", "Spark", "Ice", "Ginger", "Swedish Delight", "KJH", "Jmook",
        ]
        for count, pool, helper in (
            (16, SAMPLE_TOP_16_ENTRANT_POOL, sample_top_16_entrants),
            (32, SAMPLE_TOP_32_ENTRANT_POOL, sample_top_32_entrants),
        ):
            with self.subTest(count=count):
                self.assertEqual(len(pool), count)
                self.assertEqual(len({entrant.tag for entrant in pool}), count)
                self.assertEqual(pool[:8], SAMPLE_TOP_8_ENTRANT_POOL)
                self.assertEqual(pool[8].tag, "RapMonster")
                self.assertEqual(pool[8].characters[0].color, "blue")
                additions = [entrant.tag.rsplit("|", 1)[-1].strip() for entrant in pool[9:]]
                self.assertEqual(additions, expected_additions[:count - 9])
                for seed in range(8):
                    results = helper(random.Random(seed))
                    self.assertEqual({entrant.tag for entrant in results}, {entrant.tag for entrant in pool})
                    self.assertEqual([entrant.placement for entrant in results], list(range(1, count + 1)))
                    self.assertEqual(sorted(entrant.seed for entrant in results), list(range(1, count + 1)))
                    self.assertTrue(original <= {entrant.tag for entrant in results})
        self.assertEqual(SAMPLE_TOP_16_ENTRANT_POOL, SAMPLE_TOP_32_ENTRANT_POOL[:16])

    def test_expanded_doubles_pair_every_selected_player_exactly_once(self):
        for count, pool, helper in (
            (8, SAMPLE_TOP_16_ENTRANT_POOL, sample_top_8_teams),
            (16, SAMPLE_TOP_32_ENTRANT_POOL, sample_top_16_teams),
        ):
            with self.subTest(count=count):
                teams = helper(random.Random(42))
                self.assertEqual(teams, helper(random.Random(42)))
                members = [member for team in teams for member in (team.entrant_1, team.entrant_2)]
                self.assertCountEqual([member.tag for member in members], [entrant.tag for entrant in pool])
                self.assertEqual(len({member.tag for member in members}), count * 2)
                self.assertEqual([team.placement for team in teams], list(range(1, count + 1)))
                self.assertEqual(sorted(team.seed for team in teams), list(range(1, count + 1)))
                self.assertTrue(all(team.team_color in SAMPLE_TEAM_COLORS for team in teams))
                self.assertGreater(len({team.team_color for team in teams}), 1)
                self.assertNotEqual(teams, helper(random.Random(43)))
                teams[0].entrant_1.characters.clear()
                self.assertTrue(all(entrant.characters for entrant in pool))

    def test_extended_character_costumes_resolve_to_real_assets(self):
        from portrait_assets import resolve_character_path
        for entrant in SAMPLE_TOP_32_ENTRANT_POOL:
            for character in entrant.characters:
                with self.subTest(player=entrant.tag, character=character):
                    self.assertIsNone(character.pose)
                    self.assertTrue(resolve_character_path(character).is_file())

    def test_extended_helpers_reject_unsupported_counts_and_unsorted_placements(self):
        for count in (True, 0, -1, 33, 2.5):
            with self.subTest(count=count), self.assertRaises(ValueError):
                sample_singles_entrants(count)
        for count in (True, 0, -1, 17, 2.5):
            with self.subTest(count=count), self.assertRaises(ValueError):
                sample_doubles_teams(count)
        with self.assertRaises(ValueError):
            sample_singles_entrants(3, placements=(2, 1, 3))

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
