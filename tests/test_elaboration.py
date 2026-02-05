"""Tests for elaboration (Tasks 13.1-13.8)."""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock

from drhp_agent.core.dtos import (
    ElaborationBlock,
    ElaborationRequest,
    ElaborationResult,
    FactStore,
    DocumentExtraction,
    ExtractedFact,
    FactLocation,
)
from drhp_agent.elaborate.elaborator import Elaborator, Elaborations
from drhp_agent.md_template.parser import TemplateParser, ParsedTemplate


class TestElaborationDTOs:
    """Tests for elaboration DTOs (Task 13.1)."""

    def test_elaboration_block_creation(self):
        block = ElaborationBlock(
            block_id="allotment_history",
            hint="Generate a table of all allotments",
            raw_marker="{{elaborate:allotment_history:Generate a table of all allotments}}",
            line_number=10,
            context="## History of Equity Share Capital",
        )
        assert block.block_id == "allotment_history"
        assert block.hint == "Generate a table of all allotments"

    def test_elaboration_request_creation(self):
        request = ElaborationRequest(
            block_id="test_block",
            hint="Generate content",
            relevant_facts=[{"fact_id": "F001", "value": "100"}],
            template_context="Some context",
        )
        assert request.block_id == "test_block"
        assert len(request.relevant_facts) == 1

    def test_elaboration_result_to_dict(self):
        result = ElaborationResult(
            block_id="test_block",
            status="generated",
            generated_markdown="# Test Content\n\nThis is generated content.",
            source_facts=["F001", "F002"],
            source_files=["doc1.md", "doc2.md"],
            confidence=0.95,
        )
        data = result.to_dict()
        assert data["block_id"] == "test_block"
        assert data["status"] == "generated"
        assert len(data["source_facts"]) == 2
        assert data["confidence"] == 0.95


class TestTemplateParserElaboration:
    """Tests for template parser elaboration block detection (Task 13.2)."""

    def test_parse_elaborate_block_with_hint(self, tmp_path):
        """Format: {{elaborate:block_id:hint}}"""
        content = "{{elaborate:allotment_history:Generate all allotments}}"
        path = tmp_path / "template.md"
        path.write_text(content)

        parser = TemplateParser(path)
        result = parser.parse()

        assert len(result.elaboration_blocks) == 1
        block = result.elaboration_blocks[0]
        assert block.block_id == "allotment_history"
        assert block.hint == "Generate all allotments"

    def test_parse_elaborate_block_no_hint(self, tmp_path):
        """Format: {{elaborate:block_id}}"""
        content = "{{elaborate:summary}}"
        path = tmp_path / "template.md"
        path.write_text(content)

        parser = TemplateParser(path)
        result = parser.parse()

        assert len(result.elaboration_blocks) == 1
        block = result.elaboration_blocks[0]
        assert block.block_id == "summary"
        assert block.hint == ""

    def test_parse_mixed_slots_and_elaborations(self, tmp_path):
        """Template with both slots and elaboration blocks."""
        content = """# Capital Structure

Company: {{text:company_name:Company name}}

{{elaborate:allotment_history:Generate allotment table}}

Total shares: {{integer:total_shares:Total shares}}
"""
        path = tmp_path / "template.md"
        path.write_text(content)

        parser = TemplateParser(path)
        result = parser.parse()

        assert len(result.slots) == 2
        assert len(result.elaboration_blocks) == 1

    def test_to_elaboration_requests(self, tmp_path):
        """Test conversion to elaboration requests."""
        content = "{{elaborate:test_block:Test hint}}"
        path = tmp_path / "template.md"
        path.write_text(content)

        parser = TemplateParser(path)
        result = parser.parse()

        # With no facts
        requests = result.to_elaboration_requests()
        assert len(requests) == 1
        assert requests[0].block_id == "test_block"
        assert requests[0].relevant_facts == []

        # With facts - all should be passed (no filtering)
        facts = [
            {"fact_id": "F001", "key": "allotment", "value": "v1"},
            {"fact_id": "F002", "key": "other", "value": "v2"},
        ]
        requests = result.to_elaboration_requests(facts)
        assert len(requests[0].relevant_facts) == 2  # All facts passed

    def test_to_dict_includes_elaboration_blocks(self, tmp_path):
        """Test that to_dict includes elaboration blocks."""
        content = "{{elaborate:block1:hint1}}\n{{elaborate:block2:hint2}}"
        path = tmp_path / "template.md"
        path.write_text(content)

        parser = TemplateParser(path)
        result = parser.parse()
        data = result.to_dict()

        assert data["elaboration_block_count"] == 2
        assert len(data["elaboration_blocks"]) == 2

    def test_parse_preserves_elaborate_raw_marker(self, tmp_path):
        """Raw marker should be preserved exactly."""
        content = "{{elaborate:test:Generate content with details}}"
        path = tmp_path / "template.md"
        path.write_text(content)

        parser = TemplateParser(path)
        result = parser.parse()

        assert result.elaboration_blocks[0].raw_marker == content


