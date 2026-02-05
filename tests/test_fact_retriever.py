"""Tests for fact retriever module (Task 16)."""

import pytest

from drhp_agent.core.dtos import (
    FactStore,
    DocumentExtraction,
    ExtractedFact,
    FactLocation,
)
from drhp_agent.retrieve.fact_retriever import (
    FactRetriever,
    AllFactsRetriever,
    KeywordRetriever,
)


class TestFactRetrieverBase:
    """Tests for FactRetriever base class."""

    @pytest.fixture
    def sample_fact_store(self):
        """Create a sample fact store with test data."""
        facts = [
            ExtractedFact(
                fact_id="F001",
                key="company_name",
                value="Test Corp Private Limited",
                value_type="text",
                raw_text="Company Name: Test Corp Private Limited",
                location=FactLocation(section="Header"),
                doc_id="DOC_001",
            ),
            ExtractedFact(
                fact_id="F002",
                key="authorized_shares",
                value=30000,
                value_type="integer",
                raw_text="30,000 equity shares authorized",
                location=FactLocation(section="Capital Structure"),
                doc_id="DOC_001",
            ),
            ExtractedFact(
                fact_id="F003",
                key="allotment_date",
                value="2019-05-15",
                value_type="date",
                raw_text="Allotment Date: 15 May 2019",
                location=FactLocation(section="Allotment Details"),
                doc_id="DOC_001",
            ),
            ExtractedFact(
                fact_id="F004",
                key="allottee_name",
                value="Mr. Rohit Sharma",
                value_type="text",
                raw_text="Allottee: Mr. Rohit Sharma",
                location=FactLocation(table="Allottees", row="1"),
                doc_id="DOC_002",
            ),
            ExtractedFact(
                fact_id="F005",
                key="shares_allotted",
                value=192,
                value_type="integer",
                raw_text="192 equity shares allotted",
                location=FactLocation(table="Allottees", row="1"),
                doc_id="DOC_002",
            ),
        ]
        extractions = [
            DocumentExtraction(
                doc_id="DOC_001",
                file_path="/test/company_info.md",
                document_type="pas3_form",
                facts=facts[:3],
            ),
            DocumentExtraction(
                doc_id="DOC_002",
                file_path="/test/allottees.md",
                document_type="list_of_allottees",
                facts=facts[3:],
            ),
        ]
        return FactStore(extractions=extractions)

    def test_facts_to_dicts_converts_all_facts(self, sample_fact_store):
        """_facts_to_dicts should convert all facts to dictionaries."""
        retriever = AllFactsRetriever()
        facts = retriever._facts_to_dicts(sample_fact_store)

        assert len(facts) == 5
        assert all(isinstance(f, dict) for f in facts)

    def test_facts_to_dicts_includes_required_fields(self, sample_fact_store):
        """Converted facts should have all required fields."""
        retriever = AllFactsRetriever()
        facts = retriever._facts_to_dicts(sample_fact_store)

        required_fields = [
            "fact_id", "key", "value", "value_type", "raw_text",
            "unit", "confidence", "doc_id", "source_file", "location"
        ]
        for fact in facts:
            for field in required_fields:
                assert field in fact

    def test_facts_to_dicts_includes_source_file(self, sample_fact_store):
        """Converted facts should have source_file from extraction."""
        retriever = AllFactsRetriever()
        facts = retriever._facts_to_dicts(sample_fact_store)

        # Facts from DOC_001 should have company_info.md
        doc1_facts = [f for f in facts if f["doc_id"] == "DOC_001"]
        assert all(f["source_file"] == "company_info.md" for f in doc1_facts)

        # Facts from DOC_002 should have allottees.md
        doc2_facts = [f for f in facts if f["doc_id"] == "DOC_002"]
        assert all(f["source_file"] == "allottees.md" for f in doc2_facts)


