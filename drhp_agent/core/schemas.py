"""JSON Schema definitions and validators for artifacts.

Task 2.14: Add schema validators for all artifacts.
"""

from typing import Any

from drhp_agent.core.exceptions import SchemaValidationError

# JSON Schema for section_template.json
SECTION_TEMPLATE_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["section_key", "section_title", "root_node"],
    "properties": {
        "section_key": {"type": "string"},
        "section_title": {"type": "string"},
        "source_file": {"type": ["string", "null"]},
        "source_line_start": {"type": ["integer", "null"]},
        "source_line_end": {"type": ["integer", "null"]},
        "root_node": {"$ref": "#/$defs/template_node"},
        "slot_specs": {
            "type": "object",
            "additionalProperties": {"$ref": "#/$defs/slot_spec"},
        },
    },
    "$defs": {
        "template_node": {
            "type": "object",
            "required": ["node_id", "node_type"],
            "properties": {
                "node_id": {"type": "string"},
                "node_type": {
                    "type": "string",
                    "enum": [
                        "heading",
                        "paragraph",
                        "table",
                        "list",
                        "list_item",
                        "text",
                        "code_block",
                        "blockquote",
                        "thematic_break",
                        "unknown",
                    ],
                },
                "text": {"type": ["string", "null"]},
                "level": {"type": ["integer", "null"]},
                "children": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/template_node"},
                },
                "slots": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/slot_spec"},
                },
                "table_id": {"type": ["string", "null"]},
                "headers": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                },
                "rows": {"type": ["array", "null"]},
                "ordered": {"type": ["boolean", "null"]},
                "source_line_start": {"type": ["integer", "null"]},
                "source_line_end": {"type": ["integer", "null"]},
                "raw_text": {"type": ["string", "null"]},
                "is_boilerplate": {"type": "boolean"},
            },
        },
        "slot_spec": {
            "type": "object",
            "required": ["slot_id", "kind"],
            "properties": {
                "slot_id": {"type": "string"},
                "kind": {
                    "type": "string",
                    "enum": [
                        "amount",
                        "percent",
                        "date",
                        "text",
                        "entity",
                        "ratio",
                        "boolean",
                        "integer",
                        "custom",
                    ],
                },
                "hint": {"type": ["string", "null"]},
                "context_window": {"type": ["string", "null"]},
                "expected_source_types": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "required": {"type": "boolean"},
                "default_value": {},
            },
        },
    },
}

# JSON Schema for filled_slots.json
FILLED_SLOTS_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["section_key", "fills"],
    "properties": {
        "section_key": {"type": "string"},
        "fill_rate": {"type": "number", "minimum": 0, "maximum": 1},
        "missing_count": {"type": "integer", "minimum": 0},
        "conflict_count": {"type": "integer", "minimum": 0},
        "fills": {
            "type": "object",
            "additionalProperties": {"$ref": "#/$defs/slot_fill"},
        },
        "validation_issues": {
            "type": "array",
            "items": {"$ref": "#/$defs/validation_issue"},
        },
    },
    "$defs": {
        "slot_fill": {
            "type": "object",
            "required": ["slot_id", "status"],
            "properties": {
                "slot_id": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["filled", "missing", "conflict", "low_confidence", "invalid"],
                },
                "value": {},
                "formatted_value": {"type": ["string", "null"]},
                "unit": {"type": ["string", "null"]},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "evidence_refs": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/evidence_ref"},
                },
                "reason": {"type": ["string", "null"]},
                "candidates": {"type": "array"},
                "conflicts": {"type": "array"},
            },
        },
        "evidence_ref": {
            "type": "object",
            "required": ["evidence_id", "evidence_type", "doc_id", "doc_path"],
            "properties": {
                "evidence_id": {"type": "string"},
                "evidence_type": {
                    "type": "string",
                    "enum": ["text_span", "table_cell", "multi_span"],
                },
                "doc_id": {"type": "string"},
                "doc_path": {"type": "string"},
                "char_start": {"type": ["integer", "null"]},
                "char_end": {"type": ["integer", "null"]},
                "line_start": {"type": ["integer", "null"]},
                "line_end": {"type": ["integer", "null"]},
                "table_id": {"type": ["string", "null"]},
                "row": {"type": ["integer", "null"]},
                "col": {"type": ["integer", "null"]},
                "heading_path": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "excerpt": {"type": ["string", "null"]},
            },
        },
        "validation_issue": {
            "type": "object",
            "required": ["issue_id", "severity", "message"],
            "properties": {
                "issue_id": {"type": "string"},
                "severity": {
                    "type": "string",
                    "enum": ["info", "warn", "error", "critical"],
                },
                "message": {"type": "string"},
                "slot_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "node_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "expected": {},
                "actual": {},
                "suggestion": {"type": ["string", "null"]},
            },
        },
    },
}