class TestElaborations:
    """Tests for Elaborations collection."""

    def test_counts(self):
        results = [
            ElaborationResult(block_id="b1", status="generated", generated_markdown="content"),
            ElaborationResult(block_id="b2", status="generated", generated_markdown="content"),
            ElaborationResult(block_id="b3", status="empty", reason="no facts"),
            ElaborationResult(block_id="b4", status="error", reason="api error"),
        ]
        elaborations = Elaborations(results=results)

        assert elaborations.generated_count == 2
        assert elaborations.empty_count == 1
        assert elaborations.error_count == 1

    def test_get_by_id(self):
        results = [
            ElaborationResult(block_id="b1", status="generated", generated_markdown="content1"),
            ElaborationResult(block_id="b2", status="generated", generated_markdown="content2"),
        ]
        elaborations = Elaborations(results=results)

        assert elaborations.get_by_id("b1").generated_markdown == "content1"
        assert elaborations.get_by_id("b2").generated_markdown == "content2"
        assert elaborations.get_by_id("b999") is None

    def test_to_dict(self):
        results = [
            ElaborationResult(
                block_id="b1",
                status="generated",
                generated_markdown="content",
                source_facts=["F001"],
                source_files=["doc.md"],
                confidence=0.9,
            )
        ]
        elaborations = Elaborations(results=results)
        data = elaborations.to_dict()

        assert data["summary"]["total"] == 1
        assert data["summary"]["generated"] == 1
        assert len(data["elaborations"]) == 1


class TestElaborator:
    """Tests for Elaborator (Task 13.4)."""

    @pytest.fixture
    def mock_llm_client(self):
        mock = Mock()
        mock.elaborate_section.return_value = {
            "generated_markdown": "# Generated Content\n\nSome prose here.",
            "source_facts": ["F001", "F002"],
            "source_files": ["doc.md"],
            "confidence": 0.95,
        }
        return mock

    @pytest.fixture
    def sample_fact_store(self):
        facts = [
            ExtractedFact(
                fact_id="F001",
                key="allotment_date",
                value="2019-05-15",
                value_type="date",
                raw_text="15 May 2019",
                location=FactLocation(),
                doc_id="DOC_001",
            ),
            ExtractedFact(
                fact_id="F002",
                key="shares_allotted",
                value=960,
                value_type="integer",
                raw_text="960 shares",
                location=FactLocation(),
                doc_id="DOC_001",
            ),
        ]
        extraction = DocumentExtraction(
            doc_id="DOC_001",
            file_path="/test/doc.md",
            document_type="board_resolution",
            facts=facts,
        )
        return FactStore(extractions=[extraction])

    def test_elaborate_success(self, mock_llm_client, sample_fact_store):
        elaborator = Elaborator(mock_llm_client)
        request = ElaborationRequest(
            block_id="test_block",
            hint="Generate content",
        )

        result = elaborator.elaborate(request, sample_fact_store)

        assert result.status == "generated"
        assert "Generated Content" in result.generated_markdown
        assert result.confidence == 0.95

    def test_elaborate_empty_facts(self, mock_llm_client):
        elaborator = Elaborator(mock_llm_client)
        empty_store = FactStore(extractions=[])

        request = ElaborationRequest(
            block_id="test_block",
            hint="Generate content",
        )

        result = elaborator.elaborate(request, empty_store)

        assert result.status == "empty"
        assert "REQUIRES REVIEW" in result.generated_markdown

    def test_elaborate_handles_error(self, mock_llm_client, sample_fact_store):
        mock_llm_client.elaborate_section.side_effect = Exception("API error")
        elaborator = Elaborator(mock_llm_client)

        request = ElaborationRequest(
            block_id="test_block",
            hint="Generate content",
        )

        result = elaborator.elaborate(request, sample_fact_store)

        assert result.status == "error"
        assert "API error" in result.reason

    def test_elaborate_all(self, mock_llm_client, sample_fact_store):
        elaborator = Elaborator(mock_llm_client)

        requests = [
            ElaborationRequest(block_id="b1", hint="hint1"),
            ElaborationRequest(block_id="b2", hint="hint2"),
        ]

        elaborations = elaborator.elaborate_all(requests, sample_fact_store)

        assert len(elaborations.results) == 2
        assert mock_llm_client.elaborate_section.call_count == 2

    def test_elaborate_all_with_progress(self, mock_llm_client, sample_fact_store):
        elaborator = Elaborator(mock_llm_client)
        progress_calls = []

        def track_progress(block_id, idx, total):
            progress_calls.append((block_id, idx, total))

        requests = [
            ElaborationRequest(block_id="b1", hint="hint1"),
            ElaborationRequest(block_id="b2", hint="hint2"),
        ]

        elaborator.elaborate_all(requests, sample_fact_store, track_progress)

        assert len(progress_calls) == 2
        assert progress_calls[0] == ("b1", 1, 2)
        assert progress_calls[1] == ("b2", 2, 2)

    def test_save_elaborations(self, mock_llm_client, tmp_path):
        elaborations = Elaborations(results=[
            ElaborationResult(block_id="b1", status="generated", generated_markdown="content")
        ])
        elaborator = Elaborator(mock_llm_client)

        output_path = tmp_path / "out" / "elaborations.json"
        elaborator.save_elaborations(elaborations, output_path)

        assert output_path.exists()
        data = json.loads(output_path.read_text())
        assert data["summary"]["generated"] == 1


