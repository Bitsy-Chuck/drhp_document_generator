"""Tests for PipelineOrchestrator (Tasks 1.5, 9.1-9.4)."""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from drhp_agent.run.orchestrator import PipelineOrchestrator, PipelineResult
from drhp_agent.core.dtos import PipelineConfig


class TestPipelineResult:
    """Tests for PipelineResult data class."""

    def test_success_without_flags_exit_code_0(self):
        from drhp_agent.core.dtos import RunManifest
        from drhp_agent.render.renderer import RenderResult

        manifest = RunManifest(
            run_id="test",
            started_at=datetime.now(),
            config_hash="",
        )
        render_result = RenderResult(
            section_markdown="content",
            annotations=[],
            review_flags=[],  # No flags
        )
        result = PipelineResult(
            success=True,
            manifest=manifest,
            render_result=render_result,
        )

        assert result.exit_code == 0
        assert not result.has_review_flags

    def test_success_with_flags_exit_code_1(self):
        from drhp_agent.core.dtos import RunManifest, ReviewFlag
        from drhp_agent.render.renderer import RenderResult
        from drhp_agent.core.enums import EnumReviewFlagType, EnumValidationSeverity

        manifest = RunManifest(
            run_id="test",
            started_at=datetime.now(),
            config_hash="",
        )
        render_result = RenderResult(
            section_markdown="content",
            annotations=[],
            review_flags=[
                ReviewFlag(
                    flag_id="RF_001",
                    flag_type=EnumReviewFlagType.MISSING_FACT,
                    severity=EnumValidationSeverity.WARN,
                    message="Missing data",
                )
            ],
        )
        result = PipelineResult(
            success=True,
            manifest=manifest,
            render_result=render_result,
        )

        assert result.exit_code == 1
        assert result.has_review_flags

    def test_failure_exit_code_2(self):
        from drhp_agent.core.dtos import RunManifest

        manifest = RunManifest(
            run_id="test",
            started_at=datetime.now(),
            config_hash="",
        )
        result = PipelineResult(
            success=False,
            manifest=manifest,
            error="Something went wrong",
        )

        assert result.exit_code == 2


