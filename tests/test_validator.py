"""Tests for FactValidator (Tasks 7.1-7.7)."""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock

from drhp_agent.validate.validator import FactValidator, ValidationResult
from drhp_agent.core.dtos import (
    FactStore,
    DocumentExtraction,
    ExtractedFact,
    FactLocation,
    ValidationIssue,
)
from drhp_agent.core.enums import EnumValidationSeverity


class TestValidationResult:
    """Tests for ValidationResult data class."""

    def test_empty_result_is_valid(self):
        result = ValidationResult(is_valid=True, issues=[])
        assert result.is_valid
        assert result.critical_count == 0
        assert result.error_count == 0

    def test_counts_by_severity(self):
        issues = [
            ValidationIssue(issue_id="V1", severity=EnumValidationSeverity.CRITICAL, message="Critical"),
            ValidationIssue(issue_id="V2", severity=EnumValidationSeverity.ERROR, message="Error 1"),
            ValidationIssue(issue_id="V3", severity=EnumValidationSeverity.ERROR, message="Error 2"),
            ValidationIssue(issue_id="V4", severity=EnumValidationSeverity.WARN, message="Warning"),
            ValidationIssue(issue_id="V5", severity=EnumValidationSeverity.INFO, message="Info"),
        ]
        result = ValidationResult(is_valid=False, issues=issues)

        assert result.critical_count == 1
        assert result.error_count == 2
        assert result.warn_count == 1
        assert result.info_count == 1

    def test_to_dict(self):
        issues = [
            ValidationIssue(
                issue_id="V1",
                severity=EnumValidationSeverity.ERROR,
                message="Test error",
                slot_ids=["s1", "s2"],
                expected=100,
                actual=90,
                suggestion="Check the values",
            )
        ]
        result = ValidationResult(is_valid=False, issues=issues)
        data = result.to_dict()

        assert data["is_valid"] is False
        assert data["summary"]["total_issues"] == 1
        assert data["summary"]["error"] == 1
        assert data["issues"][0]["message"] == "Test error"
        assert data["issues"][0]["expected"] == 100


