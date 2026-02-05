"""Elaboration DTOs for Hybrid Template System.

Tasks 13.1.1-13.1.3: ElaborationBlock, ElaborationResult, ElaborationRequest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ElaborationBlock:
    """An elaboration block parsed from the template.

    Elaboration blocks use the syntax: {{elaborate:block_id:hint}}

    They instruct the LLM to generate prose from ALL relevant facts,
    not just fill a single value. The LLM semantically matches facts to the hint.
    """

    block_id: str
    hint: str  # Instructions for what to elaborate on
    raw_marker: str = ""  # The original marker text
    line_number: int = 0  # Line in template where block appears
    context: str = ""  # Surrounding template text for context


@dataclass
class ElaborationRequest:
    """Request to elaborate a section using facts.

    Sent to LLM to generate rich prose from multiple facts.
    All facts are passed to the LLM which does semantic matching.
    """

    block_id: str
    hint: str  # What to elaborate on
    relevant_facts: list[dict[str, Any]] = field(default_factory=list)  # All facts
    template_context: str = ""  # Surrounding template for tone matching


@dataclass
class ElaborationResult:
    """Result of elaborating a block.

    Contains generated markdown and source tracking.
    """

    block_id: str
    status: str = "generated"  # generated, empty, error
    generated_markdown: str = ""
    source_facts: list[str] = field(default_factory=list)  # Fact IDs used
    source_files: list[str] = field(default_factory=list)  # Source filenames
    confidence: float = 1.0
    reason: str | None = None  # Error or note if applicable

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "block_id": self.block_id,
            "status": self.status,
            "generated_markdown": self.generated_markdown,
            "source_facts": self.source_facts,
            "source_files": self.source_files,
            "confidence": self.confidence,
            "reason": self.reason,
        }
