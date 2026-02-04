"""Pipeline orchestrator.

Task 1.5: Coordinate all pipeline stages end-to-end.
Task 13.6: Add elaboration stage for hybrid template system.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from drhp_agent.core.dtos import FactStore, PipelineConfig, RunManifest, StageStatus
from drhp_agent.fill.slot_filler import FilledSlots, SlotFiller
from drhp_agent.elaborate.elaborator import Elaborator, Elaborations
from drhp_agent.ingest.extractor import FactExtractor
from drhp_agent.ingest.loader import DocumentLoader
from drhp_agent.llm.client import LLMClient, LLMConfig
from drhp_agent.md_template.parser import ParsedTemplate, TemplateParser
from drhp_agent.render.renderer import RenderResult, SectionRenderer
from drhp_agent.validate.validator import FactValidator, ValidationResult


@dataclass
class PipelineResult:
    """Result of running the full pipeline."""

    success: bool
    manifest: RunManifest
    fact_store: FactStore | None = None
    template: ParsedTemplate | None = None
    filled_slots: FilledSlots | None = None
    elaborations: Elaborations | None = None
    validation: ValidationResult | None = None
    render_result: RenderResult | None = None
    error: str | None = None

    @property
    def has_review_flags(self) -> bool:
        """Check if any review flags exist."""
        return bool(self.render_result and self.render_result.review_flags)

    @property
    def exit_code(self) -> int:
        """Get exit code: 0=success, 1=has flags, 2=error."""
        if not self.success:
            return 2
        if self.has_review_flags:
            return 1
        return 0


class PipelineOrchestrator:
    """Orchestrates the full DRHP section drafting pipeline."""

    def __init__(
        self,
        config: PipelineConfig,
        progress_callback: Callable[[str, str], None] | None = None,
    ):
        """Initialize orchestrator.

        Args:
            config: Pipeline configuration
            progress_callback: Optional callback(stage, message)
        """
        self.config = config
        self.progress = progress_callback or (lambda s, m: None)

        # Initialize components
        llm_config = LLMConfig()
        self.llm_client = LLMClient(llm_config)

        # Create output directory
        self.out_dir = Path(config.out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.intermediate_dir = self.out_dir / "intermediate"
        self.intermediate_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> PipelineResult:
        """Run the full pipeline.

        Returns:
            PipelineResult with all outputs
        """
        start_time = datetime.now()
        stages: list[StageStatus] = []

        manifest = RunManifest(
            run_id=f"run_{start_time.strftime('%Y%m%d_%H%M%S')}",
            started_at=start_time,
            config_hash="",
            config=self.config,
            status="running",
        )

        try:
            # Stage 1: Load documents
            self.progress("ingest", "Loading documents...")
            stage = StageStatus(stage_name="ingest", status="running", started_at=datetime.now())

            loader = DocumentLoader(self.config.supporting_docs)
            documents = loader.load_all()
            manifest.input_files = [str(p) for p, _, _ in documents]
            manifest.input_checksums = {str(p): cs for p, _, cs in documents}

            self.progress("ingest", f"Found {len(documents)} documents")
            stage.status = "completed"
            stage.completed_at = datetime.now()
            stages.append(stage)

            # Stage 2: Extract facts
            self.progress("extract", "Extracting facts from documents...")
            stage = StageStatus(stage_name="extract", status="running", started_at=datetime.now())

            extractor = FactExtractor(self.llm_client)
            fact_store = extractor.extract_all(documents)
            fact_store_path = self.intermediate_dir / "fact_store.json"
            extractor.save_fact_store(fact_store, fact_store_path)

            total_facts = len(fact_store.all_facts())
            self.progress("extract", f"Extracted {total_facts} facts")
            stage.status = "completed"
            stage.completed_at = datetime.now()
            stage.artifacts = [str(fact_store_path)]
            stages.append(stage)

            # Stage 3: Parse template
            self.progress("template", "Parsing template...")
            stage = StageStatus(stage_name="template", status="running", started_at=datetime.now())

            parser = TemplateParser(self.config.drhp_md)
            template = parser.parse()
            template_path = self.intermediate_dir / "section_template.json"
            parser.save_parsed_template(template, template_path)

            self.progress("template", f"Found {len(template.slots)} slots")
            stage.status = "completed"
            stage.completed_at = datetime.now()
            stage.artifacts = [str(template_path)]
            stages.append(stage)

            # Stage 4: Fill slots
            self.progress("fill", "Filling slots...")
            stage = StageStatus(stage_name="fill", status="running", started_at=datetime.now())

            filler = SlotFiller(self.llm_client)
            fill_requests = template.to_fill_requests()

            def fill_progress(slot_id: str, idx: int, total: int):
                self.progress("fill", f"Filling slot {idx}/{total}: {slot_id}")

            filled_slots = filler.fill_all(fill_requests, fact_store, fill_progress)
            filled_slots_path = self.intermediate_dir / "filled_slots.json"
            filler.save_filled_slots(filled_slots, filled_slots_path)

            self.progress(
                "fill",
                f"Filled: {filled_slots.filled_count}, "
                f"Missing: {filled_slots.missing_count}, "
                f"Conflicts: {filled_slots.conflict_count}"
            )
            stage.status = "completed"
            stage.completed_at = datetime.now()
            stage.artifacts = [str(filled_slots_path)]
            stages.append(stage)

            # Stage 5: Elaborate (if template has elaboration blocks)
            elaborations = None
            if template.elaboration_blocks:
                self.progress("elaborate", "Elaborating sections...")
                stage = StageStatus(stage_name="elaborate", status="running", started_at=datetime.now())

                elaborator = Elaborator(self.llm_client)

                # Convert facts to dicts for elaboration requests
                facts_as_dicts = elaborator._facts_to_dicts(fact_store)
                elaborate_requests = template.to_elaboration_requests(facts_as_dicts)

                def elaborate_progress(block_id: str, idx: int, total: int):
                    self.progress("elaborate", f"Elaborating block {idx}/{total}: {block_id}")

                elaborations = elaborator.elaborate_all(elaborate_requests, fact_store, elaborate_progress)
                elaborations_path = self.intermediate_dir / "elaborations.json"
                elaborator.save_elaborations(elaborations, elaborations_path)

                self.progress(
                    "elaborate",
                    f"Elaborated: {elaborations.generated_count}, "
                    f"Empty: {elaborations.empty_count}, "
                    f"Errors: {elaborations.error_count}"
                )
                stage.status = "completed"
                stage.completed_at = datetime.now()
                stage.artifacts = [str(elaborations_path)]
                stages.append(stage)
            else:
                self.progress("elaborate", "No elaboration blocks in template, skipping...")

            # Stage 6: Validate
            self.progress("validate", "Validating facts...")
            stage = StageStatus(stage_name="validate", status="running", started_at=datetime.now())

            validator = FactValidator(self.llm_client)
            validation = validator.validate(fact_store)
            validation_path = self.intermediate_dir / "validation.json"
            validator.save_validation_result(validation, validation_path)

            self.progress(
                "validate",
                f"Validation: {'passed' if validation.is_valid else 'has issues'} "
                f"({len(validation.issues)} issues)"
            )
            stage.status = "completed"
            stage.completed_at = datetime.now()
            stage.artifacts = [str(validation_path)]
            stages.append(stage)

            # Stage 7: Render
            self.progress("render", "Rendering section...")
            stage = StageStatus(stage_name="render", status="running", started_at=datetime.now())

            renderer = SectionRenderer(self.llm_client)
            render_result = renderer.render(
                template, filled_slots, fact_store, validation, elaborations
            )

            section_path = self.out_dir / "capital_structure.md"
            annotations_path = self.out_dir / "annotations.jsonl"
            flags_path = self.out_dir / "review_flags.md"

            renderer.save_section(render_result, section_path)
            renderer.save_annotations(render_result, annotations_path)
            renderer.save_review_flags(render_result, flags_path)

            self.progress(
                "render",
                f"Rendered with {len(render_result.review_flags)} review flags"
            )
            stage.status = "completed"
            stage.completed_at = datetime.now()
            stage.artifacts = [str(section_path), str(annotations_path), str(flags_path)]
            stages.append(stage)

            # Complete manifest
            manifest.stages = stages
            manifest.output_files = [
                str(section_path),
                str(annotations_path),
                str(flags_path),
                str(fact_store_path),
                str(filled_slots_path),
            ]
            manifest.completed_at = datetime.now()
            manifest.status = "completed"

            # Save manifest
            manifest_path = self.out_dir / "manifest.json"
            self._save_manifest(manifest, manifest_path)

            return PipelineResult(
                success=True,
                manifest=manifest,
                fact_store=fact_store,
                template=template,
                filled_slots=filled_slots,
                elaborations=elaborations,
                validation=validation,
                render_result=render_result,
            )

        except Exception as e:
            manifest.stages = stages
            manifest.completed_at = datetime.now()
            manifest.status = "failed"
            manifest.error = str(e)

            # Save manifest even on failure
            manifest_path = self.out_dir / "manifest.json"
            self._save_manifest(manifest, manifest_path)

            return PipelineResult(
                success=False,
                manifest=manifest,
                error=str(e),
            )

    def _save_manifest(self, manifest: RunManifest, path: Path) -> None:
        """Save run manifest to JSON."""
        data = {
            "run_id": manifest.run_id,
            "started_at": manifest.started_at.isoformat(),
            "completed_at": manifest.completed_at.isoformat() if manifest.completed_at else None,
            "status": manifest.status,
            "error": manifest.error,
            "input_files": manifest.input_files,
            "output_files": manifest.output_files,
            "stages": [
                {
                    "stage_name": s.stage_name,
                    "status": s.status,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                    "artifacts": s.artifacts,
                }
                for s in manifest.stages
            ],
        }
        path.write_text(json.dumps(data, indent=2))
