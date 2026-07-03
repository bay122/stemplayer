import os
import re

from app.ui.chordpro_editor.model import (
    ChordProDocument,
    ChordProMetadata,
    Section,
    ValidationIssue,
)

_META_TITLE = re.compile(r"^\{(?:title|t):\s*([^}]+)\}\s*$")
_META_ARTIST = re.compile(r"^\{(?:artist|a):\s*([^}]+)\}\s*$")
_META_KEY = re.compile(r"^\{(?:key|k):\s*([^}]+)\}\s*$")
_SECTION_TAG = re.compile(r"^\{(start_of_([a-zA-Z0-9_]+))(?::\s*([^}]+))?\}\s*$")
_END_TAG = re.compile(r"^\{(end_of_[a-zA-Z0-9_]+|eoc|eov|eob)\}\s*$")
_COMMENT_TAG = re.compile(r"^\{c(?:omment)?:\s*([^}]+)\}\s*$")

_KIND_FROM_TAG = {
    "start_of_verse": "verse",
    "start_of_chorus": "chorus",
    "start_of_bridge": "bridge",
    "start_of_intro": "intro",
    "start_of_outro": "outro",
    "start_of_pre-chorus": "pre-chorus",
}

_LABEL_FROM_KIND = {
    "verse": "Verse",
    "chorus": "Chorus",
    "bridge": "Bridge",
    "intro": "Intro",
    "outro": "Outro",
    "pre-chorus": "Pre-Chorus",
    "comment": "Comment",
    "other": "Other",
}


def parse(file_path: str) -> ChordProDocument:
    metadata = ChordProMetadata()
    sections = []
    if not os.path.exists(file_path):
        return ChordProDocument(metadata=metadata, sections=sections, source_path=file_path)
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current = Section(name="Global", kind="other", lines=[], tag="c")

    def flush():
        nonlocal current
        # trim empty leading/trailing lines
        while current.lines and not current.lines[0].strip():
            current.lines.pop(0)
        while current.lines and not current.lines[-1].strip():
            current.lines.pop()
        if current.tag.startswith("end_of_"):
            return
        if current.lines or current.kind in ("comment",):
            if current.tag != "c" or current.lines or current.kind == "comment":
                sections.append(current)

    for raw in lines:
        line = raw.rstrip("\n").rstrip("\r")
        stripped = line.strip()
        if not stripped:
            current.lines.append("")
            continue
        m = _META_TITLE.match(stripped)
        if m:
            metadata.title = m.group(1).strip()
            continue
        m = _META_ARTIST.match(stripped)
        if m:
            metadata.artist = m.group(1).strip()
            continue
        m = _META_KEY.match(stripped)
        if m:
            metadata.key = m.group(1).strip()
            continue
        m = _SECTION_TAG.match(stripped)
        if m:
            tag = m.group(1)
            kind_token = m.group(2)
            name = (m.group(3) or kind_token.replace("start_of_", "")).strip()
            kind = _KIND_FROM_TAG.get(tag, kind_token)
            flush()
            current = Section(name=name, kind=kind, lines=[], tag=tag)
            continue
        m = _END_TAG.match(stripped)
        if m:
            flush()
            current = Section(name="Siguiente", kind="other", lines=[], tag="c")
            continue
        m = _COMMENT_TAG.match(stripped)
        if m:
            flush()
            current = Section(name=m.group(1).strip(), kind="comment", lines=[], tag="c")
            continue
        current.lines.append(stripped)

    flush()
    return ChordProDocument(metadata=metadata, sections=sections, source_path=file_path)


def serialize(doc: ChordProDocument) -> str:
    out = []
    if doc.metadata.title:
        out.append(f"{{title: {doc.metadata.title}}}")
    if doc.metadata.artist:
        out.append(f"{{artist: {doc.metadata.artist}}}")
    if doc.metadata.key:
        out.append(f"{{key: {doc.metadata.key}}}")
    if out:
        out.append("")

    for sec in doc.sections:
        tag = sec.tag
        if tag.startswith("end_of_"):
            continue
        if sec.kind == "comment" or tag == "c":
            out.append(f"{{c: {sec.name}}}")
        elif tag.startswith("start_of_"):
            out.append(f"{{{tag}: {sec.name}}}")
        else:
            out.append(f"{{c: {sec.name}}}")
        for line in sec.lines:
            out.append(line)
        if tag.startswith("start_of_"):
            end_tag = tag.replace("start_of_", "end_of_")
            out.append(f"{{{end_tag}}}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def validate(doc: ChordProDocument) -> list:
    issues = []
    if doc.source_path and os.path.exists(doc.source_path):
        with open(doc.source_path, "r", encoding="utf-8") as f:
            raw_lines = f.readlines()
    else:
        raw_lines = []
    open_tags = []
    for i, raw in enumerate(raw_lines, start=1):
        stripped = raw.strip()
        m = _SECTION_TAG.match(stripped)
        if m:
            open_tags.append((i, m.group(1)))
            continue
        m = _END_TAG.match(stripped)
        if m:
            end_tag = m.group(1)
            expected = end_tag.replace("end_of_", "start_of_")
            if open_tags and open_tags[-1][1] == expected:
                open_tags.pop()
            else:
                issues.append(ValidationIssue(
                    level="warning",
                    message=f"Sección '{end_tag}' sin inicio correspondiente",
                    line=i,
                ))
    for ln, tag in open_tags:
        end_tag = tag.replace("start_of_", "end_of_")
        issues.append(ValidationIssue(
            level="warning",
            message=f"Sección '{tag}' sin cerrar (falta {end_tag})",
            line=ln,
        ))
    return issues
