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

---

## 1) Architecture

### Completed ✓
- [x] 1.1 Package skeleton: `core`, `md_template`, `ingest`, `retrieve`, `fill`, `render`, `validate`, `report`, `run`
- [x] 1.2 Module contracts (DTOs) in `core/contracts.py`
- [x] 1.3 Pipeline config and run manifest DTOs
- [x] 1.4 CLI entrypoint schema defined

### Pending
- [ ] 1.5 Implement pipeline orchestrator in `run/orchestrator.py`
- [ ] 1.6 Implement CLI in `run/cli.py` with single-command execution

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

### Pending
- [ ] 5.1 Load template markdown file
- [ ] 5.2 Detect slot markers: `{{slot_name}}` or `{{type:slot_name:hint}}`
- [ ] 5.3 Parse slot metadata from marker syntax
- [ ] 5.4 Build list of `SlotFillRequest` objects
- [ ] 5.5 Emit `out/intermediate/section_template.json`

---

## 6) Slot Filling (LLM-Based)

### Pending
- [ ] 6.1 For each slot, send `SlotFillRequest` + `FactStore` to LLM with SLOT_FILL_PROMPT
- [ ] 6.2 Parse LLM response into `SlotFillResult` DTO
- [ ] 6.3 Handle statuses: filled, missing, conflict, low_confidence
- [ ] 6.4 Collect all results into filled slots collection
- [ ] 6.5 Emit `out/intermediate/filled_slots.json`

---

## 7) Validation (LLM-Based)

### Pending
- [ ] 7.1 Send `FactStore` to LLM with VALIDATION_PROMPT
- [ ] 7.2 Parse validation issues from response
- [ ] 7.3 Check: same fact matches across documents
- [ ] 7.4 Check: mathematical consistency (totals = sum of parts)
- [ ] 7.5 Check: date consistency
- [ ] 7.6 Flag missing critical facts
- [ ] 7.7 Emit validation issues with severity levels

---

## 8) Section Rendering

### Pending
- [ ] 8.1 Send template + filled slots to LLM with SECTION_GENERATE_PROMPT
- [ ] 8.2 Ensure legal disclosure tone (not AI summary)
- [ ] 8.3 Add source citations: `[Source: filename]`
- [ ] 8.4 Insert `[[REQUIRES REVIEW: reason]]` for missing/conflicted slots
- [ ] 8.5 Emit `out/capital_structure.md`
- [ ] 8.6 Map each filled value to source facts
- [ ] 8.7 Emit `out/annotations.jsonl`
- [ ] 8.8 Collect all missing, conflict, low_confidence items
- [ ] 8.9 Group by severity
- [ ] 8.10 Emit `out/review_flags.md`

---

## 9) CLI and End-to-End Execution

### Pending
- [ ] 9.1 Single command: `python -m drhp_agent.run --template templates/capital_structure.md --evidence supporting_docs/PAS-3/ --out out/`
- [ ] 9.2 Print progress: extracting docs, filling slots, validating, rendering
- [ ] 9.3 Print summary: facts extracted, slots filled, slots missing, conflicts
- [ ] 9.4 Exit code: 0 = success, 1 = has review flags, 2 = critical error

---

## 10) Sample Data and Demo

### Completed ✓
- [x] 10.1 Copy `drhp_agent/PAS-3/` to `supporting_docs/PAS-3/`
- [x] 10.2 Create `templates/capital_structure.md` with DRHP structure and slot markers

### Pending
- [ ] 10.3 Run end-to-end and capture sample output
- [ ] 10.4 Document sample run in README with exact commands
- [ ] 10.5 Include sample outputs in repo

---

## 11) Testing

### Completed ✓
- [x] 11.1 Unit tests for core module (enums, DTOs, serializers) - 60 tests passing
- [x] 11.2 Unit tests for Fact DTOs and FactStore - 18 tests
- [x] 11.3 Unit tests for LLM response parsing - 12 tests
- [x] 11.4 Unit tests for DocumentLoader - 11 tests
- [x] 11.5 Unit tests for FactExtractor - 5 tests
- [x] 11.6 Integration tests for PAS-3 file loading - 2 tests

**Total: 113 tests passing**

### Pending
- [ ] 11.7 Integration test: PAS-3 extraction → fact_store.json (with live LLM)
- [ ] 11.8 Integration test: fact_store → filled_slots.json (with live LLM)
- [ ] 11.9 End-to-end test: full pipeline with sample data
- [ ] 11.10 Snapshot test for rendered output

---

## 12) Definition of Done

- [ ] 12.1 Single command runs end-to-end without error
- [ ] 12.2 `fact_store.json` shows all extracted facts with sources
- [ ] 12.3 `filled_slots.json` shows slot values with fact references
- [ ] 12.4 Output `capital_structure.md` looks like real DRHP section
- [ ] 12.5 Every fact has source citation in output
- [ ] 12.6 Missing data clearly marked with `[[REQUIRES REVIEW]]`
- [ ] 12.7 `review_flags.md` lists all items needing human attention
- [ ] 12.8 README explains how to run with sample data

---

## Deferred (Post-MVP)

- PDF to markdown converter
- Multi-section stitching
- Local LLM support (Ollama)
- Caching of LLM extractions
- Performance optimization
- Additional section templates (Objects, Risk Factors, etc.)
