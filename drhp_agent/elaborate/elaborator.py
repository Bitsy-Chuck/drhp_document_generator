"""LLM-based elaboration for hybrid template system.

Tasks 13.4.1-13.4.6: Generate rich prose from facts for elaboration blocks.
Tasks 16.3: Integrate with retriever module.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from drhp_agent.core.dtos import (
    FactStore,
    ElaborationRequest,
    ElaborationResult,
)
from drhp_agent.llm.client import LLMClient
from drhp_agent.retrieve.fact_retriever import FactRetriever, AllFactsRetriever


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


class Elaborator:
    """Generates elaborate prose from facts using LLM."""

    def __init__(
        self,
        llm_client: LLMClient,
        retriever: FactRetriever | None = None,
    ):
        """Initialize with LLM client and optional retriever.

        Args:
            llm_client: Configured LLM client
            retriever: Optional fact retriever (defaults to AllFactsRetriever)
        """
        self.llm = llm_client
        self.retriever = retriever or AllFactsRetriever()

    def elaborate(
        self,
        request: ElaborationRequest,
        fact_store: FactStore,
    ) -> ElaborationResult:
        """Elaborate a single block using facts.

        Uses the configured retriever to select facts, then passes them
        to the LLM for semantic matching and prose generation.

        Args:
            request: Elaboration request with block details
            fact_store: Store of extracted facts

        Returns:
            ElaborationResult with generated markdown
        """
        # Use pre-populated facts from request if available
        if request.relevant_facts:
            relevant_facts = request.relevant_facts
        else:
            # Use retriever to get facts based on hint
            relevant_facts = self.retriever.retrieve(
                fact_store,
                request.hint,
                request.template_context,
            )

        # Handle empty facts
        if not relevant_facts:
            logger.warning("Block %s: no facts found, returning empty", request.block_id)
            return ElaborationResult(
                block_id=request.block_id,
                status="empty",
                generated_markdown=f"[[REQUIRES REVIEW: No facts found for {request.block_id}]]",
                confidence=0.0,
                reason="No facts available in fact store",
            )

        # Serialize facts for LLM
        facts_json = json.dumps(relevant_facts, indent=2, ensure_ascii=False)

        try:
            result = self.llm.elaborate_section(
                block_id=request.block_id,
                hint=request.hint,
                template_context=request.template_context,
                facts_json=facts_json,
            )

            elab_result = ElaborationResult(
                block_id=request.block_id,
                status="generated",
                generated_markdown=result.get("generated_markdown", ""),
                source_facts=result.get("source_facts", []),
                source_files=result.get("source_files", []),
                confidence=float(result.get("confidence", 0.9)),
            )
            logger.info("Block %s: elaborated (confidence=%.2f)", request.block_id, elab_result.confidence)
            return elab_result

        except Exception as e:
            logger.error("Block %s: elaboration error — %s", request.block_id, e)
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

        Deprecated: Use retriever._facts_to_dicts() directly for more control.
        This method is kept for backward compatibility.

        Args:
            fact_store: Store of extracted facts

        Returns:
            List of fact dictionaries
        """
        return self.retriever._facts_to_dicts(fact_store)
