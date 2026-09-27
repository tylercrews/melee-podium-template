"""Tests for the metadata retained at the bracket API boundary."""

from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import _import_response
from bracket_import import BracketImport, BracketLink, BracketProvider, ImportedMember, ImportedPlayer
from models import TournamentFormat


class BracketResponseTests(unittest.TestCase):
    def test_response_retains_provider_and_entrant_metadata(self):
        link = BracketLink(
            BracketProvider.START_GG,
            "https://start.gg/tournament/weekly/event/melee-singles",
            "weekly",
            "melee-singles",
            "123",
        )
        imported = BracketImport(
            link=link,
            tournament_name="Weekly",
            event_name="Melee Singles",
            date=None,
            location="Philadelphia",
            entrants_count=64,
            players=(ImportedPlayer(
                tag="Sponsor | Player",
                placement=1,
                seed=4,
                x_handle="@player",
                country="US",
                provider_id="entrant-1",
                members=(ImportedMember("Player", x_handle="@player", country="US"),),
            ),),
            event_format=TournamentFormat.SINGLES,
            stream_link="https://twitch.tv/weekly",
            organizer_x_account="WeeklyMelee",
            organizer_twitch_account="https://twitch.tv/weekly",
            extra={"source": "reported"},
        )

        response = _import_response(imported)

        self.assertEqual(response["tournament"]["location"], "Philadelphia")
        self.assertEqual(response["tournament"]["stream_link"], "https://twitch.tv/weekly")
        self.assertEqual(response["tournament"]["to_x_account"], "WeeklyMelee")
        self.assertEqual(response["tournament"]["to_twitch_account"], "https://twitch.tv/weekly")
        self.assertEqual(response["bracket"]["phase_group_id"], "123")
        self.assertEqual(response["provider_data"], {"source": "reported"})
        self.assertEqual(response["entrants"][0]["provider_id"], "entrant-1")
        self.assertEqual(response["entrants"][0]["x_handle"], "@player")
        self.assertEqual(response["entrants"][0]["members"][0]["country"], "US")


if __name__ == "__main__":
    unittest.main()

