"""Validation-related DTOs.

ValidationIssue, ReviewFlag.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from drhp_agent.core.enums import EnumReviewFlagType, EnumValidationSeverity

if TYPE_CHECKING:
    from drhp_agent.core.dtos.evidence import EvidenceRef


@dataclass
class ValidationIssue:
    """A validation issue found during processing."""

    issue_id: str
    severity: EnumValidationSeverity
    message: str
    slot_ids: list[str] = field(default_factory=list)
    node_ids: list[str] = field(default_factory=list)
    expected: Any = None
    actual: Any = None
    suggestion: str | None = None


@dataclass
class ReviewFlag:
    """A flag for human review."""

    flag_id: str
    flag_type: EnumReviewFlagType
    severity: EnumValidationSeverity
    message: str
    location: str | None = None
    slot_ids: list[str] = field(default_factory=list)
    node_ids: list[str] = field(default_factory=list)
    evidence_refs: list["EvidenceRef"] = field(default_factory=list)
    suggestion: str | None = None
