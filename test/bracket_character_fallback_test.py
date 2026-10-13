"""Provider-neutral handling of placed players without character reports."""

import unittest

from bracket_import import BracketImport, BracketLink, BracketProvider, ImportedCharacter, ImportedMember, ImportedPlayer
from models import Character, TournamentFormat


class BracketCharacterFallbackTest(unittest.TestCase):
    def imported(self, players, event_format=TournamentFormat.SINGLES, provider=BracketProvider.START_GG):
        return BracketImport(link=BracketLink(provider, "https://example.com/bracket", "weekly"),
            tournament_name="Weekly", event_name=None, date=None, location=None,
            entrants_count=8, players=players, event_format=event_format)

    def test_no_reported_games_uses_sandbag_for_every_provider(self):
        for provider in BracketProvider:
            with self.subTest(provider=provider):
                imported = self.imported((ImportedPlayer("DQ opponent", placement=7, seed=3),), provider=provider)
                entrant = imported.to_singles_entrants()[0]
                self.assertEqual(entrant.characters, [Character("Sandbag")])
                self.assertEqual((entrant.tag, entrant.placement, entrant.seed), ("DQ opponent", 7, 3))
                self.assertEqual(imported.players[0].characters, ())

    def test_reported_characters_and_unknown_costumes_are_preserved(self):
        imported = self.imported((ImportedPlayer("Player", placement=1,
            characters=(ImportedCharacter("Fox", "blue"), ImportedCharacter("Falco"))),))
        self.assertEqual(imported.to_singles_entrants()[0].characters,
                         [Character("Fox", color="blue"), Character("Falco", color=None)])

    def test_each_doubles_member_gets_its_own_fallback(self):
        team = ImportedPlayer("Team", placement=1, members=(
            ImportedMember("No games"), ImportedMember("Has games", (ImportedCharacter("Fox", "red"),)),
        ))
        imported = self.imported((team,), TournamentFormat.DOUBLES)
        rendered = imported.to_doubles_teams()[0]
        self.assertEqual(rendered.entrant_1.characters, [Character("Sandbag")])
        self.assertEqual(rendered.entrant_2.characters, [Character("Fox", color="red")])
        reviewed = imported.to_doubles_teams(characters_by_member={"No games": [Character("Marth")]})[0]
        self.assertEqual(reviewed.entrant_1.characters, [Character("Marth")])
        self.assertEqual(reviewed.entrant_2.characters, [Character("Fox", color="red")])
        self.assertEqual(imported.players[0].members[0].characters, ())

    def test_missing_placements_are_still_rejected(self):
        imported = self.imported((ImportedPlayer("Unplaced"),))
        with self.assertRaisesRegex(ValueError, "Placement required"):
            imported.to_singles_entrants()
        team = ImportedPlayer("Team", members=(ImportedMember("One"), ImportedMember("Two")))
        with self.assertRaisesRegex(ValueError, "placement"):
            self.imported((team,), TournamentFormat.DOUBLES).to_doubles_teams()


if __name__ == "__main__":
    unittest.main()
