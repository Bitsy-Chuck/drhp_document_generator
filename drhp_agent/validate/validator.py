"""LLM-based fact validation.

Tasks 7.1-7.7: Validate facts for consistency across documents.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from drhp_agent.core.dtos import FactStore, ValidationIssue
from drhp_agent.core.enums import EnumValidationSeverity
from drhp_agent.llm.client import LLMClient


@dataclass
class ValidationResult:
    """Result of validating extracted facts."""

    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == EnumValidationSeverity.CRITICAL)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == EnumValidationSeverity.ERROR)

    @property
    def warn_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == EnumValidationSeverity.WARN)

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == EnumValidationSeverity.INFO)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "is_valid": self.is_valid,
            "summary": {
                "total_issues": len(self.issues),
                "critical": self.critical_count,
                "error": self.error_count,
                "warn": self.warn_count,
                "info": self.info_count,
            },
            "issues": [
                {
                    "issue_id": i.issue_id,
                    "severity": i.severity.value,
                    "message": i.message,
                    "slot_ids": i.slot_ids,
                    "expected": i.expected,
                    "actual": i.actual,
                    "suggestion": i.suggestion,
                }
                for i in self.issues
            ],
        }


class FactValidator:
    """Validates extracted facts using LLM."""

    def __init__(self, llm_client: LLMClient):
        """Initialize with LLM client.

        Args:
            llm_client: Configured LLM client
        """
        self.llm = llm_client

    def validate(self, fact_store: FactStore) -> ValidationResult:
        """Validate all facts for consistency.

        Args:
            fact_store: Store of extracted facts

        Returns:
            ValidationResult with issues found
        """
        facts_json = self._serialize_facts(fact_store)

        try:
            result = self.llm.validate_facts(facts_json)

            issues = []
            for i, issue_data in enumerate(result.get("issues", [])):
                severity_str = issue_data.get("severity", "info").lower()
                try:
                    severity = EnumValidationSeverity(severity_str)
                except ValueError:
                    severity = EnumValidationSeverity.INFO

                issues.append(
                    ValidationIssue(
                        issue_id=f"V_{i+1:03d}",
                        severity=severity,
                        message=issue_data.get("message", "Unknown issue"),
                        slot_ids=issue_data.get("facts_involved", []),
                        expected=issue_data.get("expected"),
                        actual=issue_data.get("actual"),
                        suggestion=issue_data.get("suggestion"),
                    )
                )

            validation_result = ValidationResult(
                is_valid=result.get("is_valid", len(issues) == 0),
                issues=issues,
            )
            logger.info("Validation: valid=%s issues=%d (critical=%d error=%d warn=%d info=%d)",
                        validation_result.is_valid, len(issues),
                        validation_result.critical_count, validation_result.error_count,
                        validation_result.warn_count, validation_result.info_count)
            for issue in issues:
                if issue.severity in (EnumValidationSeverity.CRITICAL, EnumValidationSeverity.ERROR):
                    logger.error("Issue %s [%s]: %s", issue.issue_id, issue.severity.value, issue.message)
                else:
                    logger.warning("Issue %s [%s]: %s", issue.issue_id, issue.severity.value, issue.message)
            return validation_result

        except Exception as e:
            logger.error("Validation failed: %s", e)
            return ValidationResult(
                is_valid=False,
                issues=[
                    ValidationIssue(
                        issue_id="V_ERR",
                        severity=EnumValidationSeverity.ERROR,
                        message=f"Validation failed: {str(e)}",
                    )
                ],
            )

    def save_validation_result(
        self,
        result: ValidationResult,
        output_path: Path,
    ) -> None:
        """Save validation result to JSON.

        Args:
            result: Validation result
            output_path: Path to output file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result.to_dict(), indent=2, ensure_ascii=False)
        )

    def _serialize_facts(self, fact_store: FactStore) -> str:
        """Serialize facts to JSON for LLM prompt."""
        facts = []
        for fact in fact_store.all_facts():
            facts.append({
                "fact_id": fact.fact_id,
                "key": fact.key,
                "value": fact.value,
                "value_type": fact.value_type,
                "raw_text": fact.raw_text,
                "doc_id": fact.doc_id,
            })
        return json.dumps(facts, indent=2, ensure_ascii=False)
