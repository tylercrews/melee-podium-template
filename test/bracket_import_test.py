"""Focused fixtures for provider-neutral bracket import parsing."""

from pathlib import Path
import os
import sys
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from DrawPodium import _display_link
from bracket_import import BracketProvider, ImportedCharacter, _reported_character_usage, fetch_startgg, identify_bracket_link, parse_challonge, parse_parrygg, parse_startgg
from models import Character, TournamentFormat


class BracketImportTests(unittest.TestCase):
    def test_identifies_every_supported_link(self):
        self.assertEqual(identify_bracket_link("https://start.gg/tournament/shine/event/melee-singles").provider, BracketProvider.START_GG)
        startgg_bracket = identify_bracket_link("https://www.start.gg/tournament/just-another-melee-monthly-4/events/melee-singles/brackets/2340529/3382687/overview")
        self.assertEqual(startgg_bracket.tournament_slug, "just-another-melee-monthly-4")
        self.assertEqual(startgg_bracket.event_slug, "melee-singles")
        self.assertEqual(startgg_bracket.phase_group_id, "3382687")
        self.assertEqual(identify_bracket_link("https://foo.challonge.com/my-bracket").tournament_slug, "foo-my-bracket")
        self.assertEqual(identify_bracket_link("https://tonamel.com/competition/abc").provider, BracketProvider.TONAMEL)
        parry_bracket = identify_bracket_link("https://parry.gg/tournament/event/main/bracket")
        self.assertEqual(parry_bracket.event_slug, "event")
        self.assertEqual(parry_bracket.phase_slug, "main")
        self.assertEqual(parry_bracket.bracket_slug, "bracket")
        self.assertIsNone(identify_bracket_link("https://parry.gg/tournament").event_slug)

    def test_startgg_keeps_reported_character_but_not_an_unproven_costume(self):
        link = identify_bracket_link("https://start.gg/tournament/shine/event/melee-singles")
        data = {"data": {"event": {"name": "Melee Singles", "numEntrants": 10, "startAt": 0, "videogame": {"id": 1, "name": "Melee"}, "tournament": {"name": "Shine", "city": "Boston", "countryCode": "US", "slug": "shine"}, "standings": {"nodes": [{"placement": 1, "entrant": {"id": 9, "name": "Player", "initialSeedNum": 2, "participants": [{"gamerTag": "Player", "user": {"authorizations": [{"externalUsername": "player"}]}}]}}]}}}}
        result = parse_startgg(data, link, character_names={17: "Fox"}, character_usage={"Player": [{"selectionValue": 17}]})
        self.assertEqual(result.players[0].characters[0].name, "Fox")
        self.assertIsNone(result.players[0].characters[0].costume)
        self.assertEqual(result.players[0].x_handle, "@player")

    def test_startgg_uses_direct_character_names_and_deduplicates_them(self):
        link = identify_bracket_link("https://start.gg/tournament/shine/event/melee-singles")
        data = {"data": {"event": {"name": "Melee Singles", "numEntrants": 10, "startAt": 0, "videogame": {"id": 1, "name": "Melee"}, "tournament": {"name": "Shine", "slug": "shine"}, "standings": {"nodes": [{"placement": 1, "entrant": {"id": 9, "name": "Player", "initialSeedNum": 2, "participants": []}}]}}}}
        result = parse_startgg(data, link, character_usage={"9": [{"character": {"name": "Fox"}}, {"character": {"name": "Fox"}}, {"character": {"name": "Falco"}}]})
        self.assertEqual([character.name for character in result.players[0].characters], ["Fox", "Falco"])

    def test_startgg_imports_most_frequently_reported_usb_costume(self):
        link = identify_bracket_link("https://start.gg/tournament/shine/event/melee-singles")
        data = {"data": {"event": {"name": "Melee Singles", "numEntrants": 10, "tournament": {"name": "Shine", "slug": "shine"}, "standings": {"nodes": [{"placement": 1, "entrant": {"id": 9, "name": "Player", "participants": []}}]}}}}
        selections = [
            {"character": {"name": "Fox"}, "_startgg_score": 204},
            {"character": {"name": "Fox"}, "_startgg_score": 204},
            {"character": {"name": "Fox"}, "_startgg_score": 304},
        ]

        result = parse_startgg(data, link, character_usage={"9": selections})

        self.assertEqual(result.players[0].characters, (ImportedCharacter("Fox", "red"),))

    def test_startgg_collects_losing_selections_and_their_entrant_scores(self):
        response = {"data": {"event": {"sets": {
            "pageInfo": {"total": 1},
            "nodes": [{
                "slots": [{"entrant": {"id": 9}}, {"entrant": {"id": 12}}],
                "games": [{
                    "winnerId": 12,
                    "entrant1Score": 204,
                    "entrant2Score": 104,
                    "selections": [
                        {"entrant": {"id": 9}, "character": {"name": "Fox"}},
                        {"entrant": {"id": 12}, "character": {"name": "Falco"}},
                    ],
                }],
            }],
        }}}}
        with patch("bracket_import._startgg_request", return_value=response):
            usage = _reported_character_usage(1, {"9", "12"}, "token")

        self.assertEqual(usage["9"][0]["_startgg_score"], 204)
        self.assertEqual(usage["12"][0]["_startgg_score"], 104)
    def test_challonge_orders_final_ranks(self):
        link = identify_bracket_link("https://challonge.com/melee")
        result = parse_challonge({"tournament": {"name": "Weekly", "participants": [{"participant": {"id": 1, "name": "Second", "seed": 3, "final_rank": 2}}, {"participant": {"id": 2, "display_name": "First", "seed": 1, "final_rank": 1}}]}}, link)
        self.assertEqual([player.tag for player in result.players], ["First", "Second"])

    def test_challonge_derives_ranks_while_results_await_review(self):
        link = identify_bracket_link("https://challonge.com/5q3o6uxz")
        participants = [
            {"participant": {"id": 1, "name": "qwain.mp3", "seed": 7, "final_rank": None}},
            {"participant": {"id": 2, "name": "WhiteclawWarriors", "seed": 8, "final_rank": None}},
            {"participant": {"id": 3, "name": "30", "seed": 3, "final_rank": None}},
            {"participant": {"id": 4, "name": "I mead Brain", "seed": 9, "final_rank": None}},
        ]
        matches = [
            {"match": {"id": 1, "round": 1, "state": "complete", "player1_id": 1, "player2_id": 4, "winner_id": 1, "loser_id": 4}},
            {"match": {"id": 2, "round": 1, "state": "complete", "player1_id": 2, "player2_id": 3, "winner_id": 2, "loser_id": 3}},
            {"match": {"id": 3, "round": 2, "state": "complete", "player1_id": 1, "player2_id": 2, "winner_id": 1, "loser_id": 2}},
            {"match": {"id": 4, "round": -1, "state": "complete", "player1_id": 3, "player2_id": 4, "winner_id": 3, "loser_id": 4}},
            {"match": {"id": 5, "round": -2, "state": "complete", "player1_id": 2, "player2_id": 3, "winner_id": 2, "loser_id": 3}},
            {"match": {"id": 6, "round": 3, "state": "complete", "player1_id": 1, "player2_id": 2, "winner_id": 1, "loser_id": 2}},
        ]
        result = parse_challonge({"tournament": {"name": "Weekly", "state": "awaiting_review", "tournament_type": "double elimination", "participants": participants, "matches": matches}}, link)
        self.assertEqual(
            [(player.tag, player.placement, player.seed) for player in result.players],
            [
                ("qwain.mp3", 1, 7),
                ("WhiteclawWarriors", 2, 8),
                ("30", 3, 3),
                ("I mead Brain", 4, 9),
            ],
        )

    def test_tournament_conversion_keeps_the_source_link(self):
        link = identify_bracket_link("https://challonge.com/melee")
        result = parse_challonge({"tournament": {"name": "Weekly: Downtown", "participants": [{"participant": {"id": 1, "name": "Winner", "final_rank": 1}}]}}, link)
        tournament = result.to_tournament()
        self.assertEqual(tournament.link, "https://challonge.com/melee")
        self.assertEqual(tournament.title, "Weekly")
        self.assertEqual(tournament.subtitle, "Downtown")

    def test_footer_link_removes_scheme_and_www(self):
        self.assertEqual(_display_link("https://www.example.com/bracket"), "example.com/bracket")
        self.assertEqual(_display_link("www.example.com/bracket"), "example.com/bracket")
        self.assertEqual(_display_link(" https://www.example.com/ bracket \n"), "example.com/bracket")

    @unittest.skipUnless(
        os.environ.get("RUN_LIVE_STARTGG_TESTS") == "1" and os.environ.get("START_GG_TOKEN"),
        "Set RUN_LIVE_STARTGG_TESTS=1 and START_GG_TOKEN to run live Start.gg tests.",
    )
    def test_live_supernova_2025_top_eight_phase_import(self):
        link = identify_bracket_link(
            "https://www.start.gg/tournament/supernova-2025/event/melee-1v1-singles/brackets/1940609/2849882",
        )
        result = fetch_startgg(link)

        self.assertEqual(result.entrants_count, 2422)
        self.assertEqual(
            [(player.placement, player.tag, player.seed) for player in result.players[:8]],
            [
                (1, "Zain", 1),
                (2, "FizzyBrax | Cody Schwab", 2),
                (3, "Hungrybox", 3),
                (4, "Ginger", 21),
                (5, "Aklo", 6),
                (5, "moky", 4),
                (7, "Khryke", 27),
                (7, "Axe", 5),
            ],
        )
    def test_startgg_doubles_preserves_the_team_name_and_members(self):
        link = identify_bracket_link("https://start.gg/tournament/shine/event/melee-doubles")
        data = {"data": {"event": {"name": "Melee Doubles", "numEntrants": 8, "entrantSizeMin": 2, "tournament": {"name": "Shine", "slug": "shine"}, "standings": {"nodes": [{"placement": 1, "entrant": {"id": 9, "name": "The Team", "initialSeedNum": 2, "participants": [{"gamerTag": "Player One"}, {"gamerTag": "Player Two"}]}}]}}}}
        result = parse_startgg(data, link)
        self.assertEqual(result.event_format, TournamentFormat.DOUBLES)
        self.assertEqual([member.tag for member in result.players[0].members], ["Player One", "Player Two"])
        teams = result.to_doubles_teams(characters_by_member={"Player One": [Character("Fox")], "Player Two": [Character("Falco")]})
        self.assertEqual(teams[0].team_name, "The Team")

    def test_parrygg_imports_seeds_members_characters_and_colors(self):
        link = identify_bracket_link("https://parry.gg/weekly/melee-doubles/main/bracket")
        user_one = {"id": "u1", "gamerTag": "Fox Player", "locationCountry": "US"}
        user_two = {"id": "u2", "gamerTag": "Doc Player", "locationCountry": "CA"}
        payload = {
            "tournament": {
                "name": "Weekly: Downtown",
                "startDate": "2026-09-20T18:00:00Z",
                "address": {
                    "locality": "Boston",
                    "administrativeAreaLevel1": "MA",
                    "countryCode": "US",
                },
            },
            "event": {
                "name": "Melee Doubles",
                "entrantSize": 2,
                "entrantCount": 12,
                "startDate": "2026-09-21T18:00:00Z",
                "game": {"slug": "super-smash-bros-melee"},
            },
            "placements": [{
                "placement": 1,
                "seed": 3,
                "eventEntrant": {
                    "id": "ee1",
                    "name": "Space Doctors",
                    "entrant": {"id": "e1", "users": [user_one, user_two]},
                },
            }],
            "brackets": [{"matches": [{"matchGames": [{"slots": [{"participants": [
                {"userId": "u1", "characters": [{"slug": "fox", "name": "Fox", "color": "blue"}]},
                {"userId": "u2", "characters": [{"slug": "doctor-mario", "name": "Doctor Mario", "images": [{"variant": {"color": "red"}}]}]},
            ]}]}]}]}],
        }

        result = parse_parrygg(payload, link)

        self.assertEqual(result.event_format, TournamentFormat.DOUBLES)
        self.assertEqual(result.entrants_count, 12)
        self.assertEqual(result.location, "Boston, MA, US")
        self.assertEqual(result.players[0].tag, "Space Doctors")
        self.assertEqual(result.players[0].seed, 3)
        self.assertEqual(
            [(member.tag, member.characters[0].name, member.characters[0].costume) for member in result.players[0].members],
            [("Fox Player", "Fox", "blue"), ("Doc Player", "Dr. Mario", "red")],
        )

    def test_parrygg_treats_a_reported_character_without_variant_as_default(self):
        link = identify_bracket_link("https://parry.gg/weekly/melee-singles/_standings")
        payload = {
            "tournament": {"name": "Weekly"},
            "event": {"name": "Melee Singles", "entrantSize": 1, "entrantCount": 1},
            "placements": [{
                "placement": 1,
                "seed": 1,
                "eventEntrant": {"entrant": {"users": [{"id": "u1", "gamerTag": "Winner"}]}},
            }],
            "brackets": [{"matches": [{"matchGames": [{"slots": [{"participants": [
                {"userId": "u1", "characters": [{"slug": "mr-game-and-watch", "name": "Mr. Game & Watch"}]},
            ]}]}]}]}],
        }

        result = parse_parrygg(payload, link)

        self.assertEqual(result.players[0].characters, (ImportedCharacter("Mr. Game and Watch", "default"),))


if __name__ == "__main__":
    unittest.main()
