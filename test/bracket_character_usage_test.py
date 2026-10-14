"""Game-winning versus played-character import regressions."""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app, _import_response
from bracket_import import identify_bracket_link, parse_startgg, parse_parrygg
from bracket_import.service import _reported_character_usage


class CharacterUsageTests(unittest.TestCase):
    def startgg_payload(self):
        return {"data": {"event": {
            "name": "Singles", "numEntrants": 8, "entrantSizeMin": 1,
            "tournament": {"name": "Weekly"},
            "standings": {"nodes": [{"placement": 7, "entrant": {"id": 9, "name": "Player"}}]},
        }}}

    def test_startgg_winless_top_eight_keeps_six_characters_across_two_sets(self):
        names = ["Fox", "Falco", "Marth", "Sheik", "Peach", "Pikachu"]
        groups = iter((names[:3], names[3:]))
        def report_page(query, token):
            group = next(groups)
            return {"data": {"event": {"sets": {"pageInfo": {"total": 2}, "nodes": [{
                "slots": [{"entrant": {"id": 9}}, {"entrant": {"id": 12}}],
                "games": [{"winnerId": 12, "entrant1Score": 200, "entrant2Score": 104,
                           "selections": [{"entrant": {"id": 9}, "character": {"name": name}}]}
                          for name in group],
            }]}}}}
        with patch("bracket_import.service._startgg_request", side_effect=report_page) as request:
            usage = _reported_character_usage(1, {"9"}, "token")
        self.assertEqual(request.call_count, 2)
        self.assertTrue(all(not selection["_startgg_won"] for selection in usage["9"]))
        link = identify_bracket_link("start.gg/tournament/weekly/event/singles")
        for all_characters in (False, True):
            result = parse_startgg(self.startgg_payload(), link, character_usage=usage, import_all_characters=all_characters)
            player = result.players[0]
            self.assertEqual([character.name for character in player.characters], names)
            self.assertEqual(player.played_characters, player.characters)
            self.assertEqual(player.won_characters, ())
            self.assertEqual(player.characters[0].costume, "red")
            self.assertEqual(len(result.to_singles_entrants()[0].characters), 6)

    def test_startgg_mode_filters_characters_and_costume_counts_by_game_wins(self):
        selections = [
            {"character": {"name": "Fox"}, "_startgg_score": 300, "_startgg_won": False},
            {"character": {"name": "Fox"}, "_startgg_score": 300, "_startgg_won": False},
            {"character": {"name": "Fox"}, "_startgg_score": 204, "_startgg_won": True},
            {"character": {"name": "Marth"}, "_startgg_won": False},
            {"character": {"name": "Falco"}, "_startgg_won": True},
        ]
        link = identify_bracket_link("start.gg/tournament/weekly/event/singles")
        for all_characters in (False, True):
            result = parse_startgg(self.startgg_payload(), link, character_usage={"9": selections}, import_all_characters=all_characters)
            player = result.players[0]
            self.assertEqual([character.name for character in player.characters], ["Fox", "Marth", "Falco"] if all_characters else ["Fox", "Falco"])
            self.assertEqual(player.characters[0].costume, "blue" if all_characters else "red")
            response = _import_response(result)
            self.assertEqual(len(response["entrants"][0]["played_characters"]), 3)
            self.assertEqual(len(response["entrants"][0]["won_characters"]), 2)
            self.assertEqual(response["import_all_characters"], all_characters)

    def parry_payload(self):
        def game(placement, one, two):
            return {"slots": [{"placement": placement, "participants": [
                {"userId": "u1", "characters": [{"slug": one, "color": "blue"}]},
                {"user_id": "u2", "characters": [{"slug": two}]},
            ]}]}
        return {
            "tournament": {"name": "Weekly"}, "event": {"entrantSize": 2, "entrantCount": 8},
            "placements": [{"placement": 2, "eventEntrant": {"name": "Team", "entrant": {"users": [
                {"id": "u1", "gamerTag": "One"}, {"id": "u2", "gamerTag": "Two"},
            ]}}}],
            "brackets": [{"matches": [{"matchGames": [game(2, "fox", "sheik"), game(1, "marth", "peach")]}]}],
        }

    def test_parrygg_tracks_game_wins_per_doubles_member(self):
        link = identify_bracket_link("parry.gg/weekly/doubles/_standings")
        for all_characters in (False, True):
            result = parse_parrygg(self.parry_payload(), link, import_all_characters=all_characters)
            one, two = result.players[0].members
            self.assertEqual([c.name for c in one.characters], ["Fox", "Marth"] if all_characters else ["Marth"])
            self.assertEqual([c.name for c in two.characters], ["Sheik", "Peach"] if all_characters else ["Peach"])
            self.assertEqual(len(_import_response(result)["entrants"][0]["members"][0]["played_characters"]), 2)
            self.assertEqual(len(result.to_doubles_teams()[0].entrant_1.characters), 2 if all_characters else 1)

    def test_parrygg_winless_members_use_all_played_characters(self):
        payload = self.parry_payload()
        payload["brackets"][0]["matches"][0]["matchGames"][1]["slots"][0]["placement"] = 2
        result = parse_parrygg(payload, identify_bracket_link("parry.gg/weekly/doubles/_standings"))
        self.assertEqual([c.name for c in result.players[0].members[0].characters], ["Fox", "Marth"])
        self.assertEqual([c.name for c in result.players[0].members[1].characters], ["Sheik", "Peach"])

    def test_api_forwards_choice_to_both_character_providers(self):
        client = app.test_client()
        fixtures = [
            ("start.gg/tournament/weekly/event/singles", "fetch_startgg", parse_startgg(self.startgg_payload(), identify_bracket_link("start.gg/tournament/weekly/event/singles"))),
            ("parry.gg/weekly/doubles/_standings", "fetch_parrygg", parse_parrygg(self.parry_payload(), identify_bracket_link("parry.gg/weekly/doubles/_standings"))),
        ]
        for url, fetch, result in fixtures:
            for choice in (False, True):
                with patch(f"app.{fetch}", return_value=result) as mocked:
                    response = client.post("/api/import", json={"url": url, "import_all_characters": choice})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(mocked.call_args.kwargs["import_all_characters"], choice)
        for invalid in ("false", 0, 1, None, []):
            with self.subTest(invalid=invalid):
                response = client.post("/api/import", json={"url": fixtures[0][0], "import_all_characters": invalid})
                self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
