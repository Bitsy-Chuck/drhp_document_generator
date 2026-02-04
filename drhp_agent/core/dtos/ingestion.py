"""Document ingestion DTOs.

DocumentMetadata, ChunkInfo, TableInfo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from drhp_agent.core.enums import EnumSourceType


@dataclass
class DocumentMetadata:
    """Metadata for an ingested document."""

    doc_id: str
    file_path: str
    file_name: str
    source_type: EnumSourceType
    checksum: str
    modified_time: datetime | None = None
    size_bytes: int = 0
    chunk_count: int = 0
    table_count: int = 0


@dataclass
class ChunkInfo:
    """Information about an extracted text chunk."""

    chunk_id: str
    doc_id: str
    text: str
    char_start: int
    char_end: int
    line_start: int
    line_end: int
    heading_path: list[str] = field(default_factory=list)
    chunk_index: int = 0
    token_count: int | None = None


@dataclass
class TableInfo:
    """Information about an extracted table."""

    table_id: str
    doc_id: str
    headers: list[str]
    rows: list[list[str]]
    row_count: int
    col_count: int
    line_start: int
    line_end: int
    heading_path: list[str] = field(default_factory=list)
    caption: str | None = None
