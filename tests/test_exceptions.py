"""Unit tests for core exceptions.

Task 2.15: Unit tests for exception hierarchy.
"""

import pytest

from drhp_agent.core.exceptions import (
    ConfigurationError,
    DRHPError,
    FillingError,
    NotSupportedEnumValueError,
    NotSupportedSourceTypeError,
    NotSupportedStructureError,
    ParsingError,
    RenderingError,
    RetrievalError,
    SchemaValidationError,
    ValidationError,
)


class TestDRHPError:
    """Tests for base DRHPError."""

    def test_message_only(self):
        err = DRHPError("Something went wrong")
        assert str(err) == "Something went wrong"
        assert err.message == "Something went wrong"
        assert err.details == {}

    def test_with_details(self):
        err = DRHPError("Error occurred", details={"key": "value"})
        assert "key" in str(err)
        assert err.details == {"key": "value"}


class TestNotSupportedSourceTypeError:
    """Tests for NotSupportedSourceTypeError (Task 2.5, 5.7)."""

    def test_creates_correct_message(self):
        err = NotSupportedSourceTypeError(
            file_path="/path/to/file.pdf",
            detected_type="pdf",
        )
        assert "pdf" in str(err)
        assert "/path/to/file.pdf" in str(err)
        assert "Only markdown" in str(err)

    def test_stores_attributes(self):
        err = NotSupportedSourceTypeError(
            file_path="/path/to/file.xlsx",
            detected_type="xlsx",
        )
        assert err.file_path == "/path/to/file.xlsx"
        assert err.detected_type == "xlsx"

    def test_is_drhp_error(self):
        err = NotSupportedSourceTypeError("test.pdf", "pdf")
        assert isinstance(err, DRHPError)


class TestNotSupportedEnumValueError:
    """Tests for NotSupportedEnumValueError (Task 2.13)."""

    def test_creates_correct_message(self):
        err = NotSupportedEnumValueError(
            enum_name="EnumSlotKind",
            value="invalid",
            valid_values=["amount", "percent"],
        )
        assert "invalid" in str(err)
        assert "EnumSlotKind" in str(err)
        assert "amount" in str(err)

    def test_stores_attributes(self):
        err = NotSupportedEnumValueError(
            enum_name="EnumSourceType",
            value="pdf",
            valid_values=["md"],
        )
        assert err.enum_name == "EnumSourceType"
        assert err.value == "pdf"
        assert err.valid_values == ["md"]


class TestNotSupportedStructureError:
    """Tests for NotSupportedStructureError (Task 3.7)."""

    def test_without_suggestion(self):
        err = NotSupportedStructureError(
            structure_type="nested_table",
            context="Table in cell A1",
        )
        assert "nested_table" in str(err)
        assert "Table in cell A1" in str(err)

    def test_with_suggestion(self):
        err = NotSupportedStructureError(
            structure_type="html_block",
            context="Line 45",
            suggestion="Convert to markdown",
        )
        assert "Convert to markdown" in str(err)
        assert err.suggestion == "Convert to markdown"


class TestValidationError:
    """Tests for ValidationError."""

    def test_basic_validation_error(self):
        err = ValidationError("Field is required", field="name")
        assert "Field is required" in str(err)
        assert err.field == "name"

    def test_with_constraint(self):
        err = ValidationError(
            "Value out of range",
            field="percentage",
            value=150,
            constraint="0-100",
        )
        assert err.value == 150
        assert err.constraint == "0-100"


class TestSchemaValidationError:
    """Tests for SchemaValidationError (Task 2.14)."""

    def test_stores_schema_errors(self):
        errors = [
            {"path": ["field1"], "message": "Required"},
            {"path": ["field2"], "message": "Invalid type"},
        ]
        err = SchemaValidationError(
            message="Schema validation failed",
            schema_name="section_template.json",
            errors=errors,
        )
        assert err.schema_name == "section_template.json"
        assert len(err.errors) == 2
        assert isinstance(err, ValidationError)


class TestParsingError:
    """Tests for ParsingError."""

    def test_with_location(self):
        err = ParsingError(
            "Invalid markdown syntax",
            file_path="/path/to/file.md",
            line_number=42,
        )
        assert err.file_path == "/path/to/file.md"
        assert err.line_number == 42


class TestRetrievalError:
    """Tests for RetrievalError."""

    def test_with_query(self):
        err = RetrievalError(
            "No results found",
            query="net proceeds",
            slot_id="S_net_proceeds",
        )
        assert err.query == "net proceeds"
        assert err.slot_id == "S_net_proceeds"


class TestFillingError:
    """Tests for FillingError."""

    def test_with_reason(self):
        err = FillingError(
            "Could not extract value",
            slot_id="S_amount",
            reason="Ambiguous source",
        )
        assert err.slot_id == "S_amount"
        assert err.reason == "Ambiguous source"


class TestRenderingError:
    """Tests for RenderingError."""

    def test_with_context(self):
        err = RenderingError(
            "Failed to render",
            template_node="node_123",
            slot_id="S_value",
        )
        assert err.template_node == "node_123"
        assert err.slot_id == "S_value"


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_with_config_key(self):
        err = ConfigurationError(
            "Invalid configuration",
            config_key="retriever_mode",
        )
        assert err.config_key == "retriever_mode"


class TestExceptionHierarchy:
    """Test exception inheritance."""

    def test_all_exceptions_inherit_from_drhp_error(self):
        exceptions = [
            NotSupportedSourceTypeError("test.pdf", "pdf"),
            NotSupportedEnumValueError("Test", "val", ["a"]),
            NotSupportedStructureError("type", "ctx"),
            ValidationError("msg"),
            SchemaValidationError("msg", "schema", []),
            ParsingError("msg"),
            RetrievalError("msg"),
            FillingError("msg"),
            RenderingError("msg"),
            ConfigurationError("msg"),
        ]
        for exc in exceptions:
            assert isinstance(exc, DRHPError), f"{type(exc)} is not DRHPError"
