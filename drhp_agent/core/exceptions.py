"""Exception hierarchy for the DRHP Section Drafting System.

Task 2.15: Define exception hierarchy with explicit not-supported exceptions.
"""

from typing import Any


class DRHPError(Exception):
    """Base exception for all DRHP system errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class NotSupportedSourceTypeError(DRHPError):
    """Raised when an unsupported source type is encountered.

    Task 2.5, 5.7: Only .md files are supported in MVP.
    Non-markdown files must raise this exception immediately.
    """

    def __init__(self, file_path: str, detected_type: str):
        message = (
            f"Unsupported source type: '{detected_type}' for file '{file_path}'. "
            f"Only markdown (.md) files are supported."
        )
        super().__init__(
            message,
            details={"file_path": file_path, "detected_type": detected_type},
        )
        self.file_path = file_path
        self.detected_type = detected_type


class NotSupportedEnumValueError(DRHPError):
    """Raised when an unsupported enum value is encountered.

    Task 2.13: Strict enum parsing with explicit error (no silent fallback).
    """

    def __init__(self, enum_name: str, value: str, valid_values: list[str]):
        message = (
            f"Unsupported value '{value}' for enum '{enum_name}'. "
            f"Valid values: {valid_values}"
        )
        super().__init__(
            message,
            details={
                "enum_name": enum_name,
                "value": value,
                "valid_values": valid_values,
            },
        )
        self.enum_name = enum_name
        self.value = value
        self.valid_values = valid_values


class NotSupportedStructureError(DRHPError):
    """Raised when an unsupported markdown structure is encountered.

    Task 3.7: Detect unsupported/odd structures and emit review flags.
    """

    def __init__(self, structure_type: str, context: str, suggestion: str | None = None):
        message = f"Unsupported structure: '{structure_type}' in context: {context}"
        if suggestion:
            message += f". Suggestion: {suggestion}"
        super().__init__(
            message,
            details={
                "structure_type": structure_type,
                "context": context,
                "suggestion": suggestion,
            },
        )
        self.structure_type = structure_type
        self.context = context
        self.suggestion = suggestion


class ValidationError(DRHPError):
    """Raised when validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        constraint: str | None = None,
    ):
        super().__init__(
            message,
            details={"field": field, "value": value, "constraint": constraint},
        )
        self.field = field
        self.value = value
        self.constraint = constraint


class ParsingError(DRHPError):
    """Raised when markdown parsing fails."""

    def __init__(
        self,
        message: str,
        file_path: str | None = None,
        line_number: int | None = None,
    ):
        super().__init__(
            message,
            details={"file_path": file_path, "line_number": line_number},
        )
        self.file_path = file_path
        self.line_number = line_number


class RetrievalError(DRHPError):
    """Raised when evidence retrieval fails."""

    def __init__(self, message: str, query: str | None = None, slot_id: str | None = None):
        super().__init__(
            message,
            details={"query": query, "slot_id": slot_id},
        )
        self.query = query
        self.slot_id = slot_id


class FillingError(DRHPError):
    """Raised when slot filling fails."""

    def __init__(
        self,
        message: str,
        slot_id: str | None = None,
        reason: str | None = None,
    ):
        super().__init__(
            message,
            details={"slot_id": slot_id, "reason": reason},
        )
        self.slot_id = slot_id
        self.reason = reason


class RenderingError(DRHPError):
    """Raised when rendering fails."""

    def __init__(
        self,
        message: str,
        template_node: str | None = None,
        slot_id: str | None = None,
    ):
        super().__init__(
            message,
            details={"template_node": template_node, "slot_id": slot_id},
        )
        self.template_node = template_node
        self.slot_id = slot_id


class ConfigurationError(DRHPError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str, config_key: str | None = None):
        super().__init__(message, details={"config_key": config_key})
        self.config_key = config_key


class SchemaValidationError(ValidationError):
    """Raised when JSON schema validation fails.

    Task 2.14: Schema validators for artifacts.
    """

    def __init__(
        self,
        message: str,
        schema_name: str,
        errors: list[dict[str, Any]],
    ):
        super().__init__(message, field=schema_name)
        self.schema_name = schema_name
        self.errors = errors
        self.details["errors"] = errors
