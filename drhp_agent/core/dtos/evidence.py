"""Evidence-related DTOs.

EvidenceRef, AnnotationRecord.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from drhp_agent.core.enums import EnumEvidenceType


@dataclass
class EvidenceRef:
    """Reference to evidence supporting a filled slot."""

    evidence_id: str
    evidence_type: EnumEvidenceType
    doc_id: str
    doc_path: str

    # Text span location
    char_start: int | None = None
    char_end: int | None = None
    line_start: int | None = None
    line_end: int | None = None

    # Table cell location
    table_id: str | None = None
    row: int | None = None
    col: int | None = None

    # Heading context
    heading_path: list[str] = field(default_factory=list)

    # Extracted text for display
    excerpt: str | None = None


@dataclass
class AnnotationRecord:
    """Record mapping output span to evidence."""

    annotation_id: str
    output_span_start: int
    output_span_end: int
    slot_id: str
    evidence_refs: list[EvidenceRef]
    output_file: str
    output_line: int | None = None
