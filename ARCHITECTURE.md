# DRHP Drafting Agent — System Explanation

## How to Run

```bash
pip install -e .
export ANTHROPIC_API_KEY=your-key

python -m drhp_agent.run \
  --template templates/capital_structure.md \
  --evidence supporting_docs/PAS-3/ \
  --out out/
```

**Inputs used in sample run:**
- `templates/capital_structure.md` — template with typed slots and elaboration blocks
- `supporting_docs/PAS-3/Board Resolution Allotment of Shares.md` — board minutes
- `supporting_docs/PAS-3/List of Allottees.md` — allottee details with amounts
- `supporting_docs/PAS-3/PAS-3 Form.md` — ROC filing with capital structure data

**Output:** `out/capital_structure.md` — complete Capital Structure & Shareholding Pattern section with inline source citations and review flags.

## How Inputs Flow Through the System

```
Supporting Docs ──► EXTRACT (LLM x3) ──► FactStore (120 facts as JSON)
                                              │
Template ──► PARSE (regex) ──► 19 typed slots + 3 elaboration blocks
                                    │              │
                                    ▼              ▼
                              FILL (LLM x19)  ELABORATE (LLM x3)
                                    │              │
                                    ▼              ▼
                              VALIDATE (LLM x1) ──► 10 consistency issues
                                    │
                                    ▼
                              RENDER (no LLM) ──► capital_structure.md
```

**26 total LLM calls** (Claude Sonnet). Pipeline completes in ~5 minutes.

## The Template System

The template is a markdown file with two types of placeholders:

**Typed slots** for specific values — `{{type:id:hint}}`
```
| Equity Shares | {{integer:authorized_equity_shares:Number of authorized equity shares}} |
```
Types: `text`, `amount`, `integer`, `date`, `percentage`, `entity`.

**Elaboration blocks** for rich generated content — `{{elaborate:block_id:keyword:instructions}}`
```
{{elaborate:allotment_history:allotment:Generate a complete table of ALL share allotments...}}
```

The parser extracts **+/- 100 characters of surrounding template text** as context for each placeholder. This cross-line context tells the LLM where the value fits (which table row, which section heading), preventing duplicate headings and guiding format.

## What is Automated

| Step | Method | Output |
|------|--------|--------|
| Fact extraction from documents | LLM reads each doc, returns structured JSON | `fact_store.json` — 120 facts with keys, values, types, source locations |
| Slot filling | LLM matches facts to each template slot by type, hint, and context | `filled_slots.json` — 15 filled, 3 missing, 1 conflict |
| Elaboration | LLM generates tables/prose for each elaboration block using relevant facts | `elaborations.json` — allotment history, allottee details, shareholding pattern |
| Cross-document validation | LLM checks all facts for consistency, math errors, date mismatches | `validation.json` — 10 issues (name variations, format inconsistencies) |
| Source citations | Every value in the output has `[Source: filename]` tracing it to the original document | Inline in `capital_structure.md` |
| Review flagging | Missing data and conflicts are marked with `[[REQUIRES REVIEW: explanation]]` | `review_flags.md` — 8 items needing human attention |

## What is Left for Humans

- **Missing data:** The system found no incorporation date or initial authorized capital in the provided documents — these are flagged with `[[REQUIRES REVIEW]]` and a clear explanation of what's needed.
- **Conflicts:** When the same fact appears differently across documents (e.g., company name as "PVT LTD" vs "PRIVATE LIMITED"), the system flags it rather than guessing.
- **Validation judgment:** The system surfaces 10 consistency issues (date format variations, name capitalization differences) but does not auto-resolve them.
- **Legal review:** The output is a draft. Final legal language, regulatory compliance checks, and sign-off remain human responsibilities.

## Sample Output (Excerpt)

```markdown
## Authorized Share Capital

| Particulars | Number of Shares | Face Value | Amount |
|-------------|------------------|------------|--------|
| Equity Shares | 30,000 [Source: PAS-3 Form.md] | Rs. 10 [Source: Board Resolution...] | Rs. 3,00,000 [Source: PAS-3 Form.md] |

## Details of Allottees

| Sr. No. | Name | Address | Shares | Premium | Total Paid |
|---------|------|---------|--------|---------|------------|
| 1 | Mr. Rohit Sharma | 12/45, Sunrise Apartments, Sector-15, Rohini... | 192 | 7,850 | 15,09,120 |
| 2 | Mr. Suresh Sharma | 12/45, Sunrise Apartments, Sector-15, Rohini... | 192 | 7,850 | 15,09,120 |
| 3 | Sunrise Engineering Works Pvt. Ltd | 302 Lakshmi Tower, Ring Road... | 576 | 7,850 | 45,27,360 |

[Source: List of Allottees.md]
```

## Intermediate Artifacts

All intermediate representations are saved as structured JSON in `out/intermediate/`:

- **`fact_store.json`** — every extracted fact with `fact_id`, `key`, `value`, `value_type`, `confidence`, `doc_id`, and `location` (section/table/row/column)
- **`filled_slots.json`** — each slot's fill result with `status` (filled/missing/conflict), `value`, `source_facts`, `source_files`, and `confidence`
- **`elaborations.json`** — each elaboration block's generated markdown with source tracing
- **`validation.json`** — all consistency issues with severity, message, involved facts, and suggestions
- **`pipeline.log`** — structured log of every pipeline stage with timing

These artifacts provide full transparency into how raw documents became the final drafted section.
