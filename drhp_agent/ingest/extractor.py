"""LLM-based fact extraction.

Tasks 4.5-4.10: Extract facts from documents using LLM.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from drhp_agent.core.dtos import (
    DocumentExtraction,
    ExtractedFact,
    FactLocation,
    FactStore,
)
from drhp_agent.llm.client import LLMClient


class FactExtractor:
    """Extracts facts from documents using LLM."""

    def     __init__(self, llm_client: LLMClient):
        """Initialize extractor with LLM client.

        Args:
            llm_client: Configured LLM client
        """
        self.llm = llm_client

    def extract_from_document(
        self,
        content: str,
        file_path: Path,
        doc_id: str,
    ) -> DocumentExtraction:
        """Extract facts from a single document.

        Args:
            content: Document text content
            file_path: Path to source file
            doc_id: Unique document identifier

        Returns:
            DocumentExtraction with all extracted facts
        """
        logger.info("Extracting facts from %s (%s)", file_path.name, doc_id)
        try:
            result = self.llm.extract_facts(content, file_path.name)
            facts = self._parse_facts(result, doc_id)

            logger.info("Extracted %d facts from %s", len(facts), file_path.name)
            return DocumentExtraction(
                doc_id=doc_id,
                file_path=str(file_path),
                document_type=result.get("document_type", "other"),
                facts=facts,
                document_date=result.get("document_date"),
                extraction_timestamp=datetime.now(),
            )

        except Exception as e:
            logger.error("Extraction failed for %s: %s", file_path.name, e)
            return DocumentExtraction(
                doc_id=doc_id,
                file_path=str(file_path),
                document_type="error",
                facts=[],
                error=str(e),
                extraction_timestamp=datetime.now(),
            )

    def _parse_facts(
        self,
        llm_result: dict[str, Any],
        doc_id: str,
    ) -> list[ExtractedFact]:
        """Parse LLM extraction result into ExtractedFact objects.

        Args:
            llm_result: Raw LLM response
            doc_id: Document ID to attach to facts

        Returns:
            List of ExtractedFact objects
        """
        facts = []
        for fact_data in llm_result.get("facts", []):
            location_data = fact_data.get("location", {})
            location = FactLocation(
                section=location_data.get("section"),
                table=location_data.get("table"),
                row=location_data.get("row"),
                column=location_data.get("column"),
            )

            fact = ExtractedFact(
                fact_id=fact_data.get("fact_id", f"F_{len(facts)+1:03d}"),
                key=fact_data.get("key", "unknown"),
                value=fact_data.get("value"),
                value_type=fact_data.get("value_type", "text"),
                raw_text=fact_data.get("raw_text", ""),
                location=location,
                unit=fact_data.get("unit"),
                confidence=float(fact_data.get("confidence", 1.0)),
                doc_id=doc_id,
            )
            facts.append(fact)

        return facts

    def extract_all(
        self,
        documents: list[tuple[Path, str, str]],
    ) -> FactStore:
        """Extract facts from all documents.

        Args:
            documents: List of (path, content, checksum) tuples

        Returns:
            FactStore containing all extractions
        """
        extractions = []
        for i, (path, content, checksum) in enumerate(documents):
            doc_id = f"DOC_{i+1:03d}"
            extraction = self.extract_from_document(content, path, doc_id)
            extractions.append(extraction)

        return FactStore(extractions=extractions)

    def save_fact_store(self, store: FactStore, output_path: Path) -> None:
        """Save FactStore to JSON file.

        Args:
            store: FactStore to save
            output_path: Path to output file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "extractions": [
                {
                    "doc_id": ext.doc_id,
                    "file_path": ext.file_path,
                    "document_type": ext.document_type,
                    "document_date": ext.document_date,
                    "extraction_timestamp": ext.extraction_timestamp.isoformat()
                    if ext.extraction_timestamp
                    else None,
                    "error": ext.error,
                    "facts": [
                        {
                            "fact_id": f.fact_id,
                            "key": f.key,
                            "value": f.value,
                            "value_type": f.value_type,
                            "raw_text": f.raw_text,
                            "unit": f.unit,
                            "confidence": f.confidence,
                            "doc_id": f.doc_id,
                            "location": {
                                "section": f.location.section,
                                "table": f.location.table,
                                "row": f.location.row,
                                "column": f.location.column,
                            },
                        }
                        for f in ext.facts
                    ],
                }
                for ext in store.extractions
            ]
        }

        output_path.write_text(json.dumps(data, indent=2))
