"""Evidence retrieval module.

Contains:
- fact_retriever: Extensible fact retrieval strategies (AllFactsRetriever, KeywordRetriever)
- index: BM25 and embedding indexing
- search: Hybrid retrieval with configurable modes
"""

from drhp_agent.retrieve.fact_retriever import (
    FactRetriever,
    AllFactsRetriever,
    KeywordRetriever,
)

__all__ = [
    "FactRetriever",
    "AllFactsRetriever",
    "KeywordRetriever",
]
