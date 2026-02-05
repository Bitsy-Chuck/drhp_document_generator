# DRHP Drafting Agent - Assignment Coverage Critique

## Scope
Evaluation against the assignment in `drhp_agent/AI Engineering __ Assignment.pdf` using current code and sample output in `out/`.

## Key Gaps / Non-Compliance
- Real DRHP input requirement not met: Ingestion rejects any non-`.md` file, so a real DRHP PDF would fail immediately. This conflicts with the "Provide your system a real DRHP PDF" requirement. `drhp_agent/ingest/loader.py:17` `drhp_agent/ingest/loader.py:45`
- End-to-end run on real DRHP is not feasible: Fact extraction sends full document content to a single LLM call, which will not scale to real DRHP length and will exceed context limits. `drhp_agent/ingest/extractor.py:50`
- Traceability to source documents is weak: Slot fills only retain `doc_id`, and rendering cites the first source only; output shows `DOC_001` rather than actual filenames, undermining "which document each fact came from." `drhp_agent/fill/slot_filler.py:196` `drhp_agent/render/renderer.py:124` `out/capital_structure.md:108`
- Uncited assertions in final section: The Compliance section states facts without evidence or review flags, violating "all facts are grounded" and "missing/unclear information surfaced." `templates/capital_structure.md:53` `out/capital_structure.md:114`
- Derived / inferred facts appear without traceability: Elaboration output introduces computed values and classifications (e.g., "Private Placement", total share premium) without explicit citations or review markers. `out/capital_structure.md:37` `out/capital_structure.md:55` `drhp_agent/render/renderer.py:206`

## Quality / Correctness Risks
- Category filtering hides available facts: Allotment history shows "Date not specified" even though the allotment date exists in evidence; likely filtered out by category. `drhp_agent/elaborate/elaborator.py:136` `supporting_docs/PAS-3/List of Allottees.md:7` `out/capital_structure.md:37`
- Shareholding pattern is structurally unfillable: The template asks for shareholding data, but the extraction schema does not define a shareholding category, so the block is predictably empty. `templates/capital_structure.md:43` `drhp_agent/prompts.py:15` `out/capital_structure.md:104`
- Style/structure drift from DRHP format: Elaboration adds repeated headings and summary bullets; the assignment asks for paragraph-style disclosure, not a summary. `out/capital_structure.md:31` `out/capital_structure.md:63` `drhp_agent/render/renderer.py:206`
- Transparency metadata incomplete: `is_elaboration` is computed but not written to annotations output, so readers cannot distinguish extracted vs generated content in `annotations.jsonl`. `drhp_agent/render/renderer.py:193` `drhp_agent/render/renderer.py:279`

## Deliverables Coverage
- Sample run evidence: The repo has outputs in `out/`, but the README does not show the required "exact command + inputs + final generated section" as a clear sample run. `README.md:7`
