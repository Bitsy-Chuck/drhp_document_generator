"""Tests for template parser (Tasks 5.1-5.5)."""

import pytest
import tempfile
from pathlib import Path

from drhp_agent.md_template.parser import TemplateParser, ParsedTemplate, ParsedSlot


class TestTemplateParser:
    """Tests for TemplateParser."""

    @pytest.fixture
    def simple_template(self, tmp_path):
        """Create a simple template file."""
        content = """# Capital Structure

The company {{text:company_name:Company name}} has:
- Authorized shares: {{integer:authorized_shares:Number of shares}}
- Face value: {{amount:face_value:Per share value}}
"""
        path = tmp_path / "template.md"
        path.write_text(content)
        return path

    @pytest.fixture
    def complex_template(self, tmp_path):
        """Create a complex template with tables."""
        content = """# CAPITAL STRUCTURE

| Particulars | Shares | Amount |
|-------------|--------|--------|
| Equity | {{integer:equity_shares}} | {{amount:equity_amount}} |
| Preference | {{integer:pref_shares}} | {{amount:pref_amount}} |

The company {{text:company_name:Full legal name}} was incorporated on {{date:incorporation_date}}.
"""
        path = tmp_path / "complex.md"
        path.write_text(content)
        return path

    def test_parse_simple_template(self, simple_template):
        parser = TemplateParser(simple_template)
        result = parser.parse()

        assert isinstance(result, ParsedTemplate)
        assert len(result.slots) == 3

    def test_parse_extracts_slot_ids(self, simple_template):
        parser = TemplateParser(simple_template)
        result = parser.parse()

        slot_ids = {s.slot_id for s in result.slots}
        assert "company_name" in slot_ids
        assert "authorized_shares" in slot_ids
        assert "face_value" in slot_ids

    def test_parse_extracts_slot_types(self, simple_template):
        parser = TemplateParser(simple_template)
        result = parser.parse()

        types_by_id = {s.slot_id: s.slot_type for s in result.slots}
        assert types_by_id["company_name"] == "text"
        assert types_by_id["authorized_shares"] == "integer"
        assert types_by_id["face_value"] == "amount"

    def test_parse_extracts_hints(self, simple_template):
        parser = TemplateParser(simple_template)
        result = parser.parse()

        hints_by_id = {s.slot_id: s.hint for s in result.slots}
        assert hints_by_id["company_name"] == "Company name"
        assert hints_by_id["authorized_shares"] == "Number of shares"

    def test_parse_complex_template(self, complex_template):
        parser = TemplateParser(complex_template)
        result = parser.parse()

        assert len(result.slots) == 6

    def test_parse_slots_without_type_default_to_text(self, tmp_path):
        content = "The value is {{simple_slot}}."
        path = tmp_path / "simple.md"
        path.write_text(content)

        parser = TemplateParser(path)
        result = parser.parse()

        assert len(result.slots) == 1
        assert result.slots[0].slot_type == "text"
        assert result.slots[0].hint is None

    def test_parse_deduplicates_slots(self, tmp_path):
        content = """
The company {{text:company_name}} is incorporated.
We, {{text:company_name}}, hereby declare...
"""
        path = tmp_path / "dup.md"
        path.write_text(content)

        parser = TemplateParser(path)
        result = parser.parse()

        # Should only have one entry for company_name
        assert len(result.slots) == 1
        assert result.slots[0].slot_id == "company_name"

    def test_to_fill_requests(self, simple_template):
        parser = TemplateParser(simple_template)
        result = parser.parse()

        requests = result.to_fill_requests()

        assert len(requests) == 3
        assert all(r.slot_id for r in requests)
        assert all(r.slot_type for r in requests)

    def test_to_dict(self, simple_template):
        parser = TemplateParser(simple_template)
        result = parser.parse()

        data = result.to_dict()

        assert "file_path" in data
        assert data["slot_count"] == 3
        assert len(data["slots"]) == 3

    def test_save_parsed_template(self, simple_template, tmp_path):
        parser = TemplateParser(simple_template)
        result = parser.parse()

        output_path = tmp_path / "out" / "template.json"
        parser.save_parsed_template(result, output_path)

        assert output_path.exists()
        import json
        data = json.loads(output_path.read_text())
        assert data["slot_count"] == 3

    def test_nonexistent_template_raises(self):
        with pytest.raises(FileNotFoundError):
            TemplateParser("/nonexistent/template.md")

    def test_non_markdown_raises(self, tmp_path):
        path = tmp_path / "template.txt"
        path.write_text("content")

        with pytest.raises(ValueError, match="markdown"):
            TemplateParser(path)

    def test_parse_records_line_numbers(self, simple_template):
        parser = TemplateParser(simple_template)
        result = parser.parse()

        # company_name is on line 3
        company_slot = next(s for s in result.slots if s.slot_id == "company_name")
        assert company_slot.line_number == 3

    def test_parse_extracts_context(self, simple_template):
        parser = TemplateParser(simple_template)
        result = parser.parse()

        company_slot = next(s for s in result.slots if s.slot_id == "company_name")
        assert "company" in company_slot.context.lower()


