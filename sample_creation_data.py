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


# Historical sponsor/character choices and the aggregate-score ordering are
# documented in docs/Historic and Aggregate Melee Rankings.md. Costume names
# use this repository's asset labels (e.g. orange Fox is "red").
SAMPLE_TOP_8_ENTRANT_POOL: tuple[Entrant, ...] = (
    Entrant(tag="C9 | Mang0", characters=[
        Character("Fox", color="red", pose=None),
        Character("Falco", color="default", pose=None),
    ]),
    Entrant(tag="[A] | Armada", characters=[
        Character("Peach", color="default", pose=None),
        Character("Fox", color="red", pose=None),
    ]),
    Entrant(tag="EG | PPMD", characters=[
        Character("Falco", color="green", pose=None),
        Character("Marth", color="default", pose=None),
    ]),
    Entrant(tag="Cody", characters=[Character("Fox", color="green", pose=None)]),
    Entrant(tag="GG | Zain", characters=[Character("Marth", color="red", pose=None)]),
    Entrant(tag="FOX MVG | Mew2King", characters=[
        Character("Sheik", color="red", pose=None),
        Character("Marth", color="black", pose=None),
        Character("Fox", color="green", pose=None),
    ]),
    Entrant(tag="Liquid | Hungrybox", characters=[Character("Jigglypuff", color="green", pose=None)]),
    Entrant(tag="TSM | Leffen", characters=[
        Character("Fox", color="default", pose=None),
        Character("Sheik", color="white", pose=None),
    ]),
)

# RapMonster is mandatory in both expanded rosters, independently of his score.
SAMPLE_RAPMONSTER = Entrant(tag="RapMonster", characters=[Character("Luigi", color="blue", pose=None)])

# The highest aggregate-score players after excluding the original eight and
# RapMonster. Keep this order so larger rosters extend the same smaller roster.
SAMPLE_AGGREGATE_ADDITIONS: tuple[Entrant, ...] = (
    Entrant(tag="Tempo | Axe", characters=[Character("Pikachu", color="blue", pose=None)]),
    Entrant(tag="Envy | Wizzrobe", characters=[Character("Captain Falcon", color="default", pose=None)]),
    Entrant(tag="VGBC | aMSa", characters=[Character("Yoshi", color="red", pose=None)]),
    Entrant(tag="S2J", characters=[Character("Captain Falcon", color="default", pose=None)]),
    Entrant(tag="Plup", characters=[
        Character("Sheik", color="white", pose=None),
        Character("Fox", color="green", pose=None),
        Character("Samus", color="black", pose=None),
        Character("Luigi", color="default", pose=None),
    ]),
    Entrant(tag="Lucky", characters=[Character("Fox", color="red", pose=None)]),
    Entrant(tag="n0ne", characters=[
        Character("Captain Falcon", color="black", pose=None),
        Character("Ganondorf", color="default", pose=None),
    ]),
    Entrant(tag="SFAT", characters=[Character("Fox", color="red", pose=None)]),
    Entrant(tag="Fiction", characters=[
        Character("Falco", color="default", pose=None),
        Character("Fox", color="blue", pose=None),
    ]),
    Entrant(tag="Shroomed", characters=[
        Character("Sheik", color="red", pose=None),
        Character("Marth", color="red", pose=None),
        Character("Dr. Mario", color="black", pose=None),
    ]),
    Entrant(tag="moky", characters=[Character("Fox", color="blue", pose=None)]),
    Entrant(tag="Trif", characters=[Character("Peach", color="green", pose=None)]),
    Entrant(tag="Colbol", characters=[
        Character("Fox", color="default", pose=None),
        Character("Marth", color="green", pose=None),
    ]),
    Entrant(tag="PewPewU", characters=[Character("Marth", color="default", pose=None)]),
    Entrant(tag="Westballz", characters=[Character("Falco", color="red", pose=None)]),
    Entrant(tag="lloD", characters=[Character("Peach", color="green", pose=None)]),
    Entrant(tag="ChuDat", characters=[Character("Ice Climbers", color="default", pose=None)]),
    Entrant(tag="Spark", characters=[Character("Sheik", color="white", pose=None)]),
    Entrant(tag="Ice", characters=[Character("Fox", color="default", pose=None)]),
    Entrant(tag="Ginger", characters=[Character("Falco", color="blue", pose=None)]),
    Entrant(tag="Swedish Delight", characters=[Character("Sheik", color="default", pose=None)]),
    Entrant(tag="KJH", characters=[
        Character("Fox", color="green", pose=None),
        Character("Falco", color="blue", pose=None),
    ]),
    Entrant(tag="FLY | Jmook", characters=[Character("Sheik", color="white", pose=None)]),
)

SAMPLE_TOP_16_ENTRANT_POOL: tuple[Entrant, ...] = (
    SAMPLE_TOP_8_ENTRANT_POOL + (SAMPLE_RAPMONSTER,) + SAMPLE_AGGREGATE_ADDITIONS[:7]
)
SAMPLE_TOP_32_ENTRANT_POOL: tuple[Entrant, ...] = (
    SAMPLE_TOP_8_ENTRANT_POOL + (SAMPLE_RAPMONSTER,) + SAMPLE_AGGREGATE_ADDITIONS
)
# Preserve the public Top 25 fixture for the reviewed Eyes PR layouts.
SAMPLE_TOP_25_ENTRANT_POOL: tuple[Entrant, ...] = SAMPLE_TOP_32_ENTRANT_POOL[:25]
SAMPLE_CLAPPING_SLUG = Entrant(tag="BLE | SluG", characters=[Character("Ice Climbers", pose=None)])


