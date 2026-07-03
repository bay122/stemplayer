import os
import tempfile

from app.ui.chordpro_editor.model import (
    ChordProDocument,
    ChordProMetadata,
    Section,
)
from app.ui.chordpro_editor.parser import parse, serialize, validate


def _write(tmp_path, content: str) -> str:
    p = tmp_path / "song.chopro"
    p.write_text(content, encoding="utf-8")
    return str(p)


def test_parse_empty_file(tmp_path):
    doc = parse(_write(tmp_path, ""))
    assert doc.sections == []
    assert doc.metadata.title == ""


def test_parse_metadata_directives(tmp_path):
    content = (
        "{title: My Song}\n"
        "{artist: The Band}\n"
        "{key: C}\n"
        "\n"
        "[C]Hello [G]world\n"
    )
    doc = parse(_write(tmp_path, content))
    assert doc.metadata.title == "My Song"
    assert doc.metadata.artist == "The Band"
    assert doc.metadata.key == "C"
    assert len(doc.sections) == 1
    assert doc.sections[0].lines == ["[C]Hello [G]world"]


def test_parse_short_directives(tmp_path):
    content = (
        "{t: Title}\n"
        "{a: Artist}\n"
        "{k: Am}\n"
        "\n"
        "[Am]Line\n"
    )
    doc = parse(_write(tmp_path, content))
    assert doc.metadata.title == "Title"
    assert doc.metadata.artist == "Artist"
    assert doc.metadata.key == "Am"


def test_parse_sections(tmp_path):
    content = (
        "{title: T}\n"
        "\n"
        "{start_of_verse: Verse 1}\n"
        "[C]line one\n"
        "[G]line two\n"
        "{end_of_verse}\n"
        "\n"
        "{start_of_chorus: Chorus}\n"
        "[F]chorus line\n"
        "{end_of_chorus}\n"
    )
    doc = parse(_write(tmp_path, content))
    assert len(doc.sections) == 2
    assert doc.sections[0].name == "Verse 1"
    assert doc.sections[0].kind == "verse"
    assert doc.sections[0].lines == ["[C]line one", "[G]line two"]
    assert doc.sections[1].name == "Chorus"
    assert doc.sections[1].kind == "chorus"


def test_parse_comment_section(tmp_path):
    content = "{c: Spoken intro}\nspoke here\n"
    doc = parse(_write(tmp_path, content))
    assert len(doc.sections) == 1
    assert doc.sections[0].kind == "comment"
    assert doc.sections[0].tag == "c"


def test_serialize_roundtrip(tmp_path):
    content = (
        "{title: T}\n"
        "{artist: A}\n"
        "{key: Dm}\n"
        "\n"
        "{start_of_verse: Verse 1}\n"
        "[Dm]Hello [A7]world\n"
        "{end_of_verse}\n"
        "\n"
        "{start_of_chorus: Chorus}\n"
        "[Gm]chorus\n"
        "{end_of_chorus}\n"
    )
    p = _write(tmp_path, content)
    doc1 = parse(p)
    out = serialize(doc1)
    p2 = tmp_path / "out.chopro"
    p2.write_text(out, encoding="utf-8")
    doc2 = parse(str(p2))
    assert doc1.metadata.title == doc2.metadata.title
    assert doc1.metadata.artist == doc2.metadata.artist
    assert doc1.metadata.key == doc2.metadata.key
    assert len(doc1.sections) == len(doc2.sections)
    for s1, s2 in zip(doc1.sections, doc2.sections):
        assert s1.name == s2.name
        assert s1.kind == s2.kind
        assert s1.lines == s2.lines


def test_validate_unclosed_section(tmp_path):
    content = (
        "{title: T}\n"
        "{start_of_verse: V}\n"
        "[C]x\n"
    )
    doc = parse(_write(tmp_path, content))
    issues = validate(doc)
    assert any("end_of_verse" in i.message for i in issues)


def test_validate_balanced(tmp_path):
    content = (
        "{title: T}\n"
        "{start_of_verse: V}\n"
        "[C]x\n"
        "{end_of_verse}\n"
    )
    doc = parse(_write(tmp_path, content))
    issues = validate(doc)
    assert not any(i.level == "warning" for i in issues)
