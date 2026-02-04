"""Contracts (interfaces) for dependency inversion.

Task 1.5: Interfaces in core/contracts, implementations in feature modules.
"""

from abc import ABC, abstractmethod
from typing import Any

from drhp_agent.core.dtos import (
    AnnotationRecord,
    ChunkInfo,
    DocumentMetadata,
    FilledSlotsResult,
    PipelineConfig,
    ReviewFlag,
    RunManifest,
    SectionTemplate,
    SlotFill,
    SlotSpec,
    TableInfo,
    TemplateNode,
    ValidationIssue,
)
from drhp_agent.core.enums import EnumSectionKey


class IMarkdownParser(ABC):
    """Interface for markdown parsing.

    Task 1.4: Plugin registry for parsers.
    """

    @abstractmethod
    def parse(self, content: str, file_path: str | None = None) -> TemplateNode:
        """Parse markdown content into a normalized node tree.

        Args:
            content: The markdown content to parse.
            file_path: Optional path for error reporting.

        Returns:
            Root TemplateNode of the parsed tree.
        """
        ...

    @abstractmethod
    def extract_section(
        self,
        root: TemplateNode,
        section_key: EnumSectionKey,
        aliases: list[str] | None = None,
    ) -> TemplateNode | None:
        """Extract a section from the parsed tree.

        Args:
            root: The root node of the parsed tree.
            section_key: The section to extract.
            aliases: Optional section title aliases.

        Returns:
            The extracted section node, or None if not found.
        """
        ...


class ISlotDetector(ABC):
    """Interface for slot detection.

    Task 1.4: Plugin registry for slot labelers.
    """

    @abstractmethod
    def detect_slots(self, node: TemplateNode, context: dict[str, Any] | None = None) -> list[SlotSpec]:
        """Detect fillable slots in a template node.

        Args:
            node: The template node to analyze.
            context: Optional context for detection.

        Returns:
            List of detected slot specifications.
        """
        ...


class IDocumentIngester(ABC):
    """Interface for document ingestion.

    Task 1.4: Plugin registry for parsers.
    """

    @abstractmethod
    def ingest(self, file_path: str) -> tuple[DocumentMetadata, list[ChunkInfo], list[TableInfo]]:
        """Ingest a document and extract chunks and tables.

        Args:
            file_path: Path to the document.

        Returns:
            Tuple of (metadata, chunks, tables).
        """
        ...

    @abstractmethod
    def supports(self, file_path: str) -> bool:
        """Check if this ingester supports the given file type.

        Args:
            file_path: Path to check.

        Returns:
            True if supported, False otherwise.
        """
        ...


class IRetriever(ABC):
    """Interface for evidence retrieval.

    Task 1.4: Plugin registry for retrievers.
    """

    @abstractmethod
    def index(self, chunks: list[ChunkInfo], tables: list[TableInfo]) -> None:
        """Index chunks and tables for retrieval.

        Args:
            chunks: List of text chunks.
            tables: List of tables.
        """
        ...

    @abstractmethod
    def retrieve(
        self,
        query: str,
        slot_spec: SlotSpec | None = None,
        top_k: int = 10,
    ) -> list[tuple[ChunkInfo | TableInfo, float]]:
        """Retrieve relevant evidence for a query.

        Args:
            query: The search query.
            slot_spec: Optional slot specification for context.
            top_k: Maximum number of results.

        Returns:
            List of (evidence, score) tuples.
        """
        ...


class ISlotFiller(ABC):
    """Interface for slot filling."""

    @abstractmethod
    def fill_slot(
        self,
        slot_spec: SlotSpec,
        candidates: list[tuple[ChunkInfo | TableInfo, float]],
        context: dict[str, Any] | None = None,
    ) -> SlotFill:
        """Fill a slot with evidence-backed value.

        Args:
            slot_spec: The slot to fill.
            candidates: Retrieved evidence candidates with scores.
            context: Optional context for filling.

        Returns:
            The slot fill result.
        """
        ...


class IValidator(ABC):
    """Interface for validation.

    Task 1.4: Plugin registry for validators.
    """

    @abstractmethod
    def validate(
        self,
        fills: dict[str, SlotFill],
        template: SectionTemplate,
        config: PipelineConfig,
    ) -> list[ValidationIssue]:
        """Validate filled slots.

        Args:
            fills: Dictionary of slot fills.
            template: The section template.
            config: Pipeline configuration.

        Returns:
            List of validation issues.
        """
        ...


class IRenderer(ABC):
    """Interface for output rendering.

    Task 1.4: Plugin registry for renderers.
    """

    @abstractmethod
    def render(
        self,
        template: SectionTemplate,
        fills: dict[str, SlotFill],
        config: PipelineConfig,
    ) -> tuple[str, list[AnnotationRecord], list[ReviewFlag]]:
        """Render the final section output.

        Args:
            template: The section template.
            fills: Dictionary of slot fills.
            config: Pipeline configuration.

        Returns:
            Tuple of (rendered_markdown, annotations, review_flags).
        """
        ...


class IPipelineStage(ABC):
    """Interface for pipeline stages.

    Task 1.3: Pipeline orchestrator stages.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Stage name."""
        ...

    @abstractmethod
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute this pipeline stage.

        Args:
            context: Pipeline context with inputs from previous stages.

        Returns:
            Updated context with stage outputs.
        """
        ...


class IPipelineOrchestrator(ABC):
    """Interface for pipeline orchestration.

    Task 1.3: Pipeline orchestrator that executes stages in order.
    """

    @abstractmethod
    def register_stage(self, stage: IPipelineStage) -> None:
        """Register a pipeline stage.

        Args:
            stage: The stage to register.
        """
        ...

    @abstractmethod
    def execute(self, config: PipelineConfig) -> RunManifest:
        """Execute the full pipeline.

        Args:
            config: Pipeline configuration.

        Returns:
            Run manifest with results.
        """
        ...
