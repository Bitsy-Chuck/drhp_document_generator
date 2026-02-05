# DRHP Section Drafting System: Implementation TODO

## Assignment Requirements (Non-Negotiable)
- Must run end-to-end with single command
- Output looks like real DRHP section (legal disclosure tone, not AI summary)
- All facts traceable to source documents
- Missing/unclear parts explicitly flagged
- Show intermediate JSON artifact

---

## 0) Scope and Constraints

### Completed ✓
- [x] 0.1 MVP scope: Capital Structure section from template + PAS-3 evidence files
- [x] 0.2 Required outputs: section markdown, filled_slots.json, annotations.jsonl, review_flags.md
- [x] 0.3 Non-goals: PDF parsing (converter built later), multi-section, legal automation
- [x] 0.4 Grounding rule: only evidence-backed values populate slots
- [x] 0.5 Fallback rule: unresolved values render `[[REQUIRES REVIEW: reason]]`
- [x] 0.6 Input constraint: markdown only (`.md` files)
- [x] 0.7 Create `templates/capital_structure.md` with standard DRHP structure and slot markers
- [x] 0.8 Hybrid template: slots for critical facts, elaboration blocks for rich prose
- [x] 0.9 Elaboration syntax: `{{elaborate:block_id:hint}}` generates prose from ALL relevant facts

---

## 1) Architecture

### Completed ✓
- [x] 1.1 Package skeleton: `core`, `md_template`, `ingest`, `retrieve`, `fill`, `render`, `validate`, `report`, `run`
- [x] 1.2 Module contracts (DTOs) in `core/contracts.py`
- [x] 1.3 Pipeline config and run manifest DTOs
- [x] 1.4 CLI entrypoint schema defined
- [x] 1.5 Implement pipeline orchestrator in `run/orchestrator.py`
- [x] 1.6 Implement CLI in `run/cli.py` with single-command execution

---

## 2) Core Data Model

### Completed ✓
- [x] 2.1-2.15 All enums, DTOs, exceptions, schemas, serializers implemented
- [x] 2.16 Unit tests passing (60 tests)
- [x] 2.17 Created `prompts.py` with LLM prompt templates
- [x] 2.18 Add `FactLocation` DTO (section, table, row, column, line numbers)
- [x] 2.19 Add `ExtractedFact` DTO (fact_id, category, key, value, value_type, raw_text, location, unit, confidence)
- [x] 2.20 Add `DocumentExtraction` DTO (doc_id, file_path, document_type, document_date, facts list)
- [x] 2.21 Add `FactStore` DTO with helper methods (all_facts, facts_by_category, facts_by_key)
- [x] 2.22 Add `SlotFillRequest` DTO (slot_id, slot_type, slot_hint, slot_context)
- [x] 2.23 Add `SlotFillResult` DTO (slot_id, status, value, formatted_value, source_facts, source_files, confidence, reason)

---

## 3) LLM Integration

### Completed ✓
- [x] 3.1 Create `llm/client.py` with LLM provider abstraction
- [x] 3.2 Support Anthropic Claude API
- [x] 3.3 Add API key configuration (environment variable or config file)
- [x] 3.4 Add retry logic and error handling for API calls
- [x] 3.5 Add response parsing and JSON validation
- [x] 3.6 Define FACT_SCHEMA JSON structure
- [x] 3.7 Create EXTRACTION_SYSTEM_PROMPT (doc-agnostic fact extraction)
- [x] 3.8 Create EXTRACTION_USER_PROMPT template
- [x] 3.9 Create SLOT_FILL_SYSTEM_PROMPT
- [x] 3.10 Create SLOT_FILL_USER_PROMPT template
- [x] 3.11 Create SECTION_GENERATE_SYSTEM_PROMPT
- [x] 3.12 Create SECTION_GENERATE_USER_PROMPT template
- [x] 3.13 Create VALIDATION_SYSTEM_PROMPT
- [x] 3.14 Create VALIDATION_USER_PROMPT template

---

## 4) Document Ingestion

### Completed ✓
- [x] 4.1 Recursively discover `.md` files in `supporting_docs/`
- [x] 4.2 Reject non-`.md` files with `NotSupportedSourceTypeError`
- [x] 4.3 Compute file checksums for caching
- [x] 4.4 Read file content with encoding handling
- [x] 4.5 For each document, send content to LLM with EXTRACTION_PROMPT
- [x] 4.6 Parse LLM response into `DocumentExtraction` DTO
- [x] 4.7 Validate extracted facts against FACT_SCHEMA
- [x] 4.8 Handle extraction errors gracefully (retry, fallback)
- [x] 4.9 Aggregate all extractions into `FactStore`
- [x] 4.10 Emit `out/intermediate/fact_store.json`

