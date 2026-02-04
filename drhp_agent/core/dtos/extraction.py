"""LLM extraction DTOs.

FactLocation, ExtractedFact, DocumentExtraction, FactStore.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class FactLocation:
    """Location of a fact within a source document."""

    section: str | None = None
    table: str | None = None
    row: str | None = None
    column: str | None = None
    line_start: int | None = None
    line_end: int | None = None


@dataclass
class ExtractedFact:
    """A single fact extracted from a document."""

    fact_id: str
    category: str  # company_info, capital_structure, allotment, allottee, financial, date, signatory
    key: str  # Normalized field name
    value: Any
    value_type: str  # amount, integer, percentage, date, text, entity, table_row
    raw_text: str
    location: FactLocation
    unit: str | None = None
    confidence: float = 1.0
    doc_id: str | None = None


@dataclass
class DocumentExtraction:
    """All facts extracted from a single document."""

    doc_id: str
    file_path: str
    document_type: str  # board_resolution, list_of_allottees, pas3_form, other
    facts: list[ExtractedFact] = field(default_factory=list)
    document_date: str | None = None
    extraction_timestamp: datetime | None = None
    error: str | None = None


@dataclass
class FactStore:
    """Aggregated facts from all documents."""

    extractions: list[DocumentExtraction] = field(default_factory=list)

    def all_facts(self) -> list[ExtractedFact]:
        """Return all facts from all documents."""
        facts = []
        for extraction in self.extractions:
            for fact in extraction.facts:
                if fact.doc_id is None:
                    fact.doc_id = extraction.doc_id
                facts.append(fact)
        return facts

    def facts_by_category(self, category: str) -> list[ExtractedFact]:
        """Return facts filtered by category."""
        return [f for f in self.all_facts() if f.category == category]

    def facts_by_key(self, key: str) -> list[ExtractedFact]:
        """Return facts filtered by key."""
        return [f for f in self.all_facts() if f.key == key]

    def facts_by_doc(self, doc_id: str) -> list[ExtractedFact]:
        """Return facts from a specific document."""
        for extraction in self.extractions:
            if extraction.doc_id == doc_id:
                return extraction.facts
        return []

    def get_fact(self, fact_id: str) -> ExtractedFact | None:
        """Get a specific fact by ID."""
        for fact in self.all_facts():
            if fact.fact_id == fact_id:
                return fact
        return None
