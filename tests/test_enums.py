"""Unit tests for core enums.

Task 12.1: Unit tests for enums.
"""

import pytest

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
    strict_enum_parse,
)
from drhp_agent.core.exceptions import NotSupportedEnumValueError


class TestEnumSectionKey:
    """Tests for EnumSectionKey (Task 2.1)."""

    def test_all_values_defined(self):
        expected = [
            "objects",
            "risk_factors",
            "business_overview",
            "industry_overview",
            "financial_information",
            "legal_proceedings",
            "management",
            "promoters",
            "issue_details",
            "capital_structure",
            "custom",
        ]
        actual = [e.value for e in EnumSectionKey]
        assert set(actual) == set(expected)

    def test_custom_key_exists(self):
        assert EnumSectionKey.CUSTOM.value == "custom"


class TestEnumNodeType:
    """Tests for EnumNodeType (Task 2.2)."""

    def test_all_values_defined(self):
        expected = [
            "heading",
            "paragraph",
            "table",
            "list",
            "list_item",
            "text",
            "code_block",
            "blockquote",
            "thematic_break",
            "unknown",
        ]
        actual = [e.value for e in EnumNodeType]
        assert set(actual) == set(expected)

    def test_unknown_exists(self):
        assert EnumNodeType.UNKNOWN.value == "unknown"


class TestEnumSlotKind:
    """Tests for EnumSlotKind (Task 2.3)."""

    def test_all_values_defined(self):
        expected = [
            "amount",
            "percent",
            "date",
            "text",
            "entity",
            "ratio",
            "boolean",
            "integer",
            "custom",
        ]
        actual = [e.value for e in EnumSlotKind]
        assert set(actual) == set(expected)


class TestEnumEvidenceType:
    """Tests for EnumEvidenceType (Task 2.4)."""

    def test_all_values_defined(self):
        expected = ["text_span", "table_cell", "multi_span"]
        actual = [e.value for e in EnumEvidenceType]
        assert set(actual) == set(expected)


class TestEnumSourceType:
    """Tests for EnumSourceType (Task 2.5)."""

    def test_only_md_supported(self):
        """Only MD is supported for MVP."""
        assert len(list(EnumSourceType)) == 1
        assert EnumSourceType.MD.value == "md"


class TestEnumFillStatus:
    """Tests for EnumFillStatus (Task 2.6)."""

    def test_all_values_defined(self):
        expected = ["filled", "missing", "conflict", "low_confidence", "invalid"]
        actual = [e.value for e in EnumFillStatus]
        assert set(actual) == set(expected)


class TestEnumValidationSeverity:
    """Tests for EnumValidationSeverity (Task 2.7)."""

    def test_all_values_defined(self):
        expected = ["info", "warn", "error", "critical"]
        actual = [e.value for e in EnumValidationSeverity]
        assert set(actual) == set(expected)


class TestEnumReviewFlagType:
    """Tests for EnumReviewFlagType (Task 2.8)."""

    def test_all_values_defined(self):
        expected = [
            "missing_fact",
            "conflicting_facts",
            "failed_reconciliation",
            "unsupported_structure",
            "low_confidence",
            "type_mismatch",
        ]
        actual = [e.value for e in EnumReviewFlagType]
        assert set(actual) == set(expected)


class TestEnumRetrieverMode:
    """Tests for EnumRetrieverMode (Task 2.9)."""

    def test_all_values_defined(self):
        expected = ["bm25", "embedding", "hybrid", "table_first"]
        actual = [e.value for e in EnumRetrieverMode]
        assert set(actual) == set(expected)


class TestEnumConflictPolicy:
    """Tests for EnumConflictPolicy (Task 2.10)."""

    def test_all_values_defined(self):
        expected = [
            "highest_confidence",
            "most_recent_doc",
            "priority_source",
            "review_required",
        ]
        actual = [e.value for e in EnumConflictPolicy]
        assert set(actual) == set(expected)


class TestEnumDateStyle:
    """Tests for EnumDateStyle (Task 2.11)."""

    def test_all_values_defined(self):
        expected = ["iso", "dmy_slash", "mdy_slash", "dmy_dot", "long_en", "long_in"]
        actual = [e.value for e in EnumDateStyle]
        assert set(actual) == set(expected)


class TestEnumNumberStyle:
    """Tests for EnumNumberStyle (Task 2.11)."""

    def test_all_values_defined(self):
        expected = ["plain", "comma_en", "lakh_crore", "abbreviated"]
        actual = [e.value for e in EnumNumberStyle]
        assert set(actual) == set(expected)


class TestEnumPipelineMode:
    """Tests for EnumPipelineMode (Task 1.11)."""

    def test_all_values_defined(self):
        expected = ["strict", "dry_run", "debug"]
        actual = [e.value for e in EnumPipelineMode]
        assert set(actual) == set(expected)


class TestStrictEnumParse:
    """Tests for strict_enum_parse (Task 2.13)."""

    def test_valid_value_parses(self):
        result = strict_enum_parse(EnumSlotKind, "amount")
        assert result == EnumSlotKind.AMOUNT

    def test_invalid_value_raises_not_supported_error(self):
        with pytest.raises(NotSupportedEnumValueError) as exc_info:
            strict_enum_parse(EnumSlotKind, "invalid_kind")

        assert exc_info.value.enum_name == "EnumSlotKind"
        assert exc_info.value.value == "invalid_kind"
        assert "amount" in exc_info.value.valid_values

    def test_error_contains_all_valid_values(self):
        with pytest.raises(NotSupportedEnumValueError) as exc_info:
            strict_enum_parse(EnumSourceType, "pdf")

        assert exc_info.value.valid_values == ["md"]
