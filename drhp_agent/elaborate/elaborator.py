"""LLM-based elaboration for hybrid template system.

Tasks 13.4.1-13.4.6: Generate rich prose from facts for elaboration blocks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from drhp_agent.core.dtos import (
    FactStore,
    ElaborationRequest,
    ElaborationResult,
)
from drhp_agent.llm.client import LLMClient


@dataclass
class Elaborations:
    """Collection of elaboration results."""

    results: list[ElaborationResult] = field(default_factory=list)

    @property
    def generated_count(self) -> int:
        return sum(1 for r in self.results if r.status == "generated")

    @property
    def empty_count(self) -> int:
        return sum(1 for r in self.results if r.status == "empty")

    @property
    def error_count(self) -> int:
        return sum(1 for r in self.results if r.status == "error")

    def get_by_id(self, block_id: str) -> ElaborationResult | None:
        """Get result by block ID."""
        for r in self.results:
            if r.block_id == block_id:
                return r
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "summary": {
                "total": len(self.results),
                "generated": self.generated_count,
                "empty": self.empty_count,
                "error": self.error_count,
            },
            "elaborations": [r.to_dict() for r in self.results],
        }


class FactFilter:
    """Filters facts by category and keywords."""

    @staticmethod
    def filter_by_category(
        facts: list[dict[str, Any]],
        category: str | None,
    ) -> list[dict[str, Any]]:
        """Filter facts by category.

        Args:
            facts: List of fact dictionaries
            category: Category to filter by, or None for all

        Returns:
            Filtered list of facts
        """
        if category is None:
            return facts
        return [f for f in facts if f.get("category") == category]

    @staticmethod
    def filter_by_keywords(
        facts: list[dict[str, Any]],
        keywords: list[str],
    ) -> list[dict[str, Any]]:
        """Filter facts by keywords in key or raw_text.

        Args:
            facts: List of fact dictionaries
            keywords: Keywords to match

        Returns:
            Filtered list of facts containing any keyword
        """
        if not keywords:
            return facts

        result = []
        for fact in facts:
            key = fact.get("key", "").lower()
            raw = fact.get("raw_text", "").lower()
            for kw in keywords:
                if kw.lower() in key or kw.lower() in raw:
                    result.append(fact)
                    break
        return result


class Elaborator:
    """Generates elaborate prose from facts using LLM."""

    def __init__(self, llm_client: LLMClient):
        """Initialize with LLM client.

        Args:
            llm_client: Configured LLM client
        """
        self.llm = llm_client

    def elaborate(
        self,
        request: ElaborationRequest,
        fact_store: FactStore,
    ) -> ElaborationResult:
        """Elaborate a single block using facts.

        Args:
            request: Elaboration request with block details
            fact_store: Store of extracted facts

        Returns:
            ElaborationResult with generated markdown
        """
        # Get all facts as dicts
        all_facts = self._facts_to_dicts(fact_store)

        # Filter by category if specified
        relevant_facts = FactFilter.filter_by_category(
            all_facts, request.fact_category
        )

        # If request has pre-filtered facts, use those instead
        if request.relevant_facts:
            relevant_facts = request.relevant_facts

        # Handle empty facts
        if not relevant_facts:
            return ElaborationResult(
                block_id=request.block_id,
                status="empty",
                generated_markdown=f"[[REQUIRES REVIEW: No facts found for {request.block_id}. "
                f"Category filter: {request.fact_category or 'none'}]]",
                confidence=0.0,
                reason="No relevant facts found",
            )

        # Serialize facts for LLM
        facts_json = json.dumps(relevant_facts, indent=2, ensure_ascii=False)

        try:
            result = self.llm.elaborate_section(
                block_id=request.block_id,
                hint=request.hint,
                fact_category=request.fact_category,
                template_context=request.template_context,
                facts_json=facts_json,
            )

            return ElaborationResult(
                block_id=request.block_id,
                status="generated",
                generated_markdown=result.get("generated_markdown", ""),
                source_facts=result.get("source_facts", []),
                source_files=result.get("source_files", []),
                confidence=float(result.get("confidence", 0.9)),
            )

        except Exception as e:
            return ElaborationResult(
                block_id=request.block_id,
                status="error",
                generated_markdown=f"[[REQUIRES REVIEW: Error elaborating {request.block_id}: {str(e)}]]",
                confidence=0.0,
                reason=f"Error: {str(e)}",
            )

    def elaborate_all(
        self,
        requests: list[ElaborationRequest],
        fact_store: FactStore,
        progress_callback: callable | None = None,
    ) -> Elaborations:
        """Elaborate all blocks from requests.

        Args:
            requests: List of elaboration requests
            fact_store: Store of extracted facts
            progress_callback: Optional callback(block_id, index, total)

        Returns:
            Elaborations with all results
        """
        results = []
        total = len(requests)

        for i, request in enumerate(requests):
            if progress_callback:
                progress_callback(request.block_id, i + 1, total)

            result = self.elaborate(request, fact_store)
            results.append(result)

        return Elaborations(results=results)

    def save_elaborations(
        self,
        elaborations: Elaborations,
        output_path: Path,
    ) -> None:
        """Save elaborations to JSON.

        Args:
            elaborations: Elaborations collection
            output_path: Path to output file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(elaborations.to_dict(), indent=2, ensure_ascii=False)
        )

    def _facts_to_dicts(self, fact_store: FactStore) -> list[dict[str, Any]]:
        """Convert fact store to list of dictionaries.

        Args:
            fact_store: Store of extracted facts

        Returns:
            List of fact dictionaries
        """
        facts = []
        for fact in fact_store.all_facts():
            # Find source filename from extractions
            source_file = None
            for extraction in fact_store.extractions:
                if extraction.doc_id == fact.doc_id:
                    source_file = Path(extraction.file_path).name
                    break

            facts.append({
                "fact_id": fact.fact_id,
                "category": fact.category,
                "key": fact.key,
                "value": fact.value,
                "value_type": fact.value_type,
                "raw_text": fact.raw_text,
                "unit": fact.unit,
                "confidence": fact.confidence,
                "doc_id": fact.doc_id,
                "source_file": source_file,
                "location": {
                    "section": fact.location.section,
                    "table": fact.location.table,
                    "row": fact.location.row,
                    "column": fact.location.column,
                },
            })

        return facts