class TestAllFactsRetriever:
    """Tests for AllFactsRetriever."""

    @pytest.fixture
    def sample_fact_store(self):
        """Create a sample fact store."""
        facts = [
            ExtractedFact(
                fact_id="F001",
                key="company_name",
                value="Test Corp",
                value_type="text",
                raw_text="Test Corp",
                location=FactLocation(),
                doc_id="DOC_001",
            ),
            ExtractedFact(
                fact_id="F002",
                key="authorized_shares",
                value=30000,
                value_type="integer",
                raw_text="30,000 shares",
                location=FactLocation(),
                doc_id="DOC_001",
            ),
        ]
        extraction = DocumentExtraction(
            doc_id="DOC_001",
            file_path="/test/doc.md",
            document_type="test",
            facts=facts,
        )
        return FactStore(extractions=[extraction])

    def test_retrieve_returns_all_facts(self, sample_fact_store):
        """AllFactsRetriever should return all facts regardless of query."""
        retriever = AllFactsRetriever()

        facts = retriever.retrieve(sample_fact_store, "any query")

        assert len(facts) == 2

    def test_retrieve_ignores_query(self, sample_fact_store):
        """Query should not affect results for AllFactsRetriever."""
        retriever = AllFactsRetriever()

        facts1 = retriever.retrieve(sample_fact_store, "company name")
        facts2 = retriever.retrieve(sample_fact_store, "shares allotted")

        assert len(facts1) == len(facts2)
        assert facts1 == facts2

    def test_retrieve_empty_store(self):
        """Should return empty list for empty fact store."""
        retriever = AllFactsRetriever()
        empty_store = FactStore(extractions=[])

        facts = retriever.retrieve(empty_store, "any query")

        assert facts == []


class TestKeywordRetriever:
    """Tests for KeywordRetriever."""

    @pytest.fixture
    def sample_fact_store(self):
        """Create a sample fact store with diverse facts."""
        facts = [
            ExtractedFact(
                fact_id="F001",
                key="company_name",
                value="Test Corp Private Limited",
                value_type="text",
                raw_text="Company: Test Corp Private Limited",
                location=FactLocation(),
                doc_id="DOC_001",
            ),
            ExtractedFact(
                fact_id="F002",
                key="authorized_shares",
                value=30000,
                value_type="integer",
                raw_text="Authorized equity shares: 30,000",
                location=FactLocation(),
                doc_id="DOC_001",
            ),
            ExtractedFact(
                fact_id="F003",
                key="allotment_date",
                value="2019-05-15",
                value_type="date",
                raw_text="Date of allotment: 15 May 2019",
                location=FactLocation(),
                doc_id="DOC_001",
            ),
            ExtractedFact(
                fact_id="F004",
                key="shares_allotted",
                value=960,
                value_type="integer",
                raw_text="960 equity shares were allotted",
                location=FactLocation(),
                doc_id="DOC_001",
            ),
            ExtractedFact(
                fact_id="F005",
                key="board_resolution_date",
                value="2019-05-15",
                value_type="date",
                raw_text="Board resolution dated 15 May 2019",
                location=FactLocation(),
                doc_id="DOC_001",
            ),
        ]
        extraction = DocumentExtraction(
            doc_id="DOC_001",
            file_path="/test/doc.md",
            document_type="test",
            facts=facts,
        )
        return FactStore(extractions=[extraction])

    def test_retrieve_filters_by_keyword(self, sample_fact_store):
        """Should filter facts containing the keyword."""
        retriever = KeywordRetriever()

        # Query with "shares" should match F002, F004
        facts = retriever.retrieve(sample_fact_store, "shares")

        # Should match F002 (authorized_shares, "equity shares"), F004 (shares_allotted, "equity shares")
        assert len(facts) == 2
        fact_ids = {f["fact_id"] for f in facts}
        assert "F002" in fact_ids
        assert "F004" in fact_ids

    def test_retrieve_multiple_keywords(self, sample_fact_store):
        """Should match facts with any of multiple keywords."""
        retriever = KeywordRetriever()

        facts = retriever.retrieve(sample_fact_store, "company authorized shares")

        # Should match F001 (company), F002 (authorized, shares)
        assert len(facts) >= 2

    def test_retrieve_fallback_to_all(self, sample_fact_store):
        """Should fall back to all facts when no keyword matches."""
        retriever = KeywordRetriever(fallback_to_all=True)

        facts = retriever.retrieve(sample_fact_store, "nonexistent_keyword_xyz")

        # Should return all facts as fallback
        assert len(facts) == 5

    def test_retrieve_no_fallback(self, sample_fact_store):
        """Should return empty list when no matches and fallback disabled."""
        retriever = KeywordRetriever(fallback_to_all=False)

        facts = retriever.retrieve(sample_fact_store, "nonexistent_keyword_xyz")

        assert facts == []

    def test_retrieve_excludes_stop_words(self, sample_fact_store):
        """Stop words in query should not affect matching."""
        retriever = KeywordRetriever()

        # "the", "of", "and" are stop words
        facts1 = retriever.retrieve(sample_fact_store, "company")
        facts2 = retriever.retrieve(sample_fact_store, "the company and shares")

        # Should get same results with "company" keyword
        company_facts1 = [f for f in facts1 if "company" in f["key"]]
        company_facts2 = [f for f in facts2 if "company" in f["key"]]
        assert len(company_facts1) == len(company_facts2)

    def test_retrieve_case_insensitive(self, sample_fact_store):
        """Keyword matching should be case insensitive."""
        retriever = KeywordRetriever()

        facts_lower = retriever.retrieve(sample_fact_store, "company")
        facts_upper = retriever.retrieve(sample_fact_store, "COMPANY")
        facts_mixed = retriever.retrieve(sample_fact_store, "Company")

        assert len(facts_lower) == len(facts_upper) == len(facts_mixed)

    def test_retrieve_with_context(self, sample_fact_store):
        """Context should be combined with query for keyword extraction."""
        retriever = KeywordRetriever()

        # Query with "shares" alone
        facts_shares_only = retriever.retrieve(
            sample_fact_store, "shares"
        )

        # With context that adds "company" keyword
        facts_with_context = retriever.retrieve(
            sample_fact_store,
            "shares",
            context="company"
        )

        # Context adds "company" keyword, so should match company_name too
        assert len(facts_with_context) >= len(facts_shares_only)
        fact_ids = {f["fact_id"] for f in facts_with_context}
        assert "F001" in fact_ids  # company_name matched by "company"

    def test_extract_keywords_removes_short_words(self):
        """Keywords shorter than minimum length should be excluded."""
        retriever = KeywordRetriever()

        keywords = retriever._extract_keywords("I am a test of the code")

        # "I", "am", "a", "of" are too short (< 3 chars)
        assert "i" not in keywords
        assert "am" not in keywords
        assert "a" not in keywords
        assert "test" in keywords
        assert "code" in keywords

    def test_extract_keywords_unique(self):
        """Duplicate keywords should be removed."""
        retriever = KeywordRetriever()

        keywords = retriever._extract_keywords("test test test different")

        assert keywords.count("test") == 1
        assert "different" in keywords


