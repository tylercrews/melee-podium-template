"""User-facing labels for the stable pose codes embedded in portrait filenames."""

# Keep labels separate from the filename pose IDs (such as "a" and "b") so
# changing copy does not require migrating assets, saved favorites, or scales.
POSE_LABELS = {
    "Bowser": {"a": "Standing Upright", "b": "Archived Crouched"},
    "Captain Falcon": {"a": "Archived Standing Foot Back", "b": "Salute", "c": "Victory B - Talk To The Hand", "d": "Victory Y - Shirt Rip", "e": "Victory X - High Kick"},
    "Donkey Kong": {"a": "Fist Pump", "b": "Kung Fu", "c": "Victory B - Flex"},
    "Dr. Mario": {"a": "Standing", "b": "Stethoscope", "c": "Pill Toss"},
    "Falco": {"a": "Salute", "b": "Standing??", "c": "Victory B - Post-Kicks", "d": "Victory Y - Landing", "e": "Victory X - Arms Crossed"},
    "Fox": {"a": "Point", "b": "Blasting", "c": "Victory B - Hand On Hip", "d": "Victory Y - Gun Down", "e": "Gun Up", "f": "Victory Smash Ult - Back Turned"},
    "Ganondorf": {"a": "Standing", "b": "Crouch"},
    "Ice Climbers": {"a": "Nana Above", "b": "Standing"},
    "Jigglypuff": {"a": "Surprised", "b": "Waving"},
    "Kirby": {"a": "Tippie Toes", "b": "Waving"},
    "Link": {"a": "Standing", "b": "Blocking"},
    "Luigi": {"a": "Bashful", "b": "Looking Into The Distance"},
    "Mario": {"a": "Victory Hand", "b": "Jumping"},
    "Marth": {"a": "Wide Stance", "b": "Narrow Stance"},
    "Mewtwo": {"a": "Glaring", "b": "Pokemon Crystal Sprite", "c": "Victory B - Shadow Blast", "d": "Victory X - Levitate"},
    "Mr. Game and Watch": {"a": "Walking", "b": "Aghast"},
    "Ness": {"a": "Airplane Run", "b": "Thumbs Up"},
    "Peach": {"a": "Heart Hands", "b": "Standing"},
    "Pichu": {"a": "POSE A", "b": "POSE B", "c": "POSE C"},
    "Pikachu": {"a": "POSE A", "b": "POSE B"},
    "Roy": {"a": "POSE A", "b": "POSE B"},
    "Samus": {"a": "POSE A", "b": "POSE B"},
    "Sheik": {"a": "POSE A", "b": "POSE B"},
    "Yoshi": {"a": "POSE A", "b": "POSE B", "c": "POSE C", "d": "POSE D"},
    "Young Link": {"a": "POSE A", "b": "POSE B"},
    "Zelda": {"a": "POSE A", "b": "POSE B"},
}
