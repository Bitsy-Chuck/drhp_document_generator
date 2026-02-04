"""Pipeline execution DTOs.

PipelineConfig, StageStatus, RunManifest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from drhp_agent.core.enums import (
    EnumConflictPolicy,
    EnumDateStyle,
    EnumNumberStyle,
    EnumPipelineMode,
    EnumRetrieverMode,
)


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution."""

    section: str
    drhp_md: str
    supporting_docs: str
    out_dir: str
    mode: EnumPipelineMode = EnumPipelineMode.STRICT
    retriever_mode: EnumRetrieverMode = EnumRetrieverMode.HYBRID
    conflict_policy: EnumConflictPolicy = EnumConflictPolicy.HIGHEST_CONFIDENCE
    date_style: EnumDateStyle = EnumDateStyle.LONG_IN
    number_style: EnumNumberStyle = EnumNumberStyle.LAKH_CRORE
    top_k: int = 10
    chunk_size: int = 500
    chunk_overlap: int = 50
    confidence_threshold: float = 0.7
    reconciliation_tolerance: float = 0.01
    config_hash: str | None = None


@dataclass
class StageStatus:
    """Status of a pipeline stage."""

    stage_name: str
    status: str  # pending, running, completed, failed, skipped
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    artifacts: list[str] = field(default_factory=list)


@dataclass
class RunManifest:
    """Manifest tracking a pipeline run."""

    run_id: str
    started_at: datetime
    config_hash: str
    completed_at: datetime | None = None
    config: PipelineConfig | None = None
    input_files: list[str] = field(default_factory=list)
    input_checksums: dict[str, str] = field(default_factory=dict)
    stages: list[StageStatus] = field(default_factory=list)
    output_files: list[str] = field(default_factory=list)
    status: str = "pending"
    error: str | None = None