class TestRetrieverIntegration:
    """Integration tests for retrievers with SlotFiller and Elaborator."""

    @pytest.fixture
    def sample_fact_store(self):
        """Create a sample fact store."""
        facts = [
            ExtractedFact(
                fact_id="F001",
                key="company_name",
                value="Test Corp",
                value_type="text",
                raw_text="Test Corp",
                location=FactLocation(),
                doc_id="DOC_001",
            ),
        ]
        extraction = DocumentExtraction(
            doc_id="DOC_001",
            file_path="/test/doc.md",
            document_type="test",
            facts=facts,
        )
        return FactStore(extractions=[extraction])

    def test_slot_filler_with_custom_retriever(self, sample_fact_store):
        """SlotFiller should accept custom retriever."""
        from unittest.mock import Mock
        from drhp_agent.fill.slot_filler import SlotFiller
        from drhp_agent.core.dtos import SlotFillRequest

        mock_llm = Mock()
        mock_llm.fill_slot.return_value = {
            "slot_id": "company_name",
            "status": "filled",
            "value": "Test Corp",
            "confidence": 0.95,
        }

        # Use KeywordRetriever
        retriever = KeywordRetriever()
        filler = SlotFiller(mock_llm, retriever=retriever)

        request = SlotFillRequest(
            slot_id="company_name",
            slot_type="text",
            slot_hint="Company name",
        )
        result = filler.fill_slot(request, sample_fact_store)

        assert result.status == "filled"
        assert result.value == "Test Corp"

    def test_elaborator_with_custom_retriever(self, sample_fact_store):
        """Elaborator should accept custom retriever."""
        from unittest.mock import Mock
        from drhp_agent.elaborate.elaborator import Elaborator
        from drhp_agent.core.dtos import ElaborationRequest

        mock_llm = Mock()
        mock_llm.elaborate_section.return_value = {
            "generated_markdown": "# Test Content",
            "source_facts": ["F001"],
            "source_files": ["doc.md"],
            "confidence": 0.95,
        }

        # Use KeywordRetriever
        retriever = KeywordRetriever()
        elaborator = Elaborator(mock_llm, retriever=retriever)

        request = ElaborationRequest(
            block_id="test_block",
            hint="Generate content about the company",
        )
        result = elaborator.elaborate(request, sample_fact_store)

        assert result.status == "generated"
        assert "Test Content" in result.generated_markdown

    def test_default_retriever_is_all_facts(self, sample_fact_store):
        """Default retriever should be AllFactsRetriever."""
        from unittest.mock import Mock
        from drhp_agent.fill.slot_filler import SlotFiller
        from drhp_agent.elaborate.elaborator import Elaborator

        mock_llm = Mock()

        filler = SlotFiller(mock_llm)
        elaborator = Elaborator(mock_llm)

        assert isinstance(filler.retriever, AllFactsRetriever)
        assert isinstance(elaborator.retriever, AllFactsRetriever)
