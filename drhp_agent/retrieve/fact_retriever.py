"""Fact retriever module for extensible fact retrieval strategies.

Tasks 16.1-16.5: Create retriever abstraction for slot filling and elaboration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from drhp_agent.core.dtos import FactStore


class FactRetriever(ABC):
    """Base class for fact retrieval strategies.

    Retrievers are responsible for selecting which facts to pass to
    the LLM for slot filling or elaboration. Different strategies
    can be used depending on the use case (e.g., all facts, keyword
    matching, or semantic/embedding-based retrieval).
    """

    @abstractmethod
    def retrieve(
        self,
        fact_store: FactStore,
        query: str,
        context: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve relevant facts for the given query.

        Args:
            fact_store: Store of all extracted facts
            query: The query/hint describing what facts are needed
            context: Optional surrounding template context

        Returns:
            List of fact dictionaries ready for LLM consumption
        """
        pass

    def _facts_to_dicts(
        self, fact_store: FactStore
    ) -> list[dict[str, Any]]:
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


class AllFactsRetriever(FactRetriever):
    """Pass all facts to the LLM.

    This is the default retriever that passes all facts to the LLM,
    letting the LLM do semantic matching based on the query/hint.

    Best for:
    - Small to medium fact stores (< 200 facts)
    - When facts are interconnected and context matters
    - Maximum accuracy at the cost of token usage
    """

    def retrieve(
        self,
        fact_store: FactStore,
        query: str,
        context: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return all facts for LLM semantic matching.

        Args:
            fact_store: Store of all extracted facts
            query: The query (unused - all facts returned)
            context: Optional context (unused)

        Returns:
            List of all fact dictionaries
        """
        return self._facts_to_dicts(fact_store)


class KeywordRetriever(FactRetriever):
    """Filter facts by keyword matching.

    Extracts keywords from the query/hint and filters facts that
    contain those keywords in their key or raw_text fields.
    Falls back to all facts if no matches found.

    Best for:
    - Large fact stores (> 200 facts)
    - When queries are specific and targeted
    - Reducing token usage while maintaining relevance
    """

    # Common stop words to exclude from keyword extraction
    STOP_WORDS = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
        "be", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "must", "shall", "can", "this",
        "that", "these", "those", "it", "its", "all", "each", "every", "both",
        "few", "more", "most", "other", "some", "such", "no", "nor", "not",
        "only", "own", "same", "so", "than", "too", "very", "just", "any",
        "generate", "create", "provide", "include", "detail", "details",
        "table", "list", "show", "display", "using", "use", "based",
    }

    # Minimum keyword length to consider
    MIN_KEYWORD_LENGTH = 3

    def __init__(self, fallback_to_all: bool = True):
        """Initialize keyword retriever.

        Args:
            fallback_to_all: If True, return all facts when no keyword matches
        """
        self.fallback_to_all = fallback_to_all

    def retrieve(
        self,
        fact_store: FactStore,
        query: str,
        context: str | None = None,
    ) -> list[dict[str, Any]]:
        """Filter facts by keywords from query.

        Args:
            fact_store: Store of all extracted facts
            query: The query/hint to extract keywords from
            context: Optional context (combined with query for keywords)

        Returns:
            Filtered list of fact dictionaries, or all if no matches
        """
        all_facts = self._facts_to_dicts(fact_store)

        if not all_facts:
            return []

        # Extract keywords from query (and context if provided)
        text_to_search = query
        if context:
            text_to_search = f"{query} {context}"

        keywords = self._extract_keywords(text_to_search)

        if not keywords:
            # No meaningful keywords - return all facts
            return all_facts

        # Filter facts by keywords
        matched_facts = self._filter_by_keywords(all_facts, keywords)

        if matched_facts:
            return matched_facts
        elif self.fallback_to_all:
            # No matches - fall back to all facts
            return all_facts
        else:
            return []

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract meaningful keywords from text.

        Args:
            text: Text to extract keywords from

        Returns:
            List of lowercase keywords
        """
        # Tokenize: split on non-alphanumeric characters
        import re
        tokens = re.findall(r'\b[a-zA-Z0-9_]+\b', text.lower())

        # Filter out stop words and short tokens
        keywords = [
            token for token in tokens
            if token not in self.STOP_WORDS
            and len(token) >= self.MIN_KEYWORD_LENGTH
        ]

        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)

        return unique_keywords

    def _filter_by_keywords(
        self,
        facts: list[dict[str, Any]],
        keywords: list[str],
    ) -> list[dict[str, Any]]:
        """Filter facts that match any keyword.

        Args:
            facts: List of fact dictionaries
            keywords: List of keywords to match

        Returns:
            Facts containing any of the keywords
        """
        matched = []
        for fact in facts:
            key = fact.get("key", "").lower()
            raw = fact.get("raw_text", "").lower()
            value_str = str(fact.get("value", "")).lower()

            # Check if any keyword matches
            for kw in keywords:
                if kw in key or kw in raw or kw in value_str:
                    matched.append(fact)
                    break

        return matched