---

## 5) Template Processing

### Completed ✓
- [x] 5.1 Load template markdown file
- [x] 5.2 Detect slot markers: `{{slot_name}}` or `{{type:slot_name:hint}}`
- [x] 5.3 Parse slot metadata from marker syntax
- [x] 5.4 Build list of `SlotFillRequest` objects
- [x] 5.5 Emit `out/intermediate/section_template.json`

---

## 6) Slot Filling (LLM-Based)

### Completed ✓
- [x] 6.1 For each slot, send `SlotFillRequest` + `FactStore` to LLM with SLOT_FILL_PROMPT
- [x] 6.2 Parse LLM response into `SlotFillResult` DTO
- [x] 6.3 Handle statuses: filled, missing, conflict, low_confidence
- [x] 6.4 Collect all results into filled slots collection
- [x] 6.5 Emit `out/intermediate/filled_slots.json`

---

## 7) Validation (LLM-Based)

### Completed ✓
- [x] 7.1 Send `FactStore` to LLM with VALIDATION_PROMPT
- [x] 7.2 Parse validation issues from response
- [x] 7.3 Check: same fact matches across documents
- [x] 7.4 Check: mathematical consistency (totals = sum of parts)
- [x] 7.5 Check: date consistency
- [x] 7.6 Flag missing critical facts
- [x] 7.7 Emit validation issues with severity levels

---

## 8) Section Rendering

### Completed ✓
- [x] 8.1 Send template + filled slots to LLM with SECTION_GENERATE_PROMPT
- [x] 8.2 Ensure legal disclosure tone (not AI summary)
- [x] 8.3 Add source citations: `[Source: filename]`
- [x] 8.4 Insert `[[REQUIRES REVIEW: reason]]` for missing/conflicted slots
- [x] 8.5 Emit `out/capital_structure.md`
- [x] 8.6 Map each filled value to source facts
- [x] 8.7 Emit `out/annotations.jsonl`
- [x] 8.8 Collect all missing, conflict, low_confidence items
- [x] 8.9 Group by severity
- [x] 8.10 Emit `out/review_flags.md`

---

## 9) CLI and End-to-End Execution

### Completed ✓
- [x] 9.1 Single command: `python -m drhp_agent.run --template templates/capital_structure.md --evidence supporting_docs/PAS-3/ --out out/`
- [x] 9.2 Print progress: extracting docs, filling slots, validating, rendering
- [x] 9.3 Print summary: facts extracted, slots filled, slots missing, conflicts
- [x] 9.4 Exit code: 0 = success, 1 = has review flags, 2 = critical error

---

## 10) Sample Data and Demo

### Completed ✓
- [x] 10.1 Copy `drhp_agent/PAS-3/` to `supporting_docs/PAS-3/`
- [x] 10.2 Create `templates/capital_structure.md` with DRHP structure and slot markers

### Completed ✓
- [x] 10.3 Run end-to-end and capture sample output
- [ ] 10.4 Document sample run in README with exact commands
- [ ] 10.5 Include sample outputs in repo

---

## 11) Testing

### Completed ✓
- [x] 11.1 Unit tests for core module (enums, DTOs, serializers) - 60 tests
- [x] 11.2 Unit tests for Fact DTOs and FactStore - 18 tests
- [x] 11.3 Unit tests for LLM response parsing - 12 tests
- [x] 11.4 Unit tests for DocumentLoader - 11 tests
- [x] 11.5 Unit tests for FactExtractor - 5 tests
- [x] 11.6 Integration tests for PAS-3 file loading - 2 tests
- [x] 11.7 Unit tests for TemplateParser - 14 tests
- [x] 11.8 Unit tests for SlotFiller - 10 tests
- [x] 11.9 Unit tests for SectionRenderer - 10 tests
- [x] 11.10 Unit tests for prompts - 20 tests
- [x] 11.11 Unit tests for ingestion DTOs - 9 tests
- [x] 11.12 Unit tests for validation DTOs - 9 tests
- [x] 11.13 Unit tests for LLM edge cases - 19 tests
- [x] 11.14 Unit tests for FactValidator - 13 tests
- [x] 11.15 Unit tests for PipelineOrchestrator - 12 tests
- [x] 11.16 Unit tests for CLI - 14 tests
- [x] 11.17 Edge case tests for TemplateParser - 12 tests
- [x] 11.18 Business logic tests for SlotFiller - 9 tests
- [x] 11.19 Edge case tests for SectionRenderer - 8 tests

**Total: 295 tests passing**