class TestRendererWithElaboration:
    """Tests for renderer with elaboration blocks (Task 13.5)."""

    @pytest.fixture
    def mock_llm_client(self):
        return Mock()

    @pytest.fixture
    def template_with_elaboration(self, tmp_path):
        content = """# Test

Company: {{text:company_name}}

{{elaborate:details:Generate details}}
"""
        path = tmp_path / "template.md"
        path.write_text(content)

        parser = TemplateParser(path)
        return parser.parse()

    def test_render_with_elaborations(self, mock_llm_client, template_with_elaboration):
        from drhp_agent.fill.slot_filler import FilledSlots
        from drhp_agent.core.dtos import SlotFillResult, FactStore
        from drhp_agent.elaborate.elaborator import Elaborations, ElaborationResult
        from drhp_agent.render.renderer import SectionRenderer

        filled_slots = FilledSlots(results=[
            SlotFillResult(
                slot_id="company_name",
                status="filled",
                value="Test Corp",
                source_files=["doc.md"],
            )
        ])

        elaborations = Elaborations(results=[
            ElaborationResult(
                block_id="details",
                status="generated",
                generated_markdown="## Details\n\nGenerated prose here.",
                source_facts=["F001"],
                source_files=["doc.md"],
            )
        ])

        fact_store = FactStore(extractions=[])
        renderer = SectionRenderer(mock_llm_client)

        result = renderer.render(
            template_with_elaboration,
            filled_slots,
            fact_store,
            elaborations=elaborations,
        )

        assert "Test Corp" in result.section_markdown
        assert "Generated prose here" in result.section_markdown
        assert "{{elaborate:" not in result.section_markdown

    def test_render_missing_elaboration_creates_flag(self, mock_llm_client, template_with_elaboration):
        from drhp_agent.fill.slot_filler import FilledSlots
        from drhp_agent.core.dtos import SlotFillResult, FactStore
        from drhp_agent.elaborate.elaborator import Elaborations
        from drhp_agent.render.renderer import SectionRenderer

        filled_slots = FilledSlots(results=[
            SlotFillResult(slot_id="company_name", status="filled", value="Test Corp")
        ])

        # Empty elaborations - block not processed
        elaborations = Elaborations(results=[])

        fact_store = FactStore(extractions=[])
        renderer = SectionRenderer(mock_llm_client)

        result = renderer.render(
            template_with_elaboration,
            filled_slots,
            fact_store,
            elaborations=elaborations,
        )

        assert "REQUIRES REVIEW" in result.section_markdown
        assert len(result.review_flags) >= 1
