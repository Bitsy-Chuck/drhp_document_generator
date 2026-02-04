"""Template-related DTOs.

SlotSpec, TableCell, TemplateNode, SectionTemplate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from drhp_agent.core.enums import EnumNodeType, EnumSectionKey, EnumSlotKind


@dataclass
class SlotSpec:
    """Specification for a fillable slot in the template."""

    slot_id: str
    kind: EnumSlotKind
    hint: str | None = None
    context_window: str | None = None
    expected_source_types: list[str] = field(default_factory=list)
    required: bool = True
    default_value: Any = None


@dataclass
class TableCell:
    """A cell in a markdown table."""

    text: str
    row: int
    col: int
    slots: list[SlotSpec] = field(default_factory=list)
    is_header: bool = False


@dataclass
class TemplateNode:
    """A node in the template tree."""

    node_id: str
    node_type: EnumNodeType
    text: str | None = None
    level: int | None = None
    children: list[TemplateNode] = field(default_factory=list)
    slots: list[SlotSpec] = field(default_factory=list)

    # Table-specific fields
    table_id: str | None = None
    headers: list[str] | None = None
    rows: list[list[TableCell]] | None = None

    # List-specific fields
    ordered: bool | None = None

    # Metadata
    source_line_start: int | None = None
    source_line_end: int | None = None
    raw_text: str | None = None
    is_boilerplate: bool = False


@dataclass
class SectionTemplate:
    """Complete template for a section."""

    section_key: EnumSectionKey
    section_title: str
    root_node: TemplateNode
    slot_specs: dict[str, SlotSpec] = field(default_factory=dict)
    source_file: str | None = None
    source_line_start: int | None = None
    source_line_end: int | None = None