def _pool_for_count(count: int) -> tuple[Entrant, ...]:
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 32:
        raise ValueError("count must be an integer between 1 and 32")
    return SAMPLE_TOP_8_ENTRANT_POOL if count <= 8 else SAMPLE_TOP_32_ENTRANT_POOL[:count]


def sample_singles_entrants(
    count: int,
    rng: random.Random | None = None,
    *,
    placements: Sequence[int] | None = None,
) -> list[SinglesEntrant]:
    """Return up to 32 unique entrants with randomized results and unique seeds.

    Expanded rosters include the original eight and RapMonster, then the next
    eligible aggregate-score players. Explicit placements may include ties.
    """
    pool = _pool_for_count(count)
    if placements is None:
        placements = tuple(range(1, count + 1))
    if len(placements) != count or any(
        isinstance(placement, bool) or not isinstance(placement, int) or placement <= 0
        for placement in placements
    ):
        raise ValueError("placements must contain one positive integer per entrant")
    if list(placements) != sorted(placements):
        raise ValueError("placements must be in result-display order")
    randomizer = rng if rng is not None else random
    entrants = randomizer.sample(pool, k=count)
    seeds = randomizer.sample(range(1, count + 1), k=count)
    return [SinglesEntrant(
        tag=entrant.tag,
        characters=list(entrant.characters),
        bluesky_handle=entrant.bluesky_handle,
        x_handle=entrant.x_handle,
        seed=seed,
        placement=placement,
    ) for placement, entrant, seed in zip(placements, entrants, seeds, strict=True)]


def sample_top_8_entrants(rng: random.Random | None = None) -> list[SinglesEntrant]:
    """Return the original eight with random results, seeds, and portrait poses."""
    return sample_singles_entrants(8, rng)


def sample_top_16_entrants(rng: random.Random | None = None) -> list[SinglesEntrant]:
    """Return the original eight, RapMonster, and seven aggregate-score additions."""
    return sample_singles_entrants(16, rng)


def sample_top_32_entrants(rng: random.Random | None = None) -> list[SinglesEntrant]:
    """Return the original eight, RapMonster, and 23 aggregate-score additions."""
    return sample_singles_entrants(32, rng)


def sample_doubles_teams(count: int, rng: random.Random | None = None) -> list[DoublesTeam]:
    """Pair each selected player once; randomize seeds, pairings, and team colors."""
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 16:
        raise ValueError("team count must be an integer between 1 and 16")
    pool = _pool_for_count(count * 2)
    randomizer = rng if rng is not None else random
    paired = randomizer.sample(pool, k=count * 2)
    seeds = randomizer.sample(range(1, count + 1), k=count)
    return [DoublesTeam(
        seed=seeds[index],
        placement=index + 1,
        entrant_1=_copy_entrant(paired[index * 2]),
        entrant_2=_copy_entrant(paired[index * 2 + 1]),
        team_name=f"{paired[index * 2].tag} / {paired[index * 2 + 1].tag}",
        team_color=randomizer.choice(SAMPLE_TEAM_COLORS),
    ) for index in range(count)]


def sample_top_4_teams(rng: random.Random | None = None) -> list[DoublesTeam]:
    """Pair all original eight once into four teams, sorted by placement."""
    return sample_doubles_teams(4, rng)


def sample_top_8_teams(rng: random.Random | None = None) -> list[DoublesTeam]:
    """Pair all Top 16 sample players once into eight doubles teams."""
    return sample_doubles_teams(8, rng)


def sample_top_16_teams(rng: random.Random | None = None) -> list[DoublesTeam]:
    """Pair all Top 32 sample players once into sixteen doubles teams."""
    return sample_doubles_teams(16, rng)


def sample_clapping_top_8_entrants(
    rng: random.Random | None = None,
) -> list[SinglesEntrant]:
    """Include varied lower-result identities for the four-podium crop review."""

    randomizer = rng if rng is not None else random
    lower_tags = ("BLE | SluG", "TSM | Leffen", "EG | PPMD", "Tempo | Axe")
    lower = [next(entrant for entrant in (*SAMPLE_TOP_32_ENTRANT_POOL, SAMPLE_CLAPPING_SLUG) if entrant.tag == tag)
             for tag in lower_tags]
    upper = randomizer.sample(
        [entrant for entrant in SAMPLE_TOP_8_ENTRANT_POOL if entrant.tag not in lower_tags],
        k=4,
    )
    seeds = randomizer.sample(range(1, 9), k=8)
    return [SinglesEntrant(
        tag=entrant.tag,
        characters=list(entrant.characters),
        placement=slot,
        seed=seeds[slot - 1],
    ) for slot, entrant in enumerate([*upper, *lower], start=1)]


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
