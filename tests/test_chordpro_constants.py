from app.ui.chordpro_editor.constants import (
    parse_chord_name,
    format_chord,
    detect_key_preference,
    transpose_chord_name,
)


def test_parse_simple_major():
    root, ctype, bass = parse_chord_name("C")
    assert (root, ctype, bass) == (0, "", None)


def test_parse_minor():
    root, ctype, bass = parse_chord_name("Am")
    assert (root, ctype, bass) == (9, "m", None)


def test_parse_sharp_seventh():
    root, ctype, bass = parse_chord_name("F#m7")
    assert (root, ctype, bass) == (6, "m7", None)


def test_parse_slash_chord():
    root, ctype, bass = parse_chord_name("C/G")
    assert (root, ctype, bass) == (0, "", 7)


def test_parse_flat_root():
    root, ctype, bass = parse_chord_name("Bb")
    assert (root, ctype, bass) == (10, "", None)


def test_parse_sus_and_dim():
    assert parse_chord_name("Dsus4") == (2, "sus4", None)
    assert parse_chord_name("Bdim") == (11, "dim", None)


def test_parse_invalid_returns_zero():
    assert parse_chord_name("Hx") == (0, "", None)


def test_format_roundtrip_major():
    assert format_chord(0, "") == "C"


def test_format_with_flats():
    assert format_chord(10, "", use_flats=True) == "Bb"
    assert format_chord(10, "", use_flats=False) == "A#"


def test_format_with_bass():
    assert format_chord(0, "", bass=7) == "C/G"


def test_format_complex_type():
    assert format_chord(6, "m7") == "F#m7"


def test_detect_key_preference_flats():
    assert detect_key_preference(5) is True    # F → flats
    assert detect_key_preference(10) is True   # Bb → flats
    assert detect_key_preference(1) is True    # Db → flats
    assert detect_key_preference(8) is True    # Ab → flats
    assert detect_key_preference(3) is True    # Eb → flats


def test_detect_key_preference_sharps():
    assert detect_key_preference(6) is False   # F# → sharps
    assert detect_key_preference(11) is False  # B → sharps
    assert detect_key_preference(2) is False   # D → sharps (default)
    assert detect_key_preference(0) is False   # C → sharps


def test_transpose_chord_up():
    assert transpose_chord_name("C", 2) == "D"
    assert transpose_chord_name("Am", 3) == "Cm"


def test_transpose_chord_down():
    assert transpose_chord_name("C", -1) == "B"
    assert transpose_chord_name("Bb", -1, use_flats=True) == "A"


def test_transpose_chord_with_bass():
    assert transpose_chord_name("C/G", 2) == "D/A"


def test_transpose_roundtrip():
    for name in ["C", "Am", "F#m7", "Bb", "G/B"]:
        for n in [1, 3, 5, 7, 12]:
            assert transpose_chord_name(transpose_chord_name(name, n), -n) == name


def test_transpose_preserves_type():
    assert transpose_chord_name("Cmaj7", 2) == "Dmaj7"
    assert transpose_chord_name("F#sus4", 1) == "Gsus4"
