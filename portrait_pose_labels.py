"""User-facing labels for the stable pose codes embedded in portrait filenames."""

# Keep labels separate from the filename pose IDs (such as "a" and "b") so
# changing copy does not require migrating assets, saved favorites, or scales.
POSE_LABELS = {
    "Sandbag": {"a": "Standing"},
    # Wireframe labels name the fighter animation each pose was taken from.
    "Wireframe-Male": {"a": "Captain Falcon - Salute Wave", "b": "Captain Falcon Victory X - High Kick", "c": "Ganondorf Victory B - Fist Raised", "d": "Ganondorf Victory Y - Flick Off", "e": "Marth Victory X - Jojo Pose", "f": "Marth Victory X - Arm Out"},
    "Wireframe-Female": {"a": "Peach Taunt - Victory Hand", "b": "Peach Victory B - Wave", "c": "Peach Victory X - Arm Out", "d": "Samus Victory Y - Crouch", "e": "Sheik Victory Y - Jojo Pose", "f": "Sheik Victory X - High Kick"},
    "Bowser": {"a": "Standing Upright", "b": "Archived - Char Select Portrait - Crouched", "c": "Victory B - Flex"},
    "Captain Falcon": {"a": "Archived Standing Foot Back", "b": "Char Select Portrait - Salute", "c": "Victory B - Talk To The Hand", "d": "Victory Y - Shirt Rip", "e": "Victory X - High Kick"},
    "Donkey Kong": {"a": "Fist Pump", "b": "Char Select Portrait - Kung Fu", "c": "Victory B - Flex"},
    "Dr. Mario": {"a": "Standing", "b": "Char Select Portrait - Stethoscope", "c": "Pill Toss"},
    "Falco": {"a": "Salute", "b": "Char Select Portrait - Lean", "c": "Victory B - Post-Kicks", "d": "Victory Y - Landing", "e": "Victory X - Arms Crossed"},
    "Fox": {"a": "Point", "b": "Char Select Portrait - Blasting", "c": "Victory B - Hand On Hip", "d": "Victory Y - Gun Down", "e": "Gun Up", "f": "Victory Smash Ult - Back Turned"},
    "Ganondorf": {"a": "Standing", "b": "Char Select Portrait - Crouch", "c": "Victory X - Sword Plant"},
    "Ice Climbers": {"a": "Nana Above", "b": "Char Select Portrait - Standing", "c": "Victory Y - High Five", "d": "Victory Y - High Five (Swap)", "e": "Cheerleading Liberty Lift", "f": "Cheerleading Liberty Lift (Swap)"},
    "Jigglypuff": {"a": "Surprised", "b": "Char Select Portrait - Waving", "c": "Victory B - Tilted", "d": "Victory X - Rest", "e": "Taunt"},
    "Kirby": {"a": "Tippie Toes", "b": "Char Select Portrait - Waving", "c": "Forgotten Land Cover"},
    "Link": {"a": "Standing", "b": "Char Select Portrait - Blocking", "c": "Victory Y* - Sword Raise"},
    "Luigi": {"a": "Bashful", "b": "Char Select Portrait - Hat Tip", "c": "Victory B - Plank", "d": "Victory Y - Finger Guns", "e": "Brawl Up Taunt - Point Right", "g": "Downsmash - The Richie"},
    "Mario": {"a": "Victory Hand", "b": "Char Select Portrait - Jumping", "c": "Victory Y - Pointing"},
    "Marth": {"a": "Wide Stance", "b": "Char Select Portrait - Narrow Stance", "c": "Victory B - Sword Point", "d": "Victory Y - Looking Back", "e": "Victory X - Jojo Pose"},
    "Mewtwo": {"a": "Glaring", "b": "Char Select Portrait - Crystal Sprite", "c": "Victory B - Shadow Blast", "d": "Victory X - Levitate"},
    "Mr. Game and Watch": {"a": "Walking", "b": "Char Select Portrait - Aghast", "c": "Flag"},
    "Ness": {"a": "Airplane Run", "b": "Char Select Portrait - Thumbs Up", "c": "Victory X - Home Run"},
    "Peach": {"a": "Heart Hands", "b": "Char Select Portrait - Standing", "c": "Victory B - Wave", "d": "Victory Y - Oh, Did I Win?"},
    "Pichu": {"a": "Wave", "b": "Char Select Portrait - Jump", "c": "Superman"},
    "Pikachu": {"a": "On All Fours", "b": "Char Select Portrait - Standing Up", "c": "Victory B - Spin", "d": "Victory X - Asleep"},
    "Roy": {"a": "Clenched Fist", "b": "Char Select Portrait - Squatting", "c": "Victory X - Sword Down"},
    "Samus": {"a": "Braced", "b": "Char Select Portrait - Lock On", "c": "Victory Y - Metroid 2 Cover", "d": "Victory X - Taunt"},
    "Sheik": {"a": "Archived Zelda And Sheik Standing", "b": "Archived Falling With Needles", "c": "Victory Y - Standing", "d": "Victory X - Squat", "e": "Balancing", "f": "Handstand"},
    "Yoshi": {"a": "On One Foot", "b": "Char Select Portrait - Hop On!", "c": "Victory B - Victory Hand", "d": "Victory X - Backwards Flex"},
    "Young Link": {"a": "Walking", "b": "Char Select Portrait - Blocking", "c": "Victory X - Fists On Hips"},
    "Zelda": {"a": "Zelda And Sheik Standing", "b": "Char Select Portrait - Idle Pose - Arms Crossed", "c": "Victory B - Praying"},
}
