"""Focused fixtures for provider-neutral bracket import parsing."""

from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from DrawPodium import _display_link
from bracket_import import BracketProvider, identify_bracket_link, parse_challonge, parse_startgg


class BracketImportTests(unittest.TestCase):
    def test_identifies_every_supported_link(self):
        self.assertEqual(identify_bracket_link("https://start.gg/tournament/shine/event/melee-singles").provider, BracketProvider.START_GG)
        self.assertEqual(identify_bracket_link("https://foo.challonge.com/my-bracket").tournament_slug, "my-bracket")
        self.assertEqual(identify_bracket_link("https://tonamel.com/competition/abc").provider, BracketProvider.TONAMEL)
        self.assertEqual(identify_bracket_link("https://parry.gg/tournament/event").event_slug, "event")

    def test_startgg_keeps_reported_character_but_not_an_unproven_costume(self):
        link = identify_bracket_link("https://start.gg/tournament/shine/event/melee-singles")
        data = {"data": {"event": {"name": "Melee Singles", "numEntrants": 10, "startAt": 0, "videogame": {"id": 1, "name": "Melee"}, "tournament": {"name": "Shine", "city": "Boston", "countryCode": "US", "slug": "shine"}, "standings": {"nodes": [{"placement": 1, "entrant": {"id": 9, "name": "Player", "initialSeedNum": 2, "participants": [{"gamerTag": "Player", "user": {"authorizations": [{"externalUsername": "player"}]}}]}}]}}}}
        result = parse_startgg(data, link, character_names={17: "Fox"}, character_usage={"Player": [{"selectionValue": 17}]})
        self.assertEqual(result.players[0].characters[0].name, "Fox")
        self.assertIsNone(result.players[0].characters[0].costume)
        self.assertEqual(result.players[0].x_handle, "@player")

    def test_challonge_orders_final_ranks(self):
        link = identify_bracket_link("https://challonge.com/melee")
        result = parse_challonge({"tournament": {"name": "Weekly", "participants": [{"participant": {"id": 1, "name": "Second", "seed": 3, "final_rank": 2}}, {"participant": {"id": 2, "display_name": "First", "seed": 1, "final_rank": 1}}]}}, link)
        self.assertEqual([player.tag for player in result.players], ["First", "Second"])

    def test_tournament_conversion_keeps_the_source_link(self):
        link = identify_bracket_link("https://challonge.com/melee")
        result = parse_challonge({"tournament": {"name": "Weekly", "participants": [{"participant": {"id": 1, "name": "Winner", "final_rank": 1}}]}}, link)
        self.assertEqual(result.to_tournament().link, "https://challonge.com/melee")

    def test_footer_link_removes_scheme_and_www(self):
        self.assertEqual(_display_link("https://www.example.com/bracket"), "example.com/bracket")
        self.assertEqual(_display_link("www.example.com/bracket"), "example.com/bracket")


if __name__ == "__main__":
    unittest.main()
