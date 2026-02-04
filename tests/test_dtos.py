"""Unit tests for core DTOs.

Task 12.1: Unit tests for DTO schema validation.
"""

import pytest
from datetime import datetime

from drhp_agent.core.dtos import (
    AnnotationRecord,
    ChunkInfo,
    DocumentMetadata,
    EvidenceRef,
    FilledSlotsResult,
    PipelineConfig,
    ReviewFlag,
    RunManifest,
    SectionTemplate,
    SlotFill,
    SlotSpec,
    StageStatus,
    TableCell,
    TableInfo,
    TemplateNode,
    ValidationIssue,
)
from drhp_agent.core.enums import (
    EnumConflictPolicy,
    EnumDateStyle,
    EnumEvidenceType,
    EnumFillStatus,
    EnumNodeType,
    EnumNumberStyle,
    EnumPipelineMode,
    EnumRetrieverMode,
    EnumReviewFlagType,
    EnumSectionKey,
    EnumSlotKind,
    EnumSourceType,
    EnumValidationSeverity,
)


class TestSlotSpec:
    """Tests for SlotSpec DTO."""

    def test_minimal_creation(self):
        spec = SlotSpec(
            slot_id="S_test",
            kind=EnumSlotKind.AMOUNT,
        )
        assert spec.slot_id == "S_test"
        assert spec.kind == EnumSlotKind.AMOUNT
        assert spec.required is True
        assert spec.hint is None

    def test_full_creation(self):
        spec = SlotSpec(
            slot_id="S_net_proceeds",
            kind=EnumSlotKind.AMOUNT,
            hint="Net Proceeds",
            context_window="The issue proceeds...",
            expected_source_types=["financial_statements"],
            required=True,
            default_value=0,
        )
        assert spec.hint == "Net Proceeds"
        assert len(spec.expected_source_types) == 1


class TestTemplateNode:
    """Tests for TemplateNode DTO."""

    def test_heading_node(self):
        node = TemplateNode(
            node_id="N_001",
            node_type=EnumNodeType.HEADING,
            text="OBJECTS OF THE ISSUE",
            level=1,
        )
        assert node.level == 1
        assert node.children == []
        assert node.slots == []

    def test_paragraph_node_with_slots(self):
        slot = SlotSpec(slot_id="S_1", kind=EnumSlotKind.AMOUNT)
        node = TemplateNode(
            node_id="N_002",
            node_type=EnumNodeType.PARAGRAPH,
            text="The proceeds amount to...",
            slots=[slot],
        )
        assert len(node.slots) == 1
        assert node.slots[0].slot_id == "S_1"

    def test_table_node(self):
        node = TemplateNode(
            node_id="N_003",
            node_type=EnumNodeType.TABLE,
            table_id="T_utilization",
            headers=["Particulars", "Amount"],
            rows=[],
        )
        assert node.table_id == "T_utilization"
        assert len(node.headers) == 2


class TestEvidenceRef:
    """Tests for EvidenceRef DTO."""

    def test_text_span_evidence(self):
        ref = EvidenceRef(
            evidence_id="E_001",
            evidence_type=EnumEvidenceType.TEXT_SPAN,
            doc_id="doc_1",
            doc_path="/docs/test.md",
            char_start=100,
            char_end=150,
            line_start=10,
            line_end=10,
            excerpt="The amount is 850 lakhs",
        )
        assert ref.evidence_type == EnumEvidenceType.TEXT_SPAN
        assert ref.char_start == 100

    def test_table_cell_evidence(self):
        ref = EvidenceRef(
            evidence_id="E_002",
            evidence_type=EnumEvidenceType.TABLE_CELL,
            doc_id="doc_2",
            doc_path="/docs/financials.md",
            table_id="T_001",
            row=5,
            col=2,
        )
        assert ref.evidence_type == EnumEvidenceType.TABLE_CELL
        assert ref.row == 5


class TestSlotFill:
    """Tests for SlotFill DTO."""

    def test_filled_slot(self):
        ref = EvidenceRef(
            evidence_id="E_1",
            evidence_type=EnumEvidenceType.TEXT_SPAN,
            doc_id="d1",
            doc_path="test.md",
        )
        fill = SlotFill(
            slot_id="S_amount",
            status=EnumFillStatus.FILLED,
            value=850.0,
            formatted_value="₹ 850.00 lakhs",
            unit="lakhs",
            confidence=0.95,
            evidence_refs=[ref],
        )
        assert fill.status == EnumFillStatus.FILLED
        assert fill.confidence == 0.95
        assert len(fill.evidence_refs) == 1

    def test_missing_slot(self):
        fill = SlotFill(
            slot_id="S_missing",
            status=EnumFillStatus.MISSING,
            confidence=0.0,
            reason="Not found in supporting docs",
        )
        assert fill.status == EnumFillStatus.MISSING
        assert fill.value is None


class TestValidationIssue:
    """Tests for ValidationIssue DTO."""

    def test_error_issue(self):
        issue = ValidationIssue(
            issue_id="V_001",
            severity=EnumValidationSeverity.ERROR,
            message="Sum does not match total",
            slot_ids=["S_1", "S_2", "S_total"],
            expected=1000,
            actual=950,
        )
        assert issue.severity == EnumValidationSeverity.ERROR
        assert len(issue.slot_ids) == 3


class TestPipelineConfig:
    """Tests for PipelineConfig DTO."""

    def test_default_values(self):
        config = PipelineConfig(
            section="objects",
            drhp_md="/path/to/drhp.md",
            supporting_docs="/path/to/docs/",
            out_dir="/path/to/out/",
        )
        assert config.mode == EnumPipelineMode.STRICT
        assert config.retriever_mode == EnumRetrieverMode.HYBRID
        assert config.top_k == 10
        assert config.confidence_threshold == 0.7

    def test_custom_values(self):
        config = PipelineConfig(
            section="risk_factors",
            drhp_md="/drhp.md",
            supporting_docs="/docs/",
            out_dir="/out/",
            mode=EnumPipelineMode.DEBUG,
            retriever_mode=EnumRetrieverMode.BM25,
            top_k=20,
        )
        assert config.mode == EnumPipelineMode.DEBUG
        assert config.top_k == 20


class TestRunManifest:
    """Tests for RunManifest DTO."""

    def test_creation(self):
        manifest = RunManifest(
            run_id="run_001",
            started_at=datetime.now(),
            config_hash="abc123",
        )
        assert manifest.status == "pending"
        assert manifest.completed_at is None
        assert manifest.stages == []


class TestSectionTemplate:
    """Tests for SectionTemplate DTO."""

    def test_creation(self):
        root = TemplateNode(
            node_id="root",
            node_type=EnumNodeType.HEADING,
            text="Test Section",
            level=1,
        )
        template = SectionTemplate(
            section_key=EnumSectionKey.OBJECTS,
            section_title="Objects of the Issue",
            root_node=root,
        )
        assert template.section_key == EnumSectionKey.OBJECTS
        assert template.root_node.node_id == "root"


class TestFilledSlotsResult:
    """Tests for FilledSlotsResult DTO."""

    def test_creation(self):
        fill = SlotFill(
            slot_id="S_1",
            status=EnumFillStatus.FILLED,
            value=100,
        )
        result = FilledSlotsResult(
            section_key=EnumSectionKey.OBJECTS,
            fills={"S_1": fill},
            fill_rate=1.0,
        )
        assert len(result.fills) == 1
        assert result.fill_rate == 1.0
