"""Serializers for converting DTOs to/from JSON.

Supports artifact persistence and loading.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar

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
from drhp_agent.core.schemas import (
    validate_annotation_record,
    validate_filled_slots,
    validate_run_manifest,
    validate_section_template,
)

T = TypeVar("T")


class DTOEncoder(json.JSONEncoder):
    """JSON encoder for DTOs with enum and datetime support."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, datetime):
            return obj.isoformat()
        if is_dataclass(obj) and not isinstance(obj, type):
            return asdict(obj)
        if isinstance(obj, Path):
            return str(obj)
        return super().default(obj)


def _serialize_dto(obj: Any) -> dict[str, Any]:
    """Serialize a dataclass to a dictionary."""
    if is_dataclass(obj) and not isinstance(obj, type):
        result = {}
        for key, value in asdict(obj).items():
            if isinstance(value, Enum):
                result[key] = value.value
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, list):
                result[key] = [_serialize_value(v) for v in value]
            elif isinstance(value, dict):
                result[key] = {k: _serialize_value(v) for k, v in value.items()}
            else:
                result[key] = value
        return result
    raise TypeError(f"Expected dataclass, got {type(obj)}")


def _serialize_value(value: Any) -> Any:
    """Serialize a value for JSON."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return _serialize_dto(value)
    if isinstance(value, list):
        return [_serialize_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    return value


def serialize_section_template(template: SectionTemplate) -> dict[str, Any]:
    """Serialize a SectionTemplate to JSON-compatible dict."""
    return _serialize_dto(template)


def serialize_filled_slots(result: FilledSlotsResult) -> dict[str, Any]:
    """Serialize a FilledSlotsResult to JSON-compatible dict."""
    return _serialize_dto(result)


def serialize_annotation_record(record: AnnotationRecord) -> dict[str, Any]:
    """Serialize an AnnotationRecord to JSON-compatible dict."""
    return _serialize_dto(record)


def serialize_run_manifest(manifest: RunManifest) -> dict[str, Any]:
    """Serialize a RunManifest to JSON-compatible dict."""
    return _serialize_dto(manifest)


def _parse_enum(enum_cls: type[T], value: str | T | None) -> T | None:
    """Parse a string into an enum, or return None."""
    if value is None:
        return None
    if isinstance(value, enum_cls):
        return value
    return enum_cls(value)


def _parse_datetime(value: str | datetime | None) -> datetime | None:
    """Parse an ISO datetime string, or return None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def deserialize_slot_spec(data: dict[str, Any]) -> SlotSpec:
    """Deserialize a SlotSpec from dict."""
    return SlotSpec(
        slot_id=data["slot_id"],
        kind=EnumSlotKind(data["kind"]),
        hint=data.get("hint"),
        context_window=data.get("context_window"),
        expected_source_types=data.get("expected_source_types", []),
        required=data.get("required", True),
        default_value=data.get("default_value"),
    )


def deserialize_table_cell(data: dict[str, Any]) -> TableCell:
    """Deserialize a TableCell from dict."""
    return TableCell(
        text=data["text"],
        row=data["row"],
        col=data["col"],
        slots=[deserialize_slot_spec(s) for s in data.get("slots", [])],
        is_header=data.get("is_header", False),
    )


def deserialize_template_node(data: dict[str, Any]) -> TemplateNode:
    """Deserialize a TemplateNode from dict."""
    rows = None
    if data.get("rows") is not None:
        rows = [[deserialize_table_cell(c) for c in row] for row in data["rows"]]

    return TemplateNode(
        node_id=data["node_id"],
        node_type=EnumNodeType(data["node_type"]),
        text=data.get("text"),
        level=data.get("level"),
        children=[deserialize_template_node(c) for c in data.get("children", [])],
        slots=[deserialize_slot_spec(s) for s in data.get("slots", [])],
        table_id=data.get("table_id"),
        headers=data.get("headers"),
        rows=rows,
        ordered=data.get("ordered"),
        source_line_start=data.get("source_line_start"),
        source_line_end=data.get("source_line_end"),
        raw_text=data.get("raw_text"),
        is_boilerplate=data.get("is_boilerplate", False),
    )