### Pending (Live LLM Tests)
- [ ] 11.20 Integration test: PAS-3 extraction → fact_store.json (with live LLM)
- [ ] 11.21 Integration test: fact_store → filled_slots.json (with live LLM)
- [ ] 11.22 End-to-end test: full pipeline with sample data
- [ ] 11.23 Snapshot test for rendered output

---

## 12) Definition of Done

- [x] 12.1 Single command runs end-to-end without error
- [x] 12.2 `fact_store.json` shows all extracted facts with sources (61 facts from 3 docs)
- [x] 12.3 `filled_slots.json` shows slot values with fact references
- [x] 12.4 Output `capital_structure.md` looks like real DRHP section
- [x] 12.5 Every fact has source citation in output
- [x] 12.6 Missing data clearly marked with `[[REQUIRES REVIEW]]`
- [x] 12.7 `review_flags.md` lists all items needing human attention (17 flags)
- [ ] 12.8 README explains how to run with sample data

---

## 13) Hybrid Template System (Slots + Elaboration Blocks)

**Purpose**: Slots capture exact values; elaboration blocks generate rich prose from ALL relevant facts.

### Template Syntax

```markdown
<!-- Slots: Exact values -->
The authorized capital is ₹{{amount:authorized_capital}}.

<!-- Elaborate: LLM generates from all relevant facts -->
{{elaborate:allotment_history:Detail all share allotments with dates, allottees, shares, prices. Use tables.}}
```

### 13.1) Core DTOs

- [x] 13.1.1 Add `ElaborationBlock` DTO (block_id, hint, fact_category, line_number, raw_marker)
- [x] 13.1.2 Add `ElaborationResult` DTO (block_id, generated_markdown, source_facts, source_files, confidence)
- [x] 13.1.3 Add `ElaborationRequest` DTO (block_id, hint, relevant_facts, template_context)
- [x] 13.1.4 Update `ParsedTemplate` to include `elaboration_blocks: list[ElaborationBlock]`

### 13.2) Template Parser Updates

- [x] 13.2.1 Add regex pattern for `{{elaborate:block_id:hint}}` markers
- [x] 13.2.2 Extract elaboration blocks alongside slots during parsing
- [x] 13.2.3 Parse optional fact_category filter: `{{elaborate:block_id:category:hint}}`
- [x] 13.2.4 Record line numbers and context for elaboration blocks
- [x] 13.2.5 Add `to_elaboration_requests()` method to `ParsedTemplate`
- [x] 13.2.6 Update `section_template.json` output to include elaboration blocks

### 13.3) LLM Prompts for Elaboration

- [x] 13.3.1 Create `ELABORATION_SYSTEM_PROMPT` (legal tone, factual, cite sources)
- [x] 13.3.2 Create `ELABORATION_USER_PROMPT` template (facts JSON + hint + context)
- [x] 13.3.3 Define `ELABORATION_SCHEMA` for structured response (markdown + sources)
- [x] 13.3.4 Add `elaborate_section()` method to `LLMClient`

### 13.4) Elaborator Module

- [x] 13.4.1 Create `elaborate/elaborator.py` module
- [x] 13.4.2 Implement `FactFilter` to select facts by category/keywords
- [x] 13.4.3 Implement `Elaborator.elaborate()` method:
  - Filter facts relevant to the block
  - Send to LLM with hint and surrounding context
  - Parse response into `ElaborationResult`
  - Track all source facts and files used
- [x] 13.4.4 Implement `Elaborator.elaborate_all()` for batch processing
- [x] 13.4.5 Handle empty fact sets gracefully (generate placeholder)
- [x] 13.4.6 Emit `out/intermediate/elaborations.json`

### 13.5) Renderer Updates

- [x] 13.5.1 Update `SectionRenderer` to handle both slots and elaboration blocks
- [x] 13.5.2 Replace `{{elaborate:...}}` markers with generated markdown
- [x] 13.5.3 Add citations for elaborated content (footnotes or inline)
- [x] 13.5.4 Create review flags for low-confidence elaborations
- [x] 13.5.5 Update `annotations.jsonl` to include elaboration sources

### 13.6) Pipeline Integration

- [x] 13.6.1 Add "elaborate" stage to orchestrator (after fill, before render)
- [x] 13.6.2 Update progress callback to report elaboration progress
- [x] 13.6.3 Pass elaboration results to renderer
- [x] 13.6.4 Update manifest to track elaboration stage

### 13.7) Template Updates

- [x] 13.7.1 Update `templates/capital_structure.md` with elaboration blocks:
  - `{{elaborate:allotment_history:...}}` for detailed allotment table
  - `{{elaborate:capital_changes:...}}` for capital modification history
  - `{{elaborate:shareholding_pattern:...}}` for ownership breakdown
