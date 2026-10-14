"""Shared metadata values for every image renderer."""

from datetime import date


METADATA_FIELDS = frozenset({"event", "date", "date_range", "entrants_count", "tournament_link",
    "tournament_location", "stream_link", "vod_link", "to_x_account", "to_twitch_account",
    "to_bluesky_account", "free_text_1", "free_text_2", "free_text_3", "free_text_4"})


def validate_date_range(start, end):
    if start is None and end is None:
        return
    if start is None or end is None:
        raise ValueError("Date (Range) requires both a start date and an end date")
    try:
        first = start if isinstance(start, date) else date.fromisoformat(start)
        last = end if isinstance(end, date) else date.fromisoformat(end)
        if (isinstance(start, str) and first.isoformat() != start) or (isinstance(end, str) and last.isoformat() != end):
            raise ValueError("Dates must use YYYY-MM-DD")
    except (TypeError, ValueError) as error:
        raise ValueError("Date (Range) dates must use YYYY-MM-DD") from error
    if first > last:
        raise ValueError("Date (Range) end date must be on or after the start date")


def metadata_values(tournament):
    count_label = "Teams" if tournament.event_format.value == "doubles" else "Entrants"
    start, end = getattr(tournament, "date_range_start", None), getattr(tournament, "date_range_end", None)
    date_range = f"{start} to {end}" if start is not None and end is not None else None
    return {
        "event": tournament.event, "date": str(tournament.date), "date_range": date_range,
        "entrants_count": f"{tournament.entrants_count} {count_label}",
        "tournament_link": tournament.link, "tournament_location": tournament.location,
        "stream_link": tournament.stream_link, "vod_link": tournament.vod_link,
        "to_x_account": tournament.organizer_x_account,
        "to_twitch_account": tournament.organizer_twitch_account,
        "to_bluesky_account": tournament.organizer_bluesky_account,
        **{f"free_text_{index}": getattr(tournament, f"free_text_{index}", None) for index in range(1, 5)},
    }
