"""Focused tests for composing parry.gg's unary API calls."""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from parrygg_api import fetch_parrygg_data


class ParryGGApiTests(unittest.TestCase):
    @patch("parrygg_api.request_parrygg")
    def test_specific_bracket_uses_its_placements_and_fetches_games(self, request):
        def response(service, method, body):
            if method == "GetTournament":
                return {"tournament": {"name": "Weekly", "events": [{
                    "name": "Melee Singles",
                    "slug": "melee-singles",
                    "game": {"slug": "super-smash-bros-melee"},
                    "phases": [{"slug": "main", "brackets": [{"id": "b1", "slug": "bracket"}]}],
                }]}}
            if method == "GetEventPlacements":
                return {"placements": [{"placement": 99}]}
            if method == "GetBracket":
                return {"bracket": {"id": "b1", "matches": [{"matchGames": []}]}}
            if method == "GetBracketPlacements":
                return {"placements": [{"placement": 1}]}
            self.fail(f"Unexpected call: {service}.{method} {body}")

        request.side_effect = response
        payload = fetch_parrygg_data(
            "weekly",
            event_slug="melee-singles",
            phase_slug="main",
            bracket_slug="bracket",
        )

        self.assertEqual(payload["placements"], [{"placement": 1}])
        self.assertEqual(payload["brackets"][0]["id"], "b1")

    @patch("parrygg_api.request_parrygg")
    def test_tournament_url_requires_a_choice_between_multiple_melee_events(self, request):
        request.return_value = {"tournament": {"events": [
            {"slug": "singles", "game": {"slug": "super-smash-bros-melee"}},
            {"slug": "doubles", "game": {"slug": "super-smash-bros-melee"}},
        ]}}

        with self.assertRaisesRegex(ValueError, "more than one event"):
            fetch_parrygg_data("weekly")


if __name__ == "__main__":
    unittest.main()
