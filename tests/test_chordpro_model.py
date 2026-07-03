from app.ui.chordpro_editor.model import (
    ChordProDocument,
    ChordProMetadata,
    Section,
    ValidationIssue,
)


def test_metadata_defaults():
    m = ChordProMetadata()
    assert m.title == ""
    assert m.artist == ""
    assert m.key == ""


def test_section_defaults():
    s = Section(name="Verse 1", kind="verse", lines=[], tag="start_of_verse")
    assert s.name == "Verse 1"
    assert s.kind == "verse"
    assert s.lines == []


def test_document_defaults():
    d = ChordProDocument(metadata=ChordProMetadata(), sections=[], source_path=None)
    assert d.sections == []
    assert d.source_path is None


def test_validation_issue_construction():
    v = ValidationIssue(level="warning", message="x", line=3)
    assert v.level == "warning"
    assert v.message == "x"
    assert v.line == 3


def test_document_can_hold_sections():
    d = ChordProDocument(
        metadata=ChordProMetadata(title="Song", artist="Band", key="C"),
        sections=[Section(name="Verse 1", kind="verse", lines=["[C]Hello"], tag="start_of_verse")],
        source_path="/tmp/x.chopro",
    )
    assert d.metadata.title == "Song"
    assert d.sections[0].lines == ["[C]Hello"]
