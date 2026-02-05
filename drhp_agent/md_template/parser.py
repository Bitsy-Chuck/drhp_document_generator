"""Template parsing and slot extraction.

Tasks 5.1-5.5: Load template, detect slots, build SlotFillRequests.
Tasks 13.2: Parse elaboration blocks for hybrid template system.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from drhp_agent.core.dtos import SlotFillRequest, ElaborationBlock, ElaborationRequest


@dataclass
class ParsedSlot:
    """A slot parsed from the template."""

    slot_id: str
    slot_type: str
    hint: str | None
    raw_marker: str
    line_number: int
    context: str  # Surrounding text for context


@dataclass
class ParsedTemplate:
    """Result of parsing a template file."""

    file_path: str
    content: str
    slots: list[ParsedSlot] = field(default_factory=list)
    elaboration_blocks: list[ElaborationBlock] = field(default_factory=list)

    def to_fill_requests(self) -> list[SlotFillRequest]:
        """Convert parsed slots to SlotFillRequest objects."""
        return [
            SlotFillRequest(
                slot_id=slot.slot_id,
                slot_type=slot.slot_type,
                slot_hint=slot.hint,
                slot_context=slot.context,
            )
            for slot in self.slots
        ]

    def to_elaboration_requests(
        self, facts: list[dict[str, Any]] | None = None
    ) -> list[ElaborationRequest]:
        """Convert elaboration blocks to ElaborationRequest objects.

        All facts are passed to each request. The LLM does semantic
        matching based on the hint.

        Args:
            facts: Optional list of all fact dicts

        Returns:
            List of ElaborationRequest objects ready for LLM
        """
        requests = []
        for block in self.elaboration_blocks:
            requests.append(
                ElaborationRequest(
                    block_id=block.block_id,
                    hint=block.hint,
                    relevant_facts=list(facts) if facts else [],
                    template_context=block.context,
                )
            )
        return requests

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "file_path": self.file_path,
            "slot_count": len(self.slots),
            "elaboration_block_count": len(self.elaboration_blocks),
            "slots": [
                {
                    "slot_id": s.slot_id,
                    "slot_type": s.slot_type,
                    "hint": s.hint,
                    "raw_marker": s.raw_marker,
                    "line_number": s.line_number,
                }
                for s in self.slots
            ],
            "elaboration_blocks": [
                {
                    "block_id": b.block_id,
                    "hint": b.hint,
                    "raw_marker": b.raw_marker,
                    "line_number": b.line_number,
                }
                for b in self.elaboration_blocks
            ],
        }


class TemplateParser:
    """Parses template files and extracts slot markers and elaboration blocks."""

    # Matches {{type:slot_name:hint}} or {{slot_name}}
    # But NOT {{elaborate:...}} which is handled separately
    SLOT_PATTERN = re.compile(
        r"\{\{"
        r"(?:(?P<type>(?!elaborate)\w+):)?"  # Optional type prefix (not "elaborate")
        r"(?P<slot_id>(?!elaborate)\w+)"  # Required slot ID (not starting with elaborate)
        r"(?::(?P<hint>[^}]+))?"  # Optional hint suffix
        r"\}\}"
    )

    # Matches {{elaborate:block_id:hint}}
    ELABORATE_PATTERN = re.compile(
        r"\{\{elaborate:"
        r"(?P<block_id>\w+)"  # Required block ID
        r"(?::(?P<hint>[^}]+))?"  # Optional hint
        r"\}\}"
    )

    # Context window size (characters before/after slot)
    CONTEXT_WINDOW = 100

    def __init__(self, template_path: str | Path):
        """Initialize parser with template path.

        Args:
            template_path: Path to template markdown file
        """
        self.template_path = Path(template_path)
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        if not self.template_path.suffix.lower() == ".md":
            raise ValueError(f"Template must be markdown file: {template_path}")

    def parse(self) -> ParsedTemplate:
        """Parse the template and extract all slots and elaboration blocks.

        Returns:
            ParsedTemplate with all detected slots and elaboration blocks
        """
        content = self.template_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        slots: list[ParsedSlot] = []
        elaboration_blocks: list[ElaborationBlock] = []
        seen_slots: set[str] = set()
        seen_blocks: set[str] = set()

        line_offset = 0
        for line_num, line in enumerate(lines, start=1):
            # Parse slots
            for match in self.SLOT_PATTERN.finditer(line):
                slot_id = match.group("slot_id")

                # Skip duplicates and skip if this looks like elaborate
                if slot_id in seen_slots or slot_id == "elaborate":
                    continue
                seen_slots.add(slot_id)

                slot_type = match.group("type") or "text"
                hint = match.group("hint")
                raw_marker = match.group(0)

                # Extract context around the slot (from full content, not just this line)
                abs_pos = line_offset + match.start()
                start = max(0, abs_pos - self.CONTEXT_WINDOW)
                end = min(len(content), abs_pos + len(raw_marker) + self.CONTEXT_WINDOW)
                context = content[start:end]

                slots.append(
                    ParsedSlot(
                        slot_id=slot_id,
                        slot_type=slot_type,
                        hint=hint,
                        raw_marker=raw_marker,
                        line_number=line_num,
                        context=context,
                    )
                )

            # Parse elaboration blocks
            for match in self.ELABORATE_PATTERN.finditer(line):
                block_id = match.group("block_id")

                # Skip duplicates
                if block_id in seen_blocks:
                    continue
                seen_blocks.add(block_id)

                hint = match.group("hint") or ""
                raw_marker = match.group(0)

                # Extract context around the block (from full content, not just this line)
                abs_pos = line_offset + match.start()
                start = max(0, abs_pos - self.CONTEXT_WINDOW)
                end = min(len(content), abs_pos + len(raw_marker) + self.CONTEXT_WINDOW)
                context = content[start:end]

                elaboration_blocks.append(
                    ElaborationBlock(
                        block_id=block_id,
                        hint=hint,
                        raw_marker=raw_marker,
                        line_number=line_num,
                        context=context,
                    )
                )

            line_offset += len(line) + 1  # +1 for newline

        return ParsedTemplate(
            file_path=str(self.template_path),
            content=content,
            slots=slots,
            elaboration_blocks=elaboration_blocks,
        )

    def save_parsed_template(
        self, parsed: ParsedTemplate, output_path: Path
    ) -> None:
        """Save parsed template to JSON.

        Args:
            parsed: Parsed template result
            output_path: Path to output JSON file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(parsed.to_dict(), indent=2, ensure_ascii=False)
        )
