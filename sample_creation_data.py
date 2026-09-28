"""Reusable sample tournament and entrant data for previews and tests."""

from __future__ import annotations

from datetime import date
import random
from collections.abc import Sequence

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


SAMPLE_TOP_25_ENTRANT_POOL: tuple[Entrant, ...] = SAMPLE_TOP_8_ENTRANT_POOL + (
    Entrant(tag="Tempo | Axe", characters=[Character("Pikachu", pose=None)]),
    Entrant(tag="Wizzrobe", characters=[Character("Captain Falcon", pose=None)]),
    Entrant(tag="VGBC | aMSa", characters=[Character("Yoshi", pose=None)]),
    Entrant(tag="Plup", characters=[Character("Sheik", pose=None)]),
    Entrant(tag="S2J", characters=[Character("Captain Falcon", pose=None)]),
    Entrant(tag="Moky", characters=[Character("Fox", pose=None)]),
    Entrant(tag="FLY | Jmook", characters=[Character("Sheik", pose=None)]),
    Entrant(tag="Nouns | Aklo", characters=[Character("Link", pose=None)]),
    Entrant(tag="n0ne", characters=[Character("Captain Falcon", pose=None)]),
    Entrant(tag="lloD", characters=[Character("Peach", pose=None)]),
    Entrant(tag="Trif", characters=[Character("Peach", pose=None)]),
    Entrant(tag="Spark", characters=[Character("Sheik", pose=None)]),
    Entrant(tag="Joshman", characters=[Character("Fox", pose=None)]),
    Entrant(tag="Kodorin", characters=[Character("Marth", pose=None)]),
    Entrant(tag="BLE | SluG", characters=[Character("Ice Climbers", pose=None)]),
    Entrant(tag="Junebug", characters=[Character("Donkey Kong", pose=None)]),
    Entrant(tag="Morsecode762", characters=[Character("Samus", pose=None)]),
)


def sample_singles_entrants(
    count: int,
    rng: random.Random | None = None,
    *,
    placements: Sequence[int] | None = None,
) -> list[SinglesEntrant]:
    """Return up to 25 unique sample entrants in result-display order."""

    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        raise ValueError("count must be a positive integer")
    if count > len(SAMPLE_TOP_25_ENTRANT_POOL):
        raise ValueError("sample singles data supports at most 25 entrants")
    if placements is None:
        placements = tuple(range(1, count + 1))
    if len(placements) != count or any(
        isinstance(placement, bool) or not isinstance(placement, int) or placement <= 0
        for placement in placements
    ):
        raise ValueError("placements must contain one positive integer per entrant")

    randomizer = rng if rng is not None else random
    entrants_in_result_order = randomizer.sample(
        SAMPLE_TOP_25_ENTRANT_POOL,
        k=count,
    )
    seeds = randomizer.sample(range(1, count + 1), k=count)
    return [
        SinglesEntrant(
            tag=entrant.tag,
            characters=list(entrant.characters),
            bluesky_handle=entrant.bluesky_handle,
            x_handle=entrant.x_handle,
            seed=seed,
            placement=placement,
        )
        for placement, entrant, seed in zip(
            placements,
            entrants_in_result_order,
            seeds,
            strict=True,
        )
    ]


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
            zip(entrants_in_result_order, seeds, strict=True),
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
        location="Test Venue, Philadelphia, PA",
        stream_link="twitch.tv/meleepodium",
        vod_link="youtube.com/watch?v=example",
        organizer_x_account="x.com/MeleePodium",
        organizer_twitch_account="twitch.tv/meleepodium",
        organizer_bluesky_account="bsky.app/profile/meleepodium.example",
        event_format=event_format,
    )
