"""Self-contained Flask API and static host for the Melee podium generator."""

from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
import sqlite3
from typing import Any, Mapping
import re

from flask import Flask, Response, jsonify, request, send_from_directory
from dotenv import load_dotenv

from DrawPodium import CHARACTER_FOLDER, PodiumFont, PodiumMode, draw_podium
from bracket_import import BracketImport, BracketProvider, fetch_challonge, fetch_startgg, identify_bracket_link
from models import Character, DoublesTeam, Entrant, SinglesEntrant, Tournament, TournamentFormat
from portrait_pose_labels import POSE_LABELS


PROJECT_ROOT = Path(__file__).resolve().parent
# cPanel deployment secrets live outside the web root. Keep this before the
# local fallback so production values win without overriding host variables.
load_dotenv("/home/tyrowork/melee-podium-secrets", override=False)
# The local development fallback is gitignored and must never be served from a
# public web root.
load_dotenv(PROJECT_ROOT / ".env", override=False)
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
STATS_DATABASE_PATH = Path(
    os.environ.get("PODIUM_STATS_DB", PROJECT_ROOT / "podium_stats.sqlite3")
)
_PORTRAIT_FILENAME = re.compile(
    r"^(?P<color_code>\d+)(?P<pose>[a-z]+)_(?P<color>[^_]+)_", re.IGNORECASE
)

app = Flask(__name__, static_folder=None)


def _render_count() -> int:
    """Return the persistent count of successfully generated PNGs."""
    STATS_DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(STATS_DATABASE_PATH) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS application_stats "
            "(key TEXT PRIMARY KEY, value INTEGER NOT NULL)"
        )
        connection.execute(
            "INSERT INTO application_stats(key, value) VALUES ('render_count', 0) "
            "ON CONFLICT(key) DO NOTHING"
        )
        row = connection.execute(
            "SELECT value FROM application_stats WHERE key = 'render_count'"
        ).fetchone()
    return int(row[0]) if row else 0


def _increment_render_count() -> int:
    """Atomically record one completed render and return the new total."""
    _render_count()
    with sqlite3.connect(STATS_DATABASE_PATH) as connection:
        connection.execute(
            "UPDATE application_stats SET value = value + 1 WHERE key = 'render_count'"
        )
        row = connection.execute(
            "SELECT value FROM application_stats WHERE key = 'render_count'"
        ).fetchone()
    return int(row[0]) if row else 0