class TestFactValidator:
    """Tests for FactValidator."""

    @pytest.fixture
    def mock_llm_client(self):
        mock = Mock()
        mock.validate_facts.return_value = {
            "is_valid": True,
            "issues": [],
        }
        return mock

    @pytest.fixture
    def sample_fact_store(self):
        """Create a fact store with sample data."""
        facts = [
            ExtractedFact(
                fact_id="F001",
                category="capital_structure",
                key="authorized_shares",
                value=30000,
                value_type="integer",
                raw_text="30,000 shares",
                location=FactLocation(section="Section 7"),
                doc_id="DOC_001",
            ),
            ExtractedFact(
                fact_id="F002",
                category="capital_structure",
                key="issued_shares",
                value=19321,
                value_type="integer",
                raw_text="19,321 shares",
                location=FactLocation(section="Section 7"),
                doc_id="DOC_001",
            ),
        ]
        extraction = DocumentExtraction(
            doc_id="DOC_001",
            file_path="/test/doc.md",
            document_type="pas3_form",
            facts=facts,
        )
        return FactStore(extractions=[extraction])

    def test_validate_returns_valid_when_no_issues(self, mock_llm_client, sample_fact_store):
        validator = FactValidator(mock_llm_client)
        result = validator.validate(sample_fact_store)

        assert result.is_valid
        assert len(result.issues) == 0

    def test_validate_detects_cross_document_inconsistency(self, mock_llm_client):
        """When same fact has different values across documents."""
        mock_llm_client.validate_facts.return_value = {
            "is_valid": False,
            "issues": [
                {
                    "severity": "error",
                    "type": "inconsistency",
                    "message": "authorized_shares differs: 30000 vs 35000",
                    "facts_involved": ["F001", "F003"],
                    "suggestion": "Verify the correct value from source documents",
                }
            ],
        }
        # Create fact store with conflicting values
        fact1 = ExtractedFact(
            fact_id="F001", category="capital", key="authorized_shares",
            value=30000, value_type="integer", raw_text="30,000",
            location=FactLocation(), doc_id="DOC_001",
        )
        fact2 = ExtractedFact(
            fact_id="F003", category="capital", key="authorized_shares",
            value=35000, value_type="integer", raw_text="35,000",
            location=FactLocation(), doc_id="DOC_002",
        )
        store = FactStore(extractions=[
            DocumentExtraction(doc_id="DOC_001", file_path="/d1.md", document_type="test", facts=[fact1]),
            DocumentExtraction(doc_id="DOC_002", file_path="/d2.md", document_type="test", facts=[fact2]),
        ])

        validator = FactValidator(mock_llm_client)
        result = validator.validate(store)

        assert not result.is_valid
        assert len(result.issues) == 1
        assert result.issues[0].severity == EnumValidationSeverity.ERROR
        assert "authorized_shares" in result.issues[0].message

    def test_validate_detects_math_errors(self, mock_llm_client):
        """When totals don't match sum of parts."""
        mock_llm_client.validate_facts.return_value = {
            "is_valid": False,
            "issues": [
                {
                    "severity": "error",
                    "type": "math_error",
                    "message": "Total (100) does not equal sum of parts (90)",
                    "facts_involved": ["F001", "F002", "F003"],
                    "expected": 100,
                    "actual": 90,
                }
            ],
        }
        store = FactStore(extractions=[])

        validator = FactValidator(mock_llm_client)
        result = validator.validate(store)

        assert not result.is_valid
        assert result.error_count == 1
        assert "sum" in result.issues[0].message.lower() or "total" in result.issues[0].message.lower()

    def test_validate_detects_date_inconsistencies(self, mock_llm_client):
        """When dates are illogical (e.g., allotment before incorporation)."""
        mock_llm_client.validate_facts.return_value = {
            "is_valid": False,
            "issues": [
                {
                    "severity": "warn",
                    "type": "date_error",
                    "message": "Allotment date (2019-05-15) is before incorporation date (2019-06-01)",
                    "facts_involved": ["F_date_1", "F_date_2"],
                }
            ],
        }
        store = FactStore(extractions=[])

        validator = FactValidator(mock_llm_client)
        result = validator.validate(store)

        assert result.warn_count == 1
        assert "date" in result.issues[0].message.lower()

    def test_validate_flags_missing_critical_facts(self, mock_llm_client):
        """When required facts are not found."""
        mock_llm_client.validate_facts.return_value = {
            "is_valid": False,
            "issues": [
                {
                    "severity": "critical",
                    "type": "missing",
                    "message": "Missing required fact: company_cin",
                    "suggestion": "Add CIN from company registration documents",
                }
            ],
        }
        store = FactStore(extractions=[])

        validator = FactValidator(mock_llm_client)
        result = validator.validate(store)

        assert result.critical_count == 1
        assert "missing" in result.issues[0].message.lower()

    def test_validate_handles_empty_fact_store(self, mock_llm_client):
        mock_llm_client.validate_facts.return_value = {
            "is_valid": False,
            "issues": [
                {"severity": "critical", "message": "No facts to validate"}
            ],
        }
        store = FactStore(extractions=[])

        validator = FactValidator(mock_llm_client)
        result = validator.validate(store)

        # Should handle gracefully, possibly flagging as issue
        assert isinstance(result, ValidationResult)

    def test_validate_handles_llm_error(self, mock_llm_client):
        mock_llm_client.validate_facts.side_effect = Exception("LLM API Error")
        store = FactStore(extractions=[])

        validator = FactValidator(mock_llm_client)
        result = validator.validate(store)

        assert not result.is_valid
        assert len(result.issues) == 1
        assert "failed" in result.issues[0].message.lower() or "error" in result.issues[0].message.lower()

    def test_validate_assigns_correct_severity_levels(self, mock_llm_client):
        """Test all severity levels are parsed correctly."""
        mock_llm_client.validate_facts.return_value = {
            "is_valid": False,
            "issues": [
                {"severity": "critical", "message": "Critical issue"},
                {"severity": "error", "message": "Error issue"},
                {"severity": "warn", "message": "Warning issue"},
                {"severity": "info", "message": "Info issue"},
                {"severity": "unknown", "message": "Unknown defaults to info"},
            ],
        }
        store = FactStore(extractions=[])

        validator = FactValidator(mock_llm_client)
        result = validator.validate(store)

        assert result.critical_count == 1
        assert result.error_count == 1
        assert result.warn_count == 1
        assert result.info_count == 2  # info + unknown defaults to info

    def test_save_validation_result(self, mock_llm_client, tmp_path):
        result = ValidationResult(
            is_valid=True,
            issues=[
                ValidationIssue(
                    issue_id="V1",
                    severity=EnumValidationSeverity.INFO,
                    message="All good",
                )
            ],
        )
        validator = FactValidator(mock_llm_client)

        output_path = tmp_path / "validation.json"
        validator.save_validation_result(result, output_path)

        assert output_path.exists()
        data = json.loads(output_path.read_text())
        assert data["is_valid"] is True
        assert len(data["issues"]) == 1

    def test_serialize_facts_includes_all_fields(self, mock_llm_client, sample_fact_store):
        validator = FactValidator(mock_llm_client)
        json_str = validator._serialize_facts(sample_fact_store)
        facts = json.loads(json_str)

        assert len(facts) == 2
        assert facts[0]["fact_id"] == "F001"
        assert facts[0]["category"] == "capital_structure"
        assert facts[0]["value"] == 30000
        assert facts[0]["doc_id"] == "DOC_001"
