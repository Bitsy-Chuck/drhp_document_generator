"""Tests for ingestion DTOs (DocumentMetadata, ChunkInfo, TableInfo)."""

import pytest
from datetime import datetime

from drhp_agent.core.dtos import (
    DocumentMetadata,
    ChunkInfo,
    TableInfo,
)
from drhp_agent.core.enums import EnumSourceType


class TestDocumentMetadata:
    """Tests for DocumentMetadata DTO."""

    def test_minimal_creation(self):
        meta = DocumentMetadata(
            doc_id="DOC_001",
            file_path="/path/to/doc.md",
            file_name="doc.md",
            source_type=EnumSourceType.MD,
            checksum="abc123",
        )
        assert meta.doc_id == "DOC_001"
        assert meta.file_name == "doc.md"
        assert meta.source_type == EnumSourceType.MD
        assert meta.size_bytes == 0
        assert meta.chunk_count == 0
        assert meta.table_count == 0
        assert meta.modified_time is None

    def test_full_creation(self):
        now = datetime.now()
        meta = DocumentMetadata(
            doc_id="DOC_002",
            file_path="/path/to/data.md",
            file_name="data.md",
            source_type=EnumSourceType.MD,
            checksum="def456",
            modified_time=now,
            size_bytes=5000,
            chunk_count=10,
            table_count=3,
        )
        assert meta.modified_time == now
        assert meta.size_bytes == 5000
        assert meta.chunk_count == 10
        assert meta.table_count == 3


class TestChunkInfo:
    """Tests for ChunkInfo DTO."""

    def test_minimal_creation(self):
        chunk = ChunkInfo(
            chunk_id="C_001",
            doc_id="DOC_001",
            text="This is chunk text.",
            char_start=0,
            char_end=19,
            line_start=1,
            line_end=1,
        )
        assert chunk.chunk_id == "C_001"
        assert chunk.text == "This is chunk text."
        assert chunk.char_start == 0
        assert chunk.char_end == 19
        assert chunk.heading_path == []
        assert chunk.chunk_index == 0
        assert chunk.token_count is None

    def test_with_heading_path(self):
        chunk = ChunkInfo(
            chunk_id="C_002",
            doc_id="DOC_001",
            text="Nested content.",
            char_start=100,
            char_end=115,
            line_start=10,
            line_end=10,
            heading_path=["Section 1", "Subsection 1.1", "Details"],
            chunk_index=5,
            token_count=50,
        )
        assert len(chunk.heading_path) == 3
        assert chunk.heading_path[0] == "Section 1"
        assert chunk.chunk_index == 5
        assert chunk.token_count == 50

    def test_char_range_valid(self):
        chunk = ChunkInfo(
            chunk_id="C_003",
            doc_id="DOC_001",
            text="Sample",
            char_start=100,
            char_end=106,
            line_start=5,
            line_end=5,
        )
        assert chunk.char_end - chunk.char_start == len(chunk.text)


class TestTableInfo:
    """Tests for TableInfo DTO."""

    def test_minimal_creation(self):
        table = TableInfo(
            table_id="T_001",
            doc_id="DOC_001",
            headers=["Name", "Value"],
            rows=[["Item 1", "100"], ["Item 2", "200"]],
            row_count=2,
            col_count=2,
            line_start=10,
            line_end=15,
        )
        assert table.table_id == "T_001"
        assert len(table.headers) == 2
        assert len(table.rows) == 2
        assert table.row_count == 2
        assert table.col_count == 2
        assert table.caption is None
        assert table.heading_path == []

    def test_with_caption_and_heading(self):
        table = TableInfo(
            table_id="T_002",
            doc_id="DOC_001",
            headers=["Particulars", "Amount (INR)", "Shares"],
            rows=[
                ["Authorized", "3,00,000", "30,000"],
                ["Issued", "1,93,210", "19,321"],
            ],
            row_count=2,
            col_count=3,
            line_start=50,
            line_end=60,
            heading_path=["Capital Structure"],
            caption="Table 7: Share Capital Details",
        )
        assert table.caption == "Table 7: Share Capital Details"
        assert table.heading_path == ["Capital Structure"]
        assert table.col_count == 3

    def test_empty_table(self):
        table = TableInfo(
            table_id="T_003",
            doc_id="DOC_001",
            headers=["Column A", "Column B"],
            rows=[],
            row_count=0,
            col_count=2,
            line_start=100,
            line_end=102,
        )
        assert table.row_count == 0
        assert len(table.rows) == 0
        assert len(table.headers) == 2