def deserialize_section_template(data: dict[str, Any]) -> SectionTemplate:
    """Deserialize a SectionTemplate from dict."""
    return SectionTemplate(
        section_key=EnumSectionKey(data["section_key"]),
        section_title=data["section_title"],
        root_node=deserialize_template_node(data["root_node"]),
        slot_specs={k: deserialize_slot_spec(v) for k, v in data.get("slot_specs", {}).items()},
        source_file=data.get("source_file"),
        source_line_start=data.get("source_line_start"),
        source_line_end=data.get("source_line_end"),
    )


def deserialize_evidence_ref(data: dict[str, Any]) -> EvidenceRef:
    """Deserialize an EvidenceRef from dict."""
    return EvidenceRef(
        evidence_id=data["evidence_id"],
        evidence_type=EnumEvidenceType(data["evidence_type"]),
        doc_id=data["doc_id"],
        doc_path=data["doc_path"],
        char_start=data.get("char_start"),
        char_end=data.get("char_end"),
        line_start=data.get("line_start"),
        line_end=data.get("line_end"),
        table_id=data.get("table_id"),
        row=data.get("row"),
        col=data.get("col"),
        heading_path=data.get("heading_path", []),
        excerpt=data.get("excerpt"),
    )


def deserialize_slot_fill(data: dict[str, Any]) -> SlotFill:
    """Deserialize a SlotFill from dict."""
    return SlotFill(
        slot_id=data["slot_id"],
        status=EnumFillStatus(data["status"]),
        value=data.get("value"),
        formatted_value=data.get("formatted_value"),
        unit=data.get("unit"),
        confidence=data.get("confidence", 0.0),
        evidence_refs=[deserialize_evidence_ref(e) for e in data.get("evidence_refs", [])],
        reason=data.get("reason"),
        candidates=data.get("candidates", []),
        conflicts=data.get("conflicts", []),
    )


def deserialize_validation_issue(data: dict[str, Any]) -> ValidationIssue:
    """Deserialize a ValidationIssue from dict."""
    return ValidationIssue(
        issue_id=data["issue_id"],
        severity=EnumValidationSeverity(data["severity"]),
        message=data["message"],
        slot_ids=data.get("slot_ids", []),
        node_ids=data.get("node_ids", []),
        expected=data.get("expected"),
        actual=data.get("actual"),
        suggestion=data.get("suggestion"),
    )


def deserialize_filled_slots(data: dict[str, Any]) -> FilledSlotsResult:
    """Deserialize a FilledSlotsResult from dict."""
    return FilledSlotsResult(
        section_key=EnumSectionKey(data["section_key"]),
        fills={k: deserialize_slot_fill(v) for k, v in data.get("fills", {}).items()},
        fill_rate=data.get("fill_rate", 0.0),
        missing_count=data.get("missing_count", 0),
        conflict_count=data.get("conflict_count", 0),
        validation_issues=[deserialize_validation_issue(v) for v in data.get("validation_issues", [])],
    )


def deserialize_annotation_record(data: dict[str, Any]) -> AnnotationRecord:
    """Deserialize an AnnotationRecord from dict."""
    return AnnotationRecord(
        annotation_id=data["annotation_id"],
        output_span_start=data["output_span_start"],
        output_span_end=data["output_span_end"],
        slot_id=data["slot_id"],
        evidence_refs=[deserialize_evidence_ref(e) for e in data.get("evidence_refs", [])],
        output_file=data["output_file"],
        output_line=data.get("output_line"),
    )


