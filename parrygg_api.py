"""Small JSON-over-HTTP client for the public parry.gg API."""

from __future__ import annotations

from typing import Any, Mapping
import os

import requests


PARRY_GG_API_BASE = "https://grpcweb.parry.gg/parrygg.services"


def request_parrygg(
    service: str,
    method: str,
    body: Mapping[str, Any],
    *,
    api_key: str | None = None,
) -> Mapping[str, Any]:
    """Call one unary parry.gg RPC through its documented JSON proxy."""
    key = api_key or os.environ.get("PARRY_GG_API_KEY")
    if not key:
        raise ValueError("PARRY_GG_API_KEY is not configured on the server")

    try:
        response = requests.post(
            f"{PARRY_GG_API_BASE}.{service}/{method}",
            json=dict(body),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-API-KEY": key,
                "User-Agent": "MeleePodiumTemplate/1.0",
            },
            timeout=20,
        )
    except requests.RequestException as error:
        raise ValueError("Could not reach the parry.gg API") from error

    if response.status_code in {401, 403}:
        raise ValueError("parry.gg rejected PARRY_GG_API_KEY")
    if response.status_code == 404:
        raise ValueError("The requested parry.gg tournament, event, or bracket was not found")
    if not response.ok:
        try:
            detail = response.json().get("message")
        except (ValueError, AttributeError):
            detail = None
        suffix = f": {detail}" if detail else ""
        raise ValueError(f"parry.gg API request failed ({response.status_code}){suffix}")

    try:
        payload = response.json()
    except requests.JSONDecodeError as error:
        raise ValueError("parry.gg returned an invalid JSON response") from error
    if not isinstance(payload, Mapping):
        raise ValueError("parry.gg returned an unexpected response")
    return payload


def fetch_parrygg_data(
    tournament_slug: str,
    *,
    event_slug: str | None = None,
    phase_slug: str | None = None,
    bracket_slug: str | None = None,
) -> dict[str, Any]:
    """Fetch metadata, standings, and reported games for one public event."""
    tournament_response = request_parrygg(
        "TournamentService",
        "GetTournament",
        {"tournamentSlug": tournament_slug},
    )
    tournament = tournament_response.get("tournament")
    if not isinstance(tournament, Mapping):
        raise ValueError("parry.gg returned an incomplete tournament response")

    events = [event for event in tournament.get("events", []) if isinstance(event, Mapping)]
    if event_slug:
        matches = [event for event in events if event.get("slug") == event_slug]
        if not matches:
            raise ValueError(f"parry.gg event {event_slug!r} was not found in this tournament")
        event = matches[0]
    else:
        melee_events = [
            event
            for event in events
            if isinstance(event.get("game"), Mapping)
            and event["game"].get("slug") == "super-smash-bros-melee"
        ]
        candidates = melee_events or events
        if len(candidates) != 1:
            slugs = ", ".join(str(event.get("slug")) for event in candidates if event.get("slug"))
            detail = f" Available events: {slugs}." if slugs else ""
            raise ValueError(
                "This parry.gg tournament has more than one event; paste an event or bracket URL."
                + detail
            )
        event = candidates[0]

    game = event.get("game")
    if not isinstance(game, Mapping) or game.get("slug") != "super-smash-bros-melee":
        name = game.get("name") if isinstance(game, Mapping) else "an unknown game"
        raise ValueError(f"The selected parry.gg event is for {name}, not Super Smash Bros. Melee")

    event_path = {
        "tournamentSlug": tournament_slug,
        "eventSlug": event.get("slug"),
    }
    placements_response = request_parrygg(
        "EventService",
        "GetEventPlacements",
        {"eventSlugPath": event_path},
    )

    bracket_summaries = [
        bracket
        for phase in event.get("phases", [])
        if isinstance(phase, Mapping)
        and (not phase_slug or phase.get("slug") == phase_slug)
        for bracket in phase.get("brackets", [])
        if isinstance(bracket, Mapping)
        and (not bracket_slug or bracket.get("slug") == bracket_slug)
    ]
    if (phase_slug or bracket_slug) and not bracket_summaries:
        raise ValueError("The bracket identified by this parry.gg URL was not found")

    brackets = []
    selected_bracket_id: str | None = None
    for summary in bracket_summaries:
        bracket_id = summary.get("id")
        if not bracket_id:
            continue
        response = request_parrygg("BracketService", "GetBracket", {"id": bracket_id})
        bracket = response.get("bracket")
        if isinstance(bracket, Mapping):
            brackets.append(bracket)
            if phase_slug and bracket_slug:
                selected_bracket_id = str(bracket_id)

    placements = placements_response.get("placements", [])
    # Match start.gg's phase-group behavior when the pasted URL names one
    # concrete bracket (pool, redemption bracket, finals, and so on).
    if selected_bracket_id:
        bracket_placements = request_parrygg(
            "BracketService",
            "GetBracketPlacements",
            {"id": selected_bracket_id},
        ).get("placements")
        if isinstance(bracket_placements, list) and bracket_placements:
            placements = bracket_placements

    return {
        "tournament": tournament,
        "event": event,
        "placements": placements,
        "brackets": brackets,
    }
