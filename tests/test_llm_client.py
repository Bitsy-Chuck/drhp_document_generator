"""Tests for LLM client (Tasks 3.1-3.5)."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock

from drhp_agent.llm.client import LLMClient, LLMConfig


class TestLLMConfig:
    """Tests for LLMConfig."""

    def test_default_values(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            config = LLMConfig()
            assert config.api_key == "test-key"
            assert config.model == "claude-sonnet-4-20250514"
            assert config.max_tokens == 4096
            assert config.temperature == 0.0
            assert config.max_retries == 3

    def test_explicit_api_key(self):
        config = LLMConfig(api_key="explicit-key")
        assert config.api_key == "explicit-key"

    def test_missing_api_key_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            # Remove ANTHROPIC_API_KEY if it exists
            import os
            env_backup = os.environ.get("ANTHROPIC_API_KEY")
            if "ANTHROPIC_API_KEY" in os.environ:
                del os.environ["ANTHROPIC_API_KEY"]
            try:
                with pytest.raises(ValueError, match="API key required"):
                    LLMConfig()
            finally:
                if env_backup:
                    os.environ["ANTHROPIC_API_KEY"] = env_backup

    def test_custom_values(self):
        config = LLMConfig(
            api_key="test",
            model="claude-3-opus",
            max_tokens=8192,
            temperature=0.5,
            max_retries=5,
        )
        assert config.model == "claude-3-opus"
        assert config.max_tokens == 8192
        assert config.temperature == 0.5
        assert config.max_retries == 5


class TestLLMClientJSONParsing:
    """Tests for JSON parsing in LLMClient."""

    @pytest.fixture
    def client(self):
        with patch("drhp_agent.llm.client.anthropic.Anthropic"):
            config = LLMConfig(api_key="test-key")
            return LLMClient(config)

    def test_parse_raw_json(self, client):
        text = '{"key": "value", "number": 42}'
        result = client._parse_json(text)
        assert result == {"key": "value", "number": 42}

    def test_parse_json_with_code_block(self, client):
        text = '```json\n{"key": "value"}\n```'
        result = client._parse_json(text)
        assert result == {"key": "value"}

    def test_parse_json_with_plain_code_block(self, client):
        text = '```\n{"key": "value"}\n```'
        result = client._parse_json(text)
        assert result == {"key": "value"}

    def test_parse_json_with_surrounding_text(self, client):
        text = 'Here is the result:\n{"key": "value"}\nDone.'
        result = client._parse_json(text)
        assert result == {"key": "value"}

    def test_parse_invalid_json_raises(self, client):
        text = "This is not JSON at all"
        with pytest.raises(ValueError, match="Failed to parse JSON"):
            client._parse_json(text)

    def test_parse_nested_json(self, client):
        text = '''```json
{
  "facts": [
    {"id": "F001", "value": 100},
    {"id": "F002", "value": 200}
  ],
  "document_type": "pas3_form"
}
```'''
        result = client._parse_json(text)
        assert len(result["facts"]) == 2
        assert result["document_type"] == "pas3_form"


class TestLLMClientComplete:
    """Tests for LLMClient.complete method."""

    @pytest.fixture
    def mock_anthropic(self):
        with patch("drhp_agent.llm.client.anthropic.Anthropic") as mock:
            yield mock

    def test_complete_success(self, mock_anthropic):
        # Setup mock
        mock_response = Mock()
        mock_response.content = [Mock(text="Hello, world!")]
        mock_anthropic.return_value.messages.create.return_value = mock_response

        config = LLMConfig(api_key="test-key")
        client = LLMClient(config)

        result = client.complete("System prompt", "User prompt")
        assert result == "Hello, world!"

    def test_complete_json_success(self, mock_anthropic):
        # Setup mock
        mock_response = Mock()
        mock_response.content = [Mock(text='{"status": "ok"}')]
        mock_anthropic.return_value.messages.create.return_value = mock_response

        config = LLMConfig(api_key="test-key")
        client = LLMClient(config)

        result = client.complete_json("System prompt", "User prompt")
        assert result == {"status": "ok"}


class TestLLMClientHelperMethods:
    """Tests for LLMClient helper methods."""

    @pytest.fixture
    def client(self):
        with patch("drhp_agent.llm.client.anthropic.Anthropic") as mock:
            mock_response = Mock()
            mock_response.content = [Mock(text='{"facts": [], "document_type": "test"}')]
            mock.return_value.messages.create.return_value = mock_response

            config = LLMConfig(api_key="test-key")
            return LLMClient(config)

    def test_extract_facts_calls_complete_json(self, client):
        result = client.extract_facts("Document content", "test.md")
        assert "facts" in result
        assert result["document_type"] == "test"

    def test_fill_slot_calls_complete_json(self, client):
        # Update mock for this test
        client.client.messages.create.return_value.content[0].text = json.dumps({
            "slot_id": "test_slot",
            "status": "filled",
            "value": 100,
        })

        result = client.fill_slot(
            slot_id="test_slot",
            slot_type="integer",
            slot_hint="Test hint",
            slot_context="Test context",
            facts_json="[]",
        )
        assert result["slot_id"] == "test_slot"

    def test_validate_facts_calls_complete_json(self, client):
        client.client.messages.create.return_value.content[0].text = json.dumps({
            "is_valid": True,
            "issues": [],
        })

        result = client.validate_facts("[]")
        assert result["is_valid"] is True

    def test_generate_section_calls_complete(self, client):
        client.client.messages.create.return_value.content[0].text = "# Section\n\nContent"

        result = client.generate_section(
            company_name="Test Corp",
            filled_slots_json="{}",
            source_files=["doc1.md", "doc2.md"],
        )
        assert "# Section" in result
