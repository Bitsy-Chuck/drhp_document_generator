"""Tests for section renderer (Tasks 8.1-8.10)."""

import pytest
from pathlib import Path

from drhp_agent.render.renderer import SectionRenderer, RenderResult
from drhp_agent.fill.slot_filler import FilledSlots
from drhp_agent.md_template.parser import ParsedTemplate, ParsedSlot
from drhp_agent.core.dtos import (
    SlotFillResult,
    FactStore,
    DocumentExtraction,
    ExtractedFact,
    FactLocation,
)
from drhp_agent.core.enums import EnumReviewFlagType, EnumValidationSeverity
from unittest.mock import Mock


class TestSectionRenderer:
    """Tests for SectionRenderer."""

    @pytest.fixture
    def mock_llm_client(self):
        return Mock()

    @pytest.fixture
    def simple_template(self):
        return ParsedTemplate(
            file_path="/test/template.md",
            content="# Title\nThe company {{text:company_name}} has {{integer:shares}} shares.",
            slots=[
                ParsedSlot(
                    slot_id="company_name",
                    slot_type="text",
                    hint="Company name",
                    raw_marker="{{text:company_name}}",
                    line_number=2,
                    context="company",
                ),
                ParsedSlot(
                    slot_id="shares",
                    slot_type="integer",
                    hint="Number of shares",
                    raw_marker="{{integer:shares}}",
                    line_number=2,
                    context="shares",
                ),
            ],
        )

    @pytest.fixture
    def filled_slots(self):
        return FilledSlots(results=[
            SlotFillResult(
                slot_id="company_name",
                status="filled",
                value="Test Corp",
                formatted_value="Test Corp",
                source_facts=["F001"],
                source_files=["doc.md"],
                confidence=0.95,
            ),
            SlotFillResult(
                slot_id="shares",
                status="filled",
                value=30000,
                formatted_value="30,000",
                source_facts=["F002"],
                source_files=["doc.md"],
                confidence=0.90,
            ),
        ])

    @pytest.fixture
    def empty_fact_store(self):
        return FactStore(extractions=[])

    def test_render_replaces_slots(self, mock_llm_client, simple_template, filled_slots, empty_fact_store):
        renderer = SectionRenderer(mock_llm_client)
        result = renderer.render(simple_template, filled_slots, empty_fact_store)

        assert "Test Corp" in result.section_markdown
        assert "30,000" in result.section_markdown
        assert "{{" not in result.section_markdown

    def test_render_adds_source_citations(self, mock_llm_client, simple_template, filled_slots, empty_fact_store):
        renderer = SectionRenderer(mock_llm_client)
        result = renderer.render(simple_template, filled_slots, empty_fact_store)

        assert "[Source: doc.md]" in result.section_markdown

    def test_render_creates_annotations(self, mock_llm_client, simple_template, filled_slots, empty_fact_store):
        renderer = SectionRenderer(mock_llm_client)
        result = renderer.render(simple_template, filled_slots, empty_fact_store)

        assert len(result.annotations) == 2
        assert result.annotations[0].slot_id == "company_name"
        assert result.annotations[0].source_facts == ["F001"]

    def test_render_missing_slot_creates_flag(self, mock_llm_client, simple_template, empty_fact_store):
        filled = FilledSlots(results=[
            SlotFillResult(
                slot_id="company_name",
                status="filled",
                value="Test Corp",
                formatted_value="Test Corp",
                source_files=["doc.md"],
                confidence=0.95,
            ),
            SlotFillResult(
                slot_id="shares",
                status="missing",
                reason="No data found",
            ),
        ])

        renderer = SectionRenderer(mock_llm_client)
        result = renderer.render(simple_template, filled, empty_fact_store)

        assert "[[REQUIRES REVIEW:" in result.section_markdown
        assert len(result.review_flags) == 1
        assert result.review_flags[0].flag_type == EnumReviewFlagType.MISSING_FACT

    def test_render_conflict_creates_flag(self, mock_llm_client, simple_template, empty_fact_store):
        filled = FilledSlots(results=[
            SlotFillResult(
                slot_id="company_name",
                status="conflict",
                reason="Values differ: A vs B",
            ),
            SlotFillResult(
                slot_id="shares",
                status="filled",
                value=30000,
                formatted_value="30,000",
                source_files=["doc.md"],
                confidence=0.95,
            ),
        ])

        renderer = SectionRenderer(mock_llm_client)
        result = renderer.render(simple_template, filled, empty_fact_store)

        assert "[[REQUIRES REVIEW:" in result.section_markdown
        conflict_flags = [f for f in result.review_flags if f.flag_type == EnumReviewFlagType.CONFLICTING_FACTS]
        assert len(conflict_flags) == 1

    def test_render_low_confidence_adds_warning(self, mock_llm_client, simple_template, empty_fact_store):
        filled = FilledSlots(results=[
            SlotFillResult(
                slot_id="company_name",
                status="filled",
                value="Test Corp",
                formatted_value="Test Corp",
                source_files=["doc.md"],
                confidence=0.95,
            ),
            SlotFillResult(
                slot_id="shares",
                status="low_confidence",
                value=30000,
                formatted_value="30,000",
                source_files=["doc.md"],
                confidence=0.4,
            ),
        ])

        renderer = SectionRenderer(mock_llm_client)
        result = renderer.render(simple_template, filled, empty_fact_store)

        # Low confidence should show value with warning
        assert "30,000" in result.section_markdown
        low_conf_flags = [f for f in result.review_flags if f.flag_type == EnumReviewFlagType.LOW_CONFIDENCE]
        assert len(low_conf_flags) == 1

    def test_save_section(self, mock_llm_client, tmp_path):
        result = RenderResult(
            section_markdown="# Test\nContent here.",
            annotations=[],
            review_flags=[],
        )
        renderer = SectionRenderer(mock_llm_client)

        output_path = tmp_path / "section.md"
        renderer.save_section(result, output_path)

        assert output_path.exists()
        assert "# Test" in output_path.read_text()

    def test_save_annotations(self, mock_llm_client, tmp_path):
        from drhp_agent.render.renderer import AnnotationRecord

        result = RenderResult(
            section_markdown="content",
            annotations=[
                AnnotationRecord(
                    annotation_id="A_001",
                    slot_id="test",
                    value=100,
                    source_facts=["F001"],
                    source_files=["doc.md"],
                    confidence=0.9,
                )
            ],
            review_flags=[],
        )
        renderer = SectionRenderer(mock_llm_client)

        output_path = tmp_path / "annotations.jsonl"
        renderer.save_annotations(result, output_path)

        assert output_path.exists()
        import json
        line = output_path.read_text().strip()
        data = json.loads(line)
        assert data["slot_id"] == "test"

    def test_save_review_flags(self, mock_llm_client, tmp_path):
        from drhp_agent.core.dtos import ReviewFlag

        result = RenderResult(
            section_markdown="content",
            annotations=[],
            review_flags=[
                ReviewFlag(
                    flag_id="RF_001",
                    flag_type=EnumReviewFlagType.MISSING_FACT,
                    severity=EnumValidationSeverity.WARN,
                    message="Data not found",
                    slot_ids=["test_slot"],
                )
            ],
        )
        renderer = SectionRenderer(mock_llm_client)

        output_path = tmp_path / "flags.md"
        renderer.save_review_flags(result, output_path)

        assert output_path.exists()
        content = output_path.read_text()
        assert "Review Flags" in content
        assert "RF_001" in content
        assert "MISSING_FACT" in content.lower() or "missing_fact" in content

    def test_save_review_flags_empty(self, mock_llm_client, tmp_path):
        result = RenderResult(
            section_markdown="content",
            annotations=[],
            review_flags=[],
        )
        renderer = SectionRenderer(mock_llm_client)

        output_path = tmp_path / "flags.md"
        renderer.save_review_flags(result, output_path)

        content = output_path.read_text()
        assert "No review flags" in content or "successfully" in content.lower()


