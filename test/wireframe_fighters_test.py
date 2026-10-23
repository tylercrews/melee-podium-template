"""Wireframe portraits, Random labels, and paired Random bracket imports."""

from hashlib import sha256
import json
from pathlib import Path
from random import Random
import sys
from types import SimpleNamespace
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import _import_response, app
from bracket_import import identify_bracket_link, parse_parrygg, parse_startgg
from bracket_import.random_selection import expand_random_selections, is_random_selection
from bracket_import.service import ImportedCharacter
from clapping_assets import CLAPPING_FOLDER, resolve_clapping_path
from DrawPodium import _resolve_stock_icon_path
from legacy_podium_content_renderer import LegacyPodiumContentRenderer
from models import Character, SinglesEntrant
from portrait_assets import CHARACTER_FOLDER, PORTRAIT_FILENAME, load_scaled_portrait, resolve_character_path, with_team_color
from portrait_pose_labels import POSE_LABELS
from portrait_scale_adjustment_to_character_relativity import get_pose_scale
from wireframe_fighters import (
    WIREFRAME_FEMALE,
    WIREFRAME_FIGHTERS,
    WIREFRAME_MALE,
    WIREFRAME_POSE_PAIRS,
    fighter_display_name,
    random_wireframe_poses,
)


ROOT = Path(__file__).resolve().parents[1]


def poses(fighter: str) -> set[str]:
    return {PORTRAIT_FILENAME.match(path.name).group("pose") for path in (CHARACTER_FOLDER / fighter).glob("*.png")}


def rendered_height(fighter: str, pose: str) -> float:
    with Image.open(resolve_character_path(Character(fighter, pose=pose))) as image:
        bounds = image.getchannel("A").getbbox()
    return (bounds[3] - bounds[1]) * get_pose_scale(fighter, f"00{pose}")


class WireframePortraitTest(unittest.TestCase):
    def test_renamed_poses_follow_the_render_schema_and_are_labeled(self):
        for fighter in WIREFRAME_FIGHTERS:
            files = sorted(path.name for path in (CHARACTER_FOLDER / fighter).glob("*.png"))
            self.assertEqual(len(files), 6)
            for name in files:
                self.assertRegex(name, rf"^00[a-f]_default_{fighter.replace(' ', '_')}_tyro-decomp-anims_[a-z0-9_]+\.png$")
            self.assertEqual(set(POSE_LABELS[fighter]), poses(fighter))

    def test_pose_pairs_match_every_male_pose_to_a_distinct_female_pose(self):
        self.assertEqual(set(WIREFRAME_POSE_PAIRS), poses(WIREFRAME_MALE))
        self.assertEqual(set(WIREFRAME_POSE_PAIRS.values()), poses(WIREFRAME_FEMALE))
        rng = Random(4)
        for _ in range(20):
            male, female = random_wireframe_poses(rng)
            self.assertEqual(WIREFRAME_POSE_PAIRS[male], female)

    def test_sizes_sit_between_their_reference_fighters(self):
        falcon = rendered_height("Captain Falcon", "b")
        ganondorf = rendered_height("Ganondorf", "a")
        male = rendered_height(WIREFRAME_MALE, "a")
        self.assertLess(falcon, male)
        self.assertLess(male, ganondorf)
        sheik = rendered_height("Sheik", "c")
        samus = rendered_height("Samus", "a")
        female = rendered_height(WIREFRAME_FEMALE, "a")
        self.assertLess(sheik, female)
        self.assertLess(female, samus)
        self.assertLess(female, male)
        for fighter in WIREFRAME_FIGHTERS:
            self.assertEqual(len({get_pose_scale(fighter, f"00{pose}") for pose in poses(fighter)}), 1)

    def test_team_colors_leave_single_costume_wireframes_unchanged(self):
        wireframe = Character(WIREFRAME_FEMALE, pose="c", mirror_horizontally=True)
        for color in ("red", "green", "blue"):
            self.assertIs(with_team_color(wireframe, color), wireframe)
            self.assertEqual(with_team_color(Character("Fox"), color).color, color)
        self.assertEqual(load_scaled_portrait(with_team_color(wireframe, "red"), 0.1).mode, "RGBA")

    def test_stock_icons_and_clapping_animations_resolve(self):
        manifest = json.loads((CLAPPING_FOLDER / "manifest.json").read_text(encoding="utf-8"))
        for fighter in WIREFRAME_FIGHTERS:
            character = Character(fighter, color=None, pose=None)
            slug = fighter.lower().replace("-", "_")
            self.assertEqual(_resolve_stock_icon_path(character).parent.name, slug)
            self.assertTrue((ROOT / f"frontend/public/char_assets/stock_icons/{slug}/00_default_{slug}_stock.png").is_file())
            asset = next(row for row in manifest["assets"] if row["character"] == fighter)
            path = resolve_clapping_path(character)
            self.assertEqual(path, CLAPPING_FOLDER / asset["path"])
            self.assertEqual(sha256(path.read_bytes()).hexdigest(), asset["sha256"])

    def test_fighter_name_labels_show_random(self):
        for fighter in WIREFRAME_FIGHTERS:
            entrant = SinglesEntrant(tag="Player", seed=1, placement=1, characters=[Character(fighter)])
            label = LegacyPodiumContentRenderer._text_value(SimpleNamespace(field="entrant.primary_character_name"), entrant)
            self.assertEqual(label, "Random")
        self.assertEqual(fighter_display_name("Fox"), "Fox")

    def test_picker_options_list_both_wireframes_with_pose_labels(self):
        response = app.test_client().get("/api/options")
        fighters = {row["name"]: row for row in response.get_json()["fighters"]}
        for fighter in WIREFRAME_FIGHTERS:
            self.assertEqual({option["color"] for option in fighters[fighter]["options"]}, {"default"})
            self.assertEqual({option["pose_label"] for option in fighters[fighter]["options"]}, set(POSE_LABELS[fighter].values()))


