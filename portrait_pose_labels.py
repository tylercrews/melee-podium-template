"""User-facing labels for the stable pose codes embedded in portrait filenames."""

# Keep labels separate from the filename pose IDs (such as "a" and "b") so
# changing copy does not require migrating assets, saved favorites, or scales.
POSE_LABELS = {
    "Bowser": {"a": "Standing Upright", "b": "Archived Crouched", "c": "Victory B - Flex"},
    "Captain Falcon": {"a": "Archived Standing Foot Back", "b": "Salute", "c": "Victory B - Talk To The Hand", "d": "Victory Y - Shirt Rip", "e": "Victory X - High Kick"},
    "Donkey Kong": {"a": "Fist Pump", "b": "Kung Fu", "c": "Victory B - Flex"},
    "Dr. Mario": {"a": "Standing", "b": "Stethoscope", "c": "Pill Toss"},
    "Falco": {"a": "Salute", "b": "Standing??", "c": "Victory B - Post-Kicks", "d": "Victory Y - Landing", "e": "Victory X - Arms Crossed"},
    "Fox": {"a": "Point", "b": "Blasting", "c": "Victory B - Hand On Hip", "d": "Victory Y - Gun Down", "e": "Gun Up", "f": "Victory Smash Ult - Back Turned"},
    "Ganondorf": {"a": "Standing", "b": "Crouch"},
    "Ice Climbers": {"a": "Nana Above", "b": "Standing"},
    "Jigglypuff": {"a": "Surprised", "b": "Waving", "c": "Victory B - Tilted", "d": "Victory X - Rest", "e": "Taunt"},
    "Kirby": {"a": "Tippie Toes", "b": "Waving"},
    "Link": {"a": "Standing", "b": "Blocking"},
    "Luigi": {"a": "Bashful", "b": "Looking Into The Distance"},
    "Mario": {"a": "Victory Hand", "b": "Jumping"},
    "Marth": {"a": "Wide Stance", "b": "Narrow Stance"},
    "Mewtwo": {"a": "Glaring", "b": "Pokemon Crystal Sprite", "c": "Victory B - Shadow Blast", "d": "Victory X - Levitate"},
    "Mr. Game and Watch": {"a": "Walking", "b": "Aghast", "c": "Flag"},
    "Ness": {"a": "Airplane Run", "b": "Thumbs Up", "c": "Victory X - Home Run"},
    "Peach": {"a": "Heart Hands", "b": "Standing"},
    "Pichu": {"a": "Wave", "b": "Jump", "c": "Superman"},
    "Pikachu": {"a": "On All Fours", "b": "Standing Up"},
    "Roy": {"a": "Clenched Fist", "b": "Squatting"},
    "Samus": {"a": "Metroid 2 Box Art", "b": "Lock On"},
    "Sheik": {"a": "Archived Zelda And Sheik Standing", "b": "Archived Falling With Needles", "c": "Victory Y - Standing", "d": "Victory X - Squat", "e": "Balancing", "f": "Handstand"},
    "Yoshi": {"a": "On One Foot", "b": "Over The Shoulder", "c": "Victory B - Victory Hand", "d": "Victory X - Backwards Flex"},
    "Young Link": {"a": "Walking", "b": "Blocking"},
    "Zelda": {"a": "Zelda And Sheik Standing", "b": "Idle/Portrait Stance"},
}
