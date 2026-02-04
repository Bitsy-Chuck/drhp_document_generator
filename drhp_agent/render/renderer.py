"""Section rendering and output generation.

Tasks 8.1-8.10: Generate DRHP section, annotations, and review flags.
Tasks 13.5: Handle both slots and elaboration blocks in hybrid template system.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from drhp_agent.core.dtos import FactStore, ReviewFlag
from drhp_agent.core.enums import EnumReviewFlagType, EnumValidationSeverity
from drhp_agent.fill.slot_filler import FilledSlots
from drhp_agent.elaborate.elaborator import Elaborations
from drhp_agent.llm.client import LLMClient
from drhp_agent.md_template.parser import ParsedTemplate
from drhp_agent.validate.validator import ValidationResult


@dataclass
class AnnotationRecord:
    """Record mapping output text to source evidence."""

    annotation_id: str
    slot_id: str  # Can be slot_id or block_id
    value: Any
    source_facts: list[str]
    source_files: list[str]
    confidence: float
    is_elaboration: bool = False  # True if from elaboration block


@dataclass
class RenderResult:
    """Result of rendering a section."""

    section_markdown: str
    annotations: list[AnnotationRecord] = field(default_factory=list)
    review_flags: list[ReviewFlag] = field(default_factory=list)


class SectionRenderer:
    """Renders DRHP section from filled slots and elaboration blocks."""

    # Pattern for slot markers in template (not elaborate)
    SLOT_PATTERN = re.compile(
        r"\{\{(?:(?P<type>(?!elaborate)\w+):)?(?P<slot_id>(?!elaborate)\w+)(?::(?P<hint>[^}]+))?\}\}"
    )

    # Pattern for elaboration blocks
    ELABORATE_PATTERN = re.compile(
        r"\{\{elaborate:(?P<block_id>\w+)(?::(?P<category_or_hint>[^:}]+))?(?::(?P<hint>[^}]+))?\}\}"
    )

    def __init__(self, llm_client: LLMClient):
        """Initialize with LLM client.

        Args:
            llm_client: Configured LLM client
        """
        self.llm = llm_client

    def render(
        self,
        template: ParsedTemplate,
        filled_slots: FilledSlots,
        fact_store: FactStore,
        validation_result: ValidationResult | None = None,
        elaborations: Elaborations | None = None,
    ) -> RenderResult:
        """Render the section by replacing slots and elaboration blocks.

        Args:
            template: Parsed template
            filled_slots: Filled slot results
            fact_store: Store of extracted facts
            validation_result: Optional validation results
            elaborations: Optional elaboration results for hybrid template

        Returns:
            RenderResult with markdown, annotations, and flags
        """
        content = template.content
        annotations = []
        review_flags = []

        # Replace each slot with its filled value
        def replace_slot(match: re.Match) -> str:
            slot_id = match.group("slot_id")
            result = filled_slots.get_by_id(slot_id)

            if result is None:
                # Slot not found in fill requests
                flag = ReviewFlag(
                    flag_id=f"RF_{len(review_flags)+1:03d}",
                    flag_type=EnumReviewFlagType.MISSING_FACT,
                    severity=EnumValidationSeverity.ERROR,
                    message=f"Slot '{slot_id}' not processed",
                    slot_ids=[slot_id],
                )
                review_flags.append(flag)
                return f"[[REQUIRES REVIEW: Slot '{slot_id}' not processed]]"

            if result.status == "filled":
                # Create annotation for this filled value
                annotations.append(
                    AnnotationRecord(
                        annotation_id=f"A_{len(annotations)+1:03d}",
                        slot_id=slot_id,
                        value=result.value,
                        source_facts=result.source_facts,
                        source_files=result.source_files,
                        confidence=result.confidence,
                    )
                )

                # Add source citation if we have source files
                value_str = str(result.formatted_value or result.value)
                if result.source_files:
                    source = result.source_files[0]
                    return f"{value_str} [Source: {source}]"
                return value_str

            elif result.status == "missing":
                flag = ReviewFlag(
                    flag_id=f"RF_{len(review_flags)+1:03d}",
                    flag_type=EnumReviewFlagType.MISSING_FACT,
                    severity=EnumValidationSeverity.WARN,
                    message=result.reason or f"No data found for '{slot_id}'",
                    slot_ids=[slot_id],
                )
                review_flags.append(flag)
                reason = result.reason or "Data not found in documents"
                return f"[[REQUIRES REVIEW: {reason}]]"

            elif result.status == "conflict":
                flag = ReviewFlag(
                    flag_id=f"RF_{len(review_flags)+1:03d}",
                    flag_type=EnumReviewFlagType.CONFLICTING_FACTS,
                    severity=EnumValidationSeverity.ERROR,
                    message=result.reason or f"Conflicting values for '{slot_id}'",
                    slot_ids=[slot_id],
                )
                review_flags.append(flag)
                reason = result.reason or "Conflicting values found"
                return f"[[REQUIRES REVIEW: {reason}]]"

            elif result.status == "low_confidence":
                flag = ReviewFlag(
                    flag_id=f"RF_{len(review_flags)+1:03d}",
                    flag_type=EnumReviewFlagType.LOW_CONFIDENCE,
                    severity=EnumValidationSeverity.INFO,
                    message=f"Low confidence ({result.confidence:.0%}) for '{slot_id}'",
                    slot_ids=[slot_id],
                )
                review_flags.append(flag)

                value_str = str(result.formatted_value or result.value)
                if result.source_files:
                    source = result.source_files[0]
                    return f"{value_str} [Source: {source}] ⚠️"
                return f"{value_str} ⚠️"

            else:
                return f"[[REQUIRES REVIEW: Unknown status '{result.status}']]"

        # Replace all slot markers
        rendered_content = self.SLOT_PATTERN.sub(replace_slot, content)

        # Replace elaboration blocks if provided
        if elaborations:
            def replace_elaborate(match: re.Match) -> str:
                block_id = match.group("block_id")
                result = elaborations.get_by_id(block_id)

                if result is None:
                    # Block not found in elaboration results
                    flag = ReviewFlag(
                        flag_id=f"RF_{len(review_flags)+1:03d}",
                        flag_type=EnumReviewFlagType.MISSING_FACT,
                        severity=EnumValidationSeverity.ERROR,
                        message=f"Elaboration block '{block_id}' not processed",
                        slot_ids=[block_id],
                    )
                    review_flags.append(flag)
                    return f"[[REQUIRES REVIEW: Elaboration block '{block_id}' not processed]]"

                if result.status == "generated":
                    # Create annotation for elaboration
                    annotations.append(
                        AnnotationRecord(
                            annotation_id=f"A_{len(annotations)+1:03d}",
                            slot_id=block_id,
                            value=f"[Elaboration: {len(result.generated_markdown)} chars]",
                            source_facts=result.source_facts,
                            source_files=result.source_files,
                            confidence=result.confidence,
                            is_elaboration=True,
                        )
                    )
                    return result.generated_markdown

                elif result.status == "empty":
                    flag = ReviewFlag(
                        flag_id=f"RF_{len(review_flags)+1:03d}",
                        flag_type=EnumReviewFlagType.MISSING_FACT,
                        severity=EnumValidationSeverity.WARN,
                        message=result.reason or f"No facts found for '{block_id}'",
                        slot_ids=[block_id],
                    )
                    review_flags.append(flag)
                    return result.generated_markdown  # Contains REQUIRES REVIEW

                elif result.status == "error":
                    flag = ReviewFlag(
                        flag_id=f"RF_{len(review_flags)+1:03d}",
                        flag_type=EnumReviewFlagType.FAILED_RECONCILIATION,
                        severity=EnumValidationSeverity.ERROR,
                        message=result.reason or f"Error elaborating '{block_id}'",
                        slot_ids=[block_id],
                    )
                    review_flags.append(flag)
                    return result.generated_markdown  # Contains REQUIRES REVIEW

                else:
                    return f"[[REQUIRES REVIEW: Unknown status '{result.status}']]"

            rendered_content = self.ELABORATE_PATTERN.sub(replace_elaborate, rendered_content)

        # Add validation issues as review flags
        if validation_result:
            for issue in validation_result.issues:
                if issue.severity in (
                    EnumValidationSeverity.ERROR,
                    EnumValidationSeverity.CRITICAL,
                ):
                    flag = ReviewFlag(
                        flag_id=f"RF_{len(review_flags)+1:03d}",
                        flag_type=EnumReviewFlagType.FAILED_RECONCILIATION,
                        severity=issue.severity,
                        message=issue.message,
                        slot_ids=issue.slot_ids,
                        suggestion=issue.suggestion,
                    )
                    review_flags.append(flag)

        return RenderResult(
            section_markdown=rendered_content,
            annotations=annotations,
            review_flags=review_flags,
        )

    def save_section(self, result: RenderResult, output_path: Path) -> None:
        """Save rendered section to markdown file.

        Args:
            result: Render result
            output_path: Path to output file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result.section_markdown, encoding="utf-8")

    def save_annotations(self, result: RenderResult, output_path: Path) -> None:
        """Save annotations to JSONL file.

        Args:
            result: Render result
            output_path: Path to output file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        for ann in result.annotations:
            lines.append(
                json.dumps(
                    {
                        "annotation_id": ann.annotation_id,
                        "slot_id": ann.slot_id,
                        "value": ann.value,
                        "source_facts": ann.source_facts,
                        "source_files": ann.source_files,
                        "confidence": ann.confidence,
                    },
                    ensure_ascii=False,
                )
            )
        output_path.write_text("\n".join(lines) + "\n" if lines else "", encoding="utf-8")

    def save_review_flags(self, result: RenderResult, output_path: Path) -> None:
        """Save review flags to markdown file.

        Args:
            result: Render result
            output_path: Path to output file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "# Review Flags",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        if not result.review_flags:
            lines.append("✅ No review flags. All slots filled successfully.")
        else:
            # Group by severity
            critical = [f for f in result.review_flags if f.severity == EnumValidationSeverity.CRITICAL]
            errors = [f for f in result.review_flags if f.severity == EnumValidationSeverity.ERROR]
            warnings = [f for f in result.review_flags if f.severity == EnumValidationSeverity.WARN]
            info = [f for f in result.review_flags if f.severity == EnumValidationSeverity.INFO]

            lines.append(f"**Total: {len(result.review_flags)} flags**")
            lines.append(f"- Critical: {len(critical)}")
            lines.append(f"- Errors: {len(errors)}")
            lines.append(f"- Warnings: {len(warnings)}")
            lines.append(f"- Info: {len(info)}")
            lines.append("")

            for severity_name, flags in [
                ("🔴 Critical", critical),
                ("🟠 Errors", errors),
                ("🟡 Warnings", warnings),
                ("🔵 Info", info),
            ]:
                if flags:
                    lines.append(f"## {severity_name}")
                    lines.append("")
                    for flag in flags:
                        lines.append(f"### {flag.flag_id}: {flag.flag_type.value}")
                        lines.append(f"**Message:** {flag.message}")
                        if flag.slot_ids:
                            lines.append(f"**Slots:** {', '.join(flag.slot_ids)}")
                        if flag.suggestion:
                            lines.append(f"**Suggestion:** {flag.suggestion}")
                        lines.append("")

        output_path.write_text("\n".join(lines), encoding="utf-8")