class TestSectionRendererEdgeCases:
    """Edge case tests for SectionRenderer."""

    @pytest.fixture
    def mock_llm_client(self):
        return Mock()

    @pytest.fixture
    def empty_fact_store(self):
        return FactStore(extractions=[])

    def test_render_slot_not_in_fill_requests(self, mock_llm_client, empty_fact_store):
        """Slot in template but not processed should create error flag."""
        template = ParsedTemplate(
            file_path="/test.md",
            content="Company: {{text:company_name}} and {{text:unknown_slot}}",
            slots=[
                ParsedSlot(slot_id="company_name", slot_type="text", hint=None,
                           raw_marker="{{text:company_name}}", line_number=1, context=""),
                ParsedSlot(slot_id="unknown_slot", slot_type="text", hint=None,
                           raw_marker="{{text:unknown_slot}}", line_number=1, context=""),
            ],
        )
        # Only fill one slot, leave the other unprocessed
        filled = FilledSlots(results=[
            SlotFillResult(
                slot_id="company_name", status="filled",
                value="Test Corp", formatted_value="Test Corp",
                source_files=["doc.md"], confidence=0.95,
            ),
            # unknown_slot is NOT in results
        ])

        renderer = SectionRenderer(mock_llm_client)
        result = renderer.render(template, filled, empty_fact_store)

        assert "[[REQUIRES REVIEW:" in result.section_markdown
        assert "unknown_slot" in result.section_markdown

    def test_render_multiple_source_files_citation(self, mock_llm_client, empty_fact_store):
        """When value has multiple sources, should cite first one."""
        template = ParsedTemplate(
            file_path="/test.md",
            content="Value: {{amount:total}}",
            slots=[ParsedSlot(slot_id="total", slot_type="amount", hint=None,
                              raw_marker="{{amount:total}}", line_number=1, context="")],
        )
        filled = FilledSlots(results=[
            SlotFillResult(
                slot_id="total", status="filled",
                value=100000, formatted_value="₹ 1,00,000",
                source_facts=["F001", "F002"],
                source_files=["pas3.md", "resolution.md", "allottees.md"],
                confidence=0.95,
            ),
        ])

        renderer = SectionRenderer(mock_llm_client)
        result = renderer.render(template, filled, empty_fact_store)

        assert "[Source: pas3.md]" in result.section_markdown

    def test_render_empty_annotations_file(self, mock_llm_client, tmp_path):
        """Empty annotations should create empty file."""
        result = RenderResult(
            section_markdown="content",
            annotations=[],
            review_flags=[],
        )
        renderer = SectionRenderer(mock_llm_client)

        output_path = tmp_path / "annotations.jsonl"
        renderer.save_annotations(result, output_path)

        assert output_path.exists()
        assert output_path.read_text().strip() == ""

    def test_render_many_review_flags_grouped_by_severity(self, mock_llm_client, tmp_path):
        """Many flags should be grouped by severity in output."""
        from drhp_agent.core.dtos import ReviewFlag

        flags = [
            ReviewFlag(flag_id="RF_001", flag_type=EnumReviewFlagType.MISSING_FACT,
                       severity=EnumValidationSeverity.CRITICAL, message="Critical 1"),
            ReviewFlag(flag_id="RF_002", flag_type=EnumReviewFlagType.MISSING_FACT,
                       severity=EnumValidationSeverity.ERROR, message="Error 1"),
            ReviewFlag(flag_id="RF_003", flag_type=EnumReviewFlagType.LOW_CONFIDENCE,
                       severity=EnumValidationSeverity.WARN, message="Warning 1"),
            ReviewFlag(flag_id="RF_004", flag_type=EnumReviewFlagType.LOW_CONFIDENCE,
                       severity=EnumValidationSeverity.INFO, message="Info 1"),
            ReviewFlag(flag_id="RF_005", flag_type=EnumReviewFlagType.CONFLICTING_FACTS,
                       severity=EnumValidationSeverity.ERROR, message="Error 2"),
        ]
        result = RenderResult(
            section_markdown="content",
            annotations=[],
            review_flags=flags,
        )
        renderer = SectionRenderer(mock_llm_client)

        output_path = tmp_path / "flags.md"
        renderer.save_review_flags(result, output_path)

        content = output_path.read_text()
        # Check severity sections appear
        assert "Critical" in content
        assert "Error" in content
        assert "Warning" in content
        assert "Info" in content
        # Check counts
        assert "5" in content or "Total: 5" in content or "5 flags" in content

    def test_render_preserves_markdown_structure(self, mock_llm_client, empty_fact_store):
        """Rendering should preserve markdown structure (headers, tables, lists)."""
        template = ParsedTemplate(
            file_path="/test.md",
            content="""# Main Title

## Section 1

| Column A | Column B |
|----------|----------|
| {{text:value_a}} | {{text:value_b}} |

- Item: {{text:item}}

**Bold text** with {{text:inline}}.
""",
            slots=[
                ParsedSlot(slot_id="value_a", slot_type="text", hint=None,
                           raw_marker="{{text:value_a}}", line_number=7, context=""),
                ParsedSlot(slot_id="value_b", slot_type="text", hint=None,
                           raw_marker="{{text:value_b}}", line_number=7, context=""),
                ParsedSlot(slot_id="item", slot_type="text", hint=None,
                           raw_marker="{{text:item}}", line_number=9, context=""),
                ParsedSlot(slot_id="inline", slot_type="text", hint=None,
                           raw_marker="{{text:inline}}", line_number=11, context=""),
            ],
        )
        filled = FilledSlots(results=[
            SlotFillResult(slot_id="value_a", status="filled", value="A1",
                           formatted_value="A1", source_files=["doc.md"], confidence=0.9),
            SlotFillResult(slot_id="value_b", status="filled", value="B1",
                           formatted_value="B1", source_files=["doc.md"], confidence=0.9),
            SlotFillResult(slot_id="item", status="filled", value="Item 1",
                           formatted_value="Item 1", source_files=["doc.md"], confidence=0.9),
            SlotFillResult(slot_id="inline", status="filled", value="text",
                           formatted_value="text", source_files=["doc.md"], confidence=0.9),
        ])

        renderer = SectionRenderer(mock_llm_client)
        result = renderer.render(template, filled, empty_fact_store)

        # Check structure preserved
        assert "# Main Title" in result.section_markdown
        assert "## Section 1" in result.section_markdown
        assert "| Column A |" in result.section_markdown
        assert "- Item:" in result.section_markdown
        assert "**Bold text**" in result.section_markdown

    def test_render_validation_issues_become_flags(self, mock_llm_client, empty_fact_store):
        """Validation issues should be added as review flags."""
        from drhp_agent.validate.validator import ValidationResult
        from drhp_agent.core.dtos import ValidationIssue

        template = ParsedTemplate(
            file_path="/test.md",
            content="Content: {{text:slot}}",
            slots=[ParsedSlot(slot_id="slot", slot_type="text", hint=None,
                              raw_marker="{{text:slot}}", line_number=1, context="")],
        )
        filled = FilledSlots(results=[
            SlotFillResult(slot_id="slot", status="filled", value="Test",
                           formatted_value="Test", source_files=["doc.md"], confidence=0.9),
        ])
        validation = ValidationResult(
            is_valid=False,
            issues=[
                ValidationIssue(
                    issue_id="V1",
                    severity=EnumValidationSeverity.ERROR,
                    message="Values do not match across documents",
                    slot_ids=["slot"],
                    suggestion="Verify manually",
                ),
            ],
        )

        renderer = SectionRenderer(mock_llm_client)
        result = renderer.render(template, filled, empty_fact_store, validation)

        # Validation issue should become a review flag
        assert len(result.review_flags) >= 1
        reconciliation_flags = [f for f in result.review_flags
                                if f.flag_type == EnumReviewFlagType.FAILED_RECONCILIATION]
        assert len(reconciliation_flags) == 1

    def test_render_with_no_source_files(self, mock_llm_client, empty_fact_store):
        """Filled slot with no source files should render without citation."""
        template = ParsedTemplate(
            file_path="/test.md",
            content="Value: {{text:slot}}",
            slots=[ParsedSlot(slot_id="slot", slot_type="text", hint=None,
                              raw_marker="{{text:slot}}", line_number=1, context="")],
        )
        filled = FilledSlots(results=[
            SlotFillResult(
                slot_id="slot", status="filled",
                value="Test Value", formatted_value="Test Value",
                source_facts=[], source_files=[],  # No sources
                confidence=0.9,
            ),
        ])

        renderer = SectionRenderer(mock_llm_client)
        result = renderer.render(template, filled, empty_fact_store)

        assert "Test Value" in result.section_markdown
        assert "[Source:" not in result.section_markdown  # No citation

    def test_render_unknown_status_creates_flag(self, mock_llm_client, empty_fact_store):
        """Unknown slot status should create review flag."""
        template = ParsedTemplate(
            file_path="/test.md",
            content="Value: {{text:slot}}",
            slots=[ParsedSlot(slot_id="slot", slot_type="text", hint=None,
                              raw_marker="{{text:slot}}", line_number=1, context="")],
        )
        filled = FilledSlots(results=[
            SlotFillResult(
                slot_id="slot",
                status="unknown_status",  # Invalid status
                value="Test",
            ),
        ])

        renderer = SectionRenderer(mock_llm_client)
        result = renderer.render(template, filled, empty_fact_store)

        assert "[[REQUIRES REVIEW:" in result.section_markdown
        assert "unknown_status" in result.section_markdown
