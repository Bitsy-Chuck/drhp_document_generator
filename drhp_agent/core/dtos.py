"""Data Transfer Objects (DTOs) for the DRHP Section Drafting System.

This module re-exports all DTOs from the dtos/ package for backward compatibility.
"""

from drhp_agent.core.dtos import (
    # Template
    SlotSpec,
    TableCell,
    TemplateNode,
    SectionTemplate,
    # Evidence
    EvidenceRef,
    AnnotationRecord,
    # Validation
    ValidationIssue,
    ReviewFlag,
    # Filling
    SlotFill,
    SlotFillRequest,
    SlotFillResult,
    FilledSlotsResult,
    # Ingestion
    DocumentMetadata,
    ChunkInfo,
    TableInfo,
    # Extraction
    FactLocation,
    ExtractedFact,
    DocumentExtraction,
    FactStore,
    # Pipeline
    PipelineConfig,
    StageStatus,
    RunManifest,
)

__all__ = [
    "SlotSpec",
    "TableCell",
    "TemplateNode",
    "SectionTemplate",
    "EvidenceRef",
    "AnnotationRecord",
    "ValidationIssue",
    "ReviewFlag",
    "SlotFill",
    "SlotFillRequest",
    "SlotFillResult",
    "FilledSlotsResult",
    "DocumentMetadata",
    "ChunkInfo",
    "TableInfo",
    "FactLocation",
    "ExtractedFact",
    "DocumentExtraction",
    "FactStore",
    "PipelineConfig",
    "StageStatus",
    "RunManifest",
]
