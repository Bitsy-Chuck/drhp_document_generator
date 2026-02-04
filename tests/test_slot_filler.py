"""Tests for slot filler (Tasks 6.1-6.5)."""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock

from drhp_agent.fill.slot_filler import SlotFiller, FilledSlots
from drhp_agent.core.dtos import (
    SlotFillRequest,
    SlotFillResult,
    FactStore,
    DocumentExtraction,
    ExtractedFact,
    FactLocation,
)


class TestFilledSlots:
    """Tests for FilledSlots collection."""

    def test_counts(self):
        results = [
            SlotFillResult(slot_id="s1", status="filled", value=100),
            SlotFillResult(slot_id="s2", status="filled", value=200),
            SlotFillResult(slot_id="s3", status="missing", reason="not found"),
            SlotFillResult(slot_id="s4", status="conflict", reason="mismatch"),
            SlotFillResult(slot_id="s5", status="low_confidence", value=50, confidence=0.3),
        ]
        filled = FilledSlots(results=results)

        assert filled.filled_count == 2
        assert filled.missing_count == 1
        assert filled.conflict_count == 1
        assert filled.low_confidence_count == 1

    def test_get_by_id(self):
        results = [
            SlotFillResult(slot_id="s1", status="filled", value=100),
            SlotFillResult(slot_id="s2", status="missing"),
        ]
        filled = FilledSlots(results=results)

        assert filled.get_by_id("s1").value == 100
        assert filled.get_by_id("s2").status == "missing"
        assert filled.get_by_id("s999") is None

    def test_to_dict(self):
        results = [
            SlotFillResult(
                slot_id="s1",
                status="filled",
                value=100,
                formatted_value="₹ 100",
                source_facts=["F001"],
                source_files=["doc.md"],
                confidence=0.95,
            )
        ]
        filled = FilledSlots(results=results)

        data = filled.to_dict()
        assert data["summary"]["total"] == 1
        assert data["summary"]["filled"] == 1
        assert len(data["slots"]) == 1
        assert data["slots"][0]["value"] == 100


class TestSlotFiller:
    """Tests for SlotFiller."""

    @pytest.fixture
    def mock_llm_client(self):
        mock = Mock()
        mock.fill_slot.return_value = {
            "slot_id": "company_name",
            "status": "filled",
            "value": "Test Corp",
            "formatted_value": "Test Corp",
            "source_facts": ["F001"],
            "source_files": ["doc.md"],
            "confidence": 0.95,
        }
        return mock

    @pytest.fixture
    def sample_fact_store(self):
        fact = ExtractedFact(
            fact_id="F001",
            category="company_info",
            key="company_name",
            value="Test Corp",
            value_type="text",
            raw_text="Test Corp",
            location=FactLocation(),
            doc_id="DOC_001",
        )
        extraction = DocumentExtraction(
            doc_id="DOC_001",
            file_path="/test/doc.md",
            document_type="test",
            facts=[fact],
        )
        return FactStore(extractions=[extraction])

    def test_fill_slot_success(self, mock_llm_client, sample_fact_store):
        filler = SlotFiller(mock_llm_client)

        request = SlotFillRequest(
            slot_id="company_name",
            slot_type="text",
            slot_hint="Company name",
        )

        result = filler.fill_slot(request, sample_fact_store)

        assert result.slot_id == "company_name"
        assert result.status == "filled"
        assert result.value == "Test Corp"
        assert result.confidence == 0.95

    def test_fill_slot_missing(self, mock_llm_client, sample_fact_store):
        mock_llm_client.fill_slot.return_value = {
            "slot_id": "missing_slot",
            "status": "missing",
            "reason": "No matching fact found",
        }
        filler = SlotFiller(mock_llm_client)

        request = SlotFillRequest(slot_id="missing_slot", slot_type="text")
        result = filler.fill_slot(request, sample_fact_store)

        assert result.status == "missing"
        assert "No matching" in result.reason

    def test_fill_slot_handles_error(self, mock_llm_client, sample_fact_store):
        mock_llm_client.fill_slot.side_effect = Exception("API error")
        filler = SlotFiller(mock_llm_client)

        request = SlotFillRequest(slot_id="test", slot_type="text")
        result = filler.fill_slot(request, sample_fact_store)

        assert result.status == "missing"
        assert "API error" in result.reason

    def test_fill_all(self, mock_llm_client, sample_fact_store):
        filler = SlotFiller(mock_llm_client)

        requests = [
            SlotFillRequest(slot_id="s1", slot_type="text"),
            SlotFillRequest(slot_id="s2", slot_type="integer"),
        ]

        filled = filler.fill_all(requests, sample_fact_store)

        assert len(filled.results) == 2
        assert mock_llm_client.fill_slot.call_count == 2

    def test_fill_all_with_progress(self, mock_llm_client, sample_fact_store):
        filler = SlotFiller(mock_llm_client)
        progress_calls = []

        def track_progress(slot_id, idx, total):
            progress_calls.append((slot_id, idx, total))

        requests = [
            SlotFillRequest(slot_id="s1", slot_type="text"),
            SlotFillRequest(slot_id="s2", slot_type="text"),
        ]

        filler.fill_all(requests, sample_fact_store, track_progress)

        assert len(progress_calls) == 2
        assert progress_calls[0] == ("s1", 1, 2)
        assert progress_calls[1] == ("s2", 2, 2)

    def test_save_filled_slots(self, mock_llm_client, tmp_path):
        filled = FilledSlots(results=[
            SlotFillResult(slot_id="s1", status="filled", value=100)
        ])
        filler = SlotFiller(mock_llm_client)

        output_path = tmp_path / "out" / "filled.json"
        filler.save_filled_slots(filled, output_path)

        assert output_path.exists()
        data = json.loads(output_path.read_text())
        assert data["summary"]["filled"] == 1

    def test_serialize_facts(self, mock_llm_client, sample_fact_store):
        filler = SlotFiller(mock_llm_client)
        json_str = filler._serialize_facts(sample_fact_store)

        facts = json.loads(json_str)
        assert len(facts) == 1
        assert facts[0]["fact_id"] == "F001"
        assert facts[0]["value"] == "Test Corp"


