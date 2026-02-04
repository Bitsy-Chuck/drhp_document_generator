"""Unit tests for serializers.

Task 12.1: Unit tests for schema validation and serialization.
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
import tempfile

from drhp_agent.core.dtos import (
    AnnotationRecord,
    EvidenceRef,
    FilledSlotsResult,
    PipelineConfig,
    RunManifest,
    SectionTemplate,
    SlotFill,
    SlotSpec,
    TemplateNode,
    ValidationIssue,
)
from drhp_agent.core.enums import (
    EnumEvidenceType,
    EnumFillStatus,
    EnumNodeType,
    EnumSectionKey,
    EnumSlotKind,
    EnumValidationSeverity,
)
from drhp_agent.core.serializers import (
    deserialize_section_template,
    deserialize_filled_slots,
    deserialize_annotation_record,
    deserialize_run_manifest,
    serialize_section_template,
    serialize_filled_slots,
    serialize_annotation_record,
    serialize_run_manifest,
    save_section_template,
    load_section_template,
    save_filled_slots,
    load_filled_slots,
    save_annotations,
    load_annotations,
    DTOEncoder,
)


class TestDTOEncoder:
    """Tests for DTOEncoder."""

    def test_encodes_enum(self):
        result = json.dumps({"kind": EnumSlotKind.AMOUNT}, cls=DTOEncoder)
        assert '"amount"' in result

    def test_encodes_datetime(self):
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = json.dumps({"time": dt}, cls=DTOEncoder)
        assert "2024-01-15" in result


class TestSectionTemplateSerializer:
    """Tests for SectionTemplate serialization."""

    def test_round_trip(self):
        slot = SlotSpec(slot_id="S_1", kind=EnumSlotKind.AMOUNT, hint="Test")
        root = TemplateNode(
            node_id="N_1",
            node_type=EnumNodeType.HEADING,
            text="Test Section",
            level=1,
            slots=[slot],
        )
        template = SectionTemplate(
            section_key=EnumSectionKey.OBJECTS,
            section_title="Objects",
            root_node=root,
            slot_specs={"S_1": slot},
        )

        # Serialize
        data = serialize_section_template(template)
        assert data["section_key"] == "objects"
        assert data["root_node"]["node_type"] == "heading"

        # Deserialize
        restored = deserialize_section_template(data)
        assert restored.section_key == EnumSectionKey.OBJECTS
        assert restored.root_node.node_type == EnumNodeType.HEADING
        assert restored.root_node.slots[0].kind == EnumSlotKind.AMOUNT

    def test_file_round_trip(self):
        root = TemplateNode(
            node_id="N_1",
            node_type=EnumNodeType.PARAGRAPH,
            text="Test",
        )
        template = SectionTemplate(
            section_key=EnumSectionKey.RISK_FACTORS,
            section_title="Risk Factors",
            root_node=root,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "template.json"
            save_section_template(template, path, validate=False)
            restored = load_section_template(path, validate=False)

            assert restored.section_key == EnumSectionKey.RISK_FACTORS


class TestFilledSlotsSerializer:
    """Tests for FilledSlotsResult serialization."""

    def test_round_trip(self):
        ref = EvidenceRef(
            evidence_id="E_1",
            evidence_type=EnumEvidenceType.TEXT_SPAN,
            doc_id="doc_1",
            doc_path="/test.md",
            char_start=0,
            char_end=100,
        )
        fill = SlotFill(
            slot_id="S_1",
            status=EnumFillStatus.FILLED,
            value=850.0,
            confidence=0.9,
            evidence_refs=[ref],
        )
        result = FilledSlotsResult(
            section_key=EnumSectionKey.OBJECTS,
            fills={"S_1": fill},
            fill_rate=1.0,
        )

        # Serialize
        data = serialize_filled_slots(result)
        assert data["section_key"] == "objects"
        assert data["fills"]["S_1"]["status"] == "filled"

        # Deserialize
        restored = deserialize_filled_slots(data)
        assert restored.fills["S_1"].status == EnumFillStatus.FILLED
        assert restored.fills["S_1"].evidence_refs[0].evidence_type == EnumEvidenceType.TEXT_SPAN

    def test_file_round_trip(self):
        fill = SlotFill(
            slot_id="S_1",
            status=EnumFillStatus.MISSING,
            reason="Not found",
        )
        result = FilledSlotsResult(
            section_key=EnumSectionKey.OBJECTS,
            fills={"S_1": fill},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "filled.json"
            save_filled_slots(result, path, validate=False)
            restored = load_filled_slots(path, validate=False)

            assert restored.fills["S_1"].status == EnumFillStatus.MISSING


class TestAnnotationRecordSerializer:
    """Tests for AnnotationRecord serialization."""

    def test_round_trip(self):
        ref = EvidenceRef(
            evidence_id="E_1",
            evidence_type=EnumEvidenceType.TABLE_CELL,
            doc_id="doc_1",
            doc_path="/test.md",
            table_id="T_1",
            row=1,
            col=2,
        )
        record = AnnotationRecord(
            annotation_id="A_1",
            output_span_start=100,
            output_span_end=120,
            slot_id="S_1",
            evidence_refs=[ref],
            output_file="out.md",
            output_line=15,
        )

        # Serialize
        data = serialize_annotation_record(record)
        assert data["slot_id"] == "S_1"

        # Deserialize
        restored = deserialize_annotation_record(data)
        assert restored.evidence_refs[0].table_id == "T_1"

    def test_jsonl_round_trip(self):
        records = [
            AnnotationRecord(
                annotation_id="A_1",
                output_span_start=0,
                output_span_end=10,
                slot_id="S_1",
                evidence_refs=[],
                output_file="out.md",
            ),
            AnnotationRecord(
                annotation_id="A_2",
                output_span_start=20,
                output_span_end=30,
                slot_id="S_2",
                evidence_refs=[],
                output_file="out.md",
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "annotations.jsonl"
            save_annotations(records, path, validate=False)
            restored = load_annotations(path, validate=False)

            assert len(restored) == 2
            assert restored[0].annotation_id == "A_1"
            assert restored[1].slot_id == "S_2"


class TestRunManifestSerializer:
    """Tests for RunManifest serialization."""

    def test_round_trip(self):
        manifest = RunManifest(
            run_id="run_001",
            started_at=datetime(2024, 1, 15, 10, 0, 0),
            config_hash="abc123",
        )
        manifest.status = "running"
        manifest.input_files = ["/input/drhp.md"]

        # Serialize
        data = serialize_run_manifest(manifest)
        assert data["run_id"] == "run_001"
        assert "2024-01-15" in data["started_at"]

        # Deserialize
        restored = deserialize_run_manifest(data)
        assert restored.run_id == "run_001"
        assert restored.started_at.year == 2024
