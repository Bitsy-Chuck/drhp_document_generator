"""Slot filling DTOs.

SlotFill, SlotFillRequest, SlotFillResult, FilledSlotsResult.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from drhp_agent.core.enums import EnumFillStatus, EnumSectionKey
from drhp_agent.core.dtos.evidence import EvidenceRef
from drhp_agent.core.dtos.validation import ValidationIssue


@dataclass
class SlotFill:
    """Result of filling a slot with evidence-backed value."""

    slot_id: str
    status: EnumFillStatus
    value: Any = None
    formatted_value: str | None = None
    unit: str | None = None
    confidence: float = 0.0
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    reason: str | None = None
    candidates: list[dict[str, Any]] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SlotFillRequest:
    """Request to fill a template slot (input for LLM)."""

    slot_id: str
    slot_type: str  # amount, date, text, entity, integer, percentage
    slot_hint: str | None = None
    slot_context: str | None = None


@dataclass
class SlotFillResult:
    """Result of filling a single slot (output from LLM)."""

    slot_id: str
    status: str  # filled, missing, conflict, low_confidence
    value: Any = None
    formatted_value: str | None = None
    source_facts: list[str] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)
    confidence: float = 0.0
    reason: str | None = None


@dataclass
class FilledSlotsResult:
    """Complete result of slot filling."""

    section_key: EnumSectionKey
    fills: dict[str, SlotFill]
    fill_rate: float = 0.0
    missing_count: int = 0
    conflict_count: int = 0
    validation_issues: list[ValidationIssue] = field(default_factory=list)
