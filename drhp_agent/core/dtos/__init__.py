"""DTOs for the DRHP Section Drafting System.

Re-exports all DTOs for backward compatibility.
"""

from drhp_agent.core.dtos.template import (
    SlotSpec,
    TableCell,
    TemplateNode,
    SectionTemplate,
)
from drhp_agent.core.dtos.evidence import (
    EvidenceRef,
    AnnotationRecord,
)
from drhp_agent.core.dtos.validation import (
    ValidationIssue,
    ReviewFlag,
)
from drhp_agent.core.dtos.filling import (
    SlotFill,
    SlotFillRequest,
    SlotFillResult,
    FilledSlotsResult,
)
from drhp_agent.core.dtos.ingestion import (
    DocumentMetadata,
    ChunkInfo,
    TableInfo,
)
from drhp_agent.core.dtos.extraction import (
    FactLocation,
    ExtractedFact,
    DocumentExtraction,
    FactStore,
)
from drhp_agent.core.dtos.pipeline import (
    PipelineConfig,
    StageStatus,
    RunManifest,
)

__all__ = [
    # Template
    "SlotSpec",
    "TableCell",
    "TemplateNode",
    "SectionTemplate",
    # Evidence
    "EvidenceRef",
    "AnnotationRecord",
    # Validation
    "ValidationIssue",
    "ReviewFlag",
    # Filling
    "SlotFill",
    "SlotFillRequest",
    "SlotFillResult",
    "FilledSlotsResult",
    # Ingestion
    "DocumentMetadata",
    "ChunkInfo",
    "TableInfo",
    # Extraction
    "FactLocation",
    "ExtractedFact",
    "DocumentExtraction",
    "FactStore",
    # Pipeline
    "PipelineConfig",
    "StageStatus",
    "RunManifest",
]
