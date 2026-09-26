"""Reusable sample tournament and entrant data for previews and tests."""

from __future__ import annotations

from datetime import date
import random

from models import (
    Character,
    DoublesTeam,
    Entrant,
    SinglesEntrant,
    Tournament,
    TournamentFormat,
)


SAMPLE_TEAM_COLORS = ("red", "green", "blue")


SAMPLE_TOP_8_ENTRANT_POOL: tuple[Entrant, ...] = (
    Entrant(
        tag="C9 | Mang0",
        characters=[
            Character("Fox", pose=None),
            Character("Falco", pose=None),
        ],
    ),
    Entrant(tag="Armada", characters=[Character("Peach", pose=None)]),
    Entrant(
        tag="GG | PPMD",
        characters=[
            Character("Falco", color="green", pose=None),
            Character("Marth", pose=None),
        ],
    ),
    Entrant(tag="Cody", characters=[Character("Fox", color="green", pose=None)]),
    Entrant(tag="Zain", characters=[Character("Marth", color="red", pose=None)]),
    Entrant(
        tag="Mew2King",
        characters=[
            Character("Sheik", color="green", pose=None),
            Character("Marth", color="black", pose=None),
        ],
    ),
    Entrant(
        tag="Liquid | Hungrybox",
        characters=[Character("Jigglypuff", color="green", pose=None)],
    ),
    Entrant(tag="TSM | Leffen", characters=[Character("Fox", pose=None)]),
)


def sample_top_8_entrants(
    rng: random.Random | None = None,
) -> list[SinglesEntrant]:
    """Return sample entrants with random placements, seeds, and portrait poses."""

    randomizer = rng if rng is not None else random
    entrants_in_result_order = randomizer.sample(
        SAMPLE_TOP_8_ENTRANT_POOL,
        k=len(SAMPLE_TOP_8_ENTRANT_POOL),
    )
    seeds = randomizer.sample(range(1, 9), k=8)

    return [
        SinglesEntrant(
            tag=entrant.tag,
            characters=list(entrant.characters),
            bluesky_handle=entrant.bluesky_handle,
            x_handle=entrant.x_handle,
            seed=seed,
            placement=placement,
        )
        for placement, (entrant, seed) in enumerate(
            zip(
                entrants_in_result_order,
                seeds,
                strict=True,
            ),
            start=1,
        )
    ]


def sample_top_4_teams(
    rng: random.Random | None = None,
) -> list[DoublesTeam]:
    """Pair all sample entrants once and return randomized teams by placement."""

    randomizer = rng if rng is not None else random
    paired_entrants = randomizer.sample(
        SAMPLE_TOP_8_ENTRANT_POOL,
        k=len(SAMPLE_TOP_8_ENTRANT_POOL),
    )
    seeds = randomizer.sample(range(1, 5), k=4)

    teams: list[DoublesTeam] = []
    for placement, offset in enumerate(range(0, len(paired_entrants), 2), start=1):
        first = paired_entrants[offset]
        second = paired_entrants[offset + 1]
        teams.append(
            DoublesTeam(
                seed=seeds[placement - 1],
                placement=placement,
                entrant_1=_copy_entrant(first),
                entrant_2=_copy_entrant(second),
                team_name=f"{first.tag} / {second.tag}",
                team_color=randomizer.choice(SAMPLE_TEAM_COLORS),
            )
        )
    return teams


def _copy_entrant(entrant: Entrant) -> Entrant:
    """Return a sample entrant with an independently mutable character list."""

    return Entrant(
        tag=entrant.tag,
        characters=list(entrant.characters),
        bluesky_handle=entrant.bluesky_handle,
        x_handle=entrant.x_handle,
    )


def sample_tournament(
    event_format: TournamentFormat = TournamentFormat.SINGLES,
) -> Tournament:
    """Return complete tournament metadata with today's date."""

    if event_format not in {TournamentFormat.SINGLES, TournamentFormat.DOUBLES}:
        raise ValueError("Sample tournament format must be singles or doubles")
    return Tournament(
        title="Test Tournament Name",
        subtitle="Test Tournament Subtitle",
        event="Test Singles" if event_format is TournamentFormat.SINGLES else "Test Doubles",
        date=date.today(),
        entrants_count=50,
        link="start.gg/notareallink/tournamentlink",
        stream_link="twitch.tv/meleepodium",
        vod_link="youtube.com/watch?v=example",
        organizer_x_account="x.com/MeleePodium",
        organizer_twitch_account="twitch.tv/meleepodium",
        organizer_bluesky_account="bsky.app/profile/meleepodium.example",
        event_format=event_format,
    )
