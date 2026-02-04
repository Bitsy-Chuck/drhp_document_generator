"""Tests for CLI (Tasks 1.6, 9.1-9.4)."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, Mock
from io import StringIO

from drhp_agent.run.cli import main, print_progress, print_summary


class TestPrintProgress:
    """Tests for progress printing."""

    def test_print_progress_with_known_stage(self, capsys):
        print_progress("ingest", "Loading documents...")
        captured = capsys.readouterr()
        assert "INGEST" in captured.out
        assert "Loading documents" in captured.out

    def test_print_progress_with_unknown_stage(self, capsys):
        print_progress("custom", "Custom message")
        captured = capsys.readouterr()
        assert "CUSTOM" in captured.out
        assert "Custom message" in captured.out


class TestPrintSummary:
    """Tests for summary printing."""

    def test_print_summary_success(self, capsys):
        from drhp_agent.run.orchestrator import PipelineResult
        from drhp_agent.core.dtos import RunManifest, FactStore, DocumentExtraction, ExtractedFact, FactLocation
        from drhp_agent.fill.slot_filler import FilledSlots
        from drhp_agent.core.dtos import SlotFillResult
        from drhp_agent.render.renderer import RenderResult
        from drhp_agent.validate.validator import ValidationResult
        from datetime import datetime

        # Create a successful result
        fact = ExtractedFact(
            fact_id="F001", category="test", key="test",
            value="val", value_type="text", raw_text="val",
            location=FactLocation(), doc_id="DOC_001",
        )
        fact_store = FactStore(extractions=[
            DocumentExtraction(doc_id="DOC_001", file_path="/test.md",
                               document_type="test", facts=[fact])
        ])
        filled_slots = FilledSlots(results=[
            SlotFillResult(slot_id="s1", status="filled", value="test")
        ])
        validation = ValidationResult(is_valid=True, issues=[])
        render_result = RenderResult(section_markdown="content", annotations=[], review_flags=[])
        manifest = RunManifest(
            run_id="test", started_at=datetime.now(), config_hash="",
            output_files=["/out/file.md"]
        )

        result = PipelineResult(
            success=True,
            manifest=manifest,
            fact_store=fact_store,
            filled_slots=filled_slots,
            validation=validation,
            render_result=render_result,
        )

        print_summary(result)
        captured = capsys.readouterr()

        assert "SUCCESS" in captured.out
        assert "Facts extracted" in captured.out
        assert "Slots filled" in captured.out

    def test_print_summary_failure(self, capsys):
        from drhp_agent.run.orchestrator import PipelineResult
        from drhp_agent.core.dtos import RunManifest
        from datetime import datetime

        manifest = RunManifest(run_id="test", started_at=datetime.now(), config_hash="")
        result = PipelineResult(
            success=False,
            manifest=manifest,
            error="Something went wrong",
        )

        print_summary(result)
        captured = capsys.readouterr()

        assert "FAILED" in captured.out
        assert "Something went wrong" in captured.out


class TestCLIArgumentParsing:
    """Tests for CLI argument parsing."""

    def test_cli_shows_help(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "--template" in captured.out
        assert "--evidence" in captured.out
        assert "--out" in captured.out

    def test_cli_requires_template(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--evidence", "/some/path", "--out", "/out"])
        assert exc_info.value.code != 0

    def test_cli_requires_evidence(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--template", "/some/template.md", "--out", "/out"])
        assert exc_info.value.code != 0

    def test_cli_requires_out(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--template", "/t.md", "--evidence", "/e"])
        assert exc_info.value.code != 0


class TestCLIValidation:
    """Tests for CLI input validation."""

    def test_cli_validates_template_exists(self, tmp_path, capsys):
        evidence_dir = tmp_path / "evidence"
        evidence_dir.mkdir()

        exit_code = main([
            "--template", "/nonexistent/template.md",
            "--evidence", str(evidence_dir),
            "--out", str(tmp_path / "out"),
        ])

        assert exit_code == 2
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower() or "error" in captured.err.lower()

    def test_cli_validates_evidence_exists(self, tmp_path, capsys):
        template = tmp_path / "template.md"
        template.write_text("# Test")

        exit_code = main([
            "--template", str(template),
            "--evidence", "/nonexistent/evidence",
            "--out", str(tmp_path / "out"),
        ])

        assert exit_code == 2
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower() or "error" in captured.err.lower()


class TestCLIExecution:
    """Tests for CLI execution."""

    @pytest.fixture
    def valid_setup(self, tmp_path):
        """Create valid template and evidence for testing."""
        template = tmp_path / "template.md"
        template.write_text("# Title\nCompany: {{text:company_name}}")

        evidence_dir = tmp_path / "evidence"
        evidence_dir.mkdir()
        (evidence_dir / "doc.md").write_text("# Doc\nCompany: Test Corp")

        out_dir = tmp_path / "out"

        return {
            "template": str(template),
            "evidence": str(evidence_dir),
            "out": str(out_dir),
        }

    def test_cli_quiet_mode_suppresses_output(self, valid_setup, capsys):
        mock_llm_responses = {
            "extract": {"facts": [], "document_type": "test"},
            "fill": {"slot_id": "company_name", "status": "missing", "reason": "Not found"},
            "validate": {"is_valid": True, "issues": []},
        }

        with patch("drhp_agent.run.orchestrator.LLMConfig"):
            with patch("drhp_agent.run.orchestrator.LLMClient") as MockLLMClient:
                mock_client = Mock()
                mock_client.extract_facts.return_value = mock_llm_responses["extract"]
                mock_client.fill_slot.return_value = mock_llm_responses["fill"]
                mock_client.validate_facts.return_value = mock_llm_responses["validate"]
                MockLLMClient.return_value = mock_client

                exit_code = main([
                    "--template", valid_setup["template"],
                    "--evidence", valid_setup["evidence"],
                    "--out", valid_setup["out"],
                    "--quiet",
                ])

        captured = capsys.readouterr()
        # Should have minimal output in quiet mode
        assert "INGEST" not in captured.out
        assert "EXTRACT" not in captured.out

    def test_cli_returns_exit_code_0_on_success(self, valid_setup):
        mock_llm_responses = {
            "extract": {
                "facts": [{
                    "fact_id": "F001", "category": "test", "key": "company_name",
                    "value": "Test Corp", "value_type": "text", "raw_text": "Test Corp",
                    "confidence": 0.95, "location": {},
                }],
                "document_type": "test",
            },
            "fill": {
                "slot_id": "company_name", "status": "filled",
                "value": "Test Corp", "formatted_value": "Test Corp",
                "source_facts": ["F001"], "source_files": ["doc.md"],
                "confidence": 0.95,
            },
            "validate": {"is_valid": True, "issues": []},
        }

        with patch("drhp_agent.run.orchestrator.LLMConfig"):
            with patch("drhp_agent.run.orchestrator.LLMClient") as MockLLMClient:
                mock_client = Mock()
                mock_client.extract_facts.return_value = mock_llm_responses["extract"]
                mock_client.fill_slot.return_value = mock_llm_responses["fill"]
                mock_client.validate_facts.return_value = mock_llm_responses["validate"]
                MockLLMClient.return_value = mock_client

                exit_code = main([
                    "--template", valid_setup["template"],
                    "--evidence", valid_setup["evidence"],
                    "--out", valid_setup["out"],
                    "--quiet",
                ])

        assert exit_code == 0

    def test_cli_returns_exit_code_1_with_review_flags(self, valid_setup):
        mock_llm_responses = {
            "extract": {"facts": [], "document_type": "test"},
            "fill": {
                "slot_id": "company_name", "status": "missing",
                "reason": "No matching fact found",
            },
            "validate": {"is_valid": True, "issues": []},
        }

        with patch("drhp_agent.run.orchestrator.LLMConfig"):
            with patch("drhp_agent.run.orchestrator.LLMClient") as MockLLMClient:
                mock_client = Mock()
                mock_client.extract_facts.return_value = mock_llm_responses["extract"]
                mock_client.fill_slot.return_value = mock_llm_responses["fill"]
                mock_client.validate_facts.return_value = mock_llm_responses["validate"]
                MockLLMClient.return_value = mock_client

                exit_code = main([
                    "--template", valid_setup["template"],
                    "--evidence", valid_setup["evidence"],
                    "--out", valid_setup["out"],
                    "--quiet",
                ])

        # Missing slot should create review flag → exit code 1
        assert exit_code == 1

    def test_cli_returns_exit_code_2_on_error(self, tmp_path, capsys):
        """Pipeline error (e.g., missing evidence dir) should return exit code 2."""
        template = tmp_path / "template.md"
        template.write_text("# Test\n{{text:slot}}")

        # Use nonexistent evidence dir to cause failure
        exit_code = main([
            "--template", str(template),
            "--evidence", "/nonexistent/evidence/dir",
            "--out", str(tmp_path / "out"),
            "--quiet",
        ])

        assert exit_code == 2