def deserialize_pipeline_config(data: dict[str, Any]) -> PipelineConfig:
    """Deserialize a PipelineConfig from dict."""
    return PipelineConfig(
        section=data["section"],
        drhp_md=data["drhp_md"],
        supporting_docs=data["supporting_docs"],
        out_dir=data["out_dir"],
        mode=_parse_enum(EnumPipelineMode, data.get("mode")) or EnumPipelineMode.STRICT,
        retriever_mode=_parse_enum(EnumRetrieverMode, data.get("retriever_mode")) or EnumRetrieverMode.HYBRID,
        conflict_policy=_parse_enum(EnumConflictPolicy, data.get("conflict_policy"))
        or EnumConflictPolicy.HIGHEST_CONFIDENCE,
        date_style=_parse_enum(EnumDateStyle, data.get("date_style")) or EnumDateStyle.LONG_IN,
        number_style=_parse_enum(EnumNumberStyle, data.get("number_style")) or EnumNumberStyle.LAKH_CRORE,
        top_k=data.get("top_k", 10),
        chunk_size=data.get("chunk_size", 500),
        chunk_overlap=data.get("chunk_overlap", 50),
        confidence_threshold=data.get("confidence_threshold", 0.7),
        reconciliation_tolerance=data.get("reconciliation_tolerance", 0.01),
        config_hash=data.get("config_hash"),
    )


def deserialize_stage_status(data: dict[str, Any]) -> StageStatus:
    """Deserialize a StageStatus from dict."""
    return StageStatus(
        stage_name=data["stage_name"],
        status=data["status"],
        started_at=_parse_datetime(data.get("started_at")),
        completed_at=_parse_datetime(data.get("completed_at")),
        error=data.get("error"),
        artifacts=data.get("artifacts", []),
    )


def deserialize_run_manifest(data: dict[str, Any]) -> RunManifest:
    """Deserialize a RunManifest from dict."""
    config = None
    if data.get("config"):
        config = deserialize_pipeline_config(data["config"])

    return RunManifest(
        run_id=data["run_id"],
        started_at=_parse_datetime(data["started_at"]) or datetime.now(),
        completed_at=_parse_datetime(data.get("completed_at")),
        config=config,
        config_hash=data["config_hash"],
        input_files=data.get("input_files", []),
        input_checksums=data.get("input_checksums", {}),
        stages=[deserialize_stage_status(s) for s in data.get("stages", [])],
        output_files=data.get("output_files", []),
        status=data.get("status", "pending"),
        error=data.get("error"),
    )


# File I/O helpers


def save_section_template(template: SectionTemplate, path: Path, validate: bool = True) -> None:
    """Save a SectionTemplate to a JSON file."""
    data = serialize_section_template(template)
    if validate:
        validate_section_template(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, cls=DTOEncoder))


def load_section_template(path: Path, validate: bool = True) -> SectionTemplate:
    """Load a SectionTemplate from a JSON file."""
    data = json.loads(path.read_text())
    if validate:
        validate_section_template(data)
    return deserialize_section_template(data)


def save_filled_slots(result: FilledSlotsResult, path: Path, validate: bool = True) -> None:
    """Save a FilledSlotsResult to a JSON file."""
    data = serialize_filled_slots(result)
    if validate:
        validate_filled_slots(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, cls=DTOEncoder))


def load_filled_slots(path: Path, validate: bool = True) -> FilledSlotsResult:
    """Load a FilledSlotsResult from a JSON file."""
    data = json.loads(path.read_text())
    if validate:
        validate_filled_slots(data)
    return deserialize_filled_slots(data)


def save_annotations(records: list[AnnotationRecord], path: Path, validate: bool = True) -> None:
    """Save annotation records to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for record in records:
            data = serialize_annotation_record(record)
            if validate:
                validate_annotation_record(data)
            f.write(json.dumps(data, cls=DTOEncoder) + "\n")


def load_annotations(path: Path, validate: bool = True) -> list[AnnotationRecord]:
    """Load annotation records from a JSONL file."""
    records = []
    with path.open() as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                if validate:
                    validate_annotation_record(data)
                records.append(deserialize_annotation_record(data))
    return records


def save_run_manifest(manifest: RunManifest, path: Path, validate: bool = True) -> None:
    """Save a RunManifest to a JSON file."""
    data = serialize_run_manifest(manifest)
    if validate:
        validate_run_manifest(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, cls=DTOEncoder))


def load_run_manifest(path: Path, validate: bool = True) -> RunManifest:
    """Load a RunManifest from a JSON file."""
    data = json.loads(path.read_text())
    if validate:
        validate_run_manifest(data)
    return deserialize_run_manifest(data)