class TestSlotFillerBusinessLogic:
    """Tests for slot filler business logic scenarios."""

    @pytest.fixture
    def mock_llm_client(self):
        return Mock()

    @pytest.fixture
    def multi_fact_store(self):
        """Fact store with multiple facts for matching scenarios."""
        facts = [
            ExtractedFact(
                fact_id="F001", category="capital_structure", key="authorized_shares",
                value=30000, value_type="integer", raw_text="30,000 equity shares",
                location=FactLocation(section="Section 7", table="Capital"),
                doc_id="DOC_001", confidence=0.95,
            ),
            ExtractedFact(
                fact_id="F002", category="capital_structure", key="authorized_shares",
                value=35000, value_type="integer", raw_text="35,000 shares authorized",
                location=FactLocation(section="Header"),
                doc_id="DOC_002", confidence=0.85,
            ),
            ExtractedFact(
                fact_id="F003", category="company_info", key="company_name",
                value="Test Corp Private Limited", value_type="text",
                raw_text="Test Corp Private Limited",
                location=FactLocation(), doc_id="DOC_001", confidence=0.99,
            ),
            ExtractedFact(
                fact_id="F004", category="allotment", key="allotment_date",
                value="2019-05-15", value_type="date", raw_text="15 May 2019",
                location=FactLocation(section="Resolution"),
                doc_id="DOC_001", confidence=0.90,
            ),
        ]
        extractions = [
            DocumentExtraction(doc_id="DOC_001", file_path="/pas3.md",
                               document_type="pas3_form", facts=[facts[0], facts[2], facts[3]]),
            DocumentExtraction(doc_id="DOC_002", file_path="/resolution.md",
                               document_type="board_resolution", facts=[facts[1]]),
        ]
        return FactStore(extractions=extractions)

    def test_slot_type_integer_expects_numeric_value(self, mock_llm_client, multi_fact_store):
        """Integer slot should get numeric value."""
        mock_llm_client.fill_slot.return_value = {
            "slot_id": "authorized_shares",
            "status": "filled",
            "value": 30000,
            "formatted_value": "30,000",
            "source_facts": ["F001"],
            "source_files": ["pas3.md"],
            "confidence": 0.95,
        }
        filler = SlotFiller(mock_llm_client)

        request = SlotFillRequest(
            slot_id="authorized_shares",
            slot_type="integer",
            slot_hint="Number of authorized shares",
        )
        result = filler.fill_slot(request, multi_fact_store)

        assert result.status == "filled"
        assert isinstance(result.value, int)

    def test_conflict_detection_multiple_values(self, mock_llm_client, multi_fact_store):
        """When multiple facts have different values, should detect conflict."""
        mock_llm_client.fill_slot.return_value = {
            "slot_id": "authorized_shares",
            "status": "conflict",
            "source_facts": ["F001", "F002"],
            "source_files": ["pas3.md", "resolution.md"],
            "reason": "Values differ: 30,000 vs 35,000",
            "confidence": 0.5,
        }
        filler = SlotFiller(mock_llm_client)

        request = SlotFillRequest(
            slot_id="authorized_shares",
            slot_type="integer",
        )
        result = filler.fill_slot(request, multi_fact_store)

        assert result.status == "conflict"
        assert len(result.source_facts) == 2
        assert "differ" in result.reason.lower()

    def test_hint_text_passed_to_llm(self, mock_llm_client, multi_fact_store):
        """Hint should be passed to LLM for better matching."""
        mock_llm_client.fill_slot.return_value = {
            "slot_id": "test", "status": "filled", "value": "Test"
        }
        filler = SlotFiller(mock_llm_client)

        request = SlotFillRequest(
            slot_id="test",
            slot_type="text",
            slot_hint="Full legal company name including Private Limited suffix",
        )
        filler.fill_slot(request, multi_fact_store)

        # Verify hint was passed
        call_args = mock_llm_client.fill_slot.call_args
        assert "Full legal company name" in call_args.kwargs.get("slot_hint", "")

    def test_context_window_passed_to_llm(self, mock_llm_client, multi_fact_store):
        """Context should be passed to LLM for disambiguation."""
        mock_llm_client.fill_slot.return_value = {
            "slot_id": "test", "status": "filled", "value": "Test"
        }
        filler = SlotFiller(mock_llm_client)

        request = SlotFillRequest(
            slot_id="test",
            slot_type="text",
            slot_context="The Company, {{company_name}}, was incorporated on...",
        )
        filler.fill_slot(request, multi_fact_store)

        call_args = mock_llm_client.fill_slot.call_args
        assert "incorporated" in call_args.kwargs.get("slot_context", "")

    def test_low_confidence_below_threshold(self, mock_llm_client, multi_fact_store):
        """Low confidence should be reported as such."""
        mock_llm_client.fill_slot.return_value = {
            "slot_id": "uncertain_slot",
            "status": "low_confidence",
            "value": "Maybe Corp",
            "confidence": 0.4,
            "reason": "Multiple possible matches",
        }
        filler = SlotFiller(mock_llm_client)

        request = SlotFillRequest(slot_id="uncertain_slot", slot_type="text")
        result = filler.fill_slot(request, multi_fact_store)

        assert result.status == "low_confidence"
        assert result.confidence < 0.5

    def test_empty_fact_store_returns_missing(self, mock_llm_client):
        """Empty fact store should result in missing status."""
        mock_llm_client.fill_slot.return_value = {
            "slot_id": "any_slot",
            "status": "missing",
            "reason": "No facts available",
        }
        filler = SlotFiller(mock_llm_client)
        empty_store = FactStore(extractions=[])

        request = SlotFillRequest(slot_id="any_slot", slot_type="text")
        result = filler.fill_slot(request, empty_store)

        assert result.status == "missing"

    def test_multiple_source_files_tracked(self, mock_llm_client, multi_fact_store):
        """When value comes from multiple files, all should be tracked."""
        mock_llm_client.fill_slot.return_value = {
            "slot_id": "company_name",
            "status": "filled",
            "value": "Test Corp",
            "source_facts": ["F003", "F_other"],
            "source_files": ["pas3.md", "resolution.md", "allottees.md"],
            "confidence": 0.95,
        }
        filler = SlotFiller(mock_llm_client)

        request = SlotFillRequest(slot_id="company_name", slot_type="text")
        result = filler.fill_slot(request, multi_fact_store)

        assert len(result.source_files) == 3

    def test_date_type_formatted_correctly(self, mock_llm_client, multi_fact_store):
        """Date slots should have properly formatted values."""
        mock_llm_client.fill_slot.return_value = {
            "slot_id": "allotment_date",
            "status": "filled",
            "value": "2019-05-15",
            "formatted_value": "15 May 2019",
            "source_facts": ["F004"],
            "source_files": ["pas3.md"],
            "confidence": 0.90,
        }
        filler = SlotFiller(mock_llm_client)

        request = SlotFillRequest(
            slot_id="allotment_date",
            slot_type="date",
            slot_hint="Date of share allotment",
        )
        result = filler.fill_slot(request, multi_fact_store)

        assert result.status == "filled"
        assert "May" in result.formatted_value

    def test_amount_type_includes_currency(self, mock_llm_client, multi_fact_store):
        """Amount slots should include currency formatting."""
        mock_llm_client.fill_slot.return_value = {
            "slot_id": "total_capital",
            "status": "filled",
            "value": 300000,
            "formatted_value": "₹ 3,00,000",
            "source_facts": ["F001"],
            "source_files": ["pas3.md"],
            "confidence": 0.95,
        }
        filler = SlotFiller(mock_llm_client)

        request = SlotFillRequest(
            slot_id="total_capital",
            slot_type="amount",
        )
        result = filler.fill_slot(request, multi_fact_store)

        assert "₹" in result.formatted_value or "INR" in result.formatted_value.upper()