def _json_object(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a JSON object")
    return value


def _required_text(data: Mapping[str, Any], name: str) -> str:
    value = data.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _optional_text(data: Mapping[str, Any], name: str) -> str | None:
    value = data.get(name)
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string or null")
    return value.strip() or None


def _optional_positive_int(data: Mapping[str, Any], name: str) -> int | None:
    value = data.get(name)
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer or null")
    return value


def _character(data: Any) -> Character:
    source = _json_object(data, "character")
    return Character(
        _required_text(source, "melee_fighter_name"),
        color=_optional_text(source, "color"),
        pose=_optional_text(source, "pose"),
    )


def _entrant(data: Any) -> Entrant:
    source = _json_object(data, "entrant")
    characters = source.get("characters")
    if not isinstance(characters, list) or not characters:
        raise ValueError("entrant.characters must contain at least one character")
    return Entrant(
        tag=_required_text(source, "tag"),
        characters=[_character(item) for item in characters],
    )


def _tournament(data: Any) -> Tournament:
    source = _json_object(data, "tournament")
    event_format = _required_text(source, "event_format")
    try:
        format_value = TournamentFormat(event_format)
    except ValueError as error:
        raise ValueError("event_format must be 'singles' or 'doubles'") from error
    if format_value == TournamentFormat.UNKNOWN:
        raise ValueError("event_format must be 'singles' or 'doubles'")
    return Tournament(
        title=_required_text(source, "title"),
        date=_required_text(source, "date"),
        entrants_count=_optional_positive_int(source, "entrants_count") or 0,
        subtitle=_optional_text(source, "subtitle"),
        event=_optional_text(source, "event"),
        link=_optional_text(source, "link"),
        event_format=format_value,
    )


def _render_request(payload: Mapping[str, Any]) -> tuple[PodiumMode, list[SinglesEntrant] | list[DoublesTeam], Tournament, PodiumFont]:
    try:
        mode = PodiumMode(_required_text(payload, "mode"))
    except ValueError as error:
        choices = ", ".join(item.value for item in PodiumMode)
        raise ValueError(f"mode must be one of: {choices}") from error
    raw_font = payload.get("font", PodiumFont.TYROWO.value)
    if raw_font is None:
        font = PodiumFont.TYROWO
    elif not isinstance(raw_font, str):
        raise ValueError("font must be a string or null")
    else:
        try:
            font = PodiumFont(raw_font)
        except ValueError as error:
            choices = ", ".join(item.value for item in PodiumFont)
            raise ValueError(f"font must be one of: {choices}") from error
    tournament = _tournament(payload.get("tournament"))
    raw_entrants = payload.get("entrants")
    if not isinstance(raw_entrants, list):
        raise ValueError("entrants must be an array")

    if mode.is_doubles:
        entrants: list[DoublesTeam] = []
        for item in raw_entrants:
            source = _json_object(item, "doubles team")
            entrants.append(DoublesTeam(
                team_name=_required_text(source, "team_name"),
                seed=_optional_positive_int(source, "seed"),
                placement=_optional_positive_int(source, "placement") or 0,
                team_color=_optional_text(source, "team_color"),
                entrant_1=_entrant(source.get("entrant_1")),
                entrant_2=_entrant(source.get("entrant_2")),
            ))
        return mode, entrants, tournament, font

    entrants = []
    for item in raw_entrants:
        source = _json_object(item, "singles entrant")
        members = _entrant(source)
        entrants.append(SinglesEntrant(
            tag=members.tag,
            characters=members.characters,
            seed=_optional_positive_int(source, "seed"),
            placement=_optional_positive_int(source, "placement") or 0,
        ))
    return mode, entrants, tournament, font


def _fighter_options() -> list[dict[str, Any]]:
    fighters = []
    for folder in sorted(CHARACTER_FOLDER.iterdir(), key=lambda item: item.name.casefold()):
        if not folder.is_dir():
            continue
        options = {}
        for portrait in folder.glob("*.png"):
            match = _PORTRAIT_FILENAME.match(portrait.name)
            if match:
                key = (
                    int(match.group("color_code")),
                    match.group("color").lower(),
                    match.group("pose").lower(),
                )
                options[key] = portrait.name
        fighters.append({
            "name": folder.name,
            "options": [
                {
                    "color": color,
                    "pose": pose,
                    "pose_label": POSE_LABELS.get(folder.name, {}).get(pose, pose.upper()),
                    "color_order": color_order,
                    "portrait": portrait_name,
                }
                for (color_order, color, pose), portrait_name in sorted(options.items())
            ],
        })
    return fighters


@app.get("/api/health")
def health() -> Any:
    return jsonify(status="ok")


@app.get("/api/stats")
def stats() -> Any:
    return jsonify(render_count=_render_count())


@app.get("/api/options")
def options() -> Any:
    return jsonify(
        modes=[item.value for item in PodiumMode],
        fighters=_fighter_options(),
        team_colors=["red", "green", "blue"],
    )


@app.post("/api/render")
def render() -> Any:
    payload = request.get_json(silent=True)
    if not isinstance(payload, Mapping):
        return jsonify(error="Request body must be a JSON object"), 400
    mode, entrants, tournament, font = _render_request(payload)
    image = draw_podium(mode, entrants, tournament=tournament, font=font)
    output = BytesIO()
    image.save(output, format="PNG")
    _increment_render_count()
    return Response(
        output.getvalue(),
        mimetype="image/png",
        headers={"Content-Disposition": "inline; filename=melee-podium.png"},
    )


def _import_response(imported: BracketImport) -> dict[str, Any]:
    tournament = imported.to_tournament()
    return {
        "provider": imported.link.provider.value,
        "tournament": {
            "title": tournament.title,
            "date": str(tournament.date),
            "entrants_count": tournament.entrants_count,
            "subtitle": tournament.subtitle,
            "event": tournament.event,
            "link": tournament.link,
            "event_format": tournament.event_format.value,
        },
        "entrants": [
            {
                "tag": player.tag,
                "seed": player.seed,
                "placement": player.placement,
                "characters": [
                    {"fighter": character.name, "color": character.costume, "pose": None}
                    for character in player.characters
                ],
            }
            for player in imported.players
        ],
    }


@app.post("/api/import")
def import_bracket() -> Any:
    payload = request.get_json(silent=True)
    if not isinstance(payload, Mapping):
        return jsonify(error="Request body must be a JSON object"), 400
    link = identify_bracket_link(_required_text(payload, "url"))
    top_entrants = payload.get("top_entrants", 8)
    if top_entrants not in {3, 4, 8}:
        return jsonify(error="top_entrants must be 3, 4, or 8"), 400
    if link.provider is BracketProvider.CHALLONGE:
        imported = fetch_challonge(link)
    elif link.provider is BracketProvider.START_GG:
        imported = fetch_startgg(link, top_entrants=top_entrants)
    else:
        return jsonify(error=f"{link.provider} import is not configured yet", provider=link.provider.value), 501
    return jsonify(_import_response(imported))

@app.errorhandler(ValueError)
@app.errorhandler(TypeError)
@app.errorhandler(FileNotFoundError)
def bad_request(error: Exception) -> Any:
    return jsonify(error=str(error)), 400


@app.get("/char_assets/<path:path>")
@app.get("/melee-podium-template/char_assets/<path:path>")
def character_assets(path: str) -> Any:
    return send_from_directory(PROJECT_ROOT / "char_assets", path)

@app.get("/")
@app.get("/<path:path>")
def frontend(path: str = "") -> Any:
    if FRONTEND_DIST.is_dir():
        requested = FRONTEND_DIST / path
        if path and requested.is_file():
            return send_from_directory(FRONTEND_DIST, path)
        return send_from_directory(FRONTEND_DIST, "index.html")
    return jsonify(
        message="Frontend build not found. Run 'cd frontend; npm run build' or use the Vite dev server.",
    ), 404


if __name__ == "__main__":
    app.run(port=5000, debug=True)
