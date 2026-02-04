"""Core enums for the DRHP Section Drafting System.

All enums use strict parsing - unsupported values raise NotSupportedEnumValueError.
"""

from enum import Enum, auto
from typing import TypeVar

from drhp_agent.core.exceptions import NotSupportedEnumValueError

T = TypeVar("T", bound=Enum)


def strict_enum_parse(enum_cls: type[T], value: str) -> T:
    """Parse enum value strictly, raising NotSupportedEnumValueError for invalid values.

    Args:
        enum_cls: The enum class to parse into.
        value: The string value to parse.

    Returns:
        The parsed enum member.

    Raises:
        NotSupportedEnumValueError: If the value is not a valid enum member.
    """
    try:
        return enum_cls(value)
    except ValueError:
        valid_values = [e.value for e in enum_cls]
        raise NotSupportedEnumValueError(
            enum_name=enum_cls.__name__,
            value=value,
            valid_values=valid_values,
        )


class EnumSectionKey(str, Enum):
    """Section keys for DRHP sections.

    Task 2.1: Define section keys for the supported DRHP sections.
    CUSTOM allows for user-defined section keys via alias mapping.
    """

    OBJECTS = "objects"
    RISK_FACTORS = "risk_factors"
    BUSINESS_OVERVIEW = "business_overview"
    INDUSTRY_OVERVIEW = "industry_overview"
    FINANCIAL_INFORMATION = "financial_information"
    LEGAL_PROCEEDINGS = "legal_proceedings"
    MANAGEMENT = "management"
    PROMOTERS = "promoters"
    ISSUE_DETAILS = "issue_details"
    CAPITAL_STRUCTURE = "capital_structure"
    CUSTOM = "custom"


class EnumNodeType(str, Enum):
    """Node types for the markdown AST.

    Task 2.2: Define node types for normalized AST representation.
    """

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    LIST = "list"
    LIST_ITEM = "list_item"
    TEXT = "text"
    CODE_BLOCK = "code_block"
    BLOCKQUOTE = "blockquote"
    THEMATIC_BREAK = "thematic_break"
    UNKNOWN = "unknown"


class EnumSlotKind(str, Enum):
    """Slot kinds for template slots.

    Task 2.3: Define slot kinds for fillable template slots.
    """

    AMOUNT = "amount"
    PERCENT = "percent"
    DATE = "date"
    TEXT = "text"
    ENTITY = "entity"
    RATIO = "ratio"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    CUSTOM = "custom"


class EnumEvidenceType(str, Enum):
    """Evidence types for evidence references.

    Task 2.4: Define evidence types for grounding facts.
    """

    TEXT_SPAN = "text_span"
    TABLE_CELL = "table_cell"
    MULTI_SPAN = "multi_span"


class EnumSourceType(str, Enum):
    """Source types for input documents.

    Task 2.5: Define source types. Only MD is supported for MVP.
    Non-MD inputs must raise NotSupportedSourceTypeError.
    """

    MD = "md"


class EnumFillStatus(str, Enum):
    """Fill status for slot filling results.

    Task 2.6: Define fill status values for slot filling outcomes.
    """

    FILLED = "filled"
    MISSING = "missing"
    CONFLICT = "conflict"
    LOW_CONFIDENCE = "low_confidence"
    INVALID = "invalid"


class EnumValidationSeverity(str, Enum):
    """Validation severity levels.

    Task 2.7: Define severity levels for validation issues.
    """

    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    CRITICAL = "critical"


class EnumReviewFlagType(str, Enum):
    """Review flag types for human review.

    Task 2.8: Define flag types for items requiring human review.
    """

    MISSING_FACT = "missing_fact"
    CONFLICTING_FACTS = "conflicting_facts"
    FAILED_RECONCILIATION = "failed_reconciliation"
    UNSUPPORTED_STRUCTURE = "unsupported_structure"
    LOW_CONFIDENCE = "low_confidence"
    TYPE_MISMATCH = "type_mismatch"


class EnumRetrieverMode(str, Enum):
    """Retriever modes for evidence retrieval.

    Task 2.9: Define retriever modes for evidence search.
    """

    BM25 = "bm25"
    EMBEDDING = "embedding"
    HYBRID = "hybrid"
    TABLE_FIRST = "table_first"


class EnumConflictPolicy(str, Enum):
    """Conflict resolution policies.

    Task 2.10: Define policies for resolving conflicting evidence.
    """

    HIGHEST_CONFIDENCE = "highest_confidence"
    MOST_RECENT_DOC = "most_recent_doc"
    PRIORITY_SOURCE = "priority_source"
    REVIEW_REQUIRED = "review_required"


class EnumDateStyle(str, Enum):
    """Date formatting styles.

    Task 2.11: Define date formatting styles for output rendering.
    """

    ISO = "iso"  # 2024-01-15
    DMY_SLASH = "dmy_slash"  # 15/01/2024
    MDY_SLASH = "mdy_slash"  # 01/15/2024
    DMY_DOT = "dmy_dot"  # 15.01.2024
    LONG_EN = "long_en"  # January 15, 2024
    LONG_IN = "long_in"  # 15 January 2024


class EnumNumberStyle(str, Enum):
    """Number formatting styles.

    Task 2.11: Define number formatting styles for output rendering.
    """

    PLAIN = "plain"  # 1234567.89
    COMMA_EN = "comma_en"  # 1,234,567.89
    LAKH_CRORE = "lakh_crore"  # 12,34,567.89 (Indian numbering)
    ABBREVIATED = "abbreviated"  # 12.35 Lakhs, 1.23 Cr


class EnumPipelineMode(str, Enum):
    """Pipeline execution modes.

    Task 1.11: Define execution modes for the pipeline orchestrator.
    """

    STRICT = "strict"  # Fail on critical errors
    DRY_RUN = "dry_run"  # Parse and validate only, no output
    DEBUG = "debug"  # Full logging and intermediate artifacts
