from app.ui.chordpro_editor.constants import (
    parse_chord_name,
    format_chord,
    detect_key_preference,
    transpose_chord_name,
    chord_in_scale,
    chord_root_pc,
    scale_chords,
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


def test_scale_chords_c_major():
    result = scale_chords("C")
    assert result == ["C", "Dm", "Em", "F", "G", "Am", "B°"]


def test_scale_chords_g_major_uses_sharps():
    result = scale_chords("G")
    assert result == ["G", "Am", "Bm", "C", "D", "Em", "F#°"]


def test_scale_chords_f_major_uses_flats():
    result = scale_chords("F")
    assert result == ["F", "Gm", "Am", "Bb", "C", "Dm", "E°"]


def test_scale_chords_a_minor():
    result = scale_chords("A", mode="minor")
    assert result == ["Am", "Bm", "C", "Dm", "Em", "F", "G"]


def test_scale_chords_e_minor():
    result = scale_chords("E", mode="minor")
    assert result == ["Em", "F#m", "G", "Am", "Bm", "C", "D"]


def test_scale_chords_invalid_key_returns_empty():
    assert scale_chords("Hx") == []


def test_chord_root_pc_simple():
    assert chord_root_pc("C") == 0
    assert chord_root_pc("Am") == 9
    assert chord_root_pc("F#") == 6
    assert chord_root_pc("Bb") == 10


def test_chord_root_pc_invalid():
    assert chord_root_pc("Hx") == -1
    assert chord_root_pc("") == -1


def test_chord_in_scale_major():
    assert chord_in_scale("C", "C") is True
    assert chord_in_scale("Am", "C") is True
    assert chord_in_scale("F#", "C") is False  # F# is not in C major


def test_chord_in_scale_minor():
    assert chord_in_scale("Am", "A", mode="minor") is True
    assert chord_in_scale("G", "A", mode="minor") is True
    assert chord_in_scale("B", "A", mode="minor") is False
