"""Reusable entrant pools for layout previews and tests."""

from __future__ import annotations

import random

from models import Character, Entrant, SinglesEntrant


DEFAULT_TOP_8_ENTRANT_POOL: tuple[Entrant, ...] = (
    Entrant(
        tag="C9 | Mang0",
        characters=[Character("Fox"), Character("Falco")],
    ),
    Entrant(tag="Armada", characters=[Character("Peach")]),
    Entrant(
        tag="GG | PPMD",
        characters=[Character("Falco", "green"), Character("Marth")],
    ),
    Entrant(tag="Cody", characters=[Character("Fox", "green")]),
    Entrant(tag="Zain", characters=[Character("Marth", "red")]),
    Entrant(
        tag="Mew2King",
        characters=[Character("Sheik", "green"), Character("Marth", "black")],
    ),
    Entrant(
        tag="Liquid | Hungrybox",
        characters=[Character("Jigglypuff", "green")],
    ),
    Entrant(tag="TSM | Leffen", characters=[Character("Fox")]),
)


def random_top_8_entrants(
    rng: random.Random | None = None,
) -> list[SinglesEntrant]:
    """Return the default pool with unique random seeds and placements.

    Supplying a ``random.Random`` instance allows callers to reproduce a
    particular assignment. The returned entrants are ordered by placement.
    """

    randomizer = rng if rng is not None else random
    placements = randomizer.sample(range(1, 9), k=8)
    seeds = randomizer.sample(range(1, 9), k=8)

    entrants = [
        SinglesEntrant(
            tag=entrant.tag,
            characters=list(entrant.characters),
            bluesky_handle=entrant.bluesky_handle,
            x_handle=entrant.x_handle,
            seed=seed,
            placement=placement,
        )
        for entrant, placement, seed in zip(
            DEFAULT_TOP_8_ENTRANT_POOL,
            placements,
            seeds,
            strict=True,
        )
    ]
    return sorted(entrants, key=lambda entrant: entrant.placement)