# JSON Schema for annotations.jsonl (single record)
ANNOTATION_RECORD_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["annotation_id", "output_span_start", "output_span_end", "slot_id", "evidence_refs", "output_file"],
    "properties": {
        "annotation_id": {"type": "string"},
        "output_span_start": {"type": "integer", "minimum": 0},
        "output_span_end": {"type": "integer", "minimum": 0},
        "slot_id": {"type": "string"},
        "output_file": {"type": "string"},
        "output_line": {"type": ["integer", "null"]},
        "evidence_refs": {
            "type": "array",
            "items": {"$ref": "#/$defs/evidence_ref"},
        },
    },
    "$defs": {
        "evidence_ref": FILLED_SLOTS_SCHEMA["$defs"]["evidence_ref"],
    },
}

# JSON Schema for run_manifest.json
RUN_MANIFEST_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["run_id", "started_at", "config_hash", "status"],
    "properties": {
        "run_id": {"type": "string"},
        "started_at": {"type": "string", "format": "date-time"},
        "completed_at": {"type": ["string", "null"], "format": "date-time"},
        "config_hash": {"type": "string"},
        "status": {
            "type": "string",
            "enum": ["pending", "running", "completed", "failed"],
        },
        "error": {"type": ["string", "null"]},
        "input_files": {
            "type": "array",
            "items": {"type": "string"},
        },
        "input_checksums": {
            "type": "object",
            "additionalProperties": {"type": "string"},
        },
        "stages": {
            "type": "array",
            "items": {"$ref": "#/$defs/stage_status"},
        },
        "output_files": {
            "type": "array",
            "items": {"type": "string"},
        },
        "config": {"type": ["object", "null"]},
    },
    "$defs": {
        "stage_status": {
            "type": "object",
            "required": ["stage_name", "status"],
            "properties": {
                "stage_name": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["pending", "running", "completed", "failed", "skipped"],
                },
                "started_at": {"type": ["string", "null"], "format": "date-time"},
                "completed_at": {"type": ["string", "null"], "format": "date-time"},
                "error": {"type": ["string", "null"]},
                "artifacts": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        },
    },
}


def validate_schema(data: dict[str, Any], schema: dict[str, Any], schema_name: str) -> None:
    """Validate data against a JSON schema.

    Args:
        data: The data to validate.
        schema: The JSON schema to validate against.
        schema_name: Name of the schema for error reporting.

    Raises:
        SchemaValidationError: If validation fails.
    """
    try:
        import jsonschema
    except ImportError:
        # If jsonschema not installed, skip validation with warning
        import warnings

        warnings.warn("jsonschema not installed, skipping schema validation")
        return

    validator = jsonschema.Draft202012Validator(schema)
    errors = list(validator.iter_errors(data))

    if errors:
        error_details = [
            {
                "path": list(e.absolute_path),
                "message": e.message,
                "validator": e.validator,
            }
            for e in errors
        ]
        raise SchemaValidationError(
            message=f"Schema validation failed for {schema_name}",
            schema_name=schema_name,
            errors=error_details,
        )


def validate_section_template(data: dict[str, Any]) -> None:
    """Validate section_template.json data."""
    validate_schema(data, SECTION_TEMPLATE_SCHEMA, "section_template.json")


def validate_filled_slots(data: dict[str, Any]) -> None:
    """Validate filled_slots.json data."""
    validate_schema(data, FILLED_SLOTS_SCHEMA, "filled_slots.json")


def validate_annotation_record(data: dict[str, Any]) -> None:
    """Validate a single annotation record."""
    validate_schema(data, ANNOTATION_RECORD_SCHEMA, "annotation_record")


def validate_run_manifest(data: dict[str, Any]) -> None:
    """Validate run_manifest.json data."""
    validate_schema(data, RUN_MANIFEST_SCHEMA, "run_manifest.json")
