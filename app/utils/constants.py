KEY_MAP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTES = KEY_MAP

STEM_CATEGORIES = [
    "Vocals",
    "Guitars",
    "Bass",
    "Drums",
    "Percussion",
    "Keys",
    "Strings",
    "Brass",
    "Winds",
    "Synths",
    "FX",
    "Ref",
    "Other",
]


def get_key_at_semitone_shift(base_key: str, shift: int) -> str:
    """Devuelve la tonalidad resultante al desplazar base_key en shift semitonos."""
    try:
        idx = KEY_MAP.index(base_key)
    except ValueError:
        return base_key
    new_idx = (idx + shift) % 12
    return KEY_MAP[new_idx]