class TestPipelineOrchestrator:
    """Tests for PipelineOrchestrator."""

    @pytest.fixture
    def sample_config(self, tmp_path):
        """Create sample config with temp directories."""
        # Create template
        template_path = tmp_path / "template.md"
        template_path.write_text("# Title\nThe company {{text:company_name}} was incorporated.")

        # Create evidence directory with a doc
        evidence_dir = tmp_path / "evidence"
        evidence_dir.mkdir()
        (evidence_dir / "doc.md").write_text("# Document\nCompany: Test Corp")

        # Output directory
        out_dir = tmp_path / "out"

        return PipelineConfig(
            section="capital_structure",
            drhp_md=str(template_path),
            supporting_docs=str(evidence_dir),
            out_dir=str(out_dir),
        )

    @pytest.fixture
    def mock_llm_responses(self):
        """Mock LLM responses for all pipeline stages."""
        return {
            "extract": {
                "facts": [
                    {
                        "fact_id": "F001",
                        "category": "company_info",
                        "key": "company_name",
                        "value": "Test Corp",
                        "value_type": "text",
                        "raw_text": "Company: Test Corp",
                        "confidence": 0.95,
                        "location": {"section": "Header"},
                    }
                ],
                "document_type": "test",
                "document_date": "2024-01-01",
            },
            "fill": {
                "slot_id": "company_name",
                "status": "filled",
                "value": "Test Corp",
                "formatted_value": "Test Corp",
                "source_facts": ["F001"],
                "source_files": ["doc.md"],
                "confidence": 0.95,
            },
            "validate": {
                "is_valid": True,
                "issues": [],
            },
        }

    def test_pipeline_creates_output_directories(self, sample_config):
        """Pipeline should create out/ and out/intermediate/."""
        with patch("drhp_agent.run.orchestrator.LLMClient"):
            with patch("drhp_agent.run.orchestrator.LLMConfig"):
                # Just instantiate - don't run
                orchestrator = PipelineOrchestrator(sample_config)

                assert Path(sample_config.out_dir).exists()
                assert (Path(sample_config.out_dir) / "intermediate").exists()

    def test_pipeline_runs_all_stages_in_order(self, sample_config, mock_llm_responses):
        """Pipeline should execute: ingest → extract → template → fill → validate → render."""
        stages_executed = []

        def track_progress(stage, message):
            if stage not in [s[0] for s in stages_executed]:
                stages_executed.append((stage, message))

        with patch("drhp_agent.run.orchestrator.LLMConfig"):
            with patch("drhp_agent.run.orchestrator.LLMClient") as MockLLMClient:
                mock_client = Mock()
                mock_client.extract_facts.return_value = mock_llm_responses["extract"]
                mock_client.fill_slot.return_value = mock_llm_responses["fill"]
                mock_client.validate_facts.return_value = mock_llm_responses["validate"]
                MockLLMClient.return_value = mock_client

                orchestrator = PipelineOrchestrator(sample_config, track_progress)
                result = orchestrator.run()

        # Check stages were executed in order
        stage_names = [s[0] for s in stages_executed]
        assert "ingest" in stage_names
        assert "extract" in stage_names
        assert "template" in stage_names
        assert "fill" in stage_names
        assert "validate" in stage_names
        assert "render" in stage_names

        # Check order
        assert stage_names.index("ingest") < stage_names.index("extract")
        assert stage_names.index("extract") < stage_names.index("fill")
        assert stage_names.index("fill") < stage_names.index("render")

    def test_pipeline_saves_manifest_on_success(self, sample_config, mock_llm_responses):
        """Manifest should be saved with completed status."""
        with patch("drhp_agent.run.orchestrator.LLMConfig"):
            with patch("drhp_agent.run.orchestrator.LLMClient") as MockLLMClient:
                mock_client = Mock()
                mock_client.extract_facts.return_value = mock_llm_responses["extract"]
                mock_client.fill_slot.return_value = mock_llm_responses["fill"]
                mock_client.validate_facts.return_value = mock_llm_responses["validate"]
                MockLLMClient.return_value = mock_client

                orchestrator = PipelineOrchestrator(sample_config)
                result = orchestrator.run()

        manifest_path = Path(sample_config.out_dir) / "manifest.json"
        assert manifest_path.exists()

        manifest = json.loads(manifest_path.read_text())
        assert manifest["status"] == "completed"
        assert manifest["error"] is None
        assert len(manifest["stages"]) == 6

    def test_pipeline_saves_manifest_on_failure(self, tmp_path):
        """Manifest should be saved even when pipeline fails."""
        # Create template but NOT the evidence directory to cause failure
        template_path = tmp_path / "template.md"
        template_path.write_text("# Test")

        config = PipelineConfig(
            section="test",
            drhp_md=str(template_path),
            supporting_docs="/nonexistent/evidence/dir",  # This will cause failure
            out_dir=str(tmp_path / "out"),
        )

        with patch("drhp_agent.run.orchestrator.LLMConfig"):
            with patch("drhp_agent.run.orchestrator.LLMClient"):
                orchestrator = PipelineOrchestrator(config)
                result = orchestrator.run()

        assert not result.success
        assert result.error is not None

        manifest_path = Path(config.out_dir) / "manifest.json"
        assert manifest_path.exists()

        manifest = json.loads(manifest_path.read_text())
        assert manifest["status"] == "failed"
        assert manifest["error"] is not None

    def test_pipeline_progress_callback_invoked(self, sample_config, mock_llm_responses):
        """Progress callback should be called for each stage."""
        progress_calls = []

        def track_progress(stage, message):
            progress_calls.append((stage, message))

        with patch("drhp_agent.run.orchestrator.LLMConfig"):
            with patch("drhp_agent.run.orchestrator.LLMClient") as MockLLMClient:
                mock_client = Mock()
                mock_client.extract_facts.return_value = mock_llm_responses["extract"]
                mock_client.fill_slot.return_value = mock_llm_responses["fill"]
                mock_client.validate_facts.return_value = mock_llm_responses["validate"]
                MockLLMClient.return_value = mock_client

                orchestrator = PipelineOrchestrator(sample_config, track_progress)
                orchestrator.run()

        # Should have multiple progress calls
        assert len(progress_calls) > 0
        stages = set(call[0] for call in progress_calls)
        assert "ingest" in stages
        assert "extract" in stages

    def test_pipeline_generates_all_output_files(self, sample_config, mock_llm_responses):
        """Pipeline should generate all required output files."""
        with patch("drhp_agent.run.orchestrator.LLMConfig"):
            with patch("drhp_agent.run.orchestrator.LLMClient") as MockLLMClient:
                mock_client = Mock()
                mock_client.extract_facts.return_value = mock_llm_responses["extract"]
                mock_client.fill_slot.return_value = mock_llm_responses["fill"]
                mock_client.validate_facts.return_value = mock_llm_responses["validate"]
                MockLLMClient.return_value = mock_client

                orchestrator = PipelineOrchestrator(sample_config)
                result = orchestrator.run()

        out_dir = Path(sample_config.out_dir)

        # Main outputs
        assert (out_dir / "capital_structure.md").exists()
        assert (out_dir / "annotations.jsonl").exists()
        assert (out_dir / "review_flags.md").exists()
        assert (out_dir / "manifest.json").exists()

        # Intermediate outputs
        intermediate = out_dir / "intermediate"
        assert (intermediate / "fact_store.json").exists()
        assert (intermediate / "section_template.json").exists()
        assert (intermediate / "filled_slots.json").exists()
        assert (intermediate / "validation.json").exists()

    def test_pipeline_result_contains_all_data(self, sample_config, mock_llm_responses):
        """PipelineResult should contain fact_store, filled_slots, etc."""
        with patch("drhp_agent.run.orchestrator.LLMConfig"):
            with patch("drhp_agent.run.orchestrator.LLMClient") as MockLLMClient:
                mock_client = Mock()
                mock_client.extract_facts.return_value = mock_llm_responses["extract"]
                mock_client.fill_slot.return_value = mock_llm_responses["fill"]
                mock_client.validate_facts.return_value = mock_llm_responses["validate"]
                MockLLMClient.return_value = mock_client

                orchestrator = PipelineOrchestrator(sample_config)
                result = orchestrator.run()

        assert result.success
        assert result.fact_store is not None
        assert result.template is not None
        assert result.filled_slots is not None
        assert result.validation is not None
        assert result.render_result is not None

    def test_pipeline_handles_missing_evidence_dir(self, tmp_path):
        """Pipeline should fail gracefully if evidence dir doesn't exist."""
        template_path = tmp_path / "template.md"
        template_path.write_text("# Test")

        config = PipelineConfig(
            section="test",
            drhp_md=str(template_path),
            supporting_docs="/nonexistent/path",
            out_dir=str(tmp_path / "out"),
        )

        with patch("drhp_agent.run.orchestrator.LLMConfig"):
            with patch("drhp_agent.run.orchestrator.LLMClient"):
                orchestrator = PipelineOrchestrator(config)
                result = orchestrator.run()

        assert not result.success
        assert result.error is not None

    def test_pipeline_handles_invalid_template(self, tmp_path):
        """Pipeline should fail gracefully if template doesn't exist."""
        evidence_dir = tmp_path / "evidence"
        evidence_dir.mkdir()
        (evidence_dir / "doc.md").write_text("# Doc")

        config = PipelineConfig(
            section="test",
            drhp_md="/nonexistent/template.md",
            supporting_docs=str(evidence_dir),
            out_dir=str(tmp_path / "out"),
        )

        with patch("drhp_agent.run.orchestrator.LLMConfig"):
            with patch("drhp_agent.run.orchestrator.LLMClient") as MockLLMClient:
                mock_client = Mock()
                mock_client.extract_facts.return_value = {"facts": [], "document_type": "test"}
                MockLLMClient.return_value = mock_client

                orchestrator = PipelineOrchestrator(config)
                result = orchestrator.run()

        assert not result.success
        assert "template" in result.error.lower() or "not found" in result.error.lower()
