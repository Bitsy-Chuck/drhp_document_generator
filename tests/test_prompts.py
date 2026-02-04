"""Tests for LLM prompts (Task 3.6-3.14).

Validates prompt templates have correct placeholders and format.
"""

import pytest

from drhp_agent.prompts import (
    FACT_SCHEMA,
    EXTRACTION_SYSTEM_PROMPT,
    EXTRACTION_USER_PROMPT,
    SLOT_FILL_SYSTEM_PROMPT,
    SLOT_FILL_USER_PROMPT,
    SECTION_GENERATE_SYSTEM_PROMPT,
    SECTION_GENERATE_USER_PROMPT,
    VALIDATION_SYSTEM_PROMPT,
    VALIDATION_USER_PROMPT,
)


class TestFactSchema:
    """Tests for FACT_SCHEMA definition."""

    def test_schema_is_valid_json_like_structure(self):
        # Should contain key fields
        assert '"facts"' in FACT_SCHEMA
        assert '"fact_id"' in FACT_SCHEMA
        assert '"category"' in FACT_SCHEMA
        assert '"value"' in FACT_SCHEMA
        assert '"confidence"' in FACT_SCHEMA

    def test_schema_has_location_fields(self):
        assert '"location"' in FACT_SCHEMA
        assert '"section"' in FACT_SCHEMA
        assert '"table"' in FACT_SCHEMA
        assert '"row"' in FACT_SCHEMA

    def test_schema_has_document_metadata(self):
        assert '"document_type"' in FACT_SCHEMA
        assert '"document_date"' in FACT_SCHEMA


class TestExtractionPrompts:
    """Tests for extraction prompt templates."""

    def test_system_prompt_has_schema_placeholder(self):
        assert "{schema}" in EXTRACTION_SYSTEM_PROMPT

    def test_system_prompt_can_be_formatted(self):
        result = EXTRACTION_SYSTEM_PROMPT.format(schema=FACT_SCHEMA)
        assert FACT_SCHEMA in result
        assert "{schema}" not in result

    def test_user_prompt_has_placeholders(self):
        assert "{filename}" in EXTRACTION_USER_PROMPT
        assert "{content}" in EXTRACTION_USER_PROMPT

    def test_user_prompt_can_be_formatted(self):
        result = EXTRACTION_USER_PROMPT.format(
            filename="test.md",
            content="# Test Content"
        )
        assert "test.md" in result
        assert "# Test Content" in result
        assert "{filename}" not in result
        assert "{content}" not in result

    def test_system_prompt_mentions_extraction_purpose(self):
        assert "extract" in EXTRACTION_SYSTEM_PROMPT.lower()
        assert "fact" in EXTRACTION_SYSTEM_PROMPT.lower()


class TestSlotFillPrompts:
    """Tests for slot fill prompt templates."""

    def test_system_prompt_mentions_drhp(self):
        assert "DRHP" in SLOT_FILL_SYSTEM_PROMPT

    def test_system_prompt_mentions_statuses(self):
        assert "filled" in SLOT_FILL_SYSTEM_PROMPT
        assert "missing" in SLOT_FILL_SYSTEM_PROMPT
        assert "conflict" in SLOT_FILL_SYSTEM_PROMPT

    def test_user_prompt_has_all_placeholders(self):
        assert "{slot_id}" in SLOT_FILL_USER_PROMPT
        assert "{slot_type}" in SLOT_FILL_USER_PROMPT
        assert "{slot_hint}" in SLOT_FILL_USER_PROMPT
        assert "{slot_context}" in SLOT_FILL_USER_PROMPT
        assert "{facts_json}" in SLOT_FILL_USER_PROMPT

    def test_user_prompt_can_be_formatted(self):
        result = SLOT_FILL_USER_PROMPT.format(
            slot_id="company_name",
            slot_type="text",
            slot_hint="Full company name",
            slot_context="The Company, {{company_name}}, hereby...",
            facts_json='[{"key": "company_name", "value": "Test Corp"}]',
        )
        assert "company_name" in result
        assert "Test Corp" in result


class TestSectionGeneratePrompts:
    """Tests for section generation prompt templates."""

    def test_system_prompt_requires_legal_tone(self):
        # Should mention legal/formal style
        prompt_lower = SECTION_GENERATE_SYSTEM_PROMPT.lower()
        assert "legal" in prompt_lower or "formal" in prompt_lower

    def test_system_prompt_mentions_citations(self):
        assert "Source" in SECTION_GENERATE_SYSTEM_PROMPT
        assert "citation" in SECTION_GENERATE_SYSTEM_PROMPT.lower()

    def test_system_prompt_mentions_missing_data_marker(self):
        assert "REQUIRES REVIEW" in SECTION_GENERATE_SYSTEM_PROMPT

    def test_user_prompt_has_placeholders(self):
        assert "{company_name}" in SECTION_GENERATE_USER_PROMPT
        assert "{filled_slots_json}" in SECTION_GENERATE_USER_PROMPT
        assert "{source_files}" in SECTION_GENERATE_USER_PROMPT


class TestValidationPrompts:
    """Tests for validation prompt templates."""

    def test_system_prompt_mentions_checks(self):
        prompt_lower = VALIDATION_SYSTEM_PROMPT.lower()
        assert "consistency" in prompt_lower
        assert "validation" in prompt_lower or "check" in prompt_lower

    def test_system_prompt_mentions_severity_levels(self):
        assert "severity" in VALIDATION_SYSTEM_PROMPT.lower()

    def test_user_prompt_has_facts_placeholder(self):
        assert "{facts_json}" in VALIDATION_USER_PROMPT

    def test_user_prompt_can_be_formatted(self):
        result = VALIDATION_USER_PROMPT.format(
            facts_json='[{"fact_id": "F001", "value": 100}]'
        )
        assert "F001" in result
        assert "{facts_json}" not in result