class RandomImportTest(unittest.TestCase):
    def startgg_payload(self):
        return {"data": {"event": {
            "name": "Singles", "numEntrants": 8, "entrantSizeMin": 1, "tournament": {"name": "Weekly"},
            "standings": {"nodes": [{"placement": 1, "entrant": {"id": 9, "name": "Player"}}]},
        }}}

    def test_random_spellings_are_recognized(self):
        for name in ("Random Character", "random", " RANDOM ", "random-character"):
            self.assertTrue(is_random_selection(name))
        self.assertFalse(is_random_selection("Sandbag"))

    def test_startgg_random_imports_paired_wireframes_in_both_histories(self):
        selections = [
            {"character": {"name": "Fox"}, "_startgg_won": False},
            {"character": {"name": "Random Character"}, "_startgg_score": 203, "_startgg_won": True},
        ]
        link = identify_bracket_link("start.gg/tournament/weekly/event/singles")
        result = parse_startgg(self.startgg_payload(), link, character_usage={"9": selections}, import_all_characters=True)
        player = result.players[0]
        self.assertEqual([character.name for character in player.played_characters], ["Fox", WIREFRAME_MALE, WIREFRAME_FEMALE])
        self.assertEqual(player.won_characters, player.played_characters[1:])
        male, female = player.won_characters
        self.assertEqual((male.costume, female.costume), ("default", "default"))
        self.assertEqual(WIREFRAME_POSE_PAIRS[male.pose], female.pose)
        self.assertEqual(result.to_singles_entrants()[0].characters[1:], [
            Character(WIREFRAME_MALE, pose=male.pose), Character(WIREFRAME_FEMALE, pose=female.pose),
        ])
        serialized = _import_response(result)["entrants"][0]["characters"]
        self.assertEqual([(row["fighter"], row["pose"]) for row in serialized[1:]],
                         [(WIREFRAME_MALE, male.pose), (WIREFRAME_FEMALE, female.pose)])
        self.assertIsNone(serialized[0]["pose"])

    def test_parrygg_random_slug_imports_paired_wireframes_per_member(self):
        payload = {
            "tournament": {"name": "Weekly"}, "event": {"entrantSize": 1, "entrantCount": 8},
            "placements": [{"placement": 1, "eventEntrant": {"name": "Player", "entrant": {"users": [{"id": "u1", "gamerTag": "Player"}]}}}],
            "brackets": [{"matches": [{"matchGames": [{"slots": [{"placement": 1, "participants": [
                {"userId": "u1", "characters": [{"slug": "random"}]},
            ]}]}]}]}],
        }
        result = parse_parrygg(payload, identify_bracket_link("parry.gg/weekly/singles"))
        player = result.players[0]
        self.assertEqual([character.name for character in player.characters], [WIREFRAME_MALE, WIREFRAME_FEMALE])
        self.assertEqual(player.characters, player.members[0].characters)
        self.assertEqual(WIREFRAME_POSE_PAIRS[player.characters[0].pose], player.characters[1].pose)

    def test_expansion_uses_one_pair_for_every_history(self):
        played = (ImportedCharacter("Marth"), ImportedCharacter("Random"))
        won = (ImportedCharacter("Random"),)
        expanded_played, expanded_won = expand_random_selections(played, won, rng=Random(7))
        self.assertEqual(expanded_played[0], ImportedCharacter("Marth"))
        self.assertEqual(expanded_played[1:], expanded_won)
        self.assertEqual(expand_random_selections((ImportedCharacter("Fox"),)), ((ImportedCharacter("Fox"),),))


if __name__ == "__main__":
    unittest.main()
