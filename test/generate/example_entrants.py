"""Reusable entrant definitions for the podium generator examples."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from models import Character, Entrant


HBK = Entrant(characters=[Character("Sheik", "red", "b")], tag="HBK")
BUSTA = Entrant(characters=[Character("Fox", "green", "a")], tag="BU$TA")
QWAIN = Entrant(characters=[Character("Fox", "blue", "a")], tag="Qwain")
CHOI = Entrant(characters=[Character("Fox", "blue", "b")], tag="Choi")
TYRO = Entrant(characters=[Character("Fox", "blue", None)], tag="Tyro")
OSMICS = Entrant(characters=[Character("Falco", "green", "a")], tag="Osmics")
SHENAL = Entrant(characters=[Character("Mr. Game and Watch")], tag="Shenal")
SILENT_SKYLER = Entrant(
    characters=[Character("Sheik", "white", "b")],
    tag="Silent Skyler",
)
SUBIE = Entrant(characters=[Character("Samus", "blue", "b")], tag="Subie")
MEENIS_TINY = Entrant(characters=[Character("Fox", "red", "a")], tag="meenis tiny")
FELIPE = Entrant(characters=[Character("Marth", "green", "b")], tag="Felipé")
