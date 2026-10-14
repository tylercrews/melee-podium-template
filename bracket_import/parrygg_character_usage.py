"""Collect per-player played and winning selections from Parry.gg games."""

from collections.abc import Callable, Mapping
from typing import Any, TypeVar


Character = TypeVar("Character")


def reported_character_usage(
    brackets: Any, convert: Callable[[Mapping[str, Any]], Character | None]
) -> tuple[dict[str, tuple[Character, ...]], dict[str, tuple[Character, ...]]]:
    played: dict[str, list[Character]] = {}
    won: dict[str, list[Character]] = {}
    for bracket in brackets if isinstance(brackets, list) else []:
        if not isinstance(bracket, Mapping):
            continue
        for match in bracket.get("matches", []):
            if not isinstance(match, Mapping):
                continue
            for game in match.get("matchGames", match.get("match_games", [])):
                if not isinstance(game, Mapping):
                    continue
                for slot in game.get("slots", []):
                    if not isinstance(slot, Mapping):
                        continue
                    # MatchGameSlot.placement describes this game's result,
                    # independently of who eventually won the match.
                    winning = slot.get("placement") == 1
                    for participant in slot.get("participants", []):
                        if not isinstance(participant, Mapping):
                            continue
                        user_id = participant.get("userId") or participant.get("user_id")
                        if not user_id:
                            continue
                        selected = played.setdefault(str(user_id), [])
                        victories = won.setdefault(str(user_id), [])
                        for raw in participant.get("characters", []):
                            if not isinstance(raw, Mapping):
                                continue
                            character = convert(raw)
                            if character is None:
                                continue
                            if character not in selected:
                                selected.append(character)
                            if winning and character not in victories:
                                victories.append(character)
    return (
        {user_id: tuple(characters) for user_id, characters in played.items()},
        {user_id: tuple(characters) for user_id, characters in won.items()},
    )