class TestTemplateParserEdgeCases:
    """Edge case tests for TemplateParser."""

    def test_empty_template_file(self, tmp_path):
        """Empty file should parse but have no slots."""
        path = tmp_path / "empty.md"
        path.write_text("")

        parser = TemplateParser(path)
        result = parser.parse()

        assert len(result.slots) == 0
        assert result.content == ""

    def test_template_with_no_slots(self, tmp_path):
        """Template without slots should parse successfully."""
        content = """# Capital Structure

This is a template without any slot markers.
Just plain markdown content.
"""
        path = tmp_path / "no_slots.md"
        path.write_text(content)

        parser = TemplateParser(path)
        result = parser.parse()

        assert len(result.slots) == 0
        assert "Capital Structure" in result.content

    def test_malformed_slot_single_brace(self, tmp_path):
        """Single braces should not be parsed as slots."""
        content = "The value is {not_a_slot} here."
        path = tmp_path / "single_brace.md"
        path.write_text(content)

        parser = TemplateParser(path)
        result = parser.parse()

        assert len(result.slots) == 0

    def test_malformed_slot_unclosed(self, tmp_path):
        """Unclosed slot markers should be ignored."""
        content = "The value is {{unclosed_slot here."
        path = tmp_path / "unclosed.md"
        path.write_text(content)

        parser = TemplateParser(path)
        result = parser.parse()

        assert len(result.slots) == 0

    def test_slot_with_special_characters_in_hint(self, tmp_path):
        """Hints can contain special characters like parentheses."""
        content = "Amount: {{amount:total:Total amount (in INR)}}"
        path = tmp_path / "special.md"
        path.write_text(content)

        parser = TemplateParser(path)
        result = parser.parse()

        assert len(result.slots) == 1
        assert result.slots[0].hint == "Total amount (in INR)"

    def test_slot_with_very_long_hint(self, tmp_path):
        """Long hints should be preserved."""
        long_hint = "This is a very long hint that describes the slot in great detail " * 5
        content = f"Value: {{{{text:slot:{long_hint}}}}}"
        path = tmp_path / "long_hint.md"
        path.write_text(content)

        parser = TemplateParser(path)
        result = parser.parse()

        assert len(result.slots) == 1
        assert len(result.slots[0].hint) > 100

    def test_multiple_slots_on_same_line(self, tmp_path):
        """Multiple slots on same line should all be parsed."""
        content = "From {{date:start_date}} to {{date:end_date}} for {{amount:total}}."
        path = tmp_path / "multi.md"
        path.write_text(content)

        parser = TemplateParser(path)
        result = parser.parse()

        assert len(result.slots) == 3
        slot_ids = {s.slot_id for s in result.slots}
        assert "start_date" in slot_ids
        assert "end_date" in slot_ids
        assert "total" in slot_ids

    def test_slot_with_underscore_in_name(self, tmp_path):
        """Slot names with underscores are valid."""
        content = "{{text:company_full_legal_name:Name}}"
        path = tmp_path / "underscore.md"
        path.write_text(content)

        parser = TemplateParser(path)
        result = parser.parse()

        assert len(result.slots) == 1
        assert result.slots[0].slot_id == "company_full_legal_name"

    def test_slot_with_numbers_in_name(self, tmp_path):
        """Slot names can contain numbers."""
        content = "{{integer:allottee_shares_1:First allottee shares}}"
        path = tmp_path / "numbers.md"
        path.write_text(content)

        parser = TemplateParser(path)
        result = parser.parse()

        assert len(result.slots) == 1
        assert result.slots[0].slot_id == "allottee_shares_1"

    def test_unicode_in_template_content(self, tmp_path):
        """Template can contain Unicode (e.g., rupee symbol)."""
        content = "Amount: ₹{{amount:total:Total in ₹}}"
        path = tmp_path / "unicode.md"
        path.write_text(content, encoding="utf-8")

        parser = TemplateParser(path)
        result = parser.parse()

        assert len(result.slots) == 1
        assert "₹" in result.content

    def test_slot_in_markdown_table(self, tmp_path):
        """Slots inside markdown tables should be parsed."""
        content = """| Column | Value |
|--------|-------|
| Name | {{text:name}} |
| Amount | {{amount:value}} |
"""
        path = tmp_path / "table.md"
        path.write_text(content)

        parser = TemplateParser(path)
        result = parser.parse()

        assert len(result.slots) == 2

    def test_preserves_raw_marker(self, tmp_path):
        """Raw marker should be preserved exactly."""
        content = "{{integer:shares:Number of shares}}"
        path = tmp_path / "raw.md"
        path.write_text(content)

        parser = TemplateParser(path)
        result = parser.parse()

        assert result.slots[0].raw_marker == "{{integer:shares:Number of shares}}"

    def test_slot_context_includes_surrounding_lines(self, tmp_path):
        """Slot context should include text from lines above/below, not just the same line."""
        content = """## Section Heading

The company was incorporated on {{date:inc_date:Incorporation date}} with capital.

More text below.
"""
        path = tmp_path / "cross_line.md"
        path.write_text(content)

        parser = TemplateParser(path)
        result = parser.parse()

        slot = result.slots[0]
        assert "Section Heading" in slot.context
        assert "incorporated on" in slot.context

    def test_elaborate_block_context_includes_heading(self, tmp_path):
        """Elaborate block context should include the section heading above it."""
        content = """## History of Share Capital

The following table sets forth the history:

{{elaborate:allotment_history:Generate a table of allotments}}

## Next Section
"""
        path = tmp_path / "elaborate_ctx.md"
        path.write_text(content)

        parser = TemplateParser(path)
        result = parser.parse()

        block = result.elaboration_blocks[0]
        assert "History of Share Capital" in block.context
        assert "following table" in block.context

    def test_elaborate_block_context_not_just_marker(self, tmp_path):
        """Elaborate block on its own line should still get cross-line context."""
        content = """Some intro text above.

{{elaborate:details:Generate details}}

Some text below.
"""
        path = tmp_path / "elaborate_alone.md"
        path.write_text(content)

        parser = TemplateParser(path)
        result = parser.parse()

        block = result.elaboration_blocks[0]
        # Context should contain text from other lines, not just the marker
        assert "intro text above" in block.context
        assert "text below" in block.context
