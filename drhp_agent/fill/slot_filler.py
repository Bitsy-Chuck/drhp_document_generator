"""LLM-based slot filling.

Tasks 6.1-6.5: Fill template slots using extracted facts via LLM.
Tasks 16.2: Integrate with retriever module.
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
    SlotFillRequest,
    SlotFillResult,
)
from drhp_agent.llm.client import LLMClient
from drhp_agent.retrieve.fact_retriever import FactRetriever, AllFactsRetriever


@dataclass
class FilledSlots:
    """Collection of filled slot results."""

    results: list[SlotFillResult] = field(default_factory=list)

    @property
    def filled_count(self) -> int:
        return sum(1 for r in self.results if r.status == "filled")

    @property
    def missing_count(self) -> int:
        return sum(1 for r in self.results if r.status == "missing")

    @property
    def conflict_count(self) -> int:
        return sum(1 for r in self.results if r.status == "conflict")

    @property
    def low_confidence_count(self) -> int:
        return sum(1 for r in self.results if r.status == "low_confidence")

    def get_by_id(self, slot_id: str) -> SlotFillResult | None:
        """Get result by slot ID."""
        for r in self.results:
            if r.slot_id == slot_id:
                return r
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "summary": {
                "total": len(self.results),
                "filled": self.filled_count,
                "missing": self.missing_count,
                "conflict": self.conflict_count,
                "low_confidence": self.low_confidence_count,
            },
            "slots": [
                {
                    "slot_id": r.slot_id,
                    "status": r.status,
                    "value": r.value,
                    "formatted_value": r.formatted_value,
                    "source_facts": r.source_facts,
                    "source_files": r.source_files,
                    "confidence": r.confidence,
                    "reason": r.reason,
                }
                for r in self.results
            ],
        }


class SlotFiller:
    """Fills template slots using LLM and extracted facts."""

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

    def fill_slot(
        self,
        request: SlotFillRequest,
        fact_store: FactStore,
    ) -> SlotFillResult:
        """Fill a single slot using extracted facts.

        Uses the configured retriever to select facts for the LLM.

        Args:
            request: Slot fill request with slot details
            fact_store: Store of extracted facts

        Returns:
            SlotFillResult with filled value or status
        """
        # Retrieve relevant facts using the configured retriever
        query = request.slot_hint or request.slot_id
        facts = self.retriever.retrieve(fact_store, query, request.slot_context)
        facts_json = json.dumps(facts, indent=2, ensure_ascii=False)

        try:
            result = self.llm.fill_slot(
                slot_id=request.slot_id,
                slot_type=request.slot_type,
                slot_hint=request.slot_hint,
                slot_context=request.slot_context,
                facts_json=facts_json,
            )

            fill_result = SlotFillResult(
                slot_id=result.get("slot_id", request.slot_id),
                status=result.get("status", "missing"),
                value=result.get("value"),
                formatted_value=result.get("formatted_value"),
                source_facts=result.get("source_facts", []),
                source_files=result.get("source_files", []),
                confidence=float(result.get("confidence", 0.0)),
                reason=result.get("reason"),
            )
            logger.info("Slot %s: status=%s confidence=%.2f",
                        request.slot_id, fill_result.status, fill_result.confidence)
            return fill_result

        except Exception as e:
            logger.error("Slot %s: fill error — %s", request.slot_id, e)
            return SlotFillResult(
                slot_id=request.slot_id,
                status="missing",
                reason=f"Error filling slot: {str(e)}",
                confidence=0.0,
            )

    def fill_all(
        self,
        requests: list[SlotFillRequest],
        fact_store: FactStore,
        progress_callback: callable | None = None,
    ) -> FilledSlots:
        """Fill all slots from requests.

        Args:
            requests: List of slot fill requests
            fact_store: Store of extracted facts
            progress_callback: Optional callback(slot_id, index, total)

        Returns:
            FilledSlots with all results
        """
        results = []
        total = len(requests)

        for i, request in enumerate(requests):
            if progress_callback:
                progress_callback(request.slot_id, i + 1, total)

            result = self.fill_slot(request, fact_store)
            results.append(result)

        return FilledSlots(results=results)

    def save_filled_slots(
        self,
        filled: FilledSlots,
        output_path: Path,
    ) -> None:
        """Save filled slots to JSON.

        Args:
            filled: Filled slots collection
            output_path: Path to output file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(filled.to_dict(), indent=2, ensure_ascii=False)
        )

    def _serialize_facts(self, fact_store: FactStore) -> str:
        """Serialize all facts to JSON for LLM prompt.

        Deprecated: Use retriever.retrieve() directly for more control.
        This method is kept for backward compatibility.

        Args:
            fact_store: Store of extracted facts

        Returns:
            JSON string of all facts
        """
        # Use retriever's _facts_to_dicts method for consistent serialization
        facts = self.retriever._facts_to_dicts(fact_store)
        return json.dumps(facts, indent=2, ensure_ascii=False)
