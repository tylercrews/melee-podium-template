"""Default content selections follow layout type, independently of saved overrides."""

from placement_numbering import default_tournament_placing


def layout_text_defaults(selection):
    tournament = default_tournament_placing(selection)
    return dict(include_seeding=tournament, use_tournament_placing=tournament,
                metadata_rows=(("tournament_link",), ("event",), ("date",), ("entrants_count",))
                if tournament else (("event",), ("date_range",), ("entrants_count",)))
