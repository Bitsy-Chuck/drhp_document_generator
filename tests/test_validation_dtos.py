"""Tests for validation DTOs (ValidationIssue, ReviewFlag)."""

import pytest

from drhp_agent.core.dtos import (
    ValidationIssue,
    ReviewFlag,
    EvidenceRef,
)
from drhp_agent.core.enums import (
    EnumValidationSeverity,
    EnumReviewFlagType,
    EnumEvidenceType,
)


class TestValidationIssueSeverityLevels:
    """Tests for ValidationIssue severity handling."""

    def test_info_severity(self):
        issue = ValidationIssue(
            issue_id="V_001",
            severity=EnumValidationSeverity.INFO,
            message="Minor observation",
        )
        assert issue.severity == EnumValidationSeverity.INFO
        assert issue.slot_ids == []
        assert issue.node_ids == []

    def test_warn_severity(self):
        issue = ValidationIssue(
            issue_id="V_002",
            severity=EnumValidationSeverity.WARN,
            message="Potential issue detected",
            suggestion="Please verify manually",
        )
        assert issue.severity == EnumValidationSeverity.WARN
        assert issue.suggestion == "Please verify manually"

    def test_critical_severity(self):
        issue = ValidationIssue(
            issue_id="V_003",
            severity=EnumValidationSeverity.CRITICAL,
            message="Critical data mismatch",
            slot_ids=["S_total", "S_sum"],
            expected=1000,
            actual=900,
        )
        assert issue.severity == EnumValidationSeverity.CRITICAL
        assert len(issue.slot_ids) == 2
        assert issue.expected == 1000
        assert issue.actual == 900

    def test_issue_with_multiple_nodes(self):
        issue = ValidationIssue(
            issue_id="V_004",
            severity=EnumValidationSeverity.ERROR,
            message="Conflicting values in nodes",
            node_ids=["N_001", "N_002", "N_003"],
        )
        assert len(issue.node_ids) == 3


class TestReviewFlag:
    """Tests for ReviewFlag DTO."""

    def test_minimal_review_flag(self):
        flag = ReviewFlag(
            flag_id="RF_001",
            flag_type=EnumReviewFlagType.MISSING_FACT,
            severity=EnumValidationSeverity.WARN,
            message="Required slot not filled",
        )
        assert flag.flag_id == "RF_001"
        assert flag.flag_type == EnumReviewFlagType.MISSING_FACT
        assert flag.location is None
        assert flag.slot_ids == []
        assert flag.evidence_refs == []

    def test_review_flag_with_location(self):
        flag = ReviewFlag(
            flag_id="RF_002",
            flag_type=EnumReviewFlagType.CONFLICTING_FACTS,
            severity=EnumValidationSeverity.ERROR,
            message="Conflicting values found",
            location="Section 7, Table 1, Row 3",
            slot_ids=["S_amount_1", "S_amount_2"],
        )
        assert flag.location == "Section 7, Table 1, Row 3"
        assert len(flag.slot_ids) == 2

    def test_review_flag_with_evidence_refs(self):
        ref1 = EvidenceRef(
            evidence_id="E_001",
            evidence_type=EnumEvidenceType.TEXT_SPAN,
            doc_id="DOC_001",
            doc_path="/docs/pas3.md",
            excerpt="30,000 authorized shares",
        )
        ref2 = EvidenceRef(
            evidence_id="E_002",
            evidence_type=EnumEvidenceType.TABLE_CELL,
            doc_id="DOC_002",
            doc_path="/docs/resolution.md",
            table_id="T_001",
            row=2,
            col=1,
        )
        flag = ReviewFlag(
            flag_id="RF_003",
            flag_type=EnumReviewFlagType.LOW_CONFIDENCE,
            severity=EnumValidationSeverity.INFO,
            message="Low confidence extraction",
            evidence_refs=[ref1, ref2],
            suggestion="Verify against original documents",
        )
        assert len(flag.evidence_refs) == 2
        assert flag.evidence_refs[0].excerpt == "30,000 authorized shares"
        assert flag.suggestion == "Verify against original documents"

    def test_all_flag_types(self):
        """Verify all flag types can be used."""
        flag_types = [
            EnumReviewFlagType.MISSING_FACT,
            EnumReviewFlagType.CONFLICTING_FACTS,
            EnumReviewFlagType.LOW_CONFIDENCE,
            EnumReviewFlagType.FAILED_RECONCILIATION,
            EnumReviewFlagType.UNSUPPORTED_STRUCTURE,
            EnumReviewFlagType.TYPE_MISMATCH,
        ]
        for ft in flag_types:
            flag = ReviewFlag(
                flag_id=f"RF_{ft.value}",
                flag_type=ft,
                severity=EnumValidationSeverity.INFO,
                message=f"Test flag for {ft.value}",
            )
            assert flag.flag_type == ft

    def test_review_flag_with_node_ids(self):
        flag = ReviewFlag(
            flag_id="RF_004",
            flag_type=EnumReviewFlagType.FAILED_RECONCILIATION,
            severity=EnumValidationSeverity.WARN,
            message="Values inconsistent across document sections",
            node_ids=["N_para_1", "N_table_2"],
        )
        assert len(flag.node_ids) == 2
        assert "N_para_1" in flag.node_ids
