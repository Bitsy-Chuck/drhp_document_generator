"""Tests for extraction DTOs (Tasks 2.18-2.23)."""

import pytest
from datetime import datetime

from drhp_agent.core.dtos import (
    FactLocation,
    ExtractedFact,
    DocumentExtraction,
    FactStore,
    SlotFillRequest,
    SlotFillResult,
)


class TestFactLocation:
    """Tests for FactLocation DTO."""

    def test_empty_location(self):
        loc = FactLocation()
        assert loc.section is None
        assert loc.table is None
        assert loc.row is None
        assert loc.column is None

    def test_full_location(self):
        loc = FactLocation(
            section="Section 7",
            table="Capital Structure",
            row="Equity Shares",
            column="Authorized",
            line_start=100,
            line_end=105,
        )
        assert loc.section == "Section 7"
        assert loc.table == "Capital Structure"
        assert loc.row == "Equity Shares"
        assert loc.column == "Authorized"
        assert loc.line_start == 100
        assert loc.line_end == 105


class TestExtractedFact:
    """Tests for ExtractedFact DTO."""

    def test_minimal_fact(self):
        loc = FactLocation()
        fact = ExtractedFact(
            fact_id="F001",
            key="authorized_shares",
            value=30000,
            value_type="integer",
            raw_text="30,000 equity shares",
            location=loc,
        )
        assert fact.fact_id == "F001"
        assert fact.key == "authorized_shares"
        assert fact.value == 30000
        assert fact.confidence == 1.0
        assert fact.unit is None

    def test_full_fact(self):
        loc = FactLocation(section="Section 7", table="Table 1")
        fact = ExtractedFact(
            fact_id="F002",
            key="total_amount",
            value="75,45,600",
            value_type="amount",
            raw_text="Total: Rs.75,45,600",
            location=loc,
            unit="INR",
            confidence=0.95,
            doc_id="DOC_001",
        )
        assert fact.unit == "INR"
        assert fact.confidence == 0.95
        assert fact.doc_id == "DOC_001"


class TestDocumentExtraction:
    """Tests for DocumentExtraction DTO."""

    def test_empty_extraction(self):
        ext = DocumentExtraction(
            doc_id="DOC_001",
            file_path="/path/to/doc.md",
            document_type="board_resolution",
        )
        assert ext.doc_id == "DOC_001"
        assert ext.facts == []
        assert ext.error is None

    def test_extraction_with_facts(self):
        fact = ExtractedFact(
            fact_id="F001",
            key="company_name",
            value="Test Corp",
            value_type="text",
            raw_text="Test Corp",
            location=FactLocation(),
        )
        ext = DocumentExtraction(
            doc_id="DOC_001",
            file_path="/path/to/doc.md",
            document_type="pas3_form",
            facts=[fact],
            document_date="2019-05-15",
            extraction_timestamp=datetime(2024, 1, 15),
        )
        assert len(ext.facts) == 1
        assert ext.document_date == "2019-05-15"

    def test_extraction_with_error(self):
        ext = DocumentExtraction(
            doc_id="DOC_001",
            file_path="/path/to/doc.md",
            document_type="error",
            error="Failed to parse document",
        )
        assert ext.error == "Failed to parse document"
        assert ext.facts == []


class TestFactStore:
    """Tests for FactStore DTO."""

    @pytest.fixture
    def sample_store(self):
        """Create a sample FactStore with test data."""
        fact1 = ExtractedFact(
            fact_id="F001",
            key="authorized_shares",
            value=30000,
            value_type="integer",
            raw_text="30,000 shares",
            location=FactLocation(),
            doc_id="DOC_001",
        )
        fact2 = ExtractedFact(
            fact_id="F002",
            key="company_name",
            value="Test Corp",
            value_type="text",
            raw_text="Test Corp",
            location=FactLocation(),
            doc_id="DOC_001",
        )
        fact3 = ExtractedFact(
            fact_id="F003",
            key="issued_shares",
            value=19321,
            value_type="integer",
            raw_text="19,321 shares",
            location=FactLocation(),
            doc_id="DOC_002",
        )

        ext1 = DocumentExtraction(
            doc_id="DOC_001",
            file_path="/path/to/doc1.md",
            document_type="pas3_form",
            facts=[fact1, fact2],
        )
        ext2 = DocumentExtraction(
            doc_id="DOC_002",
            file_path="/path/to/doc2.md",
            document_type="board_resolution",
            facts=[fact3],
        )

        return FactStore(extractions=[ext1, ext2])

    def test_all_facts(self, sample_store):
        facts = sample_store.all_facts()
        assert len(facts) == 3

    def test_facts_by_key(self, sample_store):
        facts = sample_store.facts_by_key("authorized_shares")
        assert len(facts) == 1
        assert facts[0].value == 30000

    def test_facts_by_doc(self, sample_store):
        facts = sample_store.facts_by_doc("DOC_001")
        assert len(facts) == 2

    def test_get_fact(self, sample_store):
        fact = sample_store.get_fact("F002")
        assert fact is not None
        assert fact.key == "company_name"

    def test_get_fact_not_found(self, sample_store):
        fact = sample_store.get_fact("F999")
        assert fact is None

    def test_empty_store(self):
        store = FactStore()
        assert store.all_facts() == []


class TestSlotFillRequest:
    """Tests for SlotFillRequest DTO."""

    def test_minimal_request(self):
        req = SlotFillRequest(
            slot_id="authorized_shares",
            slot_type="integer",
        )
        assert req.slot_id == "authorized_shares"
        assert req.slot_hint is None
        assert req.slot_context is None

    def test_full_request(self):
        req = SlotFillRequest(
            slot_id="company_name",
            slot_type="text",
            slot_hint="Full legal name of the company",
            slot_context="The Company, {{company_name}}, was incorporated on...",
        )
        assert req.slot_hint == "Full legal name of the company"
        assert "{{company_name}}" in req.slot_context


class TestSlotFillResult:
    """Tests for SlotFillResult DTO."""

    def test_filled_result(self):
        result = SlotFillResult(
            slot_id="authorized_shares",
            status="filled",
            value=30000,
            formatted_value="30,000",
            source_facts=["F001"],
            source_files=["PAS-3 Form.md"],
            confidence=0.95,
        )
        assert result.status == "filled"
        assert result.value == 30000
        assert len(result.source_facts) == 1

    def test_missing_result(self):
        result = SlotFillResult(
            slot_id="preference_shares",
            status="missing",
            reason="No preference shares found in documents",
        )
        assert result.status == "missing"
        assert result.value is None
        assert "No preference" in result.reason

    def test_conflict_result(self):
        result = SlotFillResult(
            slot_id="total_amount",
            status="conflict",
            source_facts=["F001", "F002"],
            source_files=["doc1.md", "doc2.md"],
            reason="Values differ: 75,45,600 vs 75,46,000",
            confidence=0.5,
        )
        assert result.status == "conflict"
        assert len(result.source_facts) == 2
