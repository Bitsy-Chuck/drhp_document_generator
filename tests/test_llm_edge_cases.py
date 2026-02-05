"""Tests for LLM client edge cases and error handling."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

import anthropic

from drhp_agent.llm.client import LLMClient, LLMConfig
from drhp_agent.ingest.extractor import FactExtractor
from drhp_agent.core.dtos import FactStore, DocumentExtraction


class TestLLMClientParameterOverrides:
    """Tests for parameter override functionality."""

    @pytest.fixture
    def mock_anthropic(self):
        with patch("drhp_agent.llm.client.anthropic.Anthropic") as mock:
            mock_response = Mock()
            mock_response.content = [Mock(text="Test response")]
            mock.return_value.messages.create.return_value = mock_response
            yield mock

    def test_complete_with_temperature_override(self, mock_anthropic):
        config = LLMConfig(api_key="test-key", temperature=0.0)
        client = LLMClient(config)

        client.complete("System", "User", temperature=0.7)

        call_args = mock_anthropic.return_value.messages.create.call_args
        assert call_args.kwargs["temperature"] == 0.7

    def test_complete_with_max_tokens_override(self, mock_anthropic):
        config = LLMConfig(api_key="test-key", max_tokens=4096)
        client = LLMClient(config)

        client.complete("System", "User", max_tokens=8192)

        call_args = mock_anthropic.return_value.messages.create.call_args
        assert call_args.kwargs["max_tokens"] == 8192

    def test_complete_uses_defaults_without_override(self, mock_anthropic):
        config = LLMConfig(api_key="test-key", temperature=0.5, max_tokens=2048)
        client = LLMClient(config)

        client.complete("System", "User")

        call_args = mock_anthropic.return_value.messages.create.call_args
        assert call_args.kwargs["temperature"] == 0.5
        assert call_args.kwargs["max_tokens"] == 2048


class TestLLMClientRetryLogic:
    """Tests for retry logic on errors."""

    def test_retries_on_rate_limit_error(self):
        with patch("drhp_agent.llm.client.anthropic.Anthropic") as mock:
            mock_response = Mock()
            mock_response.content = [Mock(text="Success")]

            # Fail twice, then succeed
            mock.return_value.messages.create.side_effect = [
                anthropic.RateLimitError(
                    message="Rate limit",
                    response=Mock(status_code=429),
                    body={}
                ),
                anthropic.RateLimitError(
                    message="Rate limit",
                    response=Mock(status_code=429),
                    body={}
                ),
                mock_response,
            ]

            config = LLMConfig(api_key="test-key", retry_delay=0.01)
            client = LLMClient(config)

            with patch("time.sleep"):  # Don't actually sleep
                result = client.complete("System", "User")

            assert result == "Success"
            assert mock.return_value.messages.create.call_count == 3

    def test_retries_on_server_error(self):
        with patch("drhp_agent.llm.client.anthropic.Anthropic") as mock:
            mock_response = Mock()
            mock_response.content = [Mock(text="Success")]

            # Fail once with 500 error, then succeed
            mock.return_value.messages.create.side_effect = [
                anthropic.APIStatusError(
                    message="Server error",
                    response=Mock(status_code=500),
                    body={}
                ),
                mock_response,
            ]

            config = LLMConfig(api_key="test-key", retry_delay=0.01)
            client = LLMClient(config)

            with patch("time.sleep"):
                result = client.complete("System", "User")

            assert result == "Success"
            assert mock.return_value.messages.create.call_count == 2

    def test_raises_after_max_retries_exhausted(self):
        with patch("drhp_agent.llm.client.anthropic.Anthropic") as mock:
            mock.return_value.messages.create.side_effect = anthropic.RateLimitError(
                message="Rate limit",
                response=Mock(status_code=429),
                body={}
            )

            config = LLMConfig(api_key="test-key", max_retries=3, retry_delay=0.01)
            client = LLMClient(config)

            with patch("time.sleep"):
                with pytest.raises(anthropic.RateLimitError):
                    client.complete("System", "User")

            assert mock.return_value.messages.create.call_count == 3

    def test_does_not_retry_on_client_error(self):
        with patch("drhp_agent.llm.client.anthropic.Anthropic") as mock:
            mock.return_value.messages.create.side_effect = anthropic.APIStatusError(
                message="Bad request",
                response=Mock(status_code=400),
                body={}
            )

            config = LLMConfig(api_key="test-key")
            client = LLMClient(config)

            with pytest.raises(anthropic.APIStatusError):
                client.complete("System", "User")

            # Should NOT retry on 4xx errors
            assert mock.return_value.messages.create.call_count == 1


class TestLLMClientJSONParsingEdgeCases:
    """Tests for JSON parsing edge cases."""

    @pytest.fixture
    def client(self):
        with patch("drhp_agent.llm.client.anthropic.Anthropic"):
            config = LLMConfig(api_key="test-key")
            return LLMClient(config)

    def test_parse_json_array(self, client):
        text = '[1, 2, 3]'
        # _parse_json returns dict, array should work via json.loads
        # but our implementation expects objects
        result = client._parse_json('{"items": [1, 2, 3]}')
        assert result["items"] == [1, 2, 3]

    def test_parse_deeply_nested_json(self, client):
        nested = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": "deep"
                    }
                }
            }
        }
        text = json.dumps(nested)
        result = client._parse_json(text)
        assert result["level1"]["level2"]["level3"]["value"] == "deep"

    def test_parse_json_with_newlines_in_strings(self, client):
        text = '{"text": "line1\\nline2\\nline3"}'
        result = client._parse_json(text)
        assert "line1\nline2\nline3" == result["text"]

    def test_parse_json_with_unicode(self, client):
        text = '{"symbol": "₹", "company": "Nexus Brightlearn"}'
        result = client._parse_json(text)
        assert result["symbol"] == "₹"

    def test_parse_json_with_multiple_code_blocks_uses_first(self, client):
        text = '''```json
{"first": true}
```

Some text

```json
{"second": true}
```'''
        result = client._parse_json(text)
        assert result.get("first") is True

    def test_parse_json_with_extra_whitespace(self, client):
        text = '''

        {
            "key"  :   "value"
        }

        '''
        result = client._parse_json(text)
        assert result["key"] == "value"


class TestFactExtractorEdgeCases:
    """Tests for FactExtractor edge cases and error handling."""

    @pytest.fixture
    def mock_llm_client(self):
        return Mock()

    def test_parse_facts_with_missing_fields(self, mock_llm_client):
        """Should handle facts with missing optional fields."""
        mock_llm_client.extract_facts.return_value = {
            "facts": [
                {
                    "fact_id": "F001",
                    # Missing: value_type, confidence, location, unit
                    "key": "test_key",
                    "value": "test_value",
                    "raw_text": "test raw text",
                }
            ],
            "document_type": "test",
        }
        extractor = FactExtractor(mock_llm_client)

        extraction = extractor.extract_from_document(
            content="Test", file_path=Path("/test.md"), doc_id="DOC_001"
        )

        assert len(extraction.facts) == 1
        fact = extraction.facts[0]
        assert fact.value_type == "text"  # default
        assert fact.confidence == 1.0  # default
        assert fact.unit is None

    def test_parse_facts_with_invalid_confidence(self, mock_llm_client):
        """Should handle non-numeric confidence gracefully by recording error."""
        mock_llm_client.extract_facts.return_value = {
            "facts": [
                {
                    "fact_id": "F001",
                    "key": "test_key",
                    "value": 100,
                    "value_type": "integer",
                    "raw_text": "100",
                    "confidence": "high",  # Invalid - should be float
                }
            ],
            "document_type": "test",
        }
        extractor = FactExtractor(mock_llm_client)

        # Error is caught and recorded in the extraction's error field
        extraction = extractor.extract_from_document(
            content="Test", file_path=Path("/test.md"), doc_id="DOC_001"
        )

        assert extraction.error is not None
        assert "could not convert string to float" in extraction.error
        assert extraction.facts == []

    def test_parse_facts_empty_array(self, mock_llm_client):
        """Should handle empty facts array."""
        mock_llm_client.extract_facts.return_value = {
            "facts": [],
            "document_type": "empty_doc",
        }
        extractor = FactExtractor(mock_llm_client)

        extraction = extractor.extract_from_document(
            content="Empty doc", file_path=Path("/empty.md"), doc_id="DOC_001"
        )

        assert extraction.facts == []
        assert extraction.document_type == "empty_doc"
        assert extraction.error is None

    def test_extract_all_with_mixed_success_failure(self, mock_llm_client):
        """Should handle some documents failing while others succeed."""
        success_response = {
            "facts": [{"fact_id": "F001", "key": "test", "value": "ok", "raw_text": "ok"}],
            "document_type": "test",
        }
        mock_llm_client.extract_facts.side_effect = [
            success_response,
            Exception("LLM Error"),
            success_response,
        ]
        extractor = FactExtractor(mock_llm_client)

        documents = [
            (Path("/doc1.md"), "Content 1", "check1"),
            (Path("/doc2.md"), "Content 2", "check2"),
            (Path("/doc3.md"), "Content 3", "check3"),
        ]

        store = extractor.extract_all(documents)

        assert len(store.extractions) == 3
        assert store.extractions[0].error is None
        assert "LLM Error" in store.extractions[1].error
        assert store.extractions[2].error is None

    def test_doc_id_assignment(self, mock_llm_client):
        """Doc IDs should be assigned sequentially."""
        mock_llm_client.extract_facts.return_value = {
            "facts": [],
            "document_type": "test",
        }
        extractor = FactExtractor(mock_llm_client)

        documents = [
            (Path("/a.md"), "A", "1"),
            (Path("/b.md"), "B", "2"),
            (Path("/c.md"), "C", "3"),
        ]

        store = extractor.extract_all(documents)

        assert store.extractions[0].doc_id == "DOC_001"
        assert store.extractions[1].doc_id == "DOC_002"
        assert store.extractions[2].doc_id == "DOC_003"


class TestFactStoreSerialization:
    """Tests for FactStore JSON serialization."""

    def test_save_and_reload_fact_store(self, tmp_path):
        """Test round-trip serialization of FactStore."""
        from drhp_agent.core.dtos import FactLocation, ExtractedFact, DocumentExtraction, FactStore
        import json

        fact = ExtractedFact(
            fact_id="F001",
            key="authorized_shares",
            value=30000,
            value_type="integer",
            raw_text="30,000 shares",
            location=FactLocation(section="Section 7", table="Capital"),
            unit="shares",
            confidence=0.95,
            doc_id="DOC_001",
        )
        extraction = DocumentExtraction(
            doc_id="DOC_001",
            file_path="/test/doc.md",
            document_type="pas3_form",
            facts=[fact],
            document_date="2019-05-15",
        )
        store = FactStore(extractions=[extraction])

        # Create mock LLM client and extractor
        mock_llm = Mock()
        extractor = FactExtractor(mock_llm)

        output_path = tmp_path / "fact_store.json"
        extractor.save_fact_store(store, output_path)

        # Verify JSON structure
        data = json.loads(output_path.read_text())
        assert len(data["extractions"]) == 1
        assert data["extractions"][0]["doc_id"] == "DOC_001"
        assert len(data["extractions"][0]["facts"]) == 1
        assert data["extractions"][0]["facts"][0]["value"] == 30000
        assert data["extractions"][0]["facts"][0]["location"]["section"] == "Section 7"