- [x] 13.7.2 Keep critical facts as slots (company_name, authorized_capital, face_value)

### 13.8) Testing

- [x] 13.8.1 Unit tests for `ElaborationBlock` and `ElaborationResult` DTOs
- [x] 13.8.2 Unit tests for template parser elaboration block detection
- [x] 13.8.3 Unit tests for `FactFilter` category/keyword matching
- [x] 13.8.4 Unit tests for `Elaborator` with mock LLM
- [x] 13.8.5 Unit tests for renderer with mixed slots and elaborations
- [x] 13.8.6 Integration test: full pipeline with elaboration blocks
- [x] 13.8.7 Test edge cases: empty facts, overlapping categories, nested markers

---

## 14) Definition of Done (with Elaboration)

- [x] 14.1 Template supports both `{{type:slot:hint}}` and `{{elaborate:block:hint}}` syntax
- [x] 14.2 Elaboration blocks generate prose covering ALL relevant facts
- [x] 14.3 Generated prose maintains legal disclosure tone
- [x] 14.4 All elaborated content has source citations
- [x] 14.5 `elaborations.json` shows generated content with fact references
- [x] 14.6 Output section is richer than slot-only version
- [x] 14.7 Review flags include low-confidence elaborations

---

## Deferred (Post-MVP)

- PDF to markdown converter
- Multi-section stitching
- Local LLM support (Ollama)
- Caching of LLM extractions
- Performance optimization
- Additional section templates (Objects, Risk Factors, etc.)
- Elaboration with cross-section context
- User feedback loop for elaboration quality

---

## 15) Simplify Fact Matching - Remove Categories (COMPLETED)

### 15.1 Remove category from extraction
- [x] 15.1.1 Remove `category` field from `FACT_SCHEMA` in prompts.py
- [x] 15.1.2 Update `EXTRACTION_SYSTEM_PROMPT` to not request category assignment
- [x] 15.1.3 Remove `category` field from `ExtractedFact` DTO
- [x] 15.1.4 Update `DocumentExtraction` parsing to not expect category
- [x] 15.1.5 Update extraction tests

### 15.2 Remove category filtering
- [x] 15.2.1 Remove `facts_by_category()` method from `FactStore`
- [x] 15.2.2 Update `FactFilter` in elaborator to not filter by category
- [x] 15.2.3 Update elaboration to pass full fact_store instead of filtered subset
- [x] 15.2.4 Remove `fact_category` field from `ElaborationBlock` DTO
- [x] 15.2.5 Update template parser to not extract category from elaborate markers

### 15.3 Update slot filling
- [x] 15.3.1 Ensure slot filler passes full fact_store (already does this)
- [x] 15.3.2 Update slot fill prompt to emphasize semantic matching from all facts

### 15.4 Cleanup and testing
- [x] 15.4.1 Remove all `category` references from test files
- [x] 15.4.2 Update `fact_store.json` sample output (no category field)
- [x] 15.4.3 Run full test suite to verify nothing breaks (308 tests passing)
- [x] 15.4.4 Run end-to-end pipeline to verify output quality unchanged

---

## 16) Extract Fact Retriever Module (COMPLETED)

### 16.1 Create retriever module
- [x] 16.1.1 Create `retrieve/fact_retriever.py` with `FactRetriever` base class
- [x] 16.1.2 Implement `AllFactsRetriever` (pass all facts to LLM)
- [x] 16.1.3 Add `retrieve(fact_store, query, context) -> list[dict]` interface

### 16.2 Integrate with slot filler
- [x] 16.2.1 Update `SlotFiller.__init__` to accept optional `retriever` param
- [x] 16.2.2 Replace `_serialize_facts()` with `retriever.retrieve()`
- [x] 16.2.3 Default to `AllFactsRetriever` if none provided

### 16.3 Integrate with elaborator
- [x] 16.3.1 Update `Elaborator.__init__` to accept optional `retriever` param
- [x] 16.3.2 Replace `FactFilter` usage with `retriever.retrieve()`
- [x] 16.3.3 Remove `FactFilter` class entirely

### 16.4 Add keyword retriever (for scale)
- [x] 16.4.1 Implement `KeywordRetriever` for fact stores > 200 facts
- [x] 16.4.2 Extract keywords from query/hint
- [x] 16.4.3 Fallback to all facts if no keyword matches

### 16.5 Testing
- [x] 16.5.1 Unit tests for `AllFactsRetriever`
- [x] 16.5.2 Unit tests for `KeywordRetriever`
- [x] 16.5.3 Integration test: pipeline with custom retriever
