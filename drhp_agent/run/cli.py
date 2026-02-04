"""Command-line interface.

Task 1.6, 9.1-9.4: Single command execution with progress and exit codes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from drhp_agent.core.dtos import PipelineConfig
from drhp_agent.run.orchestrator import PipelineOrchestrator


def print_progress(stage: str, message: str) -> None:
    """Print progress message with stage indicator."""
    stage_icons = {
        "ingest": "📁",
        "extract": "🔍",
        "template": "📋",
        "fill": "✍️",
        "validate": "✅",
        "render": "📄",
    }
    icon = stage_icons.get(stage, "▶️")
    print(f"{icon} [{stage.upper()}] {message}")


def print_summary(result) -> None:
    """Print final summary."""
    print("\n" + "=" * 60)
    print("PIPELINE SUMMARY")
    print("=" * 60)

    if result.success:
        print(f"✅ Status: SUCCESS")
    else:
        print(f"❌ Status: FAILED")
        print(f"   Error: {result.error}")
        return

    if result.fact_store:
        facts = result.fact_store.all_facts()
        print(f"📊 Facts extracted: {len(facts)}")

    if result.filled_slots:
        fs = result.filled_slots
        print(f"✍️  Slots filled: {fs.filled_count}")
        print(f"❓ Slots missing: {fs.missing_count}")
        if fs.conflict_count:
            print(f"⚠️  Conflicts: {fs.conflict_count}")
        if fs.low_confidence_count:
            print(f"🔶 Low confidence: {fs.low_confidence_count}")

    if result.validation:
        v = result.validation
        if v.is_valid:
            print(f"✅ Validation: passed")
        else:
            print(f"⚠️  Validation: {len(v.issues)} issues")

    if result.render_result:
        flags = len(result.render_result.review_flags)
        if flags == 0:
            print(f"📄 Review flags: none")
        else:
            print(f"🚩 Review flags: {flags}")

    print("=" * 60)

    # Print output locations
    print("\nOutput files:")
    for f in result.manifest.output_files:
        print(f"  - {f}")

    print()
    if result.has_review_flags:
        print("⚠️  Review required. See review_flags.md for details.")
    else:
        print("✅ All slots filled successfully. Ready for review.")


def main(args: list[str] | None = None) -> int:
    """Main entry point.

    Args:
        args: Command line arguments (defaults to sys.argv)

    Returns:
        Exit code: 0=success, 1=has review flags, 2=critical error
    """
    parser = argparse.ArgumentParser(
        prog="drhp_agent",
        description="DRHP Section Drafting Agent - Generate Capital Structure section from supporting documents",
    )

    parser.add_argument(
        "--template",
        required=True,
        help="Path to template markdown file (e.g., templates/capital_structure.md)",
    )

    parser.add_argument(
        "--evidence",
        required=True,
        help="Path to supporting documents directory (e.g., supporting_docs/PAS-3/)",
    )

    parser.add_argument(
        "--out",
        required=True,
        help="Output directory for generated files (e.g., out/)",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output",
    )

    parsed = parser.parse_args(args)

    # Validate paths
    template_path = Path(parsed.template)
    if not template_path.exists():
        print(f"Error: Template not found: {parsed.template}", file=sys.stderr)
        return 2

    evidence_path = Path(parsed.evidence)
    if not evidence_path.exists():
        print(f"Error: Evidence directory not found: {parsed.evidence}", file=sys.stderr)
        return 2

    # Create configuration
    config = PipelineConfig(
        section="capital_structure",
        drhp_md=str(template_path),
        supporting_docs=str(evidence_path),
        out_dir=str(parsed.out),
    )

    # Progress callback
    progress_callback = None if parsed.quiet else print_progress

    # Run pipeline
    print("\n🚀 Starting DRHP Section Drafting Agent\n")

    orchestrator = PipelineOrchestrator(config, progress_callback)
    result = orchestrator.run()

    # Print summary
    if not parsed.quiet:
        print_summary(result)

    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
