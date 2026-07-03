from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChordProMetadata:
    title: str = ""
    artist: str = ""
    key: str = ""


@dataclass
class Section:
    name: str
    kind: str
    lines: list
    tag: str


@dataclass
class ChordProDocument:
    metadata: ChordProMetadata
    sections: list
    source_path: Optional[str] = None


@dataclass
class ValidationIssue:
    level: str  # "info" | "warning"
    message: str
    line: Optional[int] = None
