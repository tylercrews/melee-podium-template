"""Tests for the overall mode-driven creation coordinator."""

import unittest

from PIL import Image

from background_builder import BackgroundRequest, PixelSize
from creation import CreationPipeline, CreationRequest, PreferencesNotReadyError
from creation_modes import CreationMode, ModeOptions, ModeSelection
from mode_preferences import ModePreferenceRepository, ModePreferences
from models import Character, SinglesEntrant, Tournament, TournamentFormat


def singles_entrants(count: int) -> tuple[SinglesEntrant, ...]:
    return tuple(
        SinglesEntrant(
            tag=f"Player {placement}",
            characters=[Character("Fox")],
            seed=placement,
            placement=placement,
        )
        for placement in range(1, count + 1)
    )


def tournament() -> Tournament:
    return Tournament(
        title="Test Event",
        entrants_count=16,
        date="2026-09-19",
        event_format=TournamentFormat.SINGLES,
    )


class StaticPreferences:
    def __init__(self, preferences: ModePreferences) -> None:
        self.preferences = preferences

    def load(self, selection: ModeSelection) -> ModePreferences:
        return self.preferences


class RecordingFormattingRenderer:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def draw(
        self, canvas: Image.Image, preferences: ModePreferences
    ) -> Image.Image:
        self.events.append("formatting")
        if canvas.getpixel((0, 0)) != (255, 0, 0, 255):
            raise AssertionError("background must be built before formatting")
        result = canvas.copy()
        result.putpixel((0, 0), (0, 0, 255, 255))
        return result


class RecordingContentRenderer:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def draw(
        self,
        canvas: Image.Image,
        request: CreationRequest,
        preferences: ModePreferences,
    ) -> Image.Image:
        self.events.append("content")
        if canvas.getpixel((0, 0)) != (0, 0, 255, 255):
            raise AssertionError("formatting must be drawn before content")
        result = canvas.copy()
        result.putpixel((0, 0), (0, 255, 0, 255))
        return result


class CreationPipelineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.selection = ModeSelection(
            CreationMode.PODIUM,
            ModeOptions(TournamentFormat.SINGLES, 3),
        )

    def request(self, size: PixelSize = PixelSize(2, 2)) -> CreationRequest:
        return CreationRequest(
            selection=self.selection,
            background=BackgroundRequest(size, fill_color="#FF0000FF"),
            entrants=singles_entrants(3),
            tournament=tournament(),
        )

    def test_pipeline_runs_background_formatting_then_combined_content(self) -> None:
        events: list[str] = []
        preferences = ModePreferences(
            selection=self.selection,
            canvas_size=PixelSize(2, 2),
            ready=True,
        )
        pipeline = CreationPipeline(
            content_renderers={
                CreationMode.PODIUM: RecordingContentRenderer(events)
            },
            preferences=StaticPreferences(preferences),
            formatting_renderer=RecordingFormattingRenderer(events),
        )

        result = pipeline.create(self.request())

        self.assertEqual(events, ["formatting", "content"])
        self.assertEqual(result.getpixel((0, 0)), (0, 255, 0, 255))

    def test_pipeline_refuses_an_unfinished_preference_file(self) -> None:
        pipeline = CreationPipeline(
            content_renderers={},
            preferences=ModePreferenceRepository(),
        )

        with self.assertRaisesRegex(PreferencesNotReadyError, "still a scaffold"):
            pipeline.create(self.request(PixelSize(1672, 941)))

    def test_request_rejects_the_wrong_number_of_included_entrants(self) -> None:
        with self.assertRaisesRegex(ValueError, "Expected 3"):
            CreationRequest(
                selection=self.selection,
                background=BackgroundRequest(PixelSize(2, 2)),
                entrants=singles_entrants(2),
                tournament=tournament(),
            )


if __name__ == "__main__":
    unittest.main()
